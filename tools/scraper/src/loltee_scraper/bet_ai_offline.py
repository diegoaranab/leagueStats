"""Isolated, read-only Bet AI candidate price evaluator (Phase 2A).

No API, scraping, brokerage, data refresh, scheduling, or bet placement.
This is NOT a predictive model: probabilities must be supplied with evidence.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from decimal import Decimal, ROUND_CEILING, InvalidOperation
import json
from pathlib import Path


def _decimal(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not a probability or price")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise ValueError("invalid numeric input") from exc
    if not number.is_finite():
        raise ValueError("non-finite numeric input")
    return number


def _timestamp(value):
    if not isinstance(value, str):
        raise ValueError("timestamp missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("timestamp requires timezone")
    return dt.astimezone(timezone.utc)


def evaluate(candidate: dict, asof: str) -> dict:
    """Return an auditable *simulated* decision, never a betting instruction."""
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be an object")
    now = _timestamp(asof)
    output = {"id": str(candidate.get("id", "")), "decision": "NO_BET", "reasons": [],
              "p_break_even": None, "minimum_decimal_odds": None, "ev_conservative": None}
    reasons = output["reasons"]
    source = candidate.get("source") or {}
    model = candidate.get("model") or {}
    price = candidate.get("price") or {}
    if not isinstance(source, dict):
        source = {}
    if not isinstance(model, dict):
        model = {}
    if not isinstance(price, dict):
        price = {}
    if candidate.get("mode") != "VALUE":
        reasons.append("non-VALUE or missing mode cannot pass the VALUE gate")
    if candidate.get("phase") != "PREGAME":
        reasons.append("only pregame candidates; live or unknown rejected")
    try:
        start = _timestamp(candidate.get("event_start"))
        recorded = _timestamp(price.get("recorded_at"))
        if not (recorded <= now < start):
            reasons.append("price/asof must be before event start")
        if not (0 <= (now - recorded).total_seconds() <= 1200):
            reasons.append("price older than 20 minutes or from the future")
    except ValueError:
        reasons.append("event/price timestamp missing or invalid")
    if not (source.get("status") == "VALID"
            and source.get("authorization_confirmed") is True
            and source.get("coverage_verified") is True):
        reasons.append("source not authorized/validated with coverage")
    if model.get("out_of_sample_calibrated") is not True:
        reasons.append("model lacks out-of-sample calibration")
    if not model.get("uncertainty_method"):
        reasons.append("uncertainty method missing")
    if not candidate.get("market_contract"):
        reasons.append("exact market contract missing")
    try:
        odds = _decimal(price.get("decimal_odds"))
        p = _decimal(model.get("p_central"))
        lower = _decimal(model.get("p_lower"))
        if not (odds > 1 and Decimal(0) < lower <= p < Decimal(1)):
            raise ValueError("price or probability out of bounds")
        output["p_break_even"] = float(Decimal(1) / odds)
        output["minimum_decimal_odds"] = float(
            (Decimal(1) / lower).quantize(Decimal("0.01"), rounding=ROUND_CEILING))
        output["ev_conservative"] = float(lower * odds - Decimal(1))
        if lower * odds <= Decimal(1):
            reasons.append("insufficient price under conservative probability")
    except ValueError:
        reasons.append("price/probability missing, implausible or malformed")
    if not reasons:
        output["decision"] = "VALUE_CANDIDATE_REQUIRES_HUMAN_CHECK"
    return output


def main():
    parser = argparse.ArgumentParser(description="Offline simulated-only Bet AI gate")
    parser.add_argument("input", help="local JSON: {asof, candidates[]}")
    args = parser.parse_args()
    payload = json.loads(Path(args.input).read_text(encoding="utf-8"))
    reports = [evaluate(candidate, payload["asof"]) for candidate in payload["candidates"]]
    print(json.dumps({"mode": "SHADOW_ONLY", "results": reports}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()