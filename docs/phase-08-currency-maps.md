# Phase 8 — Currency and Maps Helpers

**Completed slice, 2026-10-26:** The currency and Maps helpers are implemented after their specification, plan, and validated failing tests. This is the first implementation slice of Phase 8. The six-city form, reviewed expanded catalog, visible Maps buttons, photos, v2 saved trips, and Windows/Android packages still need their remaining test gates and implementation.

**Later progress:** City profiles and loading/lookup/validation helpers are also complete; the [city-data guide](phase-08-city-data.md) records that delivery. The subsequent [server-form test checkpoint](phase-08-form-testing.md) has 1,209 passes and 242 inspected missing-feature failures before form changes. Counts below preserve the original currency/Maps delivery evidence.

## What changed and why

Three small Python files provide reusable logic without depending on a web page, database, or native app:

| File | Responsibility |
| --- | --- |
| [currencies.py](../currencies.py) | One fixed registry for EUR, NGN, GBP, USD, JPY, and ZAR, including precision and input limits. |
| [money.py](../money.py) | Parse allowance text, calculate rounded daily displays, and format amounts using the explicitly requested currency. Existing callers keep their EUR default. |
| [maps.py](../maps.py) | Build an encoded external Google Maps search URL from supplied place/location data, or return `None` when it is unusable. |

The website continues using its existing Paris/EUR flow. This delivery makes the underlying helpers available; future form and template integration will select the correct currency and show the Maps actions. The travel catalog, templates, CSS, JavaScript, and snapshot/storage modules are unchanged.

## How the currency code works

`CurrencySpec` is a frozen dataclass: a small record whose fields callers cannot change. The registry also uses a read-only mapping. One trip therefore cannot accidentally change another trip's JPY precision or EUR allowance limit.

Each record contains a code, number of decimal places, smallest monetary unit (`quantum`), minimum allowance, and maximum allowance. These maxima are software input limits, not recommended travel budgets or exchange-rate equivalents.

| Currency | Decimal places | Minimum allowance | Maximum allowance |
| --- | ---: | ---: | ---: |
| EUR | 2 | 0.01 | 1,000,000.00 |
| NGN | 2 | 0.01 | 1,000,000,000.00 |
| GBP | 2 | 0.01 | 1,000,000,000.00 |
| USD | 2 | 0.01 | 1,000,000,000.00 |
| JPY | 0 | 1 | 1,000,000,000 |
| ZAR | 2 | 0.01 | 1,000,000,000.00 |

`get_currency(code)` accepts a canonical supported code or raises `ValueError`. It does not silently interpret an unknown currency as EUR.

`parse_budget` first checks the currency rules, then the input text's format, then its allowed range. It constructs a `Decimal` from text so money arithmetic avoids binary floating-point errors. `quantize` returns the amount at the currency's precision. It never rounds fractional yen into an accepted JPY input.

For example, in the project's Python environment:

```python
from decimal import Decimal
from money import parse_budget, daily_allowance, format_money

parse_budget("300.5", currency="USD")       # Decimal('300.50')
parse_budget("300", currency="JPY")         # Decimal('300')
parse_budget("300.50", currency="JPY")      # raises ValueError

daily_allowance(Decimal("100"), 3, currency="JPY")  # Decimal('33')
daily_allowance(Decimal("100"), 3, currency="EUR")  # Decimal('33.33')
format_money(Decimal("33.335"), currency="GBP")    # '33.34'

parse_budget("300.5")                        # existing EUR default: Decimal('300.50')
```

The daily figure is for display. Existing recommendation/scheduling logic continues comparing `cost * days <= budget`; it does not use a rounded daily display to grant extra spending. Input syntax and range validation are different from display rounding.

**No conversion happens.** Asking to format `300` in JPY gives a whole-yen display of that value. It does not convert EUR 300 into an equivalent yen amount. The future form will derive currency from the destination and require acknowledgement when an entered amount changes currency.

## How the Maps code works

`build_maps_url(name, destination, location)` is a pure helper: its result depends on the supplied inputs, and it does not change them or contact a provider.

