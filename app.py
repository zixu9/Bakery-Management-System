"""
Bakery Management System — Python HTTP Server Backend
Run: python server.py
Serves static files and a JSON REST API on http://localhost:8000
"""

import json
import os
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

DATA_FILE = os.path.join(os.path.dirname(__file__), "orders.json")

# ─────────────────────────── Data helpers ───────────────────────────

def load_orders():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_orders(orders):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)


# ─────────────────────────── Request Handler ───────────────────────────

STATIC_DIR = os.path.dirname(__file__)
MIME = {
    ".html": "text/html",
    ".css":  "text/css",
    ".js":   "application/javascript",
    ".json": "application/json",
    ".ico":  "image/x-icon",
    ".png":  "image/png",
}


class BMSHandler(BaseHTTPRequestHandler):

    # ── helpers ──────────────────────────────────────────────────────

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg, status=400):
        self._send_json({"error": msg}, status)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _read_body(self):
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _serve_static(self, path):
        """Serve a file from STATIC_DIR."""
        if path == "/" or path == "":
            path = "/index.html"
        file_path = os.path.normpath(os.path.join(STATIC_DIR, path.lstrip("/")))
        # Safety check
        if not file_path.startswith(os.path.abspath(STATIC_DIR)):
            self._send_error("Forbidden", 403)
            return
        if not os.path.isfile(file_path):
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
            return
        ext = os.path.splitext(file_path)[1]
        mime = MIME.get(ext, "application/octet-stream")
        with open(file_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    # ── routing ──────────────────────────────────────────────────────

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path == "/api/orders":
            orders = load_orders()
            # Optional search query
            qs = parse_qs(parsed.query)
            q = qs.get("q", [""])[0].lower()
            if q:
                orders = [o for o in orders
                          if q in o.get("name", "").lower()
                          or q in o.get("item", "").lower()]
            self._send_json({"orders": orders, "count": len(orders)})

        elif path == "/api/stats":
            orders = load_orders()
            today = datetime.now().strftime("%Y-%m-%d")
            revenue = sum(o["qty"] * o["price"] for o in orders)
            items_sold = sum(o["qty"] for o in orders)
            today_orders = [o for o in orders if o.get("date") == today]
            today_revenue = sum(o["qty"] * o["price"] for o in today_orders)
            self._send_json({
                "total_orders": len(orders),
                "total_revenue": revenue,
                "items_sold": items_sold,
                "today_orders": len(today_orders),
                "today_revenue": today_revenue,
            })

        else:
            self._serve_static(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != "/api/orders":
            self._send_error("Not found", 404)
            return

        data = self._read_body()
        name  = str(data.get("name", "")).strip()
        item  = str(data.get("item", "")).strip()
        qty   = data.get("qty")
        price = data.get("price")

        if not name or not item:
            self._send_error("name and item are required")
            return
        try:
            qty   = int(qty);   assert qty > 0
            price = float(price); assert price >= 0
        except (TypeError, ValueError, AssertionError):
            self._send_error("qty must be a positive integer; price must be ≥ 0")
            return

        order = {
            "id":    str(uuid.uuid4()),
            "name":  name,
            "item":  item,
            "qty":   qty,
            "price": price,
            "date":  datetime.now().strftime("%Y-%m-%d"),
        }
        orders = load_orders()
        orders.append(order)
        save_orders(orders)
        self._send_json({"message": "Order created", "order": order}, 201)

    def do_PUT(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")   # ["api", "orders", "<id>"]
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "orders":
            self._send_error("Not found", 404)
            return

        order_id = parts[2]
        data = self._read_body()
        orders = load_orders()
        idx = next((i for i, o in enumerate(orders) if o["id"] == order_id), None)
        if idx is None:
            self._send_error("Order not found", 404)
            return

        # Update only provided fields
        if "name" in data:
            orders[idx]["name"] = str(data["name"]).strip()
        if "item" in data:
            orders[idx]["item"] = str(data["item"]).strip()
        if "qty" in data:
            try:
                orders[idx]["qty"] = int(data["qty"]); assert orders[idx]["qty"] > 0
            except (ValueError, AssertionError):
                self._send_error("qty must be a positive integer")
                return
        if "price" in data:
            try:
                orders[idx]["price"] = float(data["price"]); assert orders[idx]["price"] >= 0
            except (ValueError, AssertionError):
                self._send_error("price must be ≥ 0")
                return

        save_orders(orders)
        self._send_json({"message": "Order updated", "order": orders[idx]})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        parts = parsed.path.strip("/").split("/")
        if len(parts) != 3 or parts[0] != "api" or parts[1] != "orders":
            self._send_error("Not found", 404)
            return

        order_id = parts[2]
        orders = load_orders()
        new_orders = [o for o in orders if o["id"] != order_id]
        if len(new_orders) == len(orders):
            self._send_error("Order not found", 404)
            return
        save_orders(new_orders)
        self._send_json({"message": "Order deleted"})

    def log_message(self, fmt, *args):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] {fmt % args}")


# ─────────────────────────── Entry point ───────────────────────────

if __name__ == "__main__":
    HOST, PORT = "localhost", 8000
    server = HTTPServer((HOST, PORT), BMSHandler)
    print(f"""
╔══════════════════════════════════════════════╗
║   🥐  Bakery Management System — Server      ║
║   http://{HOST}:{PORT}                        ║
║   Press Ctrl+C to stop                       ║
╚══════════════════════════════════════════════╝
""")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[server] Stopped.")
