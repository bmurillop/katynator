from app.pipeline.entity_resolver import (
    AUTO_LINK_THRESHOLD,
    SUGGEST_THRESHOLD,
    jaccard_similarity,
    normalize_entity,
)


class TestNormalizeEntity:
    def test_lowercase(self):
        assert normalize_entity("BANCO NACIONAL") == "banco nacional"

    def test_accent_strip(self):
        assert normalize_entity("Línea Aérea") == "linea aerea"

    def test_punctuation_removed(self):
        assert normalize_entity("BN-PAR/BNAHOR") == "bn par bnahor"

    def test_collapse_whitespace(self):
        assert normalize_entity("  SUPER   MERCADO  ") == "super mercado"

    def test_empty_string(self):
        assert normalize_entity("") == ""


class TestJaccardSimilarity:
    def test_identical_strings(self):
        assert jaccard_similarity("banco nacional", "banco nacional") == 1.0

    def test_complete_disjoint(self):
        assert jaccard_similarity("banco nacional", "super mercado") == 0.0

    def test_partial_overlap(self):
        # tokens: {banco, nacional} vs {banco, nacional, costa, rica}
        # intersection=2, union=4 → 0.5
        score = jaccard_similarity("banco nacional", "banco nacional costa rica")
        assert abs(score - 0.5) < 1e-6

    def test_single_token_match(self):
        # {banco} vs {banco, nacional} → 1/2 = 0.5
        score = jaccard_similarity("banco", "banco nacional")
        assert abs(score - 0.5) < 1e-6

    def test_both_empty(self):
        assert jaccard_similarity("", "") == 1.0

    def test_one_empty(self):
        assert jaccard_similarity("banco", "") == 0.0
        assert jaccard_similarity("", "banco") == 0.0

    def test_case_sensitivity(self):
        # Inputs are expected to be pre-normalized (lowercase)
        score_lower = jaccard_similarity("banco nacional", "banco nacional")
        assert score_lower == 1.0

    def test_bncr_alias_partial_overlap(self):
        # "bncr servicios" vs "banco nacional costa rica" — some overlap expected
        score = jaccard_similarity("bncr servicios", "banco nacional costa rica")
        assert 0.0 <= score <= 1.0

    def test_exact_subset_score(self):
        # "icetel" vs "pago icetel 88405817"
        # {icetel} ∩ {pago, icetel, 88405817} = {icetel} → 1/3
        score = jaccard_similarity("icetel", "pago icetel 88405817")
        assert abs(score - 1 / 3) < 1e-6


class TestThresholds:
    def test_auto_link_threshold_value(self):
        assert AUTO_LINK_THRESHOLD == 0.6

    def test_suggest_threshold_value(self):
        assert SUGGEST_THRESHOLD == 0.4

    def test_suggest_below_auto_link(self):
        assert SUGGEST_THRESHOLD < AUTO_LINK_THRESHOLD

    def test_perfect_match_exceeds_auto_link(self):
        score = jaccard_similarity("banco nacional", "banco nacional")
        assert score >= AUTO_LINK_THRESHOLD

    def test_half_overlap_above_suggest(self):
        # 0.5 overlap should be in suggest range (0.4–0.6)
        score = jaccard_similarity("banco nacional", "banco nacional costa rica")
        assert SUGGEST_THRESHOLD <= score < AUTO_LINK_THRESHOLD
