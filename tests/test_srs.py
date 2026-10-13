from datetime import datetime, timedelta

import pytest

from app.domain import srs


@pytest.mark.parametrize(
    "current,expected",
    [
        (srs.NEW, srs.D1),
        (srs.D1, srs.D3),
        (srs.D3, srs.D7),
        (srs.D7, srs.D14),
        (srs.D14, srs.D30),
        (srs.D30, srs.ARCHIVE),
        (srs.ARCHIVE, srs.ARCHIVE),
    ],
)
def test_correct_transitions(current, expected):
    assert srs.next_state(current, True) == expected


@pytest.mark.parametrize(
    "current,expected",
    [
        (srs.NEW, srs.NEW),
        (srs.D1, srs.D1),
        (srs.D3, srs.D1),
        (srs.D7, srs.D3),
        (srs.D14, srs.D7),
        (srs.D30, srs.D14),
        (srs.ARCHIVE, srs.D14),
    ],
)
def test_wrong_transitions(current, expected):
    assert srs.next_state(current, False) == expected


def test_new_wrong_stays_new():
    assert srs.next_state(srs.NEW, False) == srs.NEW


def test_d30_correct_to_archive():
    assert srs.next_state(srs.D30, True) == srs.ARCHIVE


def test_archive_correct_stays_archive():
    assert srs.next_state(srs.ARCHIVE, True) == srs.ARCHIVE


def test_archive_wrong_to_d14():
    assert srs.next_state(srs.ARCHIVE, False) == srs.D14


def test_next_due_new_wrong_now():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert srs.next_due(srs.NEW, srs.NEW, now) == now


def test_next_due_d1_plus_one_day():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert srs.next_due(srs.NEW, srs.D1, now) == now + timedelta(days=1)


def test_next_due_archive_plus_30_days():
    now = datetime(2026, 1, 1, 12, 0, 0)
    assert srs.next_due(srs.ARCHIVE, srs.ARCHIVE, now) == now + timedelta(days=30)


def test_label_known():
    assert srs.label(srs.NEW) == "NEW"
    assert srs.label(srs.ARCHIVE) == "Архив"


def test_label_unknown_returns_input():
    assert srs.label("WHATEVER") == "WHATEVER"
    