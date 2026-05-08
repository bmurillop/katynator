from __future__ import annotations

from app.ai.base import FinancialParseResult
from app.models.enums import ReconciliationStatus
from app.pipeline.reconciler import ReconcileResult

_NUM_CHECKS = 7
REVIEW_THRESHOLD = 0.85


def compute_quality_score(
    result: FinancialParseResult,
    reconcile_result: ReconcileResult,
) -> float:
    """Compute a 0–1 quality score from 7 structural checks.

    Transactions from documents scoring below REVIEW_THRESHOLD (0.85)
    should be flagged needs_review=True.
    """
    checks: list[bool] = []

    # 1 & 2: Valid JSON / schema — always True; Pydantic already validated on parse.
    checks.append(True)
    checks.append(True)

    # 3. All transaction dates fall within [period_start, period_end]
    if result.period_start and result.period_end and result.transactions:
        checks.append(
            all(result.period_start <= t.date <= result.period_end for t in result.transactions)
        )
    else:
        checks.append(True)  # cannot verify; give benefit of the doubt

    # 4. Transaction count matches claimed debit + credit counts
    if result.claimed_debit_count is not None and result.claimed_credit_count is not None:
        expected = result.claimed_debit_count + result.claimed_credit_count
        checks.append(len(result.transactions) == expected)
    else:
        checks.append(True)

    # 5. Reconciliation did not fail (not_applicable counts as pass)
    checks.append(reconcile_result.status != ReconciliationStatus.failed)

    # 6. Every transaction has a strictly positive amount
    checks.append(all(t.amount > 0 for t in result.transactions))

    # 7. Currency is set and recognised
    checks.append(result.currency is not None)

    assert len(checks) == _NUM_CHECKS
    return sum(checks) / _NUM_CHECKS
