"""Shared fixtures for pipeline unit tests.

The BNCR sample statement (samples/200020007143295.pdf) gives us the ground truth:
  - 44 debits totalling 8927.45 USD
  - 2 credits totalling 8203.21 USD
  - Opening 1139.64, closing 415.40
  - Balance equation: 1139.64 + 8203.21 - 8927.45 = 415.40 ✓
"""
from datetime import date, datetime, timezone
from decimal import Decimal
from uuid import uuid4

import pytest

from app.ai.base import FinancialParseResult, ParsedTransaction
from app.models.enums import Currency, TransactionDirection


def _debit(d: str, amount: str, desc: str = "TEST") -> ParsedTransaction:
    return ParsedTransaction(
        date=date.fromisoformat(d),
        description=desc,
        amount=Decimal(amount),
        direction=TransactionDirection.debit,
    )


def _credit(d: str, amount: str, desc: str = "TEST CREDIT") -> ParsedTransaction:
    return ParsedTransaction(
        date=date.fromisoformat(d),
        description=desc,
        amount=Decimal(amount),
        direction=TransactionDirection.credit,
    )


@pytest.fixture()
def bncr_result() -> FinancialParseResult:
    """FinancialParseResult mirroring the BNCR April-2026 sample statement."""
    txns: list[ParsedTransaction] = [
        _debit("2026-03-23", "6.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-03-23", "114.38", "YOCK ZUNIGA PAOLA/ANGIE 201613"),
        _debit("2026-03-25", "17.51", "YOCK ZUNIGA PAOLA/CHUCHU ROJO"),
        _debit("2026-03-26", "69.87", "YOCK ZUNIGA PAOLA/MESITAS TERRAZA"),
        _debit("2026-03-30", "6.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-03-30", "76.59", "YOCK ZUNIGA PAOLA/GRETEL Y SUPERTACO"),
        _debit("2026-03-30", "109.41", "MURILLO PANIAGUA BERNAL/DIA DE LA FAMILIA"),
        _debit("2026-03-30", "547.05", "MURILLO PANIAGUA BERNAL/PAGO PRESTAMO ABR"),
        _credit("2026-04-01", "0.21", "BNCR/INTERESES GANADOS EN SU CUENTA DE AHORRO"),
        _credit("2026-04-01", "8203.00", "REVEALD HOLDINGS INC/TRANSFERENCIA INTERNACIONALTR"),
        _debit("2026-04-01", "300.00", "BERNAL MURILLO PANIAGUA/A MARZO 2026"),
        _debit("2026-04-01", "201.42", "MURILLO PANIAGUA BERNAL/PAGO M VALV 205760218"),
        _debit("2026-04-01", "357.67", "MURILLO PANIAGUA BERNAL/PAGO CCSS 0002057602189990"),
        _debit("2026-04-01", "29.24", "MURILLO PANIAGUA BERNAL/PAGO M VALV 111350914"),
        _debit("2026-04-01", "23.08", "MURILLO PANIAGUA BERNAL/PAGO ICETEL 88405817"),
        _debit("2026-04-01", "64.16", "MURILLO PANIAGUA BERNAL/PAGO ICELEC 624172500721"),
        _debit("2026-04-01", "37.13", "MURILLO PANIAGUA BERNAL/PAGO ICETEL 24541926"),
        _debit("2026-04-01", "26.89", "MURILLO PANIAGUA BERNAL/PAGO ICELEC 214843"),
        _debit("2026-04-01", "35.86", "MURILLO PANIAGUA BERNAL/PAGO ICELEC 453695"),
        _debit("2026-04-01", "102.64", "MURILLO PANIAGUA B/PAGO VISA 4831-89XX-XXXX-8185"),
        _debit("2026-04-01", "434.50", "MURILLO PANIAGUA B/PAGO VISA 4831-89XX-XXXX-8185"),
        _debit("2026-04-01", "1000.00", "BERNAL MURILLO PANIAGUA/PAGOS PRESTAMOS MAYO"),
        _debit("2026-04-01", "109.65", "OLGA ZUNIGA ALVARADO/PLANCHADO MAYO 2026"),
        _debit("2026-04-06", "6.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-04-06", "100.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-04-06", "200.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-04-06", "750.00", "PAOLA YOCK ZUNIGA/VARIOS"),
        _debit("2026-04-06", "163.49", "BN-PAR/BNCR-OP CREDITO : 001-0129-005-304"),
        _debit("2026-04-06", "687.09", "MURILLO PANIAGUA B/PAGO VISA 4831-26XX-XX"),
        _debit("2026-04-08", "152.99", "MURILLO PANIAGUA BERNAL/PARA SINPES"),
        _debit("2026-04-09", "120.35", "BNCR/RETIRO ATM CTA AHORROS DIFERENTE MONEDA"),
        _debit("2026-04-10", "100.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002371234"),
        _debit("2026-04-10", "200.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002457552"),
        _debit("2026-04-10", "60.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002457559"),
        _debit("2026-04-13", "6.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 010"),
        _debit("2026-04-13", "1713.71", "MURILLO PANIAGUA B/PAGO VISA 4831-26XX-XX"),
        _debit("2026-04-13", "132.16", "OLGA ZUNIGA ALVARADO/MEDICO OZA"),
        _debit("2026-04-13", "181.72", "YOCK ZUNIGA PAOLA/ANGIE 202616 BECA 36"),
        _debit("2026-04-13", "4.63", "MURILLO PANIAGUA BERNAL/COMISION CERTIFICACION"),
        _debit("2026-04-15", "15.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002207988"),
        _debit("2026-04-15", "120.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002390849"),
        _debit("2026-04-15", "26.55", "BN-PAR/ICETEL-No_TELEFONO : 86413248"),
        _debit("2026-04-15", "35.56", "YOCK ZUNIGA PAOLA/CHUCHU 2"),
        _debit("2026-04-15", "133.33", "YOCK ZUNIGA PAOLA/MY BT GB 60K INTERESES"),
        _debit("2026-04-16", "60.00", "BN-PAR/BNAHOR_NO-NUMERO DE CONTRATO : 01002377465"),
        _debit("2026-04-17", "289.82", "MURILLO PANIAGUA BERNAL/PAGO CPA PRESTAMO"),
    ]
    return FinancialParseResult(
        bank_hint="BNCR",
        account_hint="200-02-000-714329-5",
        person_hint="MURILLO PANIAGUA BERNAL",
        currency=Currency.USD,
        statement_date=date(2026, 4, 17),
        period_start=date(2026, 3, 20),
        period_end=date(2026, 4, 17),
        opening_balance=Decimal("1139.64"),
        closing_balance=Decimal("415.40"),
        claimed_debit_count=44,
        claimed_debit_total=Decimal("8927.45"),
        claimed_credit_count=2,
        claimed_credit_total=Decimal("8203.21"),
        transactions=txns,
    )
