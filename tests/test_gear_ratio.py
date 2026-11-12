# -*- coding: utf-8 -*-
"""gear_ratio 的单元测试：python -m unittest discover -s tests"""

import io
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gear_ratio


class TestClassify(unittest.TestCase):
    def test_bands_boundaries(self):
        cases = [
            (0.50, "超轻档"),
            (0.99, "超轻档"),
            (1.00, "轻档"),
            (1.49, "轻档"),
            (1.50, "中档"),
            (2.49, "中档"),
            (2.50, "重档"),
            (3.49, "重档"),
            (3.50, "超重档"),
            (5.00, "超重档"),
        ]
        for ratio, expected in cases:
            with self.subTest(ratio=ratio):
                self.assertEqual(gear_ratio.classify(ratio)[0], expected)

    def test_non_positive_rejected(self):
        for bad in (0, -1):
            with self.assertRaises(ValueError):
                gear_ratio.classify(bad)


class TestParseTeeth(unittest.TestCase):
    def test_separators(self):
        for text in ("53-39", "53,39", "53 39", "53，39", "53、39", "53/39"):
            with self.subTest(text=text):
                self.assertEqual(gear_ratio.parse_teeth(text), [53, 39])

    def test_single_value(self):
        self.assertEqual(gear_ratio.parse_teeth("53"), [53])

    def test_invalid(self):
        for text in ("", "abc", "53-0", "-5"):
            with self.subTest(text=text), self.assertRaises(ValueError):
                gear_ratio.parse_teeth(text)


class TestRatios(unittest.TestCase):
    def test_count_and_value(self):
        rows = gear_ratio.ratios([53, 39], [11, 13])
        self.assertEqual(len(rows), 4)
        self.assertAlmostEqual(rows[0][2], 53 / 11, places=6)
        self.assertEqual((rows[-1][0], rows[-1][1]), (39, 13))

    def test_summarize(self):
        rows = gear_ratio.ratios([53, 39], [11, 32])
        stats = gear_ratio.summarize(rows)
        self.assertEqual(stats["min"][1], 32)
        self.assertEqual(stats["max"][0], 53)
        self.assertAlmostEqual(stats["span"], (53 / 11) / (39 / 32), places=6)

    def test_summarize_empty(self):
        with self.assertRaises(ValueError):
            gear_ratio.summarize([])


class TestOutput(unittest.TestCase):
    def test_table_has_header_and_rows(self):
        rows = gear_ratio.ratios([53], [11])
        table = gear_ratio.format_table(rows)
        self.assertIn("牙盘", table)
        self.assertIn("4.82", table)
        self.assertIn("超重档", table)

    def test_main_default_exit_code(self):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = gear_ratio.main(["-c", "53", "-r", "11"])
        self.assertEqual(code, 0)
        self.assertIn("齿比", buf.getvalue())

    def test_main_bad_input_returns_2(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = gear_ratio.main(["-c", "abc"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
