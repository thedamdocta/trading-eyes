# Case studies — the trades that taught the system

Eleven closed practice trades under the full stack, anonymized. Risk was a
fixed ~1R dollar unit per trade; pips are weighted per position (partial and
runner averaged). Net: **+36.3 pips, 7W/4L; winners averaged 2.4× losers.**

| # | context | result | lesson |
|---|---|---|---|
| 1 | GBP_USD short, fresh M15 down-leg, early entry | +5.3p W | fresh legs pay |
| 2 | EUR_USD short, 30–60min into an extended leg | −3.7p L | the M15-scale bounce arrived on schedule (reversion, T2) |
| 3 | AUD_USD short, extended leg again | −4.8p L | same error same day — correction-as-trend |
| 4 | USD_JPY long, fresh M15 up-leg, pullback stall | +6.4p W | the recipe, long side |
| 5 | USD_JPY long, extended | −4.5p L | third extended-leg lesson |
| 6 | USD_JPY short, 7× break of a level, 3-bar confirm, limit at retest | +8.1p W | partial+trail's first clean win; trail took the runner early — the move ran +40p more (the trail-vs-structure question, measured later) |
| 7 | USD_CAD short, DELIBERATE extended-leg test (operator-approved) | +9.8p W | won by the ruler: MFE came 2h after the partial, price boxed 4h, the clock closed it. "Pays by the ruler, not by the leg" |
| 8 | USD_CHF short, only tide in an 11-pair basket, textbook stall | +4.2p W | scanning breadth finds the one tradeable pair |
| 9 | USD_JPY short, stall entry, **stop inside the pullback wick** | −8.9p L | swept at the top tick; price then fell 90+ pips. Direction right, stop address wrong |
| 10 | USD_JPY short, same read 80 min later, **stop above the real spike** | +20.3p W | survived the identical retest to within 1p of the old stop; partial +14.7p, runner +25.8p. The paired lesson with #9 |
| 11 | USD_JPY short, four-touch ceiling rejection, band-underside entry | +4.1p W | quick partial, trail protected the rest |

## The declined-trade counterfactuals that mattered

- Three extended-leg shorts declined on the fresh-over-extended caution
  during one trending night scored **+42p, +41p, +35p** as counterfactuals.
  The caution that saved trades 2/3/5 cost these. Tally: 4 for / 3 against.
  Still T3 — this is why declines get logged: the ledger arbitrates.
- A breakout chased nothing: entered on limit at the measured stall instead,
  0.5p above the eventual low of the pullback — and one night later the same
  discipline missed two fills entirely while the move left. Both outcomes
  logged. Unfilled + right costs nothing.

## Coinbase (spot, small account) — why FX became the lane

Real-money spot trading on a ~$100 account: taker fees consumed edges
(net −$4.31 over the test with $1.51 in fees on one round trip). Lessons
kept: maker-only exits where possible, fee-per-round-trip must be priced
into every target, and a small account's edge must exceed fees × 2. The
venue knowledge ships in COINBASE_NOTES.md; the module ships disabled.
