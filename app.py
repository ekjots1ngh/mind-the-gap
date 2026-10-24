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
from geo import locate
from house_style import check

ROOT = Path(__file__).parent
SF_MODEL = "gpt-4.1-mini"
MUBIT_COMPARE_URL = ("https://app.mubit.ai/console/projects/ws-5c5d9ea2c41261c1/playground"
                     "?adapter=ad_lane_2871f1e3&compare=provider")
LABELS = {
    "gpt-4.1-mini": ("GPT-4.1 mini", "SF model, the one the app used to call"),
    "gpt-6-sol": ("GPT-6 Sol", "SF frontier model"),
    "gpt-4.1-mini+rules": ("GPT-4.1 mini + written rules", "SF model with the house rules pasted into its prompt"),
    "gpt-6-sol+rules": ("GPT-6 Sol + written rules", "SF frontier model with the house rules pasted into its prompt"),
    "london-qwen3-4b-v1": ("London model v1", "Qwen3 4B + Mubit adapter, trained on GPT-4.1 mini's answers rated Good"),
    "london-qwen3-4b-v2": ("London model v2", "Qwen3 4B + Mubit adapter, after the v2 round of corrections"),
    "london-taught": ("London model, taught by GPT", "Qwen3 4B + Mubit adapter, trained on 28 of GPT-4.1 mini's answers with the written rules"),
}
ORDER = ["gpt-4.1-mini", "gpt-6-sol", "gpt-4.1-mini+rules", "gpt-6-sol+rules", "london-qwen3-4b-v1", "london-qwen3-4b-v2", "london-taught"]
SETS = {"": "Test set 1", "testset2": "Test set 2"}


def scoreboard(set_name=""):
    folder = ROOT / "results" / set_name if set_name in SETS and set_name else ROOT / "results"
    boards = []
    for f in sorted(folder.glob("*.json")):
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
    boards.sort(key=lambda b: ORDER.index(b["id"]) if b["id"] in ORDER else 99)
    sets = [{"id": k, "name": v} for k, v in SETS.items() if any((ROOT / "results" / k).glob("*.json"))]
    return {"models": boards, "compare_url": MUBIT_COMPARE_URL, "sets": sets, "set": set_name}


def _key(address):
    return " ".join(address.lower().replace(",", " ").split())


TRUTH = {_key(t["input"]): t["truth"] for f in ("testset.json", "testset2.json") if (ROOT / f).exists()
         for t in json.loads((ROOT / f).read_text(encoding="utf-8"))}


def gaps_against_truth(fields, reply, truth):
    gaps = []
    if "```" in (reply or ""):
        gaps.append({"field": "format", "problem": "return plain JSON with no code fences"})
    for k in FIELDS:
        if fields.get(k) != truth[k]:
            want = "none" if truth[k] is None else f'"{truth[k]}"'
            gaps.append({"field": k, "problem": f"should be {want}"})
    return gaps


def _recorded_london_answers():
    """London model replies recorded in Mubit's Try models page, keyed by address."""
    out = {}
    for f in sorted((ROOT / "results").rglob("london-*.json")):
        label = LABELS.get(f.stem, (f.stem, ""))[0]
        note = "reads the written rules" if f.stem == "london-taught" else "same short prompt as the SF line"
        for r in json.loads(f.read_text(encoding="utf-8")):
            out.setdefault(_key(r["input"]), {"label": label, "reply": r["reply"], "ms": r["ms"], "note": note})
    return out


LONDON = _recorded_london_answers()


def london_answer(address, truth):
    rec = LONDON.get(_key(address))
    if not rec:
        return None
    fields, _ = parse_reply(rec["reply"])
    fields = {k: ((fields or {}).get(k) or None) for k in FIELDS}
    return {"label": rec["label"], "fields": fields, "ms": rec["ms"], "note": rec["note"],
            "gaps": gaps_against_truth(fields, rec["reply"], truth) if truth else check(fields, rec["reply"], address)}


