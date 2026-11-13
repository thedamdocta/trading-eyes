# Field notes: how the desk traded after going live

The other files in this folder describe the system as it stood at the end
of the practice phase. This one covers what happened next: three weeks of
live and demo trading in September 2026, how the method changed along the
way, and the notes kept while it happened.

The results are in [WINNING_TRADES.md](WINNING_TRADES.md), which opens
with the full record: 54 trades, 18 winners, a net loss. Nothing here is a
claim that the method is profitable. It is a record of what was done, what
was measured, and what was learned.

Terms: the **tide** is the 15-minute read from `desk/structure.py` (see
[STRATEGY.md](STRATEGY.md)). A **lid** or **shelf** is a price level that
has already turned the market at least once. **R** is the risk unit: the
dollars lost if the stop is hit. "The operator" is the human whose mandate
the agent traded. Times are US Eastern and the instrument is USD/JPY on
OANDA unless marked.

## How the trading was done, phase by phase

### 1. The first live day (09-04): 6 trades, 2W/4L, −$3.97

The entry was the practice-phase stack: a declared tide, a pullback, a
limit at the stall. Five trades were on USD/JPY and one on AUD/USD. The
day split cleanly by entry type. Entries placed
after a rejection had printed went 2W/0L. Limits pre-positioned at a stall
before any rejection went 0W/4L.

Two venue facts were paid for that day. The trailing stop arms at the
fill, so a 6-pip trail on a fill inside a fast bar closed one trade in
four seconds. And margin differs by pair and by account: the first live
order was rejected because USD/JPY needed 5% margin where 2% had been
assumed.

### 2. Bitcoin nano futures (09-05 to 09-06): 3 trades, 0 wins, −$6.49

The same recipe on a fee-heavy product. A round trip cost about 60% of
the risk unit, which puts the break-even win rate near 65%. On FX the
spread was 10 to 15% of the unit and the break-even rate near 35%. The
operator parked the lane on that arithmetic.

It left notes that apply everywhere. One trade was held for a 730-point
target after it had run 420 points, and it finished at a scratch. That
same trade was managed from polled closed candles while the live chart
watch was down, which the operator ruled a breach of the system's
premise. Another had its stop moved up to fit the risk cap, which put it
inside the real low, and it was hit at the exact low of the bar.

### 3. The live recipe (09-07 to 09-09): 11 trades, 4W/7L, −$2.87

Two fast losses on 09-07 (22 seconds and 37 seconds) led to an audit of
every earlier winner. All of them shared one shape, and the operator had
the desk go back to it:

> declared tide → pullback to a level that mattered → a rejection bar
> prints → a confirmation bar prints → limit at the rejection bar's edge →
> stop beyond the real extreme → half off at +1R, trail the rest

The next day went 3W/2L. Rules were added as trades asked for them: the
spread gate, the climax clause, the resting partial, the two re-entry
rules. They are all in the checklist below. Then came three losses in a row in
the Tokyo session, and the operator paused the desk for proper analysis.

Of the 11 trades, the 8 that met every gate went 4W/4L for +$1.18. The 3
that broke a gate all lost.

### 4. The pause and the tests (09-09 to 09-10)

- **A mechanical replay.** The recipe was coded and run over 1-minute
  data. Out of sample (253 setups, June to August) it averaged −0.24R per
  trade with the recipe's exits and −0.12R holding for four hours. Five
  candidate filters (extending impulse, depth band, cooldown, rejection
  force, a regime filter) all failed between the training and the
  confirmation sample.
- **A blind chart study.** The operator pointed out that a coded replay is
  not the same as reading a chart. So 90 setup charts were rendered with
  the date and the future hidden and read one at a time, by the agent and
  by independent reader agents each given a different lens (the recipe, a
  skeptic, a discretionary scalper, tide only, and others). Under the
  recipe's exits, no reader found a profitable subset above noise.
- **An entry study.** One variant was positive in both samples: skip the
  break, wait for the first push and the dip after it, enter at the dip
  with the stop 5 pips past it, and use no trail, no breakeven and no
  partial. Out of sample it won 38% of 183 trades for +0.10R each. In
  sample it won 36% of 118 for +0.57R. The edge was all in the runners:
  without the best three trades it was flat, every early-protection
  variant measured worse, and it carried an 18R drawdown and a 14-trade
  losing streak.

