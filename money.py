"""Exact allowance parsing and display rules, independent of Flask."""

from decimal import Decimal, ROUND_HALF_UP
import re

from currencies import get_currency


# Keep the original EUR constants for historical snapshots and existing callers.
CENT = get_currency("EUR").quantum
MAX_BUDGET = get_currency("EUR").maximum
PLAIN_AMOUNT = re.compile(r"[0-9]+(?:\.[0-9]{1,2})?")
WHOLE_AMOUNT = re.compile(r"[0-9]+")


def parse_budget(raw, *, currency="EUR"):
    """Accept plain positive text in the requested currency's smallest unit."""
    spec = get_currency(currency)
    pattern = WHOLE_AMOUNT if spec.precision == 0 else PLAIN_AMOUNT
    if not isinstance(raw, str) or pattern.fullmatch(raw.strip()) is None:
        if spec.precision == 0:
            raise ValueError("Enter a whole JPY amount, such as 300.")
        label = "euro" if spec.code == "EUR" else spec.code
        raise ValueError(f"Enter a {label} amount with up to two decimal places, such as 300.50.")

    amount = Decimal(raw.strip())
    if not spec.minimum <= amount <= spec.maximum:
        minimum = format(spec.minimum, f",.{spec.precision}f")
        maximum = format(spec.maximum, f",.{spec.precision}f")
        raise ValueError(f"Enter an allowance between {spec.code} {minimum} and {spec.code} {maximum}.")

    return amount.quantize(spec.quantum)


def daily_allowance(budget, days, *, currency="EUR"):
    """Calculate a rounded display amount; never use it to filter ideas."""
    spec = get_currency(currency)
    return (budget / days).quantize(spec.quantum, rounding=ROUND_HALF_UP)


def format_money(amount, *, currency="EUR"):
    """Use the currency's display precision; this does not convert its value."""
    spec = get_currency(currency)
    rounded = amount.quantize(spec.quantum, rounding=ROUND_HALF_UP)
    return format(rounded, f".{spec.precision}f")