def recorded_sf_answer(address):
    """GPT-4.1 mini's answer from an earlier eval run, used only if the live call fails (venue wifi)."""
    for f in (ROOT / "results" / f"{SF_MODEL}.json", ROOT / "results" / "testset2" / f"{SF_MODEL}.json"):
        if f.exists():
            for r in json.loads(f.read_text(encoding="utf-8")):
                if _key(r["input"]) == _key(address):
                    return r
    return None


def parse_address(address):
    start = time.time()
    live, request_id = True, None
    try:
        raw = client.chat.completions.with_raw_response.create(
            model=SF_MODEL,
            messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": address}],
        )
        reply = raw.parse().choices[0].message.content
        request_id = raw.headers.get("x-middleware-request-id")
        ms = round((time.time() - start) * 1000)
    except Exception:
        rec = recorded_sf_answer(address)
        if not rec:
            raise
        reply, ms, live = rec["reply"], rec["ms"], False
    fields, _ = parse_reply(reply)
    fields = {k: ((fields or {}).get(k) or None) for k in FIELDS}
    truth = TRUTH.get(_key(address))
    if truth:
        gaps, checked = gaps_against_truth(fields, reply, truth), "checked against the true answer"
    else:
        gaps, checked = check(fields, reply, address), "checked against London house style rules"
    comment = "; ".join(f'{g["field"]}: {g["problem"]}' for g in gaps)
    return {"model": SF_MODEL, "reply": reply, "fields": fields, "gaps": gaps, "comment": comment,
            "checked": checked, "ms": ms, "request_id": request_id, "live": live,
            "london": london_answer(address, truth), "geo": locate(address)}


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    MIME = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
            ".css": "text/css", ".json": "application/json", ".woff2": "font/woff2", ".svg": "image/svg+xml",
            ".png": "image/png", ".txt": "text/plain; charset=utf-8"}

    def _static(self):
        rel = self.path.split("?", 1)[0][len("/static/"):]
        target = (ROOT / "static" / rel).resolve()
        if not str(target).startswith(str((ROOT / "static").resolve())) or not target.is_file():
            return self._send(404, {"error": "not found"})
        self.send_response(200)
        data = target.read_bytes()
        self.send_header("Content-Type", self.MIME.get(target.suffix, "application/octet-stream"))
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=3600")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/static/"):
            return self._static()
        if self.path.startswith("/api/geo"):
            pc = self.path.split("pc=", 1)[1] if "pc=" in self.path else ""
            from urllib.parse import unquote
            return self._send(200, locate(unquote(pc)) or {})
        if self.path in ("/", "/index.html"):
            return self._send(200, (ROOT / "static" / "index.html").read_bytes(), "text/html; charset=utf-8")
        if self.path.startswith("/api/scoreboard"):
            set_name = self.path.split("set=", 1)[1] if "set=" in self.path else ""
            return self._send(200, scoreboard(set_name if set_name in SETS else ""))
        if self.path == "/api/samples":
            tests = json.loads((ROOT / "testset.json").read_text(encoding="utf-8"))
            picks = [t["input"] for t in tests[::5]]
            set2 = ROOT / "testset2.json"
            if set2.exists():  # two set 2 addresses with the street written in full, for the taught model
                s2 = json.loads(set2.read_text(encoding="utf-8"))
                picks += [s2[i]["input"] for i in (5, 33) if i < len(s2)]
            return self._send(200, picks)
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
    # On Windows, port reuse lets an old copy of the app keep answering requests. Refuse instead.
    ThreadingHTTPServer.allow_reuse_address = False
    try:
        server = ThreadingHTTPServer(("127.0.0.1", 8000), Handler)
    except OSError:
        raise SystemExit("Port 8000 is already in use. Close the other window running app.py, then try again.")
    print("Mind the Gap running at http://localhost:8000  (Ctrl+C to stop)")
    server.serve_forever()