1. Require nonblank name, destination, and address, with no control characters or invalid text.
2. If coordinates are supplied, require both, reject booleans/non-finite/out-of-range values, and preserve their exact numeric position.
3. Build a query containing the name/address/city, or the validated latitude/longitude pair. Include a supplied usable Place ID only as the optional `query_place_id` parameter.
4. Use `urlencode` to keep spaces, accented/Japanese characters, ampersands, and other punctuation inside encoded query values. The HTTPS scheme, Google host, and search path are fixed in the code.
5. Require `api=1` and a final URL no longer than 2,048 characters; otherwise return `None`.

This follows [Google's Maps URLs documentation](https://developers.google.com/maps/documentation/urls/get-started), which documents the search format, encoding, length limit, and use without an API key. The helper imports URL-building utilities, not an HTTP client. Link construction works locally; loading the external map requires connectivity.

A missing or malformed location produces `None`, giving the future page an honest unavailable-location fallback. The helper does not research or verify an address: released data still needs source review. A valid URL is not proof of a correct real-world place, opening hours, accessibility, or an optimized route.

## Verification

The [historical foundation checkpoint](phase-08-testing.md) defined these tests before code changed. A fresh focused run immediately before implementation reproduced **197 failures and 41 passes** across the 238 currency, Maps, and legacy money cases.

After implementation:

| Check | Observed result |
| --- | --- |
| Currency, Maps, and original money tests | **238 passed**, no failures/errors/skips, in 0.27 seconds. |
| Entire collected suite | **1,159 passed, 110 remaining expected failures**, no errors/skips, in 16.57 seconds. |
| Original Phase 7 cases | All **943 pass**. |
| Previously passing cases that regressed | **0**, comparing individual test names/results with the foundation report. |
| Remaining catalog/profile/released-data cases | 52 expected failures for missing APIs/profiles and the unchanged seven-place Paris catalog. |
| Remaining v2 snapshot/storage cases | 58 expected failures for missing v2 build/decode/save support. |

Every remaining failure group was inspected. The full suite still exits with status 1 because later approved requirements are unfinished; this is not a claim that all of Phase 8 is green. No tests, expectations, frozen fixtures, skip markers, or dependency requirements were changed to obtain these results.

Ignored evidence is in `.tmp/phase8-core-red.xml`, `.tmp/phase8-core-green.xml`, `.tmp/phase8-core-full.xml`, and `.tmp/phase8-core-source-baseline.json`.

Of the **53 pre-edit fingerprinted source/asset/data/test/dependency files**, only the intended `money.py` changed. `currencies.py` and `maps.py` are new. Existing tests, source data, frozen examples, and other application files retain their hashes. Runs used fresh validated temporary directories and test databases. No browser interaction, real saved-trip edits, dependency installation, or native build was performed.

## Concepts you can explain in your presentation

- **Separation of concerns:** The pages collect/display information; these helpers handle reusable currency/URL rules.
- **Immutable data:** A frozen currency record protects shared rules from accidental changes.
- **Exact arithmetic and validation:** Decimal money, precision, limits, and user input format serve different purposes.
- **URL encoding:** Supplied text stays data inside a fixed external URL.
- **Test-first development:** We observed the relevant failures before implementing the code, then made that bounded group pass without changing the tests.
- **AI boundaries:** Explainable recommendations and greedy scheduling remain the AI-related behavior. Currency handling and URL generation support that flow; they are ordinary deterministic programming.

## Small practice tasks

1. Predict whether `300`, `300.50`, and `0.01` are accepted for JPY and USD. Check your answers with `parse_budget`.
2. Explain why JPY 100 split across three days displays JPY 33, while the affordability rule still uses the original total.
3. Read `maps.py` and identify the fixed host, `api=1`, and `urlencode`. Explain why an ampersand in a place name cannot add another URL parameter.
4. Explain why an absent saved location must produce an unavailable action rather than a guessed pin.

## Next increment

Define the remaining preferences/draft/server and actual planner-JavaScript tests, including honest currency-change acknowledgement, and prepare the legitimate migrations onto the frozen Paris fixture. Then connect reviewed city data, versioned saved content, form behavior, and visible Maps links. Photo and Windows/Android work retains its own test and real-artifact verification gates.
