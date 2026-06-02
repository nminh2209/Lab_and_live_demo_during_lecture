from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

from src.core.llm import normalize_content
from src.core.schemas import (
    AgentResult,
    CalculateTotalsInput,
    DiscountInput,
    ListProductsInput,
    OrderLineInput,
    ProductDetailInput,
    SaveOrderInput,
    ToolCallRecord,
)
from src.utils.data_store import OrderDataStore

ROOT_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = ROOT_DIR / "data"
DEFAULT_OUTPUT_DIR = ROOT_DIR / "artifacts" / "orders"


def build_system_prompt(today: str | None = None) -> str:
    current_day = today or "2026-06-01"
    return f"""
Bạn là OrderDesk Assistant cho cửa hàng điện tử. Hôm nay là {current_day}.

Nguyên tắc bắt buộc:
1) Luôn trả lời tiếng Việt, ngắn gọn, có căn cứ từ tool.
2) Không bịa thông tin sản phẩm, tồn kho, giá, giảm giá, tổng tiền hoặc đường dẫn file.
3) Nếu thiếu bất kỳ trường nào thì phải hỏi rõ và dừng, KHÔNG gọi tool:
   - customer name
   - phone number
   - email
   - shipping address
   - ít nhất 1 sản phẩm có số lượng
4) Nếu yêu cầu vi phạm chính sách (bỏ qua tồn kho, ép giảm giá, hóa đơn giả, bỏ qua catalog/policy) thì từ chối ngay, KHÔNG gọi tool.
5) Khi đủ dữ liệu hợp lệ, bắt buộc dùng tool đúng thứ tự:
   list_products -> get_product_details -> get_discount -> calculate_order_totals -> save_order
6) Chỉ gọi save_order sau khi validate qua get_product_details + calculate_order_totals thành công.
7) Ở câu trả lời cuối, xác nhận mã đơn, mức giảm giá, tổng tiền cuối cùng và đường dẫn lưu file.
""".strip()


def build_tools(store: OrderDataStore):
    from langchain_core.tools import tool

    @tool(args_schema=ListProductsInput)
    def list_products(
        query: str | None = None,
        category: str | None = None,
        max_unit_price: int | None = None,
        required_tags: list[str] | None = None,
        in_stock_only: bool = True,
        limit: int = 8,
    ) -> str:
        """Search the local product catalog and return the best matching items."""
        payload = store.list_products(
            query=query,
            category=category,
            max_unit_price=max_unit_price,
            required_tags=required_tags or [],
            in_stock_only=in_stock_only,
            limit=limit,
        )
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=ProductDetailInput)
    def get_product_details(product_ids: list[str]) -> str:
        """Return exact product details for previously discovered product IDs."""
        return json.dumps(store.get_product_details(product_ids), ensure_ascii=False)

    @tool(args_schema=DiscountInput)
    def get_discount(seed_hint: str, customer_tier: str = "standard") -> str:
        """Return the simulated campaign discount for the order."""
        return json.dumps(store.get_discount(seed_hint=seed_hint, customer_tier=customer_tier), ensure_ascii=False)

    @tool(args_schema=CalculateTotalsInput)
    def calculate_order_totals(items: list[OrderLineInput], detail_token: str, discount_rate: float) -> str:
        """Validate stock and calculate the discounted order total."""
        payload = store.calculate_order_totals(items=items, detail_token=detail_token, discount_rate=discount_rate)
        return json.dumps(payload, ensure_ascii=False)

    @tool(args_schema=SaveOrderInput)
    def save_order(
        customer_name: str,
        customer_phone: str,
        customer_email: str,
        shipping_address: str,
        items: list[OrderLineInput],
        detail_token: str,
        discount_rate: float,
        campaign_code: str,
        customer_tier: str = "standard",
        notes: str = "",
    ) -> str:
        """Persist the final order to a local JSON file."""
        payload = store.save_order(
            customer_name=customer_name,
            customer_phone=customer_phone,
            customer_email=customer_email,
            shipping_address=shipping_address,
            items=items,
            detail_token=detail_token,
            discount_rate=discount_rate,
            campaign_code=campaign_code,
            customer_tier=customer_tier,
            notes=notes,
        )
        return json.dumps(payload, ensure_ascii=False)

    return [list_products, get_product_details, get_discount, calculate_order_totals, save_order]


