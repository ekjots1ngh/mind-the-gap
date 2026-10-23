"""Send a batch of messy London addresses through Mubit so the task gets traffic.

This is how the training traffic was made: same instructions every time, so
Mubit groups the calls into one task, and the London team rates the replies
in the Mubit console (Good, or Bad with a comment saying what to fix).

Usage (PowerShell):
    $env:MUBIT_API_KEY="your mubit key"
    python send_batch.py --seed 8 --count 120 --out batch2.csv
    python send_batch.py --v2 --seed 21 --count 120 --model gpt-6-sol --out v2_batch.csv
    python send_batch.py --rules --seed 31 --count 60 --out teach_a.csv   # teacher traffic for the rules task
"""
import argparse
import re
import csv
import json
import random

from eval_sf import PROMPT, client
from grader import grade

FLATS = ["Flat 3", "Flat 2B", "Basement Flat", "Top Floor Flat", "Flat 14", None, None]
STREETS = [("Churchill Pl", "Canary Wharf", "E14 5RE"), ("Mare St", "Hackney", "E8 1HE"), ("Brick Ln", "Shoreditch", "E1 6QL"),
           ("Coldharbour Ln", "Brixton", "SW9 8LH"), ("Upper St", "Islington", "N1 0NY"), ("Kilburn High Rd", "Kilburn", "NW6 6JP"),
           ("Uxbridge Rd", "Shepherd's Bush", "W12 8LJ"), ("Walworth Rd", "Elephant and Castle", "SE17 1JE"),
           ("Northampton Sq", "Clerkenwell", "EC1V 0HB"), ("Station Rd", "Harrow", "HA1 2RT")]


V2_WORDS = {" Rd": [" road", " Road"], " St": [" street", " Street"], " Ln": [" lane", " Lane"],
            " Pl": [" place", " Place"], " Sq": [" square", " Square"]}


def messy(s, v2=False):
    if v2:
        # v2 round: the street is always written out in full, the exact gap v1 still has
        for short, longs in V2_WORDS.items():
            if s.endswith(short):
                s = s[: -len(short)] + random.choice(longs)
    elif random.random() < 0.4:
        s = re.sub(r" Rd\b", " road", s); s = re.sub(r" St\b", " street", s)
    return s.lower() if random.random() < 0.3 else s


def make_address(v2=False):
    flat = random.choice(FLATS)
    num = str(random.randint(1, 240)) + random.choice(["", "", "a", "b"])
    street, area, pc = random.choice(STREETS)
    pc_messy = random.choice([pc, pc.replace(" ", ""), pc.lower(), pc.lower().replace(" ", "")])
    parts = [p for p in [flat, f"{num} {street}", area, "London" if random.random() < 0.5 else None, pc_messy] if p]
    raw = random.choice([", ", " ", "  ,"]).join(messy(p, v2) for p in parts)
    return raw, {"flat": flat, "number": num, "street": street, "area": area, "postcode": pc}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--count", type=int, default=40)
    ap.add_argument("--model", default="gpt-4.1-mini")
    ap.add_argument("--out", default="batch.csv")
    ap.add_argument("--v2", action="store_true", help="always write the street out in full (road, lane, square...)")
    ap.add_argument("--rules", action="store_true", help="write the house rules into the prompt (teacher traffic)")
    args = ap.parse_args()
    random.seed(args.seed)
    rows, right = [], 0
    for i in range(args.count):
        raw, truth = make_address(args.v2)
        r = client.chat.completions.with_raw_response.create(
            model=args.model, messages=[{"role": "system", "content": PROMPT}, {"role": "user", "content": raw}])
        out = r.parse().choices[0].message.content
        g = grade(out, truth)
        right += g["fully_right"]
        rows.append({"request_id": r.headers.get("x-middleware-request-id"), "input": raw, "model_output": out,
                     "truth": json.dumps(truth), "fully_right": g["fully_right"], "comment": "; ".join(g["problems"])})
        print(i + 1, "OK " if g["fully_right"] else "BAD", raw)
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)
    print(f"\nDone. {right}/{args.count} fully right. Saved {args.out}")
