"""The gap detector: checks any parsed address against London house style.

Unlike grader.py, this needs no right answer, so it works on any address a
user types in. Each problem comes back in the words a London ops person
would use when rating the reply in the Mubit console.
"""
import re

FULL_WORDS = {"road": "Rd", "street": "St", "lane": "Ln", "avenue": "Ave", "place": "Pl", "square": "Sq"}
SMALL_WORDS = {"and", "of", "the", "on", "upon"}
FLAT_LABEL = re.compile(r"^(Flat \d+[A-Z]?|Basement Flat|Ground Floor Flat|Top Floor Flat)$")
POSTCODE = re.compile(r"^[A-Z]{1,2}\d[A-Z\d]? \d[A-Z]{2}$")


def _badly_capitalised(value):
    words = re.split(r"\s+", value.strip())
    for i, w in enumerate(words):
        if not w or not w[0].isalpha():
            continue
        if i > 0 and w.lower() in SMALL_WORDS:
            continue
        if w[0].islower():
            return True
    return False


def check(fields, raw_reply=""):
    """Return a list of {field, problem} for anything that breaks house style."""
    gaps = []
    if "```" in (raw_reply or ""):
        gaps.append({"field": "format", "problem": "return plain JSON with no code fences"})
    street = fields.get("street")
    if street:
        last = street.strip().split()[-1].lower()
        if last in FULL_WORDS:
            short = street.strip()[: -len(last)] + FULL_WORDS[last]
            gaps.append({"field": "street", "problem": f'abbreviate it: "{short[:1].upper() + short[1:]}" not "{street}"'})
        if _badly_capitalised(street):
            gaps.append({"field": "street", "problem": "street name needs proper capitals"})
    area = fields.get("area")
    if area:
        if "," in area or "london" in area.lower():
            gaps.append({"field": "area", "problem": "area should be the neighbourhood only, e.g. Hackney"})
        if _badly_capitalised(area):
            gaps.append({"field": "area", "problem": "area needs proper capitals"})
    flat = fields.get("flat")
    if flat and not FLAT_LABEL.match(flat.strip()):
        gaps.append({"field": "flat", "problem": 'use the full flat label, e.g. "Flat 2B", "Basement Flat"'})
    number = fields.get("number")
    if number and re.search(r"[A-Z]", number):
        gaps.append({"field": "number", "problem": f'keep the letter lowercase, e.g. "{number.lower()}"'})
    postcode = fields.get("postcode")
    if postcode and not POSTCODE.match(postcode.strip()):
        gaps.append({"field": "postcode", "problem": 'standard postcode format, e.g. "E14 5RE"'})
    return gaps
