"""Tests for the grader, the gap detector and the map lookup. Run: python -m unittest discover -s tests"""
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import geo  # noqa: E402
from grader import FIELDS, grade, parse_reply  # noqa: E402
from house_style import check, house_number_in  # noqa: E402

TRUTH = {"flat": "Flat 2B", "number": "155a", "street": "Mare St", "area": "Hackney", "postcode": "E8 1HE"}
TESTS = [t for f in ("testset.json", "testset2.json") for t in json.loads((ROOT / f).read_text(encoding="utf-8"))]


class Grader(unittest.TestCase):
    def test_parses_plain_and_fenced_json(self):
        self.assertEqual(parse_reply(json.dumps(TRUTH)), (TRUTH, False))
        self.assertEqual(parse_reply("```json\n" + json.dumps(TRUTH) + "\n```"), (TRUTH, True))
        self.assertEqual(parse_reply("not json"), (None, False))

    def test_right_answer_is_fully_right(self):
        g = grade(json.dumps(TRUTH), TRUTH)
        self.assertTrue(g["fully_right"])
        self.assertEqual(g["fields_right"], 5)

    def test_typical_sf_answer_is_wrong_field_by_field(self):
        sf = dict(TRUTH, flat="2b", street="Mare Street", area="Hackney, London")
        g = grade(json.dumps(sf), TRUTH)
        self.assertFalse(g["fully_right"])
        self.assertEqual(g["fields_right"], 2)
        self.assertIn('street should be "Mare St" not "Mare Street"', g["problems"])

    def test_code_fences_alone_make_it_wrong(self):
        self.assertFalse(grade("```" + json.dumps(TRUTH) + "```", TRUTH)["fully_right"])

    def test_empty_string_counts_as_missing(self):
        truth = dict(TRUTH, flat=None)
        self.assertTrue(grade(json.dumps(dict(truth, flat="")), truth)["fully_right"])

    def test_every_test_answer_grades_itself_right(self):
        for t in TESTS:
            self.assertTrue(grade(json.dumps(t["truth"]), t["truth"])["fully_right"], t["input"])


class GapDetector(unittest.TestCase):
    def test_right_answers_have_no_gaps(self):
        # the detector needs no right answer, so it must never flag one
        for t in TESTS:
            self.assertEqual(check(t["truth"], "", t["input"]), [], t["input"])

    def test_finds_each_kind_of_gap(self):
        address = "flat 2b 155a mare street hackney e8 1he"
        sf = {"flat": "2b", "number": "155A", "street": "Mare Street", "area": "Hackney, London", "postcode": "e81he"}
        fields = {g["field"] for g in check(sf, "```json```", address)}
        self.assertEqual(fields, {"flat", "number", "street", "area", "postcode", "format"})

    def test_house_number_ignores_flat_and_postcode(self):
        self.assertEqual(house_number_in("flat 2b 155a mare st e8 1he"), "155a")
        self.assertEqual(house_number_in("top floor flat 207b Uxbridge Rd W128LJ"), "207b")
        self.assertEqual(house_number_in("Flat 14 ,203 Mare St ,Hackney ,e8 1he"), "203")

    def test_changed_postcode_is_caught(self):
        # London model v1's real miss on test set 1
        fields = {"flat": "Top Floor Flat", "number": "163b", "street": "Lordship Ln", "area": "East Dulwich", "postcode": "SE2 2HN"}
        gaps = check(fields, "", "Top Floor Flat 163b Lordship Ln East Dulwich SE22 8HN")
        self.assertIn({"field": "postcode", "problem": 'should be "SE22 8HN", the postcode in the address'}, gaps)

    def test_london_fields_is_a_real_area(self):
        fields = {"flat": None, "number": "12", "street": "Richmond Rd", "area": "London Fields", "postcode": "E8 3QW"}
        self.assertEqual(check(fields, "", "12 richmond rd london fields e8 3qw"), [])
        self.assertTrue(check(dict(fields, area="Hackney London"), "", "12 richmond rd hackney london e8 3qw"))

    def test_missing_house_number_is_caught(self):
        gaps = check({k: TRUTH[k] for k in FIELDS} | {"number": None}, "", "flat 2b 155a mare st e8 1he")
        self.assertIn({"field": "number", "problem": 'house number is missing: "155a"'}, gaps)


class Map(unittest.TestCase):
    def test_postcode_is_normalised(self):
        self.assertEqual(geo.normalise("flat 3 91b churchill pl canary wharf london e145re"), "E14 5RE")
        self.assertIsNone(geo.normalise("no postcode here"))

    def test_nearest_station(self):
        st = geo.nearest_station(51.5047, -0.0144)
        self.assertIn("Canary Wharf", st["name"])
        self.assertLess(st["metres"], 600)

    def test_works_offline(self):
        real, geo._get = geo._get, lambda url: (_ for _ in ()).throw(OSError("no wifi"))
        try:
            geo._cache.clear()
            place = geo.locate("155a mare st e8 1he")
            self.assertEqual(place["source"], "approximate")
            self.assertEqual(place["district"], "Hackney")
        finally:
            geo._get = real
            geo._cache.clear()


if __name__ == "__main__":
    unittest.main()
