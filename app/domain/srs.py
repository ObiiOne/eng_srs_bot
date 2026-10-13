from datetime import datetime, timedelta

NEW = "NEW"
D1 = "D1"
D3 = "D3"
D7 = "D7"
D14 = "D14"
D30 = "D30"
ARCHIVE = "ARCHIVE"

ALL_STATES = (NEW, D1, D3, D7, D14, D30, ARCHIVE)

CORRECT_TRANSITIONS = {
    NEW: D1,
    D1: D3,
    D3: D7,
    D7: D14,
    D14: D30,
    D30: ARCHIVE,
    ARCHIVE: ARCHIVE,
}

WRONG_TRANSITIONS = {
    NEW: NEW,
    D1: D1,
    D3: D1,
    D7: D3,
    D14: D7,
    D30: D14,
    ARCHIVE: D14,
}

INTERVAL_DAYS = {
    NEW: 0,
    D1: 1,
    D3: 3,
    D7: 7,
    D14: 14,
    D30: 30,
    ARCHIVE: 30,
}

STATE_LABELS = {
    NEW: "NEW",
    D1: "1 день",
    D3: "3 дня",
    D7: "7 дней",
    D14: "14 дней",
    D30: "30 дней",
    ARCHIVE: "Архив",
}


def next_state(current: str, is_correct: bool) -> str:
    if current not in CORRECT_TRANSITIONS:
        raise ValueError(f"Unknown SRS state: {current}")
    return CORRECT_TRANSITIONS[current] if is_correct else WRONG_TRANSITIONS[current]


def next_due(current_state: str, new_state: str, reviewed_at: datetime) -> datetime:
    """reviewed_at — naive UTC. Для NEW+wrong возвращаем то же время."""
    if current_state == NEW and new_state == NEW:
        return reviewed_at
    days = INTERVAL_DAYS.get(new_state, 0)
    return reviewed_at + timedelta(days=days)


def label(state: str) -> str:
    return STATE_LABELS.get(state, state)