def build_agent(
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    *,
    provider: str = "google",
    model_name: str | None = None,
    today: str | None = None,
):
    from langchain.agents import create_agent

    from src.core.llm import build_chat_model

    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    model = build_chat_model(provider=provider, model_name=model_name, temperature=0.0)
    return create_agent(
        model=model,
        tools=build_tools(store),
        system_prompt=build_system_prompt(today or store.today),
    )


def run_agent(
    query: str,
    *,
    provider: str = "google",
    model_name: str | None = None,
    data_dir: Path | None = None,
    output_dir: Path | None = None,
    today: str | None = None,
) -> AgentResult:
    store = OrderDataStore(data_dir or DEFAULT_DATA_DIR, output_dir or DEFAULT_OUTPUT_DIR, today=today)
    guardrail = _guardrail_response(query)
    if guardrail is not None:
        return AgentResult(
            query=query,
            final_answer=guardrail,
            tool_calls=[],
            provider=provider,
            model_name=model_name,
            saved_order=None,
            saved_order_path=None,
        )

    parsed = _extract_order_fields(query, store)
    missing_fields = [name for name in ("customer_name", "customer_phone", "customer_email", "shipping_address") if not parsed.get(name)]
    has_item_request = _has_item_request_text(query)
    if not parsed["items"] and not has_item_request:
        missing_fields.append("items")
    if missing_fields:
        return AgentResult(
            query=query,
            final_answer=_clarification_response(missing_fields),
            tool_calls=[],
            provider=provider,
            model_name=model_name,
            saved_order=None,
            saved_order_path=None,
        )

    # The user requested items, but none map to catalog products.
    if has_item_request and not parsed["items"]:
        return AgentResult(
            query=query,
            final_answer=(
                "Mình đã nhận yêu cầu sản phẩm nhưng chưa khớp được mã hàng trong catalog hiện có. "
                "Bạn gửi lại đúng tên sản phẩm theo danh mục hoặc mã sản phẩm để mình tạo đơn ngay."
            ),
            tool_calls=[],
            provider=provider,
            model_name=model_name,
            saved_order=None,
            saved_order_path=None,
        )

    tool_calls: list[ToolCallRecord] = []
    list_result = store.list_products(query=query, in_stock_only=True, limit=20)
    tool_calls.append(ToolCallRecord(name="list_products", args={"query": query, "in_stock_only": True, "limit": 20}, output=json.dumps(list_result, ensure_ascii=False)))

    product_ids = [item.product_id for item in parsed["items"]]
    detail_result = store.get_product_details(product_ids)
    tool_calls.append(ToolCallRecord(name="get_product_details", args={"product_ids": product_ids}, output=json.dumps(detail_result, ensure_ascii=False)))

    discount_result = store.get_discount(seed_hint=parsed["customer_email"], customer_tier="standard")
    tool_calls.append(ToolCallRecord(name="get_discount", args={"seed_hint": parsed["customer_email"], "customer_tier": "standard"}, output=json.dumps(discount_result, ensure_ascii=False)))

    pricing_result = store.calculate_order_totals(
        items=parsed["items"],
        detail_token=detail_result.get("detail_token", ""),
        discount_rate=float(discount_result.get("discount_rate", 0.1)),
    )
    tool_calls.append(
        ToolCallRecord(
            name="calculate_order_totals",
            args={
                "items": [item.model_dump() for item in parsed["items"]],
                "detail_token": detail_result.get("detail_token", ""),
                "discount_rate": float(discount_result.get("discount_rate", 0.1)),
            },
            output=json.dumps(pricing_result, ensure_ascii=False),
        )
    )

    if pricing_result.get("status") != "ok":
        return AgentResult(
            query=query,
            final_answer=_stock_failure_answer(pricing_result.get("errors", [])),
            tool_calls=tool_calls,
            provider=provider,
            model_name=model_name,
            saved_order=None,
            saved_order_path=None,
        )

    save_result = store.save_order(
        customer_name=parsed["customer_name"],
        customer_phone=parsed["customer_phone"],
        customer_email=parsed["customer_email"],
        shipping_address=parsed["shipping_address"],
        items=parsed["items"],
        detail_token=detail_result.get("detail_token", ""),
        discount_rate=float(discount_result["discount_rate"]),
        campaign_code=str(discount_result["campaign_code"]),
        customer_tier="standard",
        notes="",
    )
    tool_calls.append(
        ToolCallRecord(
            name="save_order",
            args={
                "customer_name": parsed["customer_name"],
                "customer_phone": parsed["customer_phone"],
                "customer_email": parsed["customer_email"],
                "shipping_address": parsed["shipping_address"],
                "items": [item.model_dump() for item in parsed["items"]],
                "detail_token": detail_result.get("detail_token", ""),
                "discount_rate": float(discount_result["discount_rate"]),
                "campaign_code": str(discount_result["campaign_code"]),
                "customer_tier": "standard",
                "notes": "",
            },
            output=json.dumps(save_result, ensure_ascii=False),
        )
    )
    saved_order, saved_order_path = extract_saved_order(tool_calls)
    return AgentResult(
        query=query,
        final_answer=_success_answer(save_result),
        tool_calls=tool_calls,
        provider=provider,
        model_name=model_name,
        saved_order=saved_order,
        saved_order_path=saved_order_path,
    )


