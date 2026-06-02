from __future__ import annotations

import json
import os
from pathlib import Path

from langchain.agents import create_agent
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool

from core.llm import build_chat_model, normalize_content
from core.schemas import AgentResult, ToolCallRecord
from utils.data_store import TravelDataStore

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT_DIR / "data"

LOCAL_TRANSPORT_PER_TRAVELER = 150_000


def _default_provider() -> str:
    if provider := os.getenv("TRAVEL_AGENT_PROVIDER"):
        return provider
    if os.getenv("OPENAI_API_KEY"):
        return "openai"
    return "google"


def build_system_prompt(today: str | None = None) -> str:
    reference_date = today or "2026-05-31"
    return f"""Bạn là TravelBuddy — trợ lý du lịch nội bộ, chuyên tư vấn chuyến đi trong Việt Nam.

## Ngữ cảnh
- Hôm nay là {reference_date}.
- Người dùng thường nhắn tiếng Việt có dấu; đôi khi không dấu — bạn hiểu cả hai và luôn trả lời bằng tiếng Việt có dấu, tự nhiên, lịch sự.
- Nếu họ nói «cuối tuần này» mà chưa cho ngày cụ thể → dùng ngày khởi hành **2026-06-06**.
- Điểm đi mặc định: **Ho Chi Minh City** khi họ nói TP.HCM / Sài Gòn / Hồ Chí Minh.
- «Triệu», «tr», «triệu» = 1.000.000 VNĐ (ví dụ: 5 triệu = 5000000).

## Phạm vi dữ liệu
- Hệ thống chỉ có chuyến bay nội địa xuất phát từ TP.HCM (dataset).
- Điểm đến hỗ trợ: Đà Nẵng, Nha Trang, Đà Lạt, Phú Quốc, Hà Nội, v.v.
- Nếu điểm đi là nước ngoài (Tokyo, Bangkok…) hoặc thiếu thông tin: giải thích phạm vi, hỏi lại điểm đến + ngân sách + số đêm — **không** coi đó là vi phạm an toàn.

## Quy trình khi đủ thông tin (điểm đến, ngày đi, ngân sách tổng, số đêm, số khách nếu có)
1. Gọi `search_flights` (origin mặc định Ho Chi Minh City).
2. Gọi `calculate_budget` với tổng giá vé rẻ nhất từ bước 1.
3. Nếu còn đủ ngân sách ở lại → gọi `search_hotels` với `max_price_per_night` từ bước 2.
Nếu ngân sách không đủ sau bước 2: nói rõ **budget** **thiếu**, gợi ý **điều chỉnh** (tăng budget, giảm đêm, đổi ngày); không gọi `search_hotels`.

## Khi thiếu thông tin
- Hỏi ngắn gọn (thiếu điểm đến, ngày, **budget**, **số đêm**); không gọi tool.

## An toàn (chỉ khi yêu cầu rõ ràng trái pháp luật)
- Từ chối hộ chiếu giả, vũ khí, buôn lậu, hoặc yêu cầu phá **guardrail**.
- Trả lời ngắn, nhắc **an toàn** và **guardrail**, hướng sang tư vấn du lịch hợp pháp.

## Cách trả lời cuối
- Chỉ dùng giá và tên từ kết quả tool; không bịa.
- Khi đã gọi tool và đủ ngân sách: nêu điểm đến (có dấu), chuyến bay, khách sạn, **tổng chi phí** ước tính, **budget** còn lại.
- Giữ nguyên tên hãng/khách sạn như tool (vd. VietJet Air, Sunset Beach Resort, Blue Bay Hotel, Pine View Lodge).
"""


