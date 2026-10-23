"""Mind the Gap demo app. Built in SF, fixed in London.

Run (PowerShell):
    $env:MUBIT_API_KEY="your mubit key"
    python app.py
Then open http://localhost:8000

Every model call goes through Mubit. The page sends an address to the SF
model, highlights each gap against London house style, writes the
correction ready to paste into the Mubit console, and shows the scoreboard
from results/.
"""
import json
import statistics
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from eval_sf import client
from grader import FIELDS, SYSTEM_PROMPT, parse_reply
from house_style import check

ROOT = Path(__file__).parent
SF_MODEL = "gpt-4.1-mini"
MUBIT_COMPARE_URL = ("https://app.mubit.ai/console/projects/ws-5c5d9ea2c41261c1/playground"
                     "?adapter=ad_lane_2871f1e3&compare=provider")
LABELS = {
    "gpt-4.1-mini": ("GPT-4.1 mini", "SF model, the one the app used to call"),
    "gpt-6-sol": ("GPT-6 Sol", "SF frontier model"),
    "london-qwen3-4b-v1": ("London model v1", "Qwen3 4B + Mubit adapter, trained on our corrections"),
}


def scoreboard():
    boards = []
    for f in sorted((ROOT / "results").glob("*.json")):
        rows = json.loads(f.read_text(encoding="utf-8"))
        if not rows:
            continue
        n = len(rows)
        seen = [r for r in rows if r["set"] == "seen streets"]
        new = [r for r in rows if r["set"] == "new streets"]
        name, blurb = LABELS.get(f.stem, (f.stem, ""))
        boards.append({
            "id": f.stem, "name": name, "blurb": blurb, "n": n,
            "fully_right": round(100 * sum(r["fully_right"] for r in rows) / n),
            "fields_right": round(100 * sum(r["fields_right"] for r in rows) / (5 * n)),
            "seen": round(100 * sum(r["fully_right"] for r in seen) / len(seen)) if seen else None,
            "new": round(100 * sum(r["fully_right"] for r in new) / len(new)) if new else None,
            "median_ms": round(statistics.median(r["ms"] for r in rows)),
        })
    order = {"gpt-4.1-mini": 0, "gpt-6-sol": 1}
    boards.sort(key=lambda b: order.get(b["id"], 9))
    return {"models": boards, "compare_url": MUBIT_COMPARE_URL}


def parse_address(address):
    start = time.time()
    raw = client.chat.completions.with_raw_response.create(
        model=SF_MODEL,
        messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": address}],
    )
    reply = raw.parse().choices[0].message.content
    ms = round((time.time() - start) * 1000)
    fields, _ = parse_reply(reply)
    fields = {k: (fields or {}).get(k) for k in FIELDS}
    gaps = check(fields, reply)
    comment = "; ".join(f'{g["field"]}: {g["problem"]}' for g in gaps)
    return {"model": SF_MODEL, "reply": reply, "fields": fields, "gaps": gaps, "comment": comment,
            "ms": ms, "request_id": raw.headers.get("x-middleware-request-id")}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            return self._send(200, (ROOT / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path == "/api/scoreboard":
            return self._send(200, scoreboard())
        if self.path == "/api/samples":
            tests = json.loads((ROOT / "testset.json").read_text(encoding="utf-8"))
            return self._send(200, [t["input"] for t in tests[::5]])
        self._send(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/api/parse":
            return self._send(404, {"error": "not found"})
        try:
            length = int(self.headers.get("Content-Length", 0))
            address = json.loads(self.rfile.read(length) or b"{}").get("address", "").strip()
            if not address:
                return self._send(400, {"error": "type an address first"})
            self._send(200, parse_address(address))
        except Exception as e:
            self._send(500, {"error": str(e)})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("Mind the Gap running at http://localhost:8000  (Ctrl+C to stop)")
    ThreadingHTTPServer(("127.0.0.1", 8000), Handler).serve_forever()