### 5. The demo run (09-10 to 09-25): 30 trades, 11W/18L/1 scratch, −$7.10

The operator moved the desk to a demo account, at the same $2 unit, to
forward-test the second-push entry as a continuous "wave map" of pushes
and dips. Four things shaped the run.

- **Rules in, judgment out.** The first demo trade ran to +15.8 pips. The
  agent read three exit signals, took none because the tested rule said
  hold, and closed at −10.6. The operator's ruling: the rules decide the
  entry exactly as tested, and the agent's read of the live tape decides
  the exit, the minute the read is made.
- **The range edge.** Most early losers were reversal calls into the
  middle of a range. A gate was added: take a dip only if it sits within 5
  pips of the edge of the two-hour range. Every print the desk did not
  take was logged and scored on paper. Those stood at about 12 wins to 41
  losses by 09-18, and two of them were the largest winners of the run on
  paper (+2.0R and +3.7R).
- **Capture, not the maximum.** A green exit taken on a read is a win,
  even when the trade then runs further. The operator's point was that
  grading every exit against the best possible exit trains a trader to
  hold for more and give it back.
- **A fast tape breaks bar-close exits.** On 09-25 USD/JPY fell about 200
  pips with 1-minute bars of 5 to 16 pips. Exits read off closed bars were
  structurally late, and swing signals that need an 8-pip turn arrived 8
  pips late by construction. Entries after a push of under 3 pips went 2
  for 6.

One quiet day mattered as much as the fast one. On 09-14 the pair ground
152 pips in one direction on light volume. The tide was declared and
lapsed thirteen times, there were about twenty pullbacks, and exactly two
rejection bars. A system that needs a rejection finds almost nothing to
do on a drift.

### 6. The agent's own rules (09-15 to 09-17): 4 trades, 1W/3L, −$4.24

For three sessions the operator had the agent write and trade its own
rules on the demo account. Each rule had to come from a measurement, and
each trade had its direction call and its exit line written before entry.

The first idea was withdrawn before it filled. Its premise came from the
model's training knowledge, and a fact-check showed the premise was out of
date and backwards. That became a rule: every claim about the current
world is checked before it is traded.

On a central-bank day the plan was written beforehand and followed: no
trades in the half hour before the release, watch only through it, and at
most one trade afterwards on a frame written in advance. That one trade
lost. A hand-fired exit slipped 4.6 pips in the event tape and turned a
$2.00 risk into $2.70. The next trade attached its stop at the venue and
filled with about zero slippage.

On 09-25 the operator paused everything.

## The recipe as it finally stood

**In**

1. The tide is declared in the trade's direction: a leg or a build-up on
   the 15-minute read. Not consolidation, and never a leg still printing.
2. Price pulls back to a level that already mattered: a shelf, a range
   edge, a multi-touch ceiling, a level just broken.
3. A rejection bar prints at the level, and then a confirmation bar: a
   higher low and a higher close for a long, the mirror for a short.
4. A limit goes at the rejection bar's edge so the bounce fills it. If
   price has already left, the limit rests there. It is cancelled when the
   pullback's extreme breaks.
5. The stop goes past the venue's real extreme plus the spread, never
   closer than 8 pips. Size is computed from the stop.
6. The spread is at most 25% of the stop distance and never above 2.5
   pips.
7. After a climax bar, the first pullback is skipped. So is a deep one
   (past about half the leg) and one where the tide has not been
   re-declared.
8. After a stop, that pullback is finished. A new entry needs a new
   pullback. No third pullback on one leg, and nothing at a lid of a leg
   more than two hours old once it is past its second lid.
9. Flags, pennants, triangles and channels are not entries and not
   stalls.
10. If the first limit misses and the tide holds, one second try is
    allowed, with the stop at the original extreme.
11. No new entries from 16:30 and flat by 17:00, the daily rollover.
12. The live chart watch is running and the monitors are armed before the
    order. No eyes, no order.

**Out, live phase:** half off at +1R on a limit resting from the fill, a
venue trailing stop at the stop distance on the rest, and the hard stop.

**Out, demo phase:** no partial and no trail. The stop is never moved.
Stay while the wave is intact (higher lows for a long, lower highs for a
short). Get out the minute it breaks, the minute momentum fades on falling
volume at a push, or the minute the trade is clearly failing.

