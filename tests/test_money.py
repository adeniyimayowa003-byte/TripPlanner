"""Money rules for the activities and food allowance, using exact cents."""

from decimal import Decimal

import pytest


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("300", "300.00"),
        ("300.5", "300.50"),
        ("300.50", "300.50"),
        ("  300.50  ", "300.50"),
        ("0.01", "0.01"),
        ("1000000", "1000000.00"),
        ("1000000.00", "1000000.00"),
        ("0.10", "0.10"),
    ],
)
def test_budget_parser_accepts_plain_amounts_and_returns_decimal_cents(raw, expected):
    from money import parse_budget

    amount = parse_budget(raw)

    assert isinstance(amount, Decimal)
    assert amount == Decimal(expected)
    assert amount.as_tuple().exponent == -2


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "abc",
        "€300",
        "EUR 300",
        "1,000.00",
        "300,50",
        "3e2",
        "3E+2",
        "300.001",
        "300.000",
        "0",
        "0.00",
        "-0.01",
        "-300",
        "NaN",
        "Infinity",
        "-inf",
        "1000000.01",
        "999999999999999999999999999999999999999999",
    ],
)
def test_budget_parser_rejects_disallowed_formats_and_amounts_with_a_useful_error(raw):
    from money import parse_budget

    with pytest.raises(ValueError) as error:
        parse_budget(raw)

    assert str(error.value).strip()


def test_budget_parser_preserves_decimal_precision():
    from money import parse_budget

    assert parse_budget("0.10") + parse_budget("0.20") == Decimal("0.30")


@pytest.mark.parametrize(
    ("budget", "days", "expected"),
    [
        ("300.00", 3, "100.00"),
        ("100.00", 3, "33.33"),
        ("100.01", 3, "33.34"),
        ("0.01", 2, "0.01"),
        ("0.03", 2, "0.02"),
        ("1000000.00", 1, "1000000.00"),
    ],
)
def test_daily_allowance_rounds_to_cents_using_half_up(budget, days, expected):
    from money import daily_allowance

    total = Decimal(budget)

    daily = daily_allowance(total, days)

    assert isinstance(daily, Decimal)
    assert daily == Decimal(expected)
    assert daily.as_tuple().exponent == -2
    assert total == Decimal(budget), "Displaying a daily amount must not change the total."


@pytest.mark.parametrize(
    ("amount", "expected"),
    [("0", "0.00"), ("18", "18.00"), ("300.5", "300.50"), ("33.335", "33.34")],
)
def test_money_formatter_displays_two_decimal_places(amount, expected):
    from money import format_money

    assert format_money(Decimal(amount)) == expected
