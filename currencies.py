"""Small, fixed currency rules for the approved destinations; no conversion."""

from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType


@dataclass(frozen=True, slots=True)
class CurrencySpec:
    """Shared metadata cannot be changed by a caller handling one trip."""

    code: str
    precision: int
    quantum: Decimal
    minimum: Decimal
    maximum: Decimal


def _spec(code, precision, maximum):
    quantum = Decimal("1" if precision == 0 else "0.01")
    return CurrencySpec(code, precision, quantum, quantum, Decimal(maximum))


_CURRENCIES = MappingProxyType({
    "EUR": _spec("EUR", 2, "1000000.00"),
    "NGN": _spec("NGN", 2, "1000000000.00"),
    "GBP": _spec("GBP", 2, "1000000000.00"),
    "USD": _spec("USD", 2, "1000000000.00"),
    "JPY": _spec("JPY", 0, "1000000000"),
    "ZAR": _spec("ZAR", 2, "1000000000.00"),
})


def get_currency(code):
    """Require a known canonical code instead of guessing a trip's currency."""
    if not isinstance(code, str) or code not in _CURRENCIES:
        raise ValueError("Choose a supported currency code: EUR, NGN, GBP, USD, JPY, or ZAR.")
    return _CURRENCIES[code]
