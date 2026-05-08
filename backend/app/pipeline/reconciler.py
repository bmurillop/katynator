from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from app.ai.base import FinancialParseResult
from app.models.enums import ReconciliationStatus, TransactionDirection

_TOLERANCE = Decimal("0.01")


@dataclass
class ReconcileResult:
    status: ReconciliationStatus
    details: dict[str, Any] = field(default_factory=dict)


def reconcile(result: FinancialParseResult) -> ReconcileResult:
    """Run the four reconciliation checks against the bank's claimed totals.

    Returns not_applicable when the document published no totals at all —
    this is a first-class outcome, not a failure.
    """
    has_any_claim = any(
        v is not None
        for v in [
            result.claimed_debit_total,
            result.claimed_credit_total,
            result.claimed_debit_count,
            result.claimed_credit_count,
        ]
    )
    if not has_any_claim:
        return ReconcileResult(status=ReconciliationStatus.not_applicable)

    debits = [t for t in result.transactions if t.direction == TransactionDirection.debit]
    credits = [t for t in result.transactions if t.direction == TransactionDirection.credit]
    actual_debit_total = sum(t.amount for t in debits) if debits else Decimal("0")
    actual_credit_total = sum(t.amount for t in credits) if credits else Decimal("0")

    details: dict[str, Any] = {
        "actual_debit_count": len(debits),
        "actual_credit_count": len(credits),
        "actual_debit_total": str(actual_debit_total),
        "actual_credit_total": str(actual_credit_total),
    }
    failures: list[str] = []

    # Check 1: debit total
    if result.claimed_debit_total is not None:
        diff = abs(actual_debit_total - result.claimed_debit_total)
        details["debit_total_diff"] = str(diff)
        if diff > _TOLERANCE:
            failures.append(
                f"debit total off by {diff:.2f} "
                f"(expected {result.claimed_debit_total}, got {actual_debit_total})"
            )

    # Check 2: credit total
    if result.claimed_credit_total is not None:
        diff = abs(actual_credit_total - result.claimed_credit_total)
        details["credit_total_diff"] = str(diff)
        if diff > _TOLERANCE:
            failures.append(
                f"credit total off by {diff:.2f} "
                f"(expected {result.claimed_credit_total}, got {actual_credit_total})"
            )

    # Check 3: counts
    if result.claimed_debit_count is not None:
        count_diff = len(debits) - result.claimed_debit_count
        details["debit_count_diff"] = count_diff
        if count_diff != 0:
            failures.append(
                f"debit count off (expected {result.claimed_debit_count}, got {len(debits)})"
            )

    if result.claimed_credit_count is not None:
        count_diff = len(credits) - result.claimed_credit_count
        details["credit_count_diff"] = count_diff
        if count_diff != 0:
            failures.append(
                f"credit count off (expected {result.claimed_credit_count}, got {len(credits)})"
            )

    # Check 4: balance equation  opening + credits - debits == closing
    if all(
        v is not None
        for v in [
            result.opening_balance,
            result.closing_balance,
            result.claimed_debit_total,
            result.claimed_credit_total,
        ]
    ):
        expected_closing = (
            result.opening_balance
            + result.claimed_credit_total
            - result.claimed_debit_total
        )
        diff = abs(expected_closing - result.closing_balance)
        details["balance_equation_diff"] = str(diff)
        if diff > _TOLERANCE:
            failures.append(
                f"balance equation off by {diff:.2f} "
                f"(expected closing {expected_closing:.2f}, "
                f"stated {result.closing_balance:.2f})"
            )

    if failures:
        details["failures"] = failures
        return ReconcileResult(status=ReconciliationStatus.failed, details=details)

    return ReconcileResult(status=ReconciliationStatus.passed, details=details)
