import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_us_history import canonical_date, parse_numbers, normalize


class NYTake5Tests(unittest.TestCase):
    def test_date_and_five_unique_balls(self):
        self.assertEqual(canonical_date("1992-01-17T00:00:00"), "1992-01-17")
        self.assertEqual(canonical_date("10/16/2026"), "2026-10-16")
        self.assertEqual(parse_numbers("01 03 17 28 39"), [1, 3, 17, 28, 39])
        self.assertIsNone(parse_numbers("01 01 17 28 39"))
        self.assertIsNone(parse_numbers("01 05 17 28 40"))

    def test_midday_evening_same_date_retained(self):
        csv_text = (
            "Draw Date,Evening Winning Numbers,Evening Bonus #,Midday Winning Numbers,Midday Bonus #\n"
            "2026-10-16,01 05 09 12 39,,02 07 12 22 38,\n"
            "2026-10-15,02 08 17 31 36,,,\n"
            "2026-10-16,01 05 09 12 39,,02 07 12 22 38,\n"
        )
        rows, skipped = normalize(csv_text)
        self.assertEqual(skipped, 0)
        self.assertEqual(len(rows), 3)
        self.assertEqual(set(r["period"] for r in rows if r["date"] == "2026-10-16"), {"midday", "evening"})
        self.assertEqual(rows[0]["date"], "2026-10-16")

    def test_reject_conflicting_draws(self):
        rows=(
            "Draw Date,Evening Winning Numbers,Midday Winning Numbers\n"
            "2026-10-16,01 05 09 12 39,\n"
            "2026-10-16,02 05 09 12 39,\n"
        )
        with self.assertRaises(ValueError):
            normalize(rows)

    def test_reject_invalid_numbers(self):
        rows="Draw Date,Evening Winning Numbers\n2026-10-16,01 01 09 12 39\n"
        with self.assertRaises(ValueError):
            normalize(rows)


if __name__ == "__main__":
    unittest.main()
