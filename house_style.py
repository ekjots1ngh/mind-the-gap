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


POSTCODE_IN_TEXT = re.compile(r"\b[a-z]{1,2}\d[a-z\d]?\s*\d[a-z]{2}\b", re.I)
FLAT_NUMBER_IN_TEXT = re.compile(r"(?<!floor )(?<!basement )\bflat\s+\d+[a-z]?\b", re.I)
HOUSE_NUMBER_IN_TEXT = re.compile(r"\b\d{1,4}[a-z]?\b", re.I)


POSTCODE_PARTS = re.compile(r"\b([a-z]{1,2}\d[a-z\d]?)\s*(\d[a-z]{2})\b", re.I)


def postcode_in(text):
    """The postcode written in a raw address, in standard form, e.g. 'se228hn' -> 'SE22 8HN'."""
    m = POSTCODE_PARTS.search(text or "")
    return f"{m.group(1).upper()} {m.group(2).upper()}" if m else None


def house_number_in(address):
    """Best guess at the house number in a raw address, e.g. '207b'."""
    text = POSTCODE_IN_TEXT.sub(" ", address)
    text = FLAT_NUMBER_IN_TEXT.sub(" ", text)
    found = HOUSE_NUMBER_IN_TEXT.findall(text)
    return found[0].lower() if found else None


def check(fields, raw_reply="", address=None):
    """Return a list of {field, problem} for anything that breaks house style."""
    gaps = []
    expected_number = house_number_in(address) if address else None
    if expected_number:
        number = fields.get("number")
        if not number:
            gaps.append({"field": "number", "problem": f'house number is missing: "{expected_number}"'})
        elif number.lower() != expected_number:
            gaps.append({"field": "number", "problem": f'should be "{expected_number}"'})
        flat = fields.get("flat")
        if flat and expected_number in flat.lower().split():
            gaps.append({"field": "flat", "problem": f'take "{expected_number}" out, that\'s the house number'})
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
        # "Hackney, London" and "Hackney London" break the rule; "London Fields" is a real neighbourhood
        if "," in area or area.strip().lower() == "london" or area.strip().lower().endswith(" london"):
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
    # facts guard: a model may only reformat the postcode it was given, never change it
    # (London model v1 once turned SE22 8HN into SE2 2HN, which is in Abbey Wood)
    given = postcode_in(address) if address else None
    if given and postcode_in(postcode or "") != given:
        gaps.append({"field": "postcode", "problem": f'should be "{given}", the postcode in the address'})
    return gaps
