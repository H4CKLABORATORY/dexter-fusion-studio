import sys
from pathlib import Path
import unittest
from tempfile import TemporaryDirectory
from datetime import datetime, timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from scripts.build_data import parse_row, normalize

class ParsingTests(unittest.TestCase):
    def test_powerball(self):
        self.assertEqual(parse_row('powerball',{'draw_date':'2026-10-14T00:00:00.000','winning_numbers':'03 34 37 42 46 20'}), ['2026-10-14',3,34,37,42,46,20])
    def test_megamillions(self):
        self.assertEqual(parse_row('megamillions',{'Draw Date':'2026-10-16T00:00:00.000','Winning Numbers':'02 15 31 41 68','Mega Ball':'11'}), ['2026-10-16',2,15,31,41,68,11])
    def test_distinct(self):
        self.assertIsNone(parse_row('powerball',{'draw_date':'2026-10-14','winning_numbers':'03 03 37 42 46 20'}))
    def test_duplicate_and_sort(self):
        csv='Draw Date,Winning Numbers,Mega Ball\n2026-10-13,11 12 15 40 66,17\n2026-10-16,02 15 31 41 68,11\n2026-10-13,11 12 15 40 66,17\n'
        rows, skipped=normalize('megamillions',csv)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0][0],'2026-10-16')
    def test_incompatible(self):
        with self.assertRaises(ValueError):normalize('powerball','col1,col2\na,b\n')
if __name__=='__main__': unittest.main()