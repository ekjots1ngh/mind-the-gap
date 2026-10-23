import json, random
random.seed(2026)
flats = ["Flat 3", "Flat 2B", "Basement Flat", "Top Floor Flat", "Flat 14", None, None]
seen = [("Churchill Pl","Canary Wharf","E14 5RE"),("Mare St","Hackney","E8 1HE"),("Brick Ln","Shoreditch","E1 6QL"),
        ("Coldharbour Ln","Brixton","SW9 8LH"),("Upper St","Islington","N1 0NY"),("Kilburn High Rd","Kilburn","NW6 6JP"),
        ("Uxbridge Rd","Shepherd's Bush","W12 8LJ"),("Walworth Rd","Elephant and Castle","SE17 1JE"),
        ("Northampton Sq","Clerkenwell","EC1V 0HB"),("Station Rd","Harrow","HA1 2RT")]
unseen = [("Electric Ave","Brixton","SW9 8JX"),("Portobello Rd","Notting Hill","W11 1LJ"),("Kingsland Rd","Dalston","E8 4AA"),
          ("Lordship Ln","East Dulwich","SE22 8HN"),("Holloway Rd","Holloway","N7 6PA")]
def messy(s):
    s = s.replace(" Rd"," road").replace(" St"," street").replace(" Ln"," lane").replace(" Ave"," avenue") if random.random()<0.4 else s
    return s.lower() if random.random()<0.3 else s
def make(streets, n, tag):
    out = []
    for _ in range(n):
        flat = random.choice(flats); num = str(random.randint(1,240)) + random.choice(["","","a","b"])
        street, area, pc = random.choice(streets)
        pc_messy = random.choice([pc, pc.replace(" ",""), pc.lower(), pc.lower().replace(" ","")])
        parts = [p for p in [flat, f"{num} {street}", area, "London" if random.random()<0.5 else None, pc_messy] if p]
        raw = random.choice([", ", " ", "  ,"]).join(messy(p) for p in parts)
        out.append({"set": tag, "input": raw, "truth": {"flat": flat, "number": num, "street": street, "area": area, "postcode": pc}})
    return out
tests = make(seen, 28, "seen streets") + make(unseen, 12, "new streets")
json.dump(tests, open("testset.json","w"), indent=1)
print(len(tests)); [print(t["set"][:4], "|", t["input"]) for t in tests[:5]+tests[-3:]]
