# Trading Lessons — the living document

> This file is injected into every session by `hooks/lessons-inject.sh`.
> Update it after trades and sessions; keep it SHORT — every line costs
> context on every injection. Tiers carry confidence, not decoration:
> **T1** = taught by your user | **T2** = measured | **T3** = provisional,
> do NOT obey as law. Promote T3→T2 only when reps justify it. Delete what
> stops being true. A rule from two reps must never read like a law.

## THE TIDE IS ASYMMETRIC — T2 (8,772 bars) + T3 (trade sample)
M15 UP-legs hold (+0.05 next-hour drift); M15 DOWN-legs revert (+0.31).
Shorts riding old down-legs fight measured reversion. Fresh legs over
extended ones as entry context — T3, and it carried three loud
counterexamples in a single trending night. Caution, not law.

## THE BREAK IS NOT THE ENTRY — T3 (n=433 scored coil breaks, 2 sessions)
With-tide breakouts won 86% on a trend day and 28% on a range day — the
tide bucket reads the day's REGIME, not the break. No-tide breaks ≈ coin
flip both days. The only thing both days agreed on: enter the pullback
after the break, never the break.

## THE STOP LIVES BEYOND THE REAL EXTREME — T2 (paired live test)
Same read, same tide, same stall entry, 80 minutes apart: stop inside the
pullback's wick = swept at the top tick, −1R, move then paid 90+ pips
without you. Stop above the spike = survived the identical retest, +1.38R.
Size to the stop; never tighten the stop to afford more size.

## STRUCTURE IN, RULER OUT — T2 (n=14 replay)
Wave logic gets you in; the mechanical trail gets you out. Structure exits
lose to the trail on most trades and win totals only via one outlier —
leave-one-out, trail ahead 1–2.6R. Re-measure at n≥20.

## EXITS, NOT SELECTION, DECIDE P&L — T2 (n=16, the founding measurement)
Direction-only scoring beat the realized P&L. Targets in front of the
crowd, stops inside normal pullbacks, and holds through noticed
deterioration were the leaks. The partial+trail+hard-stop structure is the
patch. Respect it.

## SESSION-OPEN BREAKOUT SYSTEMS TRANSPLANT POORLY — T3 (n=3 sessions FX)
A stocks-open zone-breakout system (5-bar opening zone, break + retest +
3-red-2-green confirmation) went 0-for-11 breaks on FX session opens; the
one real fill entered 0.8p under the push high and lost −1R. FX opens do
not gap like equity opens. Keep zone alerts as data; trade the stack.

## THE PLAN FILE'S SIDE FIELD IS THE ORDER'S SIDE — T2 (cost −$0.05 live)
`.fx_plan` = `PAIR side half tp` where side is the side of the PARTIAL
ORDER (buy for a short, sell for a long). The wrong side places a
marketable order that ADDS naked units. After every fill, verify position
size and that stop AND trail are non-None.

## THE VENUE IS THE ONLY TRUTH — T1
`positions` on the venue decides what you hold. Not your memory, not the
log, not the last message. Check it at session start and after every fill,
close, and doubt.

## THE REJECTION PRINTS BEFORE THE ORDER — T1 + T2 (first live day)
Limits pre-positioned at a stall went 0W/4L; entries after a rejection bar
AND a confirmation bar had printed went 2W/0L. Flags, pennants, triangles
and channels are not stalls: a flat lid with rising lows resolves up. Wait
for both bars, then put the limit at the rejection bar's edge.

## REST THE +1R PARTIAL AT THE FILL — T2 (n=4 live)
The polled plan file missed a touch of the target that a resting limit
would have filled. Place the partial as a resting limit right after the
fill. Cancel it if the stop takes the whole position.

## THE TRAIL IS AT LEAST THE STOP DISTANCE — T2 (two live losses)
The venue trail arms at the fill. A broker-minimum trail inside the stop
IS the stop (−0.8R in 37 seconds). Pass the stop distance as the trail.

## DEPTH FROM THE VENUE EXTREME; STOP AT THE VENUE — T2
A pullback read 46% from minute closes and 73% from the real low. Measure
from the extreme. Attach the stop to the entry at the venue: a hand exit
slipped 4.6p in event tape, the venue stop about 0p (n=1 each).

## THE SPREAD IS A COST, NOT A WALL — T1
Spread ≤ 25% of the stop distance, hard cap 2.5p. A fixed 1.5p ceiling
shut out the whole Tokyo session.

## A CLIMAX VETOES THE FIRST PULLBACK, NOT THE NIGHT — T1
Skip the first pullback after a climax bar, a deep one (past ~half the
leg), and one where the tide has not re-declared. Otherwise the recipe
fires as usual.

## THE RECIPE AS CODED HAS NO MEASURED EDGE — T2 (253 out-of-sample setups)
A mechanical replay averaged −0.24R per trade, and no filter or chart-read
rescued it. Treat every entry as a forward test at the smallest size. The
full account is in FIELD_NOTES.md; the record is in WINNING_TRADES.md.
