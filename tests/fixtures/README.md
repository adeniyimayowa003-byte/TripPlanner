# Frozen Phase 7 regression examples

`phase7-paris-catalog.json` is the original seven-place source catalog copied
before the Phase 8 expansion. `phase7-paris-snapshot.json` is the current working
version-1 canonical snapshot for Paris, three days, EUR 300, food/history,
relaxed pace and the family-friendly preference.

The canonical snapshot (without its final file newline) has SHA-256:

`faa80e3581949c832e06292142ee86c5125377fcc395b78b5b2171bab427cbfb`

It contains seven alternatives, six filled slots, EUR 103.00 scheduled and
EUR 197.00 unallocated. Future code must preserve these historical bytes/hash
when reading and writing this version-1 example; do not regenerate the oracle
with the future version-2 builder.

The separate helpers in `tests/phase8_helpers.py` create synthetic QA records
for currency/arithmetic tests. Those have QA names and example.com references.
They do not establish real foreign addresses, prices, suitability or licenses,
and must never be copied into the release travel catalog.
