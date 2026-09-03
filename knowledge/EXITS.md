# Exit Structure — partial, trail, hard stop

The measured finding that started everything (n=16 early trades, scored by
direction only): **direction was mostly right; the P&L leaked through exits.**
Everything here exists to plug that leak.

## The structure

1. **Partial at +1R** — half the position, banked mechanically via `.fx_plan`
   the moment the trade is 1R in profit. Pays for the risk; the rest is free.
2. **Trailing stop at 1R distance** on the remainder, managed by the VENUE
   (OANDA server-side), not by you. It ratchets, never widens.
3. **Hard stop** — always attached to the entry order, at the invalidation.
   It is a safety net for wrongness you have NOT noticed — not a substitute
   for closing on deterioration you HAVE noticed.

## Trail vs. "structure exit" — measured, n=14 replayed trades

Every trailed trade was replayed bar-by-bar against structure-based exits
(exit on M5 phase flip). Result: the structure exit lost to the trail on 5 of
7 stack trades and won the TOTAL only because of one outlier runner. With the
best trade removed (leave-one-out), the trail was ahead by 1–2.6R in every
variant. **Verdict: trail stays.** The number that would earn a change is the
leave-one-out line at n≥20 — not the total, which one trade can flip.

## Mechanical policy

- Winning exit → LIMIT (rests, catches spikes). Losing exit → MARKET (certainty).
- Entry → limit at the stall; market only when a trigger fires at the level.
- Never hold through your session's rollover/close time. No new entries in
  the final half hour.

## The one discretionary release valve

On a runner that has given back most of its MFE inside a box, an M5
structure flip against you is a legitimate reason to close by hand before
the clock does. That is the ONLY hand exit the record supports, and it is
optional, not required.
