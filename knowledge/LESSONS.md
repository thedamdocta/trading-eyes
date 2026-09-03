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
