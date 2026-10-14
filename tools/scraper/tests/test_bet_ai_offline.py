"""Offline test fixtures are synthetic; do not imply a validated prediction model."""
import unittest
from copy import deepcopy
from loltee_scraper.bet_ai_offline import evaluate


ASOF = "2026-10-14T12:00:00-06:00"
BASE = {
    "id": "fixture-001", "mode": "VALUE", "phase": "PREGAME",
    "event_start": "2026-10-14T14:00:00-06:00",
    "market_contract": "match winner series BO5",
    "source": {"status": "VALID", "authorization_confirmed": True,
               "coverage_verified": True},
    "model": {"p_central": 0.60, "p_lower": 0.55,
              "uncertainty_method": "synthetic lower confidence bound",
              "out_of_sample_calibrated": True},
    "price": {"decimal_odds": 2.0, "recorded_at": "2026-10-14T11:55:00-06:00"},
}


class GateTests(unittest.TestCase):
    def test_eligible_synthetic(self):
        r = evaluate(BASE, ASOF)
        self.assertEqual(r["decision"], "VALUE_CANDIDATE_REQUIRES_HUMAN_CHECK")
        self.assertEqual(r["minimum_decimal_odds"], 1.82)
        self.assertAlmostEqual(r["ev_conservative"], 0.1)

    def test_low_price(self):
        c = deepcopy(BASE); c["price"]["decimal_odds"] = 1.66
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_unverified_source(self):
        c = deepcopy(BASE); c["source"]["authorization_confirmed"] = False
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_no_model_validation(self):
        c = deepcopy(BASE); c["model"]["out_of_sample_calibrated"] = False
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_future_post_event_rejected(self):
        c = deepcopy(BASE); c["event_start"] = "2026-10-14T11:00:00-06:00"
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_stale_price(self):
        c = deepcopy(BASE); c["price"]["recorded_at"] = "2026-10-14T11:00:00-06:00"
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_live_ticket_exception(self):
        c = deepcopy(BASE); c["phase"] = "LIVE"
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_star_never_value(self):
        c = deepcopy(BASE); c["mode"] = "STAR_RECREATIONAL"
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_bad_probability(self):
        c = deepcopy(BASE); c["model"]["p_lower"] = 1.01
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")

    def test_nan_odds(self):
        c = deepcopy(BASE); c["price"]["decimal_odds"] = "NaN"
        self.assertEqual(evaluate(c, ASOF)["decision"], "NO_BET")


if __name__ == "__main__":
    unittest.main()