## The notes

Tiers follow [LESSONS.md](LESSONS.md): T1 was taught by the operator, T2
was measured, T3 is provisional and is not a rule.

### T1, from the operator

- **A rejection that has printed, never one that is expected.** A
  continuation pattern is a coin flip. A flat lid with rising lows under
  it is a triangle, and triangles there resolved upward.
- **The chart watch is live for the whole life of every trade.** Polled
  candles are a bar late and blind to the wick while it prints.
- **The spread is a cost, not a wall.** A fixed 1.5-pip ceiling shut out
  the whole Tokyo session. Three full setups on one leg were passed on it
  in one evening and all three reached +1R. The gate became a share of
  the stop.
- **A climax vetoes the first pullback, not the night.** A rule drawn
  from one loss had been keeping the desk out for hours.
- **Fees are a strategy input.** On the futures product the target had to
  be at least 400 points to clear the toll, and when the 400 printed, that
  was the trade.
- **The stop never moves to fit the risk cap.** Move the entry, cut the
  size, or pass.
- **Skipped setups get tracked.** Every close call that was passed got a
  record at the moment of the pass: the entry, stop and target it would
  have used and the one reason it was refused. Each was scored later from
  the venue's candles, so a filter changes on evidence and not on how the
  last trade felt. These records never count as wins.
- **Report as it happens.** One line per 1-minute bar while an order or a
  position is open, with the bar's time, and every order event in the
  minute it happens.

### T2, measured

- **Rest the +1R partial on the book at the fill.** The plan-file poller
  missed a touch that a resting limit would have filled. Cancel the
  partial if the stop takes the whole position.
- **The trail distance is at least the stop distance.** With the broker's
  minimum trail inside an 8.5-pip stop, the trail was the stop, and the
  trade lasted 37 seconds.
- **Measure pullback depth from the venue's extreme.** One pullback read
  as 46% from the minute closes and 73% from the real low.
- **Query the margin rate for the pair before sizing.**
- **Attach the stop at the venue.** By hand in event tape: 4.6 pips of
  slippage. Venue-attached in a fast reversal: about zero. One rep each.
- **Write an exit as one read.** "Three rising closes off the low" works.
  "A close above X on above-normal volume" gets half-met and stalls the
  exit. That happened three times in one session.
- **A swing signal during a trade means look at price.** One exit was
  taken on a swing that was an artifact of a single bar.
- **Signal age is not an edge.** An early table suggested fills within
  five minutes of the signal did better. A proper count (n=20, three ways
  of timing it) found nothing, and the idea was retired.
- **The recipe as coded has no measured edge.** See phase 4.

### T3, provisional

- A lid probed several times with rising lows under it is a base, and
  bases break. The rejection should be the first clean one at that lid
  (n=1, possibly 2).
- Rejection volume: 2.0x average won, 1.0x lost, 0.35x lost (n=3).
- The second pullback on the same leg went 0 for 2 live.
- A heavy bar at a low while the whole currency basket moves one way is
  absorption, not a climax, and it failed both times (n=2, no money on
  it).
- Waiting for the tide to be re-declared cost four minutes and about a
  pip on the one trade that waited. The two setups passed because the
  declaration had lapsed would both have won.
- Send the order inside the minute of the read, or read again. One send
  that went 45 seconds late filled after the level had already broken,
  and lost. Compute the entry, stop and size at the confirmation close
  and put nothing between the read and the send.
- A fill better than the limit is a warning that price has already moved
  through the level. Compute the stop from the actual fill (n=1).
- An instruction to trade more does not lower a gate (n=1).
- A wide overnight range (75 pips) round-tripped its break. The study
  behind that trade was built on 25 to 35 pip ranges.

## What did not hold up

- The mechanical recipe, out of sample.
- Every filter fitted to rescue it.
- Chart reading on the setups the code flagged, by the agent or by a
  panel.
- Signal age.
- Trading the first pullback after a climax. Three textbook rejections
  printed that way in one afternoon, none was taken, and all three would
  have been stopped.
- Holding a demo winner for a fixed outcome while a read said to leave.

## What this adds up to

The record did not turn positive. The parts that held their value are
procedural: wait for the print, keep the stop honest, let the venue hold
the risk, write the exit before the entry, score what was passed as
carefully as what was taken, and test a rule on data it has not seen
before trusting it.
