# Ledgers & file contracts

All ledgers are JSONL, one record per line, append-only, in `desk/`.

## fx_orders.jsonl — every order placed
`{"side":"sell_limit","pair":"USD_JPY","units":-215,"price":156.12,"stop":"156.265","tp":"","trail":"0.145","id":"4160","ts":"..."}`
Closes log with `"side":"close"`.

## calls.jsonl — every directional call (entries, declines, cancels)
Written by `call.py log PAIR up|down "note"`. Each call records the mid at
call time and is scored automatically at 15/30/60m against MIN_MOVE.
**Log declined trades too** — the counterfactual ledger is how cautions get
promoted or retired. One call per thesis; don't double-log the same idea.

## coils.jsonl — every coil/shelf break across the basket
Written by `coil_log.py` (run in a loop). `coil_log.py score` buckets all
breaks by burst/body/tide/day-direction/re-break count at 15/30/60m.
Nothing becomes a filter before n≥20 per bucket.

## .fx_plan — the partial-TP instruction (one line, consumed on fill)
`PAIR side half tp` — e.g. short 415 USD_JPY with partial 208 @ 155.610:
`USD_JPY buy 208 155.610`
**side = the side of the partial ORDER** (buy closes a short, sell closes a
long). The watcher places it on fill detection and deletes the file. Wrong
side = a marketable order that ADDS to your position, unprotected.

## run/desk.log — the feeds' output (grepped by the watcher)
Line prefixes: `FX <PAIR>` (focus bars) · `FX SCAN` (basket) ·
`FX !!` (live-pair alerts) · `MANFORD` (zone lane states).
