"""House-style grader for Mind the Gap.

An answer only counts as fully right if every field matches the London
house style exactly: street abbreviations kept (Rd, St, Ln, Pl, Sq, Ave),
full flat labels ("Flat 2B"), proper capitals, standard postcodes
("E14 5RE"), null for missing fields, and plain JSON with no code fences.
"""
import json
import re

FIELDS = ["flat", "number", "street", "area", "postcode"]

SYSTEM_PROMPT = (
    "You are a UK address parser for a London delivery company. Return ONLY JSON with keys: "
    "flat, number, street, area, postcode. Use null when missing. Postcode in standard format, e.g. E14 5RE."
)


def parse_reply(reply):
    """Return (dict or None, used_code_fences)."""
    if reply is None:
        return None, False
    text = reply.strip()
    fenced = "```" in text
    text = re.sub(r"```(json)?", "", text).strip()
    try:
        out = json.loads(text)
        return (out if isinstance(out, dict) else None), fenced
    except Exception:
        return None, fenced


def grade(reply, truth):
    """Grade one reply against the true answer.

    Returns a dict with fully_right, fields_right (count), and a list of
    problems written the way a London ops person would correct them.
    """
    out, fenced = parse_reply(reply)
    problems = []
    if out is None:
        return {"fully_right": False, "fields_right": 0, "problems": ["reply was not valid JSON"]}
    right = 0
    for k in FIELDS:
        got = out.get(k)
        if got == "":
            got = None
        if got == truth[k]:
            right += 1
        else:
            problems.append(f"{k} should be {json.dumps(truth[k])} not {json.dumps(got)}")
    if fenced:
        problems.append("return plain JSON with no code fences")
    return {"fully_right": not problems, "fields_right": right, "problems": problems}
