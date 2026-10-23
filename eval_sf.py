"""Run the Mind the Gap test set through the big SF models via Mubit and score them.

Usage (PowerShell):
    $env:MUBIT_API_KEY="your mubit key"
    python eval_sf.py            # short instructions, like the real app
    python eval_sf.py --rules    # fairness check: house rules written into the prompt

Writes results/<model>.json and prints a scoreboard.
"""
import json
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from openai import OpenAI

import sys

from grader import HOUSE_RULES, SYSTEM_PROMPT, grade

MODELS = ["gpt-4.1-mini", "gpt-6-sol"]
# python eval_sf.py --rules  writes the house rules into the prompt (the fairness check)
WITH_RULES = "--rules" in sys.argv
PROMPT = SYSTEM_PROMPT + HOUSE_RULES if WITH_RULES else SYSTEM_PROMPT


def load_key():
    key = os.environ.get("MUBIT_API_KEY")
    env = Path(__file__).with_name(".env")
    if not key and env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("MUBIT_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"')
    if not key:
        raise SystemExit("Set MUBIT_API_KEY first (or put it in a .env file next to this script).")
    return key


client = OpenAI(base_url="https://api.mubit.ai/openai/v1/", api_key=load_key())
tests = json.loads(Path(__file__).with_name("testset.json").read_text(encoding="utf-8"))


def run_one(model, t):
    start = time.time()
    try:
        raw = client.chat.completions.with_raw_response.create(
            model=model,
            messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": t["input"]}],
        )
        resp = raw.parse()
        reply = resp.choices[0].message.content
        usage = resp.usage
        tokens = {"in": usage.prompt_tokens, "out": usage.completion_tokens} if usage else None
        rid = raw.headers.get("x-middleware-request-id")
    except Exception as e:
        reply, tokens, rid = None, None, f"error: {e}"
    ms = round((time.time() - start) * 1000)
    g = grade(reply, t["truth"])
    return {"set": t["set"], "input": t["input"], "truth": t["truth"], "reply": reply,
            "ms": ms, "tokens": tokens, "request_id": rid, **g}


def summarise(name, rows):
    n = len(rows)
    full = sum(r["fully_right"] for r in rows)
    fields = sum(r["fields_right"] for r in rows)
    seen = [r for r in rows if r["set"] == "seen streets"]
    new = [r for r in rows if r["set"] == "new streets"]
    pct = lambda xs: f"{100 * sum(r['fully_right'] for r in xs) / len(xs):.0f}%" if xs else "n/a"
    med = statistics.median(r["ms"] for r in rows)
    print(f"{name:<22} fully right {full:>2}/{n} ({100 * full / n:.0f}%) | fields {100 * fields / (5 * n):.0f}% "
          f"| seen streets {pct(seen)} | new streets {pct(new)} | median {med:.0f} ms")


if __name__ == "__main__":
    Path("results").mkdir(exist_ok=True)
    for model in MODELS:
        with ThreadPoolExecutor(max_workers=8) as pool:
            rows = list(pool.map(lambda t: run_one(model, t), tests))
        name = model + ("+rules" if WITH_RULES else "")
        Path(f"results/{name}.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
        summarise(name, rows)
    print("\nSaved results/. Paste these lines back to Claude.")
