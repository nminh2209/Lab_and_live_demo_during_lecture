from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from src.agent.graph import run_agent
from src.utils.data_store import OrderDataStore

ROOT_DIR = Path(__file__).resolve().parent
WEB_DIR = ROOT_DIR / "web"
INDEX_FILE = WEB_DIR / "index.html"


class DemoHandler(BaseHTTPRequestHandler):
    def _send_json(self, payload: dict, status: int = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_index(self) -> None:
        if not INDEX_FILE.exists():
            self._send_json({"error": "Missing web/index.html"}, status=HTTPStatus.NOT_FOUND)
            return
        content = INDEX_FILE.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def do_GET(self) -> None:
        if self.path == "/api/products":
            try:
                store = OrderDataStore(ROOT_DIR / "data", ROOT_DIR / "artifacts" / "orders")
                products = [
                    {
                        "product_id": product.product_id,
                        "name": product.name,
                        "brand": product.brand,
                        "category": product.category,
                        "unit_price": product.unit_price,
                        "stock": product.stock,
                    }
                    for product in sorted(store.products, key=lambda item: (item.category, item.name))
                ]
            except Exception as exc:  # pragma: no cover - demo safety
                self._send_json({"error": f"Failed to load products: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
                return
            self._send_json({"products": products})
            return
        if self.path in {"/", "/index.html"}:
            self._send_index()
            return
        self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)

    def do_POST(self) -> None:
        if self.path != "/api/order":
            self._send_json({"error": "Not found"}, status=HTTPStatus.NOT_FOUND)
            return

        content_length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(content_length).decode("utf-8")
        try:
            payload = json.loads(raw_body) if raw_body else {}
        except json.JSONDecodeError:
            self._send_json({"error": "Invalid JSON body"}, status=HTTPStatus.BAD_REQUEST)
            return

        query = str(payload.get("query", "")).strip()
        provider = str(payload.get("provider", "openai")).strip() or "openai"
        model_name = payload.get("model_name")
        if not query:
            self._send_json({"error": "Field `query` is required."}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            result = run_agent(query, provider=provider, model_name=model_name)
        except Exception as exc:  # pragma: no cover - demo safety
            self._send_json({"error": f"Agent execution failed: {exc}"}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            return

        self._send_json(result.model_dump())


def main() -> None:
    host = "127.0.0.1"
    port = 8000
    server = ThreadingHTTPServer((host, port), DemoHandler)
    print(f"Order demo running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