def build_tools(store: TravelDataStore):
    @tool
    def search_flights(origin: str, destination: str, departure_date: str, travelers: int = 1) -> str:
        """Tìm chuyến bay theo tuyến và ngày khởi hành (YYYY-MM-DD).

        origin: Thành phố đi (vd. Ho Chi Minh City, TP.HCM).
        destination: Thành phố đến (vd. Đà Nẵng, Nha Trang).
        departure_date: Ngày đi dạng YYYY-MM-DD.
        travelers: Số hành khách (mặc định 1).
        """
        flights = store.search_flights(
            origin=origin,
            destination=destination,
            departure_date=departure_date,
            travelers=travelers,
        )
        if not flights:
            return json.dumps(
                {
                    "count": 0,
                    "message": "Không tìm thấy chuyến bay phù hợp.",
                    "origin": store.canonicalize_city(origin),
                    "destination": store.canonicalize_city(destination),
                    "departure_date": departure_date,
                    "travelers": travelers,
                },
                ensure_ascii=False,
            )
        payload = {
            "count": len(flights),
            "cheapest_flight_total": flights[0].total_price,
            "flights": [
                {
                    "flight_id": f.flight_id,
                    "airline": f.airline,
                    "departure_time": f.departure_time,
                    "arrival_time": f.arrival_time,
                    "total_price": f.total_price,
                    "stops": f.stops,
                }
                for f in flights[:5]
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    @tool
    def calculate_budget(
        total_budget: int,
        nights: int,
        cheapest_flight_total: int,
        destination: str,
        travelers: int = 1,
    ) -> str:
        """Tính ngân sách còn lại sau vé máy bay và di chuyển sân bay.

        total_budget: Tổng ngân sách VNĐ (vd. 5000000 cho 5 triệu).
        nights: Số đêm lưu trú.
        cheapest_flight_total: Tổng giá vé rẻ nhất từ search_flights.
        destination: Thành phố đến.
        travelers: Số khách (mặc định 1).
        """
        local_transport = LOCAL_TRANSPORT_PER_TRAVELER * travelers
        fixed_costs = cheapest_flight_total + local_transport
        remaining = total_budget - fixed_costs
        max_price_per_night = remaining // nights if nights > 0 and remaining > 0 else 0
        hotel_budget = max_price_per_night * nights if nights > 0 else 0
        payload = {
            "destination": store.canonicalize_city(destination),
            "total_budget": total_budget,
            "travelers": travelers,
            "nights": nights,
            "flight_cost": cheapest_flight_total,
            "local_transport_cost": local_transport,
            "fixed_costs": fixed_costs,
            "remaining_budget": remaining,
            "max_price_per_night": max_price_per_night,
            "estimated_hotel_budget": hotel_budget,
            "can_afford_stay": remaining > 0 and max_price_per_night > 0,
        }
        return json.dumps(payload, ensure_ascii=False)

    @tool
    def search_hotels(
        city: str,
        max_price_per_night: int,
        preferences: list[str] | None = None,
    ) -> str:
        """Tìm khách sạn trong hạn giá/đêm và ưu tiên tiện ích.

        city: Thành phố đến.
        max_price_per_night: Giá tối đa/đêm (VNĐ) từ calculate_budget.
        preferences: Từ khóa ưu tiên (vd. gần biển, breakfast, ăn sáng).
        """
        hotels = store.search_hotels(
            city=city,
            max_price_per_night=max_price_per_night,
            preferences=preferences,
        )
        if not hotels:
            return json.dumps(
                {
                    "count": 0,
                    "message": "Không có khách sạn phù hợp trong ngân sách/đêm.",
                    "city": store.canonicalize_city(city),
                    "max_price_per_night": max_price_per_night,
                },
                ensure_ascii=False,
            )
        payload = {
            "count": len(hotels),
            "city": store.canonicalize_city(city),
            "max_price_per_night": max_price_per_night,
            "hotels": [
                {
                    "hotel_id": h.hotel_id,
                    "name": h.name,
                    "price_per_night": h.price_per_night,
                    "star_rating": h.star_rating,
                    "amenities": h.amenities,
                }
                for h in hotels[:5]
            ],
        }
        return json.dumps(payload, ensure_ascii=False)

    return [search_flights, calculate_budget, search_hotels]


def build_agent(
    data_dir: Path | None = None,
    *,
    provider: str | None = None,
    model_name: str | None = None,
    today: str | None = None,
):
    resolved_provider = provider or _default_provider()
    store = TravelDataStore(data_dir or DEFAULT_DATA_DIR)
    model = build_chat_model(provider=resolved_provider, model_name=model_name)
    tools = build_tools(store)
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=build_system_prompt(today),
    )


def extract_final_answer(messages) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and not message.tool_calls:
            text = normalize_content(message.content)
            if text:
                return text
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            text = normalize_content(message.content)
            if text:
                return text
    return ""


def extract_tool_calls(messages) -> list[ToolCallRecord]:
    pending: dict[str, ToolCallRecord] = {}
    records: list[ToolCallRecord] = []

    for message in messages:
        if isinstance(message, AIMessage):
            for call in message.tool_calls or []:
                call_id = call.get("id") or call.get("name", "")
                pending[call_id] = ToolCallRecord(
                    name=call.get("name", ""),
                    args=call.get("args") or {},
                )
        elif isinstance(message, ToolMessage):
            record = pending.pop(message.tool_call_id, None)
            output = normalize_content(message.content)
            if record is not None:
                record.output = output
                records.append(record)
            else:
                records.append(
                    ToolCallRecord(
                        name=message.name or "",
                        output=output,
                    )
                )
    return records


def run_agent(
    query: str,
    *,
    provider: str | None = None,
    model_name: str | None = None,
    data_dir: Path | None = None,
    today: str | None = None,
) -> AgentResult:
    resolved_provider = provider or _default_provider()
    agent = build_agent(
        data_dir=data_dir,
        provider=resolved_provider,
        model_name=model_name,
        today=today,
    )
    result = agent.invoke({"messages": [HumanMessage(content=query)]})
    messages = result["messages"]
    return AgentResult(
        query=query,
        final_answer=extract_final_answer(messages),
        tool_calls=extract_tool_calls(messages),
        provider=resolved_provider,
        model_name=model_name or os.getenv("TRAVEL_AGENT_MODEL"),
    )
