# The Elliott Stack — tide, wave, moment

> **Update, September 2026.** Live trading changed two things on this page.
> (1) The entry: do not pre-position at a stall. Wait for a rejection bar
> and then a confirmation bar to print at the level, and place the limit at
> the rejection bar's edge. On the first live day, pre-positioned entries
> went 0W/4L and entries after a printed rejection went 2W/0L. (2) The
> evidence: a mechanical replay of the entry over 253 out-of-sample setups
> averaged −0.24R per trade. [FIELD_NOTES.md](FIELD_NOTES.md) has the
> recipe as it finally stood and how it got there.
> [WINNING_TRADES.md](WINNING_TRADES.md) has the record.

The core read is three timeframes of the same wave logic (`desk/structure.py`):

| layer | TF | question | phases |
|---|---|---|---|
| **Tide** | M15 | which way does the session lean? | LEG_UP / LEG_DN / BUILDUP_HI / BUILDUP_LO / CONSOL |
| **Wave** | M5 | where in the swing are we? | same |
| **Moment** | M1 | is the entry forming RIGHT NOW? | same |

**The entry is always the same shape:** M15 declares a tide (leg or buildup on
the tide side) → an M5 pullback against the tide completes → M1 stalls on
fading volume at a measurable level → limit order at the stall, stop beyond
the pullback's real extreme, partial at +1R, trail the rest.

## What each phase means for you

- **LEG (printing)**: a leg in progress is NEVER entered. "DO NOT CHASE" is
  printed by the tool itself. The measured reason: by the time a leg is
  visible it is mostly done; M1-scale legs revert within ~a bar on average.
- **BUILDUP at the tide side**: compression before continuation — the wave is
  loading. This is where you pre-position at the stall.
- **CONSOL / no tide**: waves cut both ways. Stand flat. Most of the losing
  trades in this system's history were taken without a tide.

## The stall (the actual trigger)

A completed pullback shows up on M1 as: a push against the tide that gets
REJECTED (wick through, close back), then 5–15 minutes of narrowing range on
fading tick counts near the rejection. That band is the stall. The limit goes
at the band mid — not deeper (you'll miss the move waiting for a gift), not
at market (you're chasing).

## The stop (learned at a cost — see CASE_STUDIES.md #9 vs #10)

The invalidation is the pullback's REAL extreme — the spike high/low — plus a
spread buffer. NOT a tidy distance inside the wick. Two identical trades, 80
minutes apart: stop inside the wick = swept at the top tick for −1R; stop
above the spike = survived the identical retest and paid +1.38R. Size the
position to the stop distance, never the other way around.

## Cancel discipline

A resting limit is a bet on a premise. The premise dies when: the M15 tide
reading goes CONSOL, or the level goes stale (two legs printed since it was
measured), or price runs away without the pullback. Cancel immediately and
log it. Unfilled + right beats filled + wrong; both get logged as
counterfactuals so the ledger can tell you which happens more.

## What is measured vs. what is provisional

- M15 down-legs revert upward (+0.31 mean next-hour drift, n=8,772 bars);
  up-legs hold (+0.05). Shorts riding old extended down-legs fight reversion.
- Fresh legs (≤ ~2 average bars old) beat extended ones as entry context —
  but this carried 3 loud counterexamples in one night. T3. A caution, not a law.
- A coil/box breakout is NOT an entry in either direction (n=433 scored
  breaks): with-tide breaks won 86% on a trend day and 28% on a range day —
  the tide bucket reads the DAY'S REGIME, not the break. Both days agreed on
  one thing only: the pullback after the break is the entry, never the break.