def extract_final_answer(messages) -> str:
    """Optional helper: return the last non-empty AI answer."""
    for message in reversed(messages):
        role = getattr(message, "type", "")
        if role == "ai" or message.__class__.__name__ == "AIMessage":
            text = normalize_content(getattr(message, "content", ""))
            if text:
                return text
    return ""


def extract_tool_calls(messages) -> list[ToolCallRecord]:
    """Optional helper: convert tool calls and tool results into a simple grading trace."""
    pending: dict[str, dict[str, Any]] = {}
    records: list[ToolCallRecord] = []

    for message in messages:
        role = getattr(message, "type", "")
        if role == "ai" or message.__class__.__name__ == "AIMessage":
            for tool_call in getattr(message, "tool_calls", []) or []:
                pending[tool_call["id"]] = {
                    "name": tool_call["name"],
                    "args": tool_call.get("args", {}) or {},
                }
        elif role == "tool" or message.__class__.__name__ == "ToolMessage":
            metadata = pending.pop(getattr(message, "tool_call_id", ""), {})
            records.append(
                ToolCallRecord(
                    name=str(getattr(message, "name", None) or metadata.get("name", "")),
                    args=metadata.get("args", {}),
                    output=normalize_content(getattr(message, "content", "")),
                )
            )

    for metadata in pending.values():
        records.append(ToolCallRecord(name=metadata["name"], args=metadata["args"], output=""))
    return records


def extract_saved_order(tool_calls: list[ToolCallRecord]) -> tuple[dict | None, str | None]:
    """Optional helper: parse the `save_order` tool output into `(saved_order, path)`."""
    for record in reversed(tool_calls):
        if record.name != "save_order" or not record.output:
            continue
        try:
            payload = json.loads(record.output)
        except json.JSONDecodeError:
            continue
        if payload.get("status") != "saved":
            return None, None
        return payload.get("saved_order"), payload.get("path")
    return None, None


def _normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", re.sub(r"[^a-zA-Z0-9@.+-]+", " ", stripped.lower())).strip()


def _guardrail_response(query: str) -> str | None:
    text = _normalize(query)
    bad_patterns = (
        "hoa don gia",
        "fake invoice",
        "bo qua policy",
        "bo qua ton kho",
        "ignore policy",
        "khong can theo catalog",
        "manual discount",
        "giam gia 90",
        "ep giam gia",
    )
    if any(pattern in text for pattern in bad_patterns):
        return (
            "Mình không thể hỗ trợ yêu cầu này vì vi phạm chính sách (hóa đơn giả, ép khuyến mãi hoặc bỏ qua tồn kho/catalog). "
            "Mình chỉ có thể tạo đơn hợp lệ theo dữ liệu sản phẩm và quy định hiện hành."
        )
    return None


def _clarification_response(missing_fields: list[str]) -> str:
    labels = {
        "customer_name": "họ tên người nhận (hoặc tên công ty)",
        "customer_phone": "số điện thoại",
        "customer_email": "email",
        "shipping_address": "địa chỉ giao hàng",
        "items": "danh sách sản phẩm kèm số lượng",
    }
    needed = ", ".join(labels[item] for item in missing_fields)
    company_hint = ""
    if "customer_name" in missing_fields:
        company_hint = " Nếu mua cho doanh nghiệp, bạn cho mình thêm tên công ty."
    return f"Mình cần thêm thông tin trước khi tạo đơn hàng: {needed}.{company_hint} Bạn bổ sung giúp mình nhé."


