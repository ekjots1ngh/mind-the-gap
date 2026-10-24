"""Draw docs/architecture.svg: how Mind the Gap fits together, in the app's tube-map style."""
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent / "architecture.svg"
W, H = 1200, 1120
PAPER, INK, MUTED, PANEL = "#F3EFE6", "#111111", "#5E5A52", "#E7E0D2"
BLUE, PURPLE, GREEN, ORANGE, GREY = "#0019A8", "#60399E", "#007D32", "#FA7B05", "#9A968E"
SANS = "'Gill Sans', 'Gill Sans MT', Seravek, 'Trebuchet MS', Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, 'Liberation Mono', monospace"

ROW = [170 + 120 * i for i in range(7)]  # top of each row of boxes
BH = 90                                    # box height
COL = {"O": (30, 200), "L": (270, 290), "M": (620, 300), "R": (960, 220)}  # x, width

boxes = {
    # far left: open data
    "O1": ("O", 0, "OpenFreeMap", ["map tiles from", "OpenStreetMap data"]),
    "O2": ("O", 3, "postcodes.io", ["postcode to a point", "on the map"]),
    # laptop
    "L1": ("L", 0, "Departures board", ["static/index.html", "MapLibre, GSAP"]),
    "L2": ("L", 1, "Demo server", ["app.py", "/api/parse, /api/scoreboard"]),
    "L3": ("L", 2, "Gap check", ["house_style.py, grader.py", "guards the postcode"]),
    "L4": ("L", 3, "Map lookup", ["geo.py, nearest station", "station data from OSM"]),
    "L5": ("L", 4, "Training traffic", ["send_batch.py", "a script rates the replies"]),
    "L6": ("L", 5, "Test sets", ["make_testset.py", "eval_sf.py"]),
    "L7": ("L", 6, "Results", ["results/*.json", "the scoreboard's numbers"]),
    # Mubit
    "M1": ("M", 0, "Gateway", ["one base URL, OpenAI style", "keeps every call, with an id"]),
    "M2": ("M", 1, "Tasks", ["calls grouped by prompt", "and by model"]),
    "M3": ("M", 2, "Ratings", ["Mubit's rater (200 a day)", "or Good / Bad in the console"]),
    "M4": ("M", 3, "Kept rows", ["only rows rated Good", "become training data"]),
    "M5": ("M", 4, "Adapter training", ["Qwen3 4B, from 25 rows", "refreshed at most daily"]),
    "M6": ("M", 5, "Checks and silent test", ["12 held-out rows, then", "10% of live calls"]),
    "M7": ("M", 6, "Try models", ["50 calls a day", "stores and trains nothing"]),
    # right: models
    "R1": ("R", 0, "SF models", ["GPT-4.1 mini", "GPT-6 Sol"]),
    "R2": ("R", 4, "Open base model", ["Qwen3-4B-Instruct-2507", "small, open weights"]),
    "R3": ("R", 5, "London models", ["v1: 75% on test set 1", "taught: 100% on set 2"]),
}


def geom(key):
    col, row, *_ = boxes[key]
    x, w = COL[col]
    return x, ROW[row], w, BH


def cy(key):
    return geom(key)[1] + BH / 2


def left(key):
    return geom(key)[0]


def right(key):
    x, _, w, _ = geom(key)
    return x + w


def mid(key):
    x, _, w, _ = geom(key)
    return x + w / 2


svg = []
add = svg.append
add(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" '
    f'aria-label="Architecture of Mind the Gap: the demo app on the laptop, Mubit\'s training loop, and the models and open data it uses">')
add(f'<rect width="{W}" height="{H}" fill="{PAPER}"/>')
add(f'<rect width="{W}" height="8" fill="#FFD100"/>')
for i in range(0, W, 28):
    add(f'<path d="M{i} 8 L{i + 14} 0 L{i + 28} 0 L{i + 14} 8 Z" fill="{INK}"/>')

# title
add(f'<text x="30" y="62" font-family="{SANS}" font-size="32" font-weight="700" fill="{INK}">How Mind the Gap fits together</text>')
add(f'<text x="30" y="94" font-family="{SANS}" font-size="17" fill="{MUTED}">Every model call goes through Mubit. Ratings decide which replies become training rows, Mubit trains</text>')
add(f'<text x="30" y="116" font-family="{SANS}" font-size="17" fill="{MUTED}">a small open model on them, and fresh test sets score it against the SF models.</text>')

