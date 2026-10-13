from app.domain.normalization import answers_match, normalize


def test_lower_and_trim():
    assert normalize("  Warehouse  ") == "warehouse"


def test_multiple_spaces():
    assert normalize("take    responsibility") == "take responsibility"


def test_answers_match_case():
    assert answers_match("WAREHOUSE", "warehouse")


def test_strict_synonym_rejected():
    assert not answers_match("срок годности", "срок хранения")


def test_word_order_rejected():
    assert not answers_match("responsibility take", "take responsibility")

