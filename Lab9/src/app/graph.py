from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path
from typing import Any, Literal

_CUSTOMER_ID_RE = re.compile(r"\bC\d{3}\b", re.IGNORECASE)
_ORDER_ID_RE = re.compile(r"\b\d{4}\b")

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from app.config import Settings
from app.data_access import ShoppingDataStore, build_data_tools
from app.prompts import (
    DATA_WORKER_PROMPT,
    POLICY_WORKER_PROMPT,
    RESPONSE_WORKER_PROMPT,
    SUPERVISOR_PROMPT,
)
from app.state import ShoppingState
from app.utils import (
    dump_json,
    extract_json_payload,
    get_last_ai_content,
    list_worker_tools,
    serialize_message,
    timestamp_utc,
)
from provider import get_chat_model
from rag.embeddings import SentenceTransformerEmbeddings
from rag.vector_store import ChromaPolicyStore, build_policy_search_tool


RouteName = Literal["policy", "data", "response"]


class ShoppingAssistant:
    """Multi-agent shopping assistant built with LangGraph."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or Settings.load()
        self.model = get_chat_model(self.settings)
        self.data_store = ShoppingDataStore(self.settings.orders_path)
        self.embedding_model = SentenceTransformerEmbeddings(self.settings.embedding_model_name)
        self.policy_store = ChromaPolicyStore(
            persist_directory=self.settings.chroma_dir,
            embedding_model=self.embedding_model,
        )
        self.policy_store.ensure_index(self.settings.policy_path)

        self.policy_tool = build_policy_search_tool(self.policy_store, self.settings.top_k)
        self.data_tools = build_data_tools(self.data_store)
        self.policy_agent = create_react_agent(
            self.model,
            tools=[self.policy_tool],
            prompt=SystemMessage(content=POLICY_WORKER_PROMPT),
        )
        self.data_agent = create_react_agent(
            self.model,
            tools=self.data_tools,
            prompt=SystemMessage(content=DATA_WORKER_PROMPT),
        )
        self.graph = build_graph(self.model, self.policy_agent, self.data_agent)

    def ask(
        self,
        question: str,
        trace_file: Path | None = None,
        rebuild_index: bool = False,
    ) -> dict[str, Any]:
        if rebuild_index:
            self.policy_store.rebuild(self.settings.policy_path)

        initial_state: ShoppingState = {
            "question": question,
            "trace": [],
        }
        final_state = self.graph.invoke(initial_state)
        payload = {
            "question": question,
            "route": final_state.get("route", {}),
            "policy_result": final_state.get("policy_result", {}),
            "data_result": final_state.get("data_result", {}),
            "final_answer": final_state.get("final_answer", ""),
            "trace": final_state.get("trace", []),
        }

        if trace_file is not None:
            trace_file.parent.mkdir(parents=True, exist_ok=True)
            trace_file.write_text(dump_json(payload), encoding="utf-8")

        return payload

    def run_batch(
        self,
        test_file: Path,
        output_dir: Path,
        rebuild_index: bool = False,
    ) -> dict[str, Any]:
        cases = json.loads(test_file.read_text(encoding="utf-8"))
        output_dir.mkdir(parents=True, exist_ok=True)
        results: list[dict[str, Any]] = []

        for index, case in enumerate(cases, start=1):
            question = case["question"]
            trace_file = output_dir / f"{case.get('id', f'case_{index:02d}')}.json"
            payload = self.ask(question, trace_file=trace_file, rebuild_index=rebuild_index and index == 1)
            rebuild_index = False

            actual_route = _route_labels(payload.get("route", {}))
            expected_route = case.get("expected_route", [])
            final_answer = payload.get("final_answer", "")
            actual_status = _infer_status(final_answer, payload)

            results.append(
                {
                    "id": case.get("id"),
                    "question": question,
                    "expected_route": expected_route,
                    "actual_route": actual_route,
                    "route_match": actual_route == expected_route,
                    "expected_status": case.get("expected_status"),
                    "actual_status": actual_status,
                    "status_match": actual_status == case.get("expected_status"),
                    "expected_contains": case.get("expected_contains", []),
                    "contains_match": all(
                        token.lower() in final_answer.lower()
                        for token in case.get("expected_contains", [])
                    ),
                    "final_answer": final_answer,
                    "trace_file": str(trace_file),
                }
            )

        summary = {
            "generated_at": timestamp_utc(),
            "total": len(results),
            "route_matches": sum(1 for item in results if item["route_match"]),
            "status_matches": sum(1 for item in results if item["status_match"]),
            "contains_matches": sum(
                1
                for item in results
                if not item["expected_contains"] or item["contains_match"]
            ),
            "results": results,
        }
        summary_path = output_dir / "summary.json"
        summary_path.write_text(dump_json(summary), encoding="utf-8")
        return summary


def build_graph(model: Any, policy_agent: Any, data_agent: Any) -> Any:
    workflow = StateGraph(ShoppingState)
    workflow.add_node("supervisor", partial(supervisor_node, model=model))
    workflow.add_node("worker_1_policy", partial(worker_1_policy_node, policy_agent=policy_agent))
    workflow.add_node("worker_2_data", partial(worker_2_data_node, data_agent=data_agent))
    workflow.add_node("worker_3_response", partial(worker_3_response_node, model=model))

    workflow.add_edge(START, "supervisor")
    workflow.add_conditional_edges(
        "supervisor",
        route_after_supervisor,
        {
            "policy": "worker_1_policy",
            "data": "worker_2_data",
            "response": "worker_3_response",
        },
    )
    workflow.add_conditional_edges(
        "worker_2_data",
        route_after_data,
        {
            "policy": "worker_1_policy",
            "response": "worker_3_response",
        },
    )
    workflow.add_edge("worker_1_policy", "worker_3_response")
    workflow.add_edge("worker_3_response", END)
    return workflow.compile()


def supervisor_node(state: ShoppingState, model: Any) -> dict[str, Any]:
    question = state["question"]
    response = model.invoke(
        [
            SystemMessage(content=SUPERVISOR_PROMPT),
            HumanMessage(content=question),
        ]
    )
    route = extract_json_payload(str(response.content))
    if not route:
        route = {
            "status": "ok",
            "needs_policy": True,
            "needs_data": False,
            "clarification_question": None,
        }
    route = _normalize_route(question, route)

    return {
        "route": route,
        "trace": [
            {
                "step": "supervisor",
                "timestamp": timestamp_utc(),
                "output": route,
            }
        ],
    }


def worker_1_policy_node(state: ShoppingState, policy_agent: Any) -> dict[str, Any]:
    question = state["question"]
    agent_result = policy_agent.invoke({"messages": [HumanMessage(content=question)]})
    messages = agent_result["messages"]
    policy_result = extract_json_payload(get_last_ai_content(messages))
    if not policy_result:
        policy_result = {
            "status": "ok",
            "summary": get_last_ai_content(messages),
            "facts": [],
            "citations": [],
        }

    return {
        "policy_result": policy_result,
        "trace": [
            {
                "step": "worker_1_policy",
                "timestamp": timestamp_utc(),
                "tool_calls": list_worker_tools(messages),
                "messages": [serialize_message(message) for message in messages[-6:]],
                "output": policy_result,
            }
        ],
    }


def worker_2_data_node(state: ShoppingState, data_agent: Any) -> dict[str, Any]:
    question = state["question"]
    agent_result = data_agent.invoke({"messages": [HumanMessage(content=question)]})
    messages = agent_result["messages"]
    data_result = extract_json_payload(get_last_ai_content(messages))
    if not data_result:
        data_result = {
            "status": "ok",
            "summary": get_last_ai_content(messages),
            "facts": [],
            "missing_fields": [],
            "not_found_entities": [],
        }

    return {
        "data_result": data_result,
        "trace": [
            {
                "step": "worker_2_data",
                "timestamp": timestamp_utc(),
                "tool_calls": list_worker_tools(messages),
                "messages": [serialize_message(message) for message in messages[-8:]],
                "output": data_result,
            }
        ],
    }


def worker_3_response_node(state: ShoppingState, model: Any) -> dict[str, Any]:
    context = {
        "question": state.get("question", ""),
        "route": state.get("route", {}),
        "policy_result": state.get("policy_result", {}),
        "data_result": state.get("data_result", {}),
    }
    response = model.invoke(
        [
            SystemMessage(content=RESPONSE_WORKER_PROMPT),
            HumanMessage(content=dump_json(context)),
        ]
    )
    final_answer = str(response.content).strip()
    return {
        "final_answer": final_answer,
        "trace": [
            {
                "step": "worker_3_response",
                "timestamp": timestamp_utc(),
                "output": final_answer,
            }
        ],
    }


def route_after_supervisor(state: ShoppingState) -> RouteName:
    route = state.get("route", {})
    if route.get("status") == "clarification_needed":
        return "response"

    needs_policy = bool(route.get("needs_policy"))
    needs_data = bool(route.get("needs_data"))

    if needs_data:
        return "data"
    if needs_policy:
        return "policy"
    return "response"


def route_after_data(state: ShoppingState) -> RouteName:
    route = state.get("route", {})
    if route.get("needs_policy"):
        return "policy"
    return "response"


def _normalize_route(question: str, route: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(route)
    lowered = question.lower()
    customer_ids = _CUSTOMER_ID_RE.findall(question)
    order_ids = _ORDER_ID_RE.findall(question)
    has_customer = bool(customer_ids)
    has_order = bool(order_ids)

    return_keywords = any(
        keyword in lowered
        for keyword in (
            "hoàn trả",
            "hoan tra",
            "trả hàng",
            "tra hang",
            "đổi trả",
            "doi tra",
            "từ chối nhận",
            "tu choi nhan",
            "cửa sổ trả",
            "cua so tra",
        )
    )
    voucher_keywords = "voucher" in lowered or "mã" in lowered or "ma " in lowered
    customer_quota_keywords = any(
        keyword in lowered
        for keyword in ("tối đa", "toi da", "quota", "mỗi tháng", "moi thang", "hạng")
    )

    if has_customer or has_order:
        normalized["status"] = "ok"
        normalized["clarification_question"] = None
        normalized["needs_data"] = True

        if has_customer and voucher_keywords and not has_order:
            normalized["needs_policy"] = False
        elif has_customer and customer_quota_keywords and not has_order and "policy" not in lowered:
            normalized["needs_policy"] = False
        elif has_order and return_keywords:
            normalized["needs_policy"] = True
        elif "policy" in lowered and has_order:
            normalized["needs_policy"] = True

    if not has_customer and not has_order:
        personal_keywords = any(
            keyword in lowered for keyword in ("của tôi", "cua toi", "my ", "của mình")
        )
        if personal_keywords and normalized.get("status") != "clarification_needed":
            normalized["status"] = "clarification_needed"
            normalized["needs_policy"] = False
            normalized["needs_data"] = False
            normalized["clarification_question"] = normalized.get(
                "clarification_question",
                "Vui lòng cung cấp mã đơn hàng hoặc mã khách hàng để tra cứu.",
            )

    return normalized


def _route_labels(route: dict[str, Any]) -> list[str]:
    if route.get("status") == "clarification_needed":
        return []
    labels: list[str] = []
    if route.get("needs_data"):
        labels.append("data")
    if route.get("needs_policy"):
        labels.append("policy")
    return labels


def _infer_status(final_answer: str, payload: dict[str, Any]) -> str:
    answer = final_answer.lower()
    if "status: clarification_needed" in answer:
        return "clarification_needed"
    if "status: not_found" in answer:
        return "not_found"

    data_result = payload.get("data_result", {})
    if data_result.get("status") == "not_found":
        return "not_found"
    if (
        data_result.get("status") == "clarification_needed"
        and payload.get("route", {}).get("status") == "clarification_needed"
    ):
        return "clarification_needed"
    if payload.get("route", {}).get("status") == "clarification_needed":
        return "clarification_needed"
    return "ok"