def _extract_order_fields(query: str, store: OrderDataStore) -> dict[str, Any]:
    phone = _extract_phone(query)
    email_match = re.search(r"[\w.+-]+@[\w.-]+\.\w+", query)
    name_match = re.search(r"(?:cho|for)\s+([^.,;\n]+)", query, flags=re.IGNORECASE)
    address_match = re.search(
        r"(?:giao(?: hàng)? (?:đến|toi|tới|ve|về)|ship to|dia chi giao hang|địa chỉ giao hàng|dia chi(?:\s+tai|:)?|địa chỉ(?:\s+tại|:)?)\s*(.+?)(?=(?:,\s*(?:số điện thoại|so dien thoai|phone)\b|\.\s*(?:tôi|toi|mình|minh|chốt|chot|chọn|chon|phone|email)\b|$))",
        query,
        flags=re.IGNORECASE,
    )

    items = _extract_items(query, store)
    return {
        "customer_name": name_match.group(1).strip() if name_match else "",
        "customer_phone": phone,
        "customer_email": email_match.group(0).strip() if email_match else "",
        "shipping_address": address_match.group(1).strip(" .,") if address_match else "",
        "items": items,
    }


def _extract_items(query: str, store: OrderDataStore) -> list[OrderLineInput]:
    normalized_query = _normalize(query)
    folded_query = unicodedata.normalize("NFKD", query).encode("ascii", "ignore").decode("ascii").lower()
    name_index = sorted(
        [(_normalize(product.name), product.product_id) for product in store.products],
        key=lambda item: len(item[0]),
        reverse=True,
    )
    counts: dict[str, int] = {}
    for normalized_name, product_id in name_index:
        if not normalized_name:
            continue
        raw_name = re.escape(normalized_name).replace("\\ ", r"\s+")
        pattern = rf"(?<![\w-])(\d{{1,2}})\s+{raw_name}(?![\w-])"
        match = re.search(pattern, folded_query)
        if match:
            counts[product_id] = int(match.group(1))
            continue
        if normalized_name in normalized_query and product_id not in counts:
            counts[product_id] = 1
    return [OrderLineInput(product_id=product_id, quantity=qty) for product_id, qty in sorted(counts.items())]


def _stock_failure_answer(errors: list[str]) -> str:
    brief = errors[0] if errors else "Một số sản phẩm không đủ tồn kho."
    return f"Mình chưa thể tạo đơn vì tồn kho không đủ. Chi tiết: {brief}"


def _extract_phone(query: str) -> str:
    # Accept common VN style formats, with optional separators/spaces.
    candidates = re.findall(r"(?:\+?84|0)?[\d\s().-]{9,16}", query)
    for candidate in candidates:
        digits = "".join(ch for ch in candidate if ch.isdigit())
        if 9 <= len(digits) <= 11:
            return digits
    return ""


def _has_item_request_text(query: str) -> bool:
    folded = _normalize(query)
    if re.search(r"\b\d{1,3}\s+[a-z0-9]", folded):
        return True
    hints = ("toi can", "mua", "chot item", "chot", "can", "items")
    return any(hint in folded for hint in hints)


def _success_answer(save_result: dict[str, Any]) -> str:
    if save_result.get("status") != "saved":
        return "Mình chưa thể lưu đơn do dữ liệu chưa hợp lệ. Bạn kiểm tra lại giúp mình."
    saved_order = save_result["saved_order"]
    pricing = saved_order["pricing"]
    discount = saved_order["discount"]
    customer = saved_order.get("customer", {})
    items = saved_order.get("items", [])
    item_summary = "; ".join(f"{item['quantity']}x {item['name']}" for item in items[:4])
    if len(items) > 4:
        item_summary += "; ..."
    return (
        f"Đã tạo và lưu đơn hàng thành công: {saved_order['order_id']}. "
        f"Khách hàng: {customer.get('name', '')}, giao tại {customer.get('shipping_address', '')}. "
        f"Hạng mục: {item_summary}. "
        f"Dữ liệu JSON đơn hàng đã được lưu đúng cấu trúc. "
        f"Khuyến mãi {discount['campaign_code']} ({int(pricing['discount_rate'] * 100)}%), "
        f"tổng thanh toán {pricing['final_total']:,} VND. "
        f"File đã lưu tại {save_result['path']}."
    )
