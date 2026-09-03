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

If the question is about PRICE STRUCTURE → API eyes, always.
If the question is about WHAT A PAGE SHOWS → screen eyes, calibrated.
If both could answer → API. The chart is a rendering of the data; go to
the data.
