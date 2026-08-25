"""Unit tests for the pure transformation functions. Standard library only.

Run:  python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "scripts"))

from build_data import annualized_qoq, direction, recession_ranges, yoy


class TestYoY(unittest.TestCase):
    def test_basic_twelve_month_change(self):
        obs = [(f"2024-{m:02d}-01", 100.0) for m in range(1, 13)]
        obs += [("2025-01-01", 103.0)]
        result = yoy(obs)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][0], "2025-01-01")
        self.assertAlmostEqual(result[0][1], 3.0)

    def test_no_output_without_prior_year(self):
        obs = [("2024-01-01", 100.0), ("2024-02-01", 101.0)]
        self.assertEqual(yoy(obs), [])

    def test_matches_by_calendar_month_not_position(self):
        # A gap in the data must not shift the 12-month match.
        obs = [("2024-01-01", 100.0), ("2024-03-01", 100.0),
               ("2025-01-01", 102.0)]
        result = yoy(obs)
        self.assertEqual(result, [("2025-01-01", 2.0000000000000018)])


class TestAnnualizedQoQ(unittest.TestCase):
    def test_one_percent_quarterly_compounds(self):
        obs = [("2025-01-01", 100.0), ("2025-04-01", 101.0)]
        result = annualized_qoq(obs)
        self.assertEqual(result[0][0], "2025-04-01")
        self.assertAlmostEqual(result[0][1], 4.060401, places=5)

    def test_flat_levels_give_zero(self):
        obs = [("2025-01-01", 100.0), ("2025-04-01", 100.0)]
        self.assertAlmostEqual(annualized_qoq(obs)[0][1], 0.0)


class TestRecessionRanges(unittest.TestCase):
    def test_single_completed_recession(self):
        obs = [("2020-01-01", 0), ("2020-02-01", 1), ("2020-03-01", 1),
               ("2020-04-01", 1), ("2020-05-01", 0)]
        self.assertEqual(recession_ranges(obs), [
            {"start": "2020-02-01", "end": "2020-04-01", "ongoing": False}])

    def test_ongoing_recession_ends_at_last_observation(self):
        obs = [("2026-01-01", 0), ("2026-02-01", 1), ("2026-03-01", 1)]
        self.assertEqual(recession_ranges(obs), [
            {"start": "2026-02-01", "end": "2026-03-01", "ongoing": True}])

    def test_two_recessions(self):
        obs = [("1980-01-01", 1), ("1980-02-01", 0), ("1981-07-01", 1),
               ("1981-08-01", 1), ("1981-09-01", 0)]
        self.assertEqual(len(recession_ranges(obs)), 2)

    def test_no_recession(self):
        obs = [("2024-01-01", 0), ("2024-02-01", 0)]
        self.assertEqual(recession_ranges(obs), [])


class TestDirection(unittest.TestCase):
    def test_up_down_flat(self):
        self.assertEqual(direction(0.2), "up")
        self.assertEqual(direction(-0.2), "down")
        self.assertEqual(direction(0.004), "flat")
        self.assertEqual(direction(-0.004), "flat")


if __name__ == "__main__":
    unittest.main()
