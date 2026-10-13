import re

_WS_RE = re.compile(r"\s+")
_VERB_SEP_RE = re.compile(r"[^\w]+", re.UNICODE)


def normalize(text: str | None) -> str:
    """Техническая нормализация для user-пар: trim + сжатие пробелов + lower."""
    if not text:
        return ""
    return _WS_RE.sub(" ", text.strip()).lower()


def normalize_verb(text: str | None) -> str:
    """Нормализация для verb-пар: любые не-словесные символы → пробел, сжатие, lower."""
    if not text:
        return ""
    lowered = text.lower()
    spaced = _VERB_SEP_RE.sub(" ", lowered)
    return _WS_RE.sub(" ", spaced).strip()


def is_empty(text: str | None) -> bool:
    return normalize(text) == ""


def answers_match(user_answer: str, expected: str) -> bool:
    return normalize(user_answer) == normalize(expected)


def answers_match_verb(user_answer: str, expected: str) -> bool:
    return normalize_verb(user_answer) == normalize_verb(expected)
