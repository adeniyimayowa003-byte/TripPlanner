"""Test-first exact currency contracts; these are not exchange-rate tests."""

from decimal import Decimal

import pytest

from phase8_helpers import api_symbol


CODES = ("EUR", "NGN", "GBP", "USD", "JPY", "ZAR")


@pytest.mark.parametrize("code", CODES)
def test_currency_registry_has_exact_approved_precision_and_bounds(code):
    get_currency = api_symbol("currencies", "get_currency")
    currency = get_currency(code)
    assert currency.code == code
    assert currency.precision == (0 if code == "JPY" else 2)
    assert currency.quantum == Decimal("1" if code == "JPY" else "0.01")
    assert currency.minimum == currency.quantum
    assert currency.maximum == Decimal("1000000" if code == "EUR" else "1000000000")
    assert all(isinstance(value, Decimal) for value in (currency.quantum, currency.minimum, currency.maximum))


@pytest.mark.parametrize("code", [None, True, 1, "", "eur", " EUR", "EUR ", "XXX", "USD<script>"])
def test_currency_registry_rejects_unknown_codes_instead_of_guessing_eur(code):
    get_currency = api_symbol("currencies", "get_currency")
    with pytest.raises(ValueError, match=r".+"):
        get_currency(code)


def test_currency_metadata_cannot_be_mutated_for_other_callers():
    get_currency = api_symbol("currencies", "get_currency")
    metadata = get_currency("JPY")
    with pytest.raises((AttributeError, TypeError)):
        metadata.precision = 2
    assert get_currency("JPY").precision == 0


@pytest.mark.parametrize("code", CODES)
@pytest.mark.parametrize("raw", ["300", " 300 ", "1"])
def test_currency_budget_parser_returns_decimal_at_its_currency_precision(code, raw):
    parse_budget = api_symbol("money", "parse_budget")
    amount = parse_budget(raw, currency=code)
    assert amount == Decimal(raw.strip())
    assert isinstance(amount, Decimal)
    assert amount.as_tuple().exponent == (0 if code == "JPY" else -2)


@pytest.mark.parametrize("code", ["EUR", "NGN", "GBP", "USD", "ZAR"])
@pytest.mark.parametrize("raw,expected", [("0.01", "0.01"), ("300.5", "300.50"), ("0.10", "0.10")])
def test_two_decimal_currencies_preserve_minor_units(code, raw, expected):
    parse_budget = api_symbol("money", "parse_budget")
    assert str(parse_budget(raw, currency=code)) == expected


@pytest.mark.parametrize("code", CODES)
def test_budget_boundary_is_in_native_units_not_a_hidden_conversion(code):
    parse_budget = api_symbol("money", "parse_budget")
    maximum = "1000000" if code == "EUR" else "1000000000"
    assert parse_budget(maximum, currency=code) == Decimal(maximum)
    minimum = "1" if code == "JPY" else "0.01"
    assert parse_budget(minimum, currency=code) == Decimal(minimum)
    with pytest.raises(ValueError, match=r".+"):
        parse_budget(str(Decimal(maximum) + Decimal(minimum)), currency=code)


@pytest.mark.parametrize("raw", ["0.01", "1.0", "300.00", "300.5", "300.50"])
def test_jpy_fractional_syntax_is_not_silently_rounded(raw):
    parse_budget = api_symbol("money", "parse_budget")
    with pytest.raises(ValueError, match=r".+"):
        parse_budget(raw, currency="JPY")


@pytest.mark.parametrize("code", CODES)
@pytest.mark.parametrize("raw", [None, True, 300, "", "0", "-1", "+1", "1,000", "3e2", "NaN", "Infinity", "USD 300", "0.001", "9" * 1000])
def test_invalid_native_currency_budget_cannot_become_zero_or_another_amount(code, raw):
    parse_budget = api_symbol("money", "parse_budget")
    with pytest.raises(ValueError, match=r".+"):
        parse_budget(raw, currency=code)


@pytest.mark.parametrize("code,budget,days,expected", [
    ("EUR", "100.01", 3, "33.34"), ("USD", "100.01", 3, "33.34"),
    ("NGN", "1000000000.00", 14, "71428571.43"),
    ("GBP", "0.01", 2, "0.01"), ("ZAR", "0.03", 2, "0.02"),
    ("JPY", "100", 3, "33"), ("JPY", "101", 2, "51"), ("JPY", "1", 2, "1"),
])
def test_daily_allowance_rounds_display_only_at_the_currency_quantum(code, budget, days, expected):
    daily_allowance = api_symbol("money", "daily_allowance")
    original = Decimal(budget)
    result = daily_allowance(original, days, currency=code)
    assert str(result) == expected
    assert original == Decimal(budget)


@pytest.mark.parametrize("code,raw,expected", [
    ("JPY", "0", "0"), ("JPY", "300", "300"), ("JPY", "50.5", "51"),
    ("EUR", "0", "0.00"), ("NGN", "300.5", "300.50"),
    ("GBP", "33.335", "33.34"), ("USD", "18", "18.00"), ("ZAR", "0.1", "0.10"),
])
def test_money_formatter_uses_the_requested_precision_without_currency_conversion(code, raw, expected):
    format_money = api_symbol("money", "format_money")
    assert format_money(Decimal(raw), currency=code) == expected


@pytest.mark.parametrize("function,arguments", [
    ("parse_budget", ("10",)), ("format_money", (Decimal("10"),)),
    ("daily_allowance", (Decimal("10"), 3)),
])
def test_money_helpers_do_not_fall_back_to_eur_for_an_unknown_currency(function, arguments):
    helper = api_symbol("money", function)
    with pytest.raises(ValueError, match=r".+"):
        helper(*arguments, currency="XXX")


def test_legacy_eur_calls_remain_an_explicit_compatible_default():
    from money import daily_allowance, format_money, parse_budget

    assert str(parse_budget("300.5")) == "300.50"
    assert str(daily_allowance(Decimal("100.01"), 3)) == "33.34"
    assert format_money(Decimal("18")) == "18.00"
