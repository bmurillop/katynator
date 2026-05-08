from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.pipeline.dedup import compute_dedup_key, normalize_description


class TestNormalizeDescription:
    def test_lowercase(self):
        assert normalize_description("SUPERMERCADO") == "supermercado"

    def test_accent_strip(self):
        assert normalize_description("Tiendá Rústica") == "tienda rustica"

    def test_punctuation_removed(self):
        assert normalize_description("PAGO/VISA 4831-89") == "pago visa 4831 89"

    def test_collapse_whitespace(self):
        assert normalize_description("  foo   bar  ") == "foo bar"

    def test_bncr_ref_id_stripped(self):
        # ≥6 digit prefix followed by space should be removed
        assert normalize_description("99837153 MURILLO PANIAGUA BERNAL/PAGO") == \
            "murillo paniagua bernal pago"

    def test_five_digit_prefix_not_stripped(self):
        # Only 5 digits — not a reference ID, should be kept
        result = normalize_description("12345 SOME MERCHANT")
        assert result.startswith("12345")

    def test_exactly_six_digits_stripped(self):
        result = normalize_description("123456 MERCHANT NAME")
        assert not result.startswith("123456")
        assert "merchant name" in result

    def test_ref_in_middle_not_stripped(self):
        # Only strip refs at the START
        result = normalize_description("PAGO 99837153 MURILLO")
        assert "99837153" in result

    def test_bncr_real_description(self):
        # From the actual parsed output
        norm = normalize_description("YOCK ZUNIGA PAOLA/ANGIE 201613")
        assert norm == "yock zuniga paola angie 201613"

    def test_empty_string(self):
        assert normalize_description("") == ""

    def test_only_ref_id(self):
        # Pure reference ID + nothing after space
        result = normalize_description("99837153 ")
        assert result == ""


class TestComputeDedupKey:
    def test_returns_64_char_hex(self):
        key = compute_dedup_key(
            uuid4(), date(2026, 4, 1), Decimal("100.00"), "debit", "supermercado"
        )
        assert len(key) == 64
        assert all(c in "0123456789abcdef" for c in key)

    def test_same_inputs_same_key(self):
        account_id = uuid4()
        d = date(2026, 4, 1)
        key1 = compute_dedup_key(account_id, d, Decimal("50.00"), "debit", "farmacia")
        key2 = compute_dedup_key(account_id, d, Decimal("50.00"), "debit", "farmacia")
        assert key1 == key2

    def test_different_account_different_key(self):
        d = date(2026, 4, 1)
        key1 = compute_dedup_key(uuid4(), d, Decimal("50.00"), "debit", "farmacia")
        key2 = compute_dedup_key(uuid4(), d, Decimal("50.00"), "debit", "farmacia")
        assert key1 != key2

    def test_different_direction_different_key(self):
        account_id = uuid4()
        d = date(2026, 4, 1)
        key1 = compute_dedup_key(account_id, d, Decimal("50.00"), "debit", "x")
        key2 = compute_dedup_key(account_id, d, Decimal("50.00"), "credit", "x")
        assert key1 != key2

    def test_amount_formatted_to_two_decimals(self):
        account_id = uuid4()
        d = date(2026, 4, 1)
        # Decimal("100") and Decimal("100.00") should produce the same key
        key1 = compute_dedup_key(account_id, d, Decimal("100"), "debit", "x")
        key2 = compute_dedup_key(account_id, d, Decimal("100.00"), "debit", "x")
        assert key1 == key2

    def test_ref_stripped_descriptions_collide(self):
        """Two statements with different reference IDs for the same transaction
        should produce the same dedup_key after normalization."""
        account_id = uuid4()
        d = date(2026, 3, 30)
        amount = Decimal("547.05")

        norm1 = normalize_description("99837153 MURILLO PANIAGUA BERNAL/PAGO PRESTAMO ABR")
        norm2 = normalize_description("12345678 MURILLO PANIAGUA BERNAL/PAGO PRESTAMO ABR")

        key1 = compute_dedup_key(account_id, d, amount, "debit", norm1)
        key2 = compute_dedup_key(account_id, d, amount, "debit", norm2)
        assert key1 == key2
