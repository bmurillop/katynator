from decimal import Decimal

import pytest

from app.ai.base import FinancialParseResult, ParsedTransaction
from app.models.enums import Currency, ReconciliationStatus, TransactionDirection
from app.pipeline.reconciler import ReconcileResult, reconcile


class TestReconcilePass:
    def test_bncr_sample_passes(self, bncr_result):
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.passed

    def test_details_populated_on_pass(self, bncr_result):
        result = reconcile(bncr_result)
        assert "actual_debit_count" in result.details
        assert result.details["actual_debit_count"] == 44
        assert result.details["actual_credit_count"] == 2

    def test_balance_equation_holds(self, bncr_result):
        # 1139.64 + 8203.21 - 8927.45 == 415.40
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.passed
        assert "failures" not in result.details


class TestReconcileNotApplicable:
    def test_no_claims_returns_not_applicable(self):
        result = reconcile(
            FinancialParseResult(
                currency=Currency.CRC,
                transactions=[
                    ParsedTransaction(
                        date=__import__("datetime").date(2026, 1, 1),
                        description="TIENDA",
                        amount=Decimal("1000"),
                        direction=TransactionDirection.debit,
                    )
                ],
            )
        )
        assert result.status == ReconciliationStatus.not_applicable

    def test_empty_transactions_no_claims(self):
        result = reconcile(FinancialParseResult(currency=Currency.USD))
        assert result.status == ReconciliationStatus.not_applicable


class TestReconcileFail:
    def test_wrong_debit_total_fails(self, bncr_result):
        bncr_result.claimed_debit_total = Decimal("9000.00")  # wrong
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed
        assert any("debit total" in f for f in result.details["failures"])

    def test_wrong_credit_total_fails(self, bncr_result):
        bncr_result.claimed_credit_total = Decimal("100.00")  # wrong
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed
        assert any("credit total" in f for f in result.details["failures"])

    def test_wrong_debit_count_fails(self, bncr_result):
        bncr_result.claimed_debit_count = 50  # wrong (actual is 44)
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed
        assert any("debit count" in f for f in result.details["failures"])

    def test_wrong_credit_count_fails(self, bncr_result):
        bncr_result.claimed_credit_count = 5  # wrong (actual is 2)
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed
        assert any("credit count" in f for f in result.details["failures"])

    def test_wrong_closing_balance_fails(self, bncr_result):
        bncr_result.closing_balance = Decimal("999.99")  # wrong
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed
        assert any("balance equation" in f for f in result.details["failures"])

    def test_within_tolerance_still_passes(self, bncr_result):
        # Off by exactly 0.01 — should still pass
        bncr_result.claimed_debit_total = bncr_result.claimed_debit_total + Decimal("0.01")
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.passed

    def test_just_over_tolerance_fails(self, bncr_result):
        bncr_result.claimed_debit_total = bncr_result.claimed_debit_total + Decimal("0.02")
        result = reconcile(bncr_result)
        assert result.status == ReconciliationStatus.failed

    def test_partial_claims_only_checks_present_fields(self):
        """If only debit_total is claimed, only check debit_total."""
        from datetime import date
        result = reconcile(
            FinancialParseResult(
                currency=Currency.USD,
                claimed_debit_total=Decimal("50.00"),
                transactions=[
                    ParsedTransaction(
                        date=date(2026, 1, 1),
                        description="A",
                        amount=Decimal("50.00"),
                        direction=TransactionDirection.debit,
                    )
                ],
            )
        )
        assert result.status == ReconciliationStatus.passed
