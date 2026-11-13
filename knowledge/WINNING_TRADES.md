# Winning trades: what they were and how they were made

[CASE_STUDIES.md](CASE_STUDIES.md) stops at the end of the practice phase.
This file picks up from there. It covers every winning trade from
2026-09-03 to 2026-09-25: the first live week, the live recipe trades that
followed, and the two demo lanes after that. Each one has its setup, its
order and its exit, and the last section says what the winners had in
common.

Every winner is USD/JPY on OANDA. Times are US Eastern. Risk was a fixed
unit of about 2% of a small account ($2 to $4 per trade), so the dollar
figures are small by design and the R column is the one to read. "The
operator" is the human whose mandate the agent traded.

## Read this first: the full record

These winners are 18 of 54 trades, and the period as a whole lost money.

| Lane | Trades | W | L | Scratch | Net |
|---|---|---|---|---|---|
| Live FX, first live day (09-04) | 6 | 2 | 4 | 0 | −$3.97 |
| Live BTC nano futures (09-05 to 09-06) | 3 | 0 | 2 | 1 | −$6.49 |
| Live FX, the recipe (09-07 to 09-09) | 11 | 4 | 7 | 0 | −$2.87 |
| Demo, wave-map entry (09-10 to 09-25) | 30 | 11 | 18 | 1 | −$7.10 |
| Demo, the agent's own-rules lane (09-15 to 09-17) | 4 | 1 | 3 | 0 | −$4.24 |
| **Total** | **54** | **18** | **34** | **2** | **−$24.67** |

Two more facts belong beside that table:

- Of the 11 live recipe trades, the 8 that met every entry gate went
  4W/4L for +$1.18. The other 3 each broke a gate and all 3 lost.
- Replayed mechanically over 253 out-of-sample setups (June to August
  2026), the same entry rules averaged −0.24R per trade.

So the trades below are worked examples of the setup going right. They are
not evidence that the recipe has an edge.

## How the live wins were made

All six live winners followed the same six steps. Seven of the eleven live
FX losses skipped one of them.

1. **A declared tide.** `structure.py` reads the 15-minute chart as a leg
   or a build-up in one direction. No declared tide, no trade.
2. **A pullback to a level that already mattered**: a shelf, a prior high
   or low, a broken range edge. Depth is measured off the venue's real
   extreme, not a bar close.
3. **A rejection that has already printed.** A 1-minute bar pushes into the
   level and is thrown back, and the next bar confirms with a higher low
   (long) or a lower high (short). On the first live day, entries taken
   after a printed rejection went 2W/0L and entries placed in anticipation
   of one went 0W/4L.
4. **A limit at the edge of the confirmation bar.** If price has already
   moved past it, the limit rests there. It fills on the dip or it is
   cancelled when the premise breaks. It is never chased.
5. **A stop beyond the real extreme of the pullback**, at least 8 pips
   away, with size set so that distance equals the risk unit.
6. **A mechanical exit.** Half comes off at +1R on a limit that rests on
   the book from the moment of the fill. A venue trailing stop, equal to
   the stop distance, carries the other half.

## The six live winners

| # | Entry (ET) | Side | Entry → exit | Net | R | Held |
|---|---|---|---|---|---|---|
| L1 | Fri 09-04 00:50 | Long 3,500 | 156.281 → 156.357 avg | +$1.68 | +1.63 | 18 min |
| L2 | Fri 09-04 09:44 | Short 3,500 | 155.736 → 155.680 avg | +$1.26 | +0.51* | 7 min |
| L3 | Tue 09-08 03:08 | Long 2,460 | 153.825 → 153.951 / 153.833 | +$1.06 | +0.53 | 11 min |
| L4 | Tue 09-08 06:26 | Long 2,370 | 154.059 → 154.191 / 154.285 | +$2.72 | +1.36 | 52 min |
| L5 | Tue 09-08 11:48 | Long 2,882 | 154.197 → 154.304 / 154.271 | +$1.67 | +0.84 | 40 min |
| L6 | Tue 09-08 23:58 | Short 3,836 | 153.446 → 153.364 / 153.318 | +$2.60 | +1.30 | 30 min |

Where two exits are shown, the first is the +1R half and the second is the
runner. *L2's R is computed here from its 10.9-pip stop; the others come
from the trade records.

