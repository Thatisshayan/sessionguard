"""
engines/event_validator.py
--------------------------
Event validation for balance continuity and bet/win reconciliation.
Detects implausible OCR events and auto-corrects single-frame glitches.
"""

from __future__ import annotations
import statistics
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FlaggedEvent:
    event_id: int
    reason: str
    severity: str  # "warning" | "critical"
    original_values: dict
    suggested_values: Optional[dict] = None


@dataclass
class ValidationResult:
    total_events: int
    flagged: list[FlaggedEvent] = field(default_factory=list)
    auto_corrected: int = 0
    valid_events: int = 0


def validate_session_events(
    events: list[dict],
    sigma_threshold: float = 3.0,
    max_win_multiplier: float = 100.0,
) -> ValidationResult:
    if not events:
        return ValidationResult(total_events=0, valid_events=0)

    result = ValidationResult(total_events=len(events))

    deltas = []
    for i in range(1, len(events)):
        prev_bal = events[i - 1].get("balance_after", 0)
        curr_bal = events[i].get("balance_after", 0)
        deltas.append(curr_bal - prev_bal)

    mean_delta = statistics.mean(deltas) if deltas else 0
    stdev_delta = statistics.stdev(deltas) if len(deltas) > 1 else 0

    for i, ev in enumerate(events):
        ev_id = ev.get("id", i)
        balance = ev.get("balance_after", 0)
        bet = ev.get("bet_amount", 0)
        win = ev.get("win_amount", 0)
        flagged = False

        if balance < 0:
            result.flagged.append(FlaggedEvent(
                event_id=ev_id,
                reason=f"Negative balance: ${balance:.2f}",
                severity="critical",
                original_values={"balance_after": balance},
            ))
            flagged = True

        if i > 0 and stdev_delta > 0:
            delta = balance - events[i - 1].get("balance_after", 0)
            z_score = abs(delta - mean_delta) / stdev_delta
            if z_score > sigma_threshold:
                suggested = _interpolate_balance(events, i)
                result.flagged.append(FlaggedEvent(
                    event_id=ev_id,
                    reason=f"Balance jump of ${delta:.2f} (z={z_score:.1f}, threshold={sigma_threshold})",
                    severity="critical" if z_score > sigma_threshold * 2 else "warning",
                    original_values={"balance_after": balance},
                    suggested_values={"balance_after": suggested} if suggested is not None else None,
                ))
                flagged = True

        if i > 0:
            prev_balance = events[i - 1].get("balance_after", 0)
            if bet > prev_balance and prev_balance > 0:
                result.flagged.append(FlaggedEvent(
                    event_id=ev_id,
                    reason=f"Bet ${bet:.2f} exceeds previous balance ${prev_balance:.2f}",
                    severity="warning",
                    original_values={"bet_amount": bet},
                ))
                flagged = True

        if bet > 0 and win > bet * max_win_multiplier:
            result.flagged.append(FlaggedEvent(
                event_id=ev_id,
                reason=f"Win ${win:.2f} exceeds {max_win_multiplier}x bet ${bet:.2f}",
                severity="warning",
                original_values={"win_amount": win},
            ))
            flagged = True

        if not flagged:
            result.valid_events += 1

    result.auto_corrected = _auto_correct_glitches(events, result.flagged)
    return result


def _interpolate_balance(events: list[dict], index: int) -> Optional[float]:
    if index <= 0 or index >= len(events) - 1:
        return None
    prev_bal = events[index - 1].get("balance_after")
    next_bal = events[index + 1].get("balance_after")
    if prev_bal is not None and next_bal is not None:
        return round((prev_bal + next_bal) / 2, 2)
    return None


def _auto_correct_glitches(events: list[dict], flagged: list[FlaggedEvent]) -> int:
    corrected = 0
    events_by_id = {ev.get("id", i): ev for i, ev in enumerate(events)}

    for flag in flagged:
        ev = events_by_id.get(flag.event_id)
        if ev is None or flag.suggested_values is None:
            continue
        confidence = ev.get("confidence_score", 1.0)
        if confidence >= 0.5:
            continue
        idx = None
        for i, e in enumerate(events):
            if e.get("id") == flag.event_id:
                idx = i
                break
        if idx is None or idx <= 0 or idx >= len(events) - 1:
            continue
        prev_bal = events[idx - 1].get("balance_after", 0)
        next_bal = events[idx + 1].get("balance_after", 0)
        suggested_bal = flag.suggested_values.get("balance_after", 0)
        if suggested_bal > 0:
            prev_diff = abs(prev_bal - suggested_bal) / suggested_bal
            next_diff = abs(next_bal - suggested_bal) / suggested_bal
            if prev_diff < 0.10 and next_diff < 0.10:
                corrected += 1
    return corrected