# Mubit zone
add(f'<rect x="605" y="138" width="330" height="{ROW[6] + BH + 18 - 138}" rx="12" fill="{PANEL}"/>')
for x, label in [(30, "OPEN DATA"), (270, "ON THE LAPTOP"), (620, "MUBIT"), (960, "MODELS")]:
    add(f'<text x="{x}" y="160" font-family="{MONO}" font-size="13" font-weight="700" letter-spacing="2" fill="{MUTED}">{label}</text>')

lines = []  # drawn before boxes so boxes sit on top


def line(d, colour, width=8, dash=None):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    lines.append(f'<path d="{d}" fill="none" stroke="{colour}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"{extra}/>')


# Mubit spine: the London line runs down through every step of the loop
line(f"M{mid('M1')} {ROW[0] + BH} V{ROW[6]}", PURPLE, 12)
# SF line: board to server to gateway to the SF models; the gap check hangs off the server
line(f"M{mid('L1')} {ROW[0] + BH} V{ROW[1]}", BLUE)
line(f"M{mid('L2')} {ROW[1] + BH} V{ROW[2]}", BLUE)
line(f"M{right('L2')} {cy('L2')} H572 V190 H{left('M1')}", BLUE)
line(f"M{right('M1')} {cy('M1')} H{left('R1')}", BLUE)
# London line feeders: training traffic into the gateway, base model into training, adapters out
line(f"M{right('L5')} {cy('L5')} H584 V215 H{left('M1')}", PURPLE)
line(f"M{right('M5')} {cy('M5')} H{left('R2')}", GREY, 6)
line(f"M{right('M6')} {cy('M6')} H{left('R3')}", PURPLE)
# Test line: test sets through the gateway, playground scores back to results
line(f"M{right('L6')} {cy('L6')} H596 V240 H{left('M1')}", GREEN)
line(f"M{mid('L6')} {ROW[5] + BH} V{ROW[6]}", GREEN)
line(f"M{left('M7')} {cy('M7')} H{right('L7')}", GREEN)
# Map line
line(f"M{right('O1')} {cy('O1')} H{left('L1')}", ORANGE)
line(f"M{left('L2')} {cy('L2')} H255 V{cy('L4')} H{left('L4')}", ORANGE)
line(f"M{right('O2')} {cy('O2')} H255", ORANGE)
svg.extend(lines)

# station dots where lines meet boxes
dots = [(right("L2"), cy("L2")), (left("M1"), 190), (left("M1"), 215), (left("M1"), 240),
        (right("L5"), cy("L5")), (right("L6"), cy("L6")), (right("M1"), cy("M1")), (left("R1"), cy("R1")),
        (right("M5"), cy("M5")), (left("R2"), cy("R2")), (right("M6"), cy("M6")), (left("R3"), cy("R3")),
        (left("M7"), cy("M7")), (right("L7"), cy("L7")), (right("O1"), cy("O1")), (left("L1"), cy("L1")),
        (left("L2"), cy("L2")), (left("L4"), cy("L4")), (right("O2"), cy("O2"))]

for key, (col, row, title, subs) in boxes.items():
    x, y, w, h = geom(key)
    heavy = key in ("M1",)
    add(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="#FFFFFF" stroke="{INK}" stroke-width="{4 if heavy else 2.5}"/>')
    add(f'<text x="{x + 16}" y="{y + 31}" font-family="{SANS}" font-size="21" font-weight="700" fill="{INK}">{escape(title)}</text>')
    for i, s in enumerate(subs):
        add(f'<text x="{x + 16}" y="{y + 56 + 20 * i}" font-family="{MONO}" font-size="15" fill="{MUTED}">{escape(s)}</text>')

for x, y in dots:
    add(f'<circle cx="{x}" cy="{y}" r="7" fill="#FFFFFF" stroke="{INK}" stroke-width="3"/>')

# legend
ly = ROW[6] + BH + 70
items = [(BLUE, "SF line: the live call"), (PURPLE, "London line: ratings to a model"),
         (GREEN, "Test line: fresh sets, scored"), (ORANGE, "Map line: where it is")]
for (c, label), x in zip(items, (30, 285, 620, 930)):
    add(f'<path d="M{x} {ly} H{x + 40}" stroke="{c}" stroke-width="8" stroke-linecap="round"/>')
    add(f'<text x="{x + 52}" y="{ly + 6}" font-family="{SANS}" font-size="17" fill="{INK}">{escape(label)}</text>')
add(f'<text x="30" y="{ly + 44}" font-family="{SANS}" font-size="14" fill="{MUTED}">Mind the Gap, built at Night Shift, the Mubit hackathon, Canary Wharf, October 2026. Not affiliated with Transport for London.</text>')
add("</svg>")

OUT.parent.mkdir(exist_ok=True)
OUT.write_text("\n".join(svg), encoding="utf-8")
print("wrote", OUT, "height used", ly + 44)
