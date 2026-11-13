# Chart eyes — API first, screen when it matters

The desk has two kinds of eyes. Know which one you are using and why.

## 1. API eyes (primary — use these by default)

`structure.py`, `fx_desk.py`, `coil_log.py` read candles straight from the
venue's API. This is how the stack reads are made: exact OHLC, exact
volume, no rendering, no OCR error, works headless. **For any instrument
your venue serves candles for, the API is the better chart.** A human
watching TradingView and an agent reading the candle API are looking at
the same market; the agent's copy has more decimal places.

## 2. Screen eyes (the vision skill — when the data is only visual)

Some information exists only on a rendered page: an instrument your venue
does not serve, a chart with a human's drawings on it, a dashboard, a
broker UI. For those, the bundled vision skill is the workflow:

- **Watch a live chart page headlessly**: `browser_watch.py` (vision skill)
  opens a URL (e.g. a TradingView chart), captures on a cadence, and feeds
  `watch.py --source external` — the agent gets notified on change, no
  human screen needed.
- **Read a price/score region over time**: `read_text.py --digits` OCRs a
  declared region and checks the sequence is coherent (monotonic? stalled?
  reversed?). Calibrate the region FIRST with `region_calibrate.py` — a
  guessed region reads garbage confidently. (The desk's own
  `btc_desk.py` uses exactly this pattern: a screen-capture buffer + a
  calibrated region + staleness checks.)
- **Answer "did it move / is it stuck"**: one screenshot cannot tell a
  live chart from a frozen one. `see.py <video> --about "..."` measures
  over a span. A value that is SUPPOSED to update is always a time
  question.

## Known trap (measured, cost a real miss)

OCR of comma-grouped prices can split tokens — a "77,702" can read as 77.
Never act on a single OCR read of a price; require two coherent reads, and
prefer the API number whenever both exist.

## The rule of thumb

Flat, reading structure (the M15/M5/M1 stack, levels, volume history) →
API eyes: exact numbers, one call per read, no loop.
What a page shows → screen eyes, calibrated.

## In a trade, the screen eyes are primary — not optional (learned live, 2026-09-06)

A closed candle is a bar late. The API poller that stood in for the eyes on
one live trade read closed 1-minute bars every 30 seconds and never saw the
exit bar — a heavy rejection wick that closed near its open. The human
watching the chart saw it print and called it two bars ahead of the agent.
Result: a winning entry given back to a scratch. The user's ruling: **if the
eyes are not live on the chart while the trade is on, you will lose every
trade — this is why they were built.**

So, for the life of every trade:

- `browser_watch.py` on the instrument's chart (or its validated spot proxy)
  at ~2-second captures, and `btc_desk.py` / `fx_desk.py` reading the ring:
  price every ~4s, the legend's live OHLC every ~12s, the candle named while
  it is still printing, intra-bar level alerts from `levels.json`.
- **Check the capture ring at every session start, for every lane that
  could trade** — newest segment under 30 seconds old. An empty ring means
  the eyes are dark; no order goes in until they are back. Your user should
  never be the one to tell you the feed is down.
- The API is a budget, not a feed: one volume call per minute, position and
  order checks no faster than every 60 seconds, no candle-polling loops.
  A venue can cut off a key that hammers it; the eyes cost the venue nothing.
