"""Synthetic tests of snapshot rule, not a profitability claim."""
import unittest
from copy import deepcopy
from loltee_scraper.bet_ai_bankroll import morning_snapshot, money

BASE = {
    "snapshot_date": "2026-10-14",
    "reconciled_bankroll_mxn": "425.53",
    "open_exposure_mxn": "20.00",
    "reconciliation_confirmed": True,
    "source_tracker": "Bet_AI_8_tracker_2026-10-14_unidad_dinamica.xlsx",
}


class DailyUnitTests(unittest.TestCase):
    def test_current_bank(self):
        x = morning_snapshot(BASE)
        self.assertEqual((x["one_unit_mxn"], x["available_cash_mxn"]), ("10.00", "405.53"))
    def test_threshold(self):
        for amount,expected in [("999.99","10.00"),("1000.00","10.00"),("1300","13.00"),("1450","14.50"),("2000","20.00")]:
            s = deepcopy(BASE); s["reconciled_bankroll_mxn"] = amount; s["open_exposure_mxn"] = 0
            self.assertEqual(morning_snapshot(s)["one_unit_mxn"],expected)
    def test_float_rounding(self):
        s = deepcopy(BASE); s["reconciled_bankroll_mxn"] = 1450.0000000001
        self.assertEqual(morning_snapshot(s)["one_unit_mxn"],"14.50")
    def test_no_expected_payout_credit(self):
        s = deepcopy(BASE); s["unsettled_possible_return_mxn"] = 100000
        self.assertEqual(morning_snapshot(s)["one_unit_mxn"],"10.00")
    def test_deduct_open_only_from_cash(self):
        s = deepcopy(BASE); s["reconciled_bankroll_mxn"] = 1300; s["open_exposure_mxn"] = 110
        x = morning_snapshot(s)
        self.assertEqual(x["one_unit_mxn"],"13.00")
        self.assertEqual(x["available_cash_mxn"],"1190.00")
    def test_no_money(self):
        s = deepcopy(BASE); s["reconciled_bankroll_mxn"] = 0; s["open_exposure_mxn"] = 0
        self.assertFalse(morning_snapshot(s)["can_fund_one_unit"])
    def test_missing_source(self):
        s = deepcopy(BASE); s["source_tracker"] = ""
        self.assertEqual(morning_snapshot(s)["status"],"UNVERIFIED")
        self.assertFalse(morning_snapshot(s)["can_fund_one_unit"])
    def test_unverified_reconciliation(self):
        s = deepcopy(BASE); s["reconciliation_confirmed"] = False
        self.assertFalse(morning_snapshot(s)["can_fund_one_unit"])
    def test_bad_exposure(self):
        s = deepcopy(BASE); s["open_exposure_mxn"] = 600
        with self.assertRaises(ValueError): morning_snapshot(s)
    def test_negative(self):
        with self.assertRaises(ValueError): money("-1")
    def test_nonfinite(self):
        with self.assertRaises(ValueError): money("NaN")
    def test_bad_date(self):
        s = deepcopy(BASE); s["snapshot_date"] = "tomorrow"
        with self.assertRaises(ValueError): morning_snapshot(s)
    def test_bool_rejected(self):
        with self.assertRaises(ValueError): money(True)
    def test_cash_under_unit(self):
        s = deepcopy(BASE); s["open_exposure_mxn"] = "420"
        self.assertFalse(morning_snapshot(s)["can_fund_one_unit"])


if __name__ == "__main__":
    unittest.main()
