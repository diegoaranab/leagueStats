"""Private, offline-only daily bankroll snapshot unit policy. No sportsbook access."""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import json
from pathlib import Path


def money(value: object) -> Decimal:
    if isinstance(value, bool):
        raise ValueError("Boolean is not a valid monetary amount")
    try:
        d = Decimal(str(value))
    except (ValueError, TypeError, InvalidOperation) as exc:
        raise ValueError("Invalid monetary amount") from exc
    if not d.is_finite() or d < 0:
        raise ValueError("Amount must be finite and nonnegative")
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def morning_snapshot(snapshot: dict) -> dict:
    """Calculate the 1U stake once from a dated, verified tracker reconciliation.

    A morning run stores the returned unit for the rest of that local day.
    Never credit the expected payout from unsettled tickets.
    """
    if not isinstance(snapshot, dict):
        raise ValueError("Snapshot must be an object")
    day = snapshot.get("snapshot_date")
    if not isinstance(day, str) or date.fromisoformat(day).isoformat() != day:
        raise ValueError("Invalid YYYY-MM-DD snapshot date")
    bankroll = money(snapshot.get("reconciled_bankroll_mxn"))
    exposure = money(snapshot.get("open_exposure_mxn"))
    if exposure > bankroll:
        raise ValueError("Open exposure cannot exceed bankroll")
    free_cash = bankroll - exposure
    minimum = Decimal("10.00")
    unit = max(minimum, (bankroll * Decimal("0.01")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP))
    verified = snapshot.get("reconciliation_confirmed") is True
    return {
        "snapshot_date": day,
        "source_tracker": str(snapshot.get("source_tracker") or ""),
        "status": "READY" if verified and snapshot.get("source_tracker") else "UNVERIFIED",
        "bankroll_mxn": str(bankroll),
        "open_exposure_mxn": str(exposure),
        "available_cash_mxn": str(free_cash),
        "one_unit_mxn": str(unit),
        "can_fund_one_unit": bool(verified and snapshot.get("source_tracker") and free_cash >= unit),
        "unit_locked_for_day": True,
        "note": "Read-only snapshot. New settlements change tomorrow's unit, not today's."
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline daily stake snapshot, no betting.")
    parser.add_argument("snapshot", help="Local JSON file with reconciled bankroll and open stake")
    args = parser.parse_args()
    payload = json.loads(Path(args.snapshot).read_text(encoding="utf-8"))
    print(json.dumps(morning_snapshot(payload), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
