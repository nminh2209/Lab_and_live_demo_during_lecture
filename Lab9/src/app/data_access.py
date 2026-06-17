from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from langchain_core.tools import tool


class ShoppingDataStore:
    """Mock-data lookup with pre-built indexes."""

    def __init__(self, json_path: Path) -> None:
        with json_path.open(encoding="utf-8") as handle:
            data = json.load(handle)

        self.metadata: dict[str, Any] = data["metadata"]
        self.customers: list[dict[str, Any]] = data["customers"]
        self.orders: list[dict[str, Any]] = data["orders"]
        self.vouchers: list[dict[str, Any]] = data["vouchers"]

        self.customer_by_id: dict[str, dict[str, Any]] = {
            customer["customer_id"]: customer for customer in self.customers
        }
        self.order_by_id: dict[str, dict[str, Any]] = {
            order["order_id"]: order for order in self.orders
        }

        self.orders_by_customer_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for order in self.orders:
            self.orders_by_customer_id[order["customer_id"]].append(order)
        for customer_id, customer_orders in self.orders_by_customer_id.items():
            self.orders_by_customer_id[customer_id] = sorted(
                customer_orders,
                key=lambda item: item.get("created_at", ""),
                reverse=True,
            )

        self.vouchers_by_customer_id: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for voucher in self.vouchers:
            self.vouchers_by_customer_id[voucher["customer_id"]].append(voucher)

    def get_customer_by_id(self, customer_id: str) -> dict[str, Any]:
        customer = self.customer_by_id.get(customer_id)
        if customer is None:
            return {"status": "not_found", "customer_id": customer_id}
        return {"status": "ok", "customer": customer}

    def get_orders_by_customer_id(self, customer_id: str, limit: int = 10) -> dict[str, Any]:
        if customer_id not in self.customer_by_id:
            return {"status": "not_found", "customer_id": customer_id}
        orders = self.orders_by_customer_id.get(customer_id, [])[:limit]
        return {
            "status": "ok",
            "customer_id": customer_id,
            "count": len(orders),
            "orders": orders,
        }

    def get_order_detail_by_order_id(self, order_id: str) -> dict[str, Any]:
        order = self.order_by_id.get(order_id)
        if order is None:
            return {"status": "not_found", "order_id": order_id}
        return {"status": "ok", "order": order}

    def get_vouchers_by_customer_id(
        self,
        customer_id: str,
        only_active: bool = False,
    ) -> dict[str, Any]:
        if customer_id not in self.customer_by_id:
            return {"status": "not_found", "customer_id": customer_id}

        vouchers = list(self.vouchers_by_customer_id.get(customer_id, []))
        if only_active:
            vouchers = [
                voucher
                for voucher in vouchers
                if voucher.get("status") == "active" and voucher.get("remaining_uses", 0) > 0
            ]

        return {
            "status": "ok",
            "customer_id": customer_id,
            "count": len(vouchers),
            "vouchers": vouchers,
        }


def build_data_tools(store: ShoppingDataStore) -> list:
    @tool
    def get_customer_by_id(customer_id: str) -> dict[str, Any]:
        """Look up a customer profile by customer_id such as C001."""
        return store.get_customer_by_id(customer_id)

    @tool
    def get_orders_by_customer_id(customer_id: str, limit: int = 10) -> dict[str, Any]:
        """List recent orders for a customer_id, newest first."""
        return store.get_orders_by_customer_id(customer_id, limit=limit)

    @tool
    def get_order_detail_by_order_id(order_id: str) -> dict[str, Any]:
        """Look up one order by order_id such as 1971 or 2058."""
        return store.get_order_detail_by_order_id(order_id)

    @tool
    def get_vouchers_by_customer_id(customer_id: str, only_active: bool = False) -> dict[str, Any]:
        """List vouchers assigned to a customer. Set only_active=True to keep usable vouchers."""
        return store.get_vouchers_by_customer_id(customer_id, only_active=only_active)

    return [
        get_customer_by_id,
        get_orders_by_customer_id,
        get_order_detail_by_order_id,
        get_vouchers_by_customer_id,
    ]
