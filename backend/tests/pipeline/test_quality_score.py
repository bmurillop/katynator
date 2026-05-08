from datetime import date
from decimal import Decimal

import pytest

from app.ai.base import FinancialParseResult, ParsedTransaction
from app.models.enums import Currency, ReconciliationStatus, TransactionDirection
from app.pipeline.quality_score import REVIEW_THRESHOLD, compute_quality_score
from app.pipeline.reconciler import ReconcileResult, reconcile


def _passed() -> ReconcileResult:
    return ReconcileResult(status=ReconciliationStatus.passed)


def _failed() -> ReconcileResult:
    return ReconcileResult(status=ReconciliationStatus.failed, details={"failures": ["x"]})


def _na() -> ReconcileResult:
    return ReconcileResult(status=ReconciliationStatus.not_applicable)


class TestQualityScoreBNRC:
    def test_bncr_sample_scores_above_threshold(self, bncr_result):
        recon = reconcile(bncr_result)
        score = compute_quality_score(bncr_result, recon)
        assert score >= REVIEW_THRESHOLD

    def test_bncr_sample_scores_1_0(self, bncr_result):
        recon = reconcile(bncr_result)
        score = compute_quality_score(bncr_result, recon)
        assert score == 1.0


class TestQualityScoreChecks:
    def _minimal(self, txns=None, currency=Currency.USD) -> FinancialParseResult:
        return FinancialParseResult(
            currency=currency,
            transactions=txns or [],
        )

    def test_failed_reconciliation_lowers_score(self):
        result = self._minimal()
        score = compute_quality_score(result, _failed())
        # Check 5 fails → 6/7
        assert score == pytest.approx(6 / 7)

    def test_not_applicable_reconciliation_passes_check(self):
        result = self._minimal()
        score = compute_quality_score(result, _na())
        assert score == 1.0

    def test_date_out_of_range_lowers_score(self):
        result = FinancialParseResult(
            currency=Currency.USD,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            transactions=[
                ParsedTransaction(
                    date=date(2026, 5, 15),  # outside period
                    description="X",
                    amount=Decimal("10"),
                    direction=TransactionDirection.debit,
                )
            ],
        )
        score = compute_quality_score(result, _passed())
        assert score == pytest.approx(6 / 7)

    def test_count_mismatch_lowers_score(self):
        result = FinancialParseResult(
            currency=Currency.USD,
            claimed_debit_count=5,
            claimed_credit_count=0,
            transactions=[
                ParsedTransaction(
                    date=date(2026, 4, 1),
                    description="X",
                    amount=Decimal("1"),
                    direction=TransactionDirection.debit,
                )
            ],
        )
        score = compute_quality_score(result, _passed())
        assert score == pytest.approx(6 / 7)

    def test_zero_amount_lowers_score(self):
        result = FinancialParseResult(
            currency=Currency.USD,
            transactions=[
                ParsedTransaction(
                    date=date(2026, 4, 1),
                    description="X",
                    amount=Decimal("0"),
                    direction=TransactionDirection.debit,
                )
            ],
        )
        score = compute_quality_score(result, _passed())
        assert score == pytest.approx(6 / 7)

    def test_missing_currency_lowers_score(self):
        result = FinancialParseResult(currency=None)
        score = compute_quality_score(result, _passed())
        assert score == pytest.approx(6 / 7)

    def test_all_checks_fail_possible(self):
        result = FinancialParseResult(
            currency=None,
            period_start=date(2026, 4, 1),
            period_end=date(2026, 4, 30),
            claimed_debit_count=10,
            claimed_credit_count=0,
            transactions=[
                ParsedTransaction(
                    date=date(2026, 5, 1),  # out of range
                    description="X",
                    amount=Decimal("0"),   # zero
                    direction=TransactionDirection.debit,
                )
            ],
        )
        # Checks 1&2 always pass; 3 fails, 4 fails, 5 fails, 6 fails, 7 fails → 2/7
        score = compute_quality_score(result, _failed())
        assert score == pytest.approx(2 / 7)