**L1, the first live trade.** The 15-minute and 5-minute charts both read
as a build-up higher, and the 1-minute was coiling on the 156.30 shelf,
which was the previous trade's exit level now acting as support. Buy limit
at 156.300, filled better at 156.281. Stop 156.235, trail 6.5 pips, half
off at +1R. The venue rejected the first order because USD/JPY margin on
this account is 5%, so the size was cut to 3,500 units and the real risk
was $1.03. Both halves closed green.

**L2, the second entry.** The 15-minute tide was down and the pullback was
rejected at 156.115. The first limit, at 155.940, was missed. Rather than
chase, the agent waited for the next rejection at 155.805 and sold its
underside. Stop 155.845 (11 pips), trail 11 pips, half off at +1R at
155.625.

**L3, the London open, operator asleep.** The 03:02 read declared a
15-minute up-leg. Price pulled back 17% of the leg into the 153.67 to
153.73 shelf, the 03:05 bar rejected it with a 4.2-pip body, and 03:06 made
a higher low. Limit at 153.825, stop 153.700 (12.5 pips, $2.00). The +1R
half filled at the 153.95 lid and the trail took the rest when the opening
range break failed. The plan-file poller missed the first touch of the
target, and a resting limit caught the next one two minutes later. Every
trade after this one rested the partial at the fill.

**L4, the largest.** A burst to 154.290 at 04:45 was a climax. The first
pullback after it was passed on purpose. The 15-minute chart re-declared at
the 06:15 close, and the second pullback at 06:20 drove into the coil
floor at 153.95 on heavy volume and left a 7.7-pip lower wick. 06:21
held a higher low. Limit at 154.060, filled 154.059 on the next dip, stop
153.930 (13 pips, $2.00). The partial was resting 31 seconds after the fill
and filled ten minutes later. The runner rode through three prior highs to
154.416 (+35.7 pips at best), survived two shakeouts, one of them 0.7 pips
above the trail, and closed at 154.285. Worst heat on the trade was 1.6
pips.

**L5, waiting for the tide.** The rejection and the confirmation both
printed at the 154.08 to 154.13 shelf while the 15-minute read had lapsed
back to consolidation, so no order went in. Four minutes later the 11:45
close re-declared the tide with every other step already true. Price was 3
pips past the entry by then, so the limit rested at 154.198 and filled at
154.197 on a dip. Stop 154.091 (10.7 pips). The partial filled at 154.304
and the trail took the runner at 154.271 after a prior shelf top sold it.
Waiting for the declaration cost four minutes and about a pip.

**L6, the Tokyo short.** A 36.8-pip down-leg, declared at the 23:45 close.
The first lid printed a weak rejection that broke, and it was not chased.
The pullback carried on to 153.46 to 153.49, 36% of the leg, where 23:56
opened at its high and closed at its low and 23:57 made a lower high. The
order was computed in advance at the confirmation close and sent inside
the same minute: sell limit 153.444, filled 153.446, stop 153.524 (the
8-pip floor). The +1R half filled at 153.364. The runner made two new lows
and was closed at market at 153.318 on the operator's word.

## The practice win that set up L2

Two hours before the first live trade, the second-entry rule had its first
rep on the practice account (Thu 09-03, 23:08). A buy limit at 156.000 missed when the 156.06
shelf broke first. The tide was intact, so the limit was repriced to the
shelf retest at 156.060 with the stop left at the original extreme, 155.925
(13.5 pips), and the size cut to keep the risk the same. It filled at
156.059, the shelf held three probes, and the Tokyo breakout carried it to
+13.9 pips on the half and +24.2 pips on the runner: **+1.40R in 55
minutes**. L2 was the same rule on the live account ten hours later.

## The eleven demo winners (wave-map entry)

After the out-of-sample replay, live trading stopped and testing moved to
a demo account at the same $2 risk unit. The entry changed. After a break,
wait for the first push and then the dip after it, enter at the dip, and
put the stop 5 pips past the dip. The operator's ruling for this lane was
that the rules get the trade in and the agent's read of the tape gets it
out. From 09-11 a gate was added: take only dips sitting within 5 pips of
the edge of the two-hour range. D-06 and D-09 were taken through it. The
09-24 and 09-25 trades are recorded as plain map entries, sold at the
live bid.

| # | Entry (ET) | Side | Entry → exit | Net | R | The exit read |
|---|---|---|---|---|---|---|
| D-05 | Thu 09-10 23:58 | Short | 154.390 → 154.346 | +$0.52 | +0.26 | New floor defended five times, the fifth through the coil's high |
| D-06 | Fri 09-11 06:06 | Long | 154.078 → 154.094 | +$0.40 | +0.20 | Shooting star under a hurdle on thinning buying |
| D-09 | Mon 09-14 19:16 | Long | 154.328 → 154.362 | +$0.46 | +0.20 | Doji rejecting the highs on heavier selling |
| D-10 | Thu 09-24, Tokyo | Short | 158.752 → 158.736 | +$0.21 | +0.11 | Three hammers and rising closes at the low |
| D-11 | Thu 09-24, Tokyo | Short | 158.414 → 158.386 | +$0.49 | +0.25 | Two hammers at the lows and a rising close |
| D-18 | Fri 09-25 06:31 | Short | 157.832 → 157.804 | +$0.43 | +0.21 | First strong rejection past +0.5R |
| D-20 | Fri 09-25 07:04 | Short | 157.746 → 157.666 | +$0.98 | +0.49 | First bounce bar closing near its high |
| D-22 | Fri 09-25 08:56 | Short | 157.561 → 157.491 | +$0.84 | +0.42 | A 5-second spike low rejected 12.6 pips |
| D-23 | Fri 09-25 09:18 | Short | 157.308 → 157.199 | +$1.38 | +0.69 | Flush bought back 5 pips on heavy ticks |
| D-28 | Fri 09-25 11:19 | Short | 157.391 → 157.362 | +$0.58 | +0.29 | First bounce bar closing on its high |
| D-30 | Fri 09-25 11:56 | Short | 157.368 → 157.246 | +$1.86 | +0.93 | See the note below |

What these show:

- **The edge of the range was where the entry worked.** D-06 was the first
  trade taken through the range-edge gate, with the dip 0.8 pips inside the
  two-hour low. D-09's dip sat exactly on the two-hour low and was defended
  on the heaviest ticks of the evening. D-05 was a short from the flat top
  of its box.
- **The exits were early, which is why the wins are small.** D-05 banked
  +0.26R where the tested rule's own time exit made +0.87R. D-09 banked
  +0.20R where it made +3.30R. On the fast tape of 09-25, exits read off
  closed 1-minute bars captured between 35% and 96% of the best close.
- **D-30 was a win with a bad process.** It was the best result of the day
  and the exit was taken on a swing signal that turned out to be a one-bar
  artifact, without checking price first. It is counted as a win and
  recorded as a mistake.

## The own-rules lane winner

For three sessions the operator had the agent write its own rules from
what it had measured, on the demo account. One of four trades won.

**Tue 09-15, London, long 3,440 at 155.000 → 155.047, +$1.03, +0.52R.**
The overnight range was fixed at 03:00 (154.628 to 154.953). A study of
earlier sessions said the first London break of that range held 11 times
in 14, with a median run of 25.7 pips. The direction was called up at
02:35, before the move. The 04:02 bar broke the top with a 3.2-pip body
and the break was joined at market. Price ran 24.0 pips, within 1.7 pips
of the study's median. The exit was written before the entry: out on a
lower high followed by a break of 155.08. That exit banked +4.7 pips. The
break then failed and round-tripped inside the hour, so holding to the
session close would have lost about 8 pips.

## What the winners had in common

- On the live winners, the entry came after the market had shown its hand:
  a printed rejection at a known level, in the direction of a declared
  tide. None of the six was an anticipation entry.
- All six live winners were limit orders at a price worked out before the
  order was sent.
- The stop sat beyond the real extreme and was not moved to fit the risk
  unit. Size moved instead.
- The exit was decided before the entry: a resting +1R partial and a venue
  trail on the live trades, a stated read or a written line on the demo
  trades.
- L2, L4, L6 and the practice win were each the second attempt at a setup
  whose first attempt was missed or deliberately passed. Second attempts
  also lost twice in the same period, so this describes the winners and is
  not a rule.

The losses, the passed trades and the rule changes they produced are in
[LESSONS.md](LESSONS.md).
