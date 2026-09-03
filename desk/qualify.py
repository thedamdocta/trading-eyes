#!/usr/bin/env python3
"""The entry gate, in ONE place. Long or short, any pair.

  python3 qualify.py USD_JPY short             # evaluate on the DEFAULT 15-min chart
  python3 qualify.py USD_JPY short --arm       # place the resting order if it passes
  python3 qualify.py USD_JPY short --tf M1     # force the old 1-min behaviour

TIMEFRAME (changed to M15 on 2026-08-31, the operator's call). Measured: the round-trip
cost is FIXED, the bar grows with timeframe, so bar/cost improves ~3x going from
1-min to 15-min and ~6x to hourly, on BOTH venues, with no change of broker:
    GBP/USD   1-min 1.10x | 5-min 1.84x | 15-min 3.09x | 60-min 6.26x
    BTC maker 1-min 1.23x | 5-min 2.30x | 15-min 3.04x | 60-min 9.04x
At 1-min the cost of a round trip is about the size of a whole bar, which is why
every exit rule tested needed ~90% direction accuracy to break even.
the operator manages the trade on the 1-MINUTE chart (price action, structure, volume);
the 15-min chart decides WHETHER and WHICH WAY, and sizes the stop.

WHY THIS FILE EXISTS (2026-08-31 07:23):
Two reasons, both discovered the same minute.

1. MEDIAN SPREAD, not a single quote. The scanner called USD/JPY 5.3x while
   an identical check seconds later said 4.0x. The ranges agreed; the SPREAD
   did not. Measured: over 24s the USD/JPY spread ran 1.4-1.7p, which swings
   the ratio 3.8x-4.6x ON AN UNCHANGED MARKET. The gate was partly measuring
   WHEN it sampled. It now takes the MEDIAN of several quotes.
   The 5x threshold is UNCHANGED — this fixes the measurement, not the rule.
   It cuts both ways: it declines setups a lucky tight tick would have passed.

2. The same 30 lines of gate logic had been retyped inline a dozen times
   tonight, each a chance to fudge a number under pressure. One file, one
   rule, same answer every time, auditable afterwards.

The three tests a setup must pass, all measured, none by eye:
  ratio  >= 5.0   the 15m range must cover the round-trip toll
  netR   >= 1.1   reward/risk AFTER paying the spread
  stop    > avg bar   a stop inside one bar's noise is not a stop
"""
import json, statistics, subprocess, sys, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
MIN_RATIO, MIN_NETR, SPREAD_SAMPLES = 5.0, 1.1, 9
STOP_FLOOR_PIPS = 4.5    # Rule 3 (the operator approved 2026-09-01): a 3p stop
# was killed by noise on ~10% of CORRECT reads and made the spread ~33% of
# risk. 4.5p floor cuts noise-outs to ~1% and drops the friction share;
# risk_units() shrinks size so dollar risk stays $0.20.
TIMEFRAME = "M5"         # decision chart; --tf overrides
ENTRY_DEPTH = 0.75       # fraction of the median pullback to wait for
ORDER_TTL_MIN = 60       # cancel an unfilled order after this many minutes
# ORDER_TTL (2026-08-31): the fill-rate study gave every entry ONE HOUR to fill;
# past that it counted as a non-fill. So an order older than 60 min is, by the
# same measurement, waiting for a pullback that is not coming. Cancel it and let
# the next signal stand on its own — that is EXPIRY, and it is different from
# ratcheting the entry up every few minutes to chase price, which the same study
# says is 4x worse (market entry -0.281R/setup vs -0.075R at 0.75x depth).
# ENTRY_DEPTH (2026-08-31): measured fill rates on M5 gate-qualified longs —
#   at market 99% fill, -0.281R per setup      (chasing is 4x worse)
#   0.50x     68% fill, -0.127R per setup
#   0.75x     53% fill, -0.075R per setup   <- chosen
#   1.00x     40% fill, -0.069R per setup
# 0.75x and 1.00x are worth the same per setup, but 0.75x fills a THIRD more
# often. the operator: reps are the scarce resource right now, so take the extra fills
# at equal expected value. (Absolute values are negative because this measures a
# MECHANICAL long-everything signal, not judgment reads — the ordering is the
# finding, not the level.)
# M5 (the operator, 2026-08-31): "volume is more important to me right now since you
# don't really have a ton of reps." Measured over an identical 3-day window:
# M5 gives the SAME setup count as M1 (1593 vs 1492) with spread cut from 38%
# to 27% of risk. M15 remains the better economics (19%) once reps accumulate.

def _env():
    e = {}
    for line in (D.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("="); e[k.strip()] = v.strip()
    return e

E = _env()
URL, TOK, ACCT = E["OANDA_API_URL"].rstrip("/"), E["OANDA_API_KEY"], E["OANDA_ACCOUNT_ID"]

def get(path):
    r = urllib.request.Request(URL + path, headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(r, timeout=20) as x:
        return json.load(x)

def median_spread(pair, pip, n=SPREAD_SAMPLES):
    """The toll, measured properly. One quote is a coin flip; the median is the cost.

    SAMPLES RAISED 5 -> 9 (2026-08-31 09:44) after three setups evaporated between
    the check run and the arm run. Measured cause: the USD/JPY spread wanders
    1.20-1.70p with NO relationship to volatility (correlation with bar range
    = +0.019 across 399 bars — the "spread widens on big moves" hypothesis was
    tested and is FALSE). It is simply a noisy value, so a median of 5 still had
    enough variance to flip a 5.0x boundary case between two calls seconds apart.
    Nine samples cuts that. The THRESHOLD is untouched — this buys reproducibility,
    not permissiveness, and it declines as many marginal setups as it admits.

    Returns (median, bid, ask, lo, hi) — the lo/hi make a marginal call visible
    instead of hiding the uncertainty behind a single number.
    """
    s, bid, ask = [], None, None
    for i in range(n):
        q = get(f"/v3/accounts/{ACCT}/pricing?instruments={pair}")["prices"][0]
        if not q.get("tradeable"):
            return None, None, None, None, None
        b, a = float(q["bids"][0]["price"]), float(q["asks"][0]["price"])
        s.append((a - b) / pip); bid, ask = b, a
        if i < n - 1:
            time.sleep(0.6)
    return statistics.median(s), bid, ask, min(s), max(s)

TARGET_RISK_USD = 0.20      # every trade risks the same, whatever the pair

def risk_units(pair, pip, stop_pips):
    """Units sized so the stop costs TARGET_RISK_USD — not a fixed unit count.

    2026-08-31: "1000 units" risked $0.19 on USD/JPY and $0.32 on GBP/USD for
    the SAME 3-pip stop, because pip value differs per pair. Risk was drifting
    with whichever pair qualified. Sized from dollars now, capped at MAX_UNITS.

    Pip value per unit, in USD:
      XXX_USD (quote=USD)  -> pip exactly           (e.g. GBP/USD: 0.0001)
      USD_XXX (base=USD)   -> pip / price           (e.g. USD/JPY: 0.01/159.7)
    Anything else (a cross) is refused rather than guessed at.
    """
    base, quote = pair.split("_")
    px = None
    q = get(f"/v3/accounts/{ACCT}/pricing?instruments={pair}")["prices"][0]
    px = (float(q["bids"][0]["price"]) + float(q["asks"][0]["price"])) / 2
    if quote == "USD":
        pip_value = pip                      # e.g. GBP/USD — pip is already USD
    elif base == "USD":
        pip_value = pip / px                 # e.g. USD/JPY — convert at own price
    else:
        # CROSS (2026-08-31): used to fall back to a flat 1000 units, which on
        # AUD/JPY risked $0.213 instead of $0.20. A pip is denominated in the
        # QUOTE currency, so convert THAT to USD via its own USD pair.
        try:
            if quote == "JPY":
                q2 = get(f"/v3/accounts/{ACCT}/pricing?instruments=USD_JPY")["prices"][0]
                rate = (float(q2["bids"][0]["price"]) + float(q2["asks"][0]["price"])) / 2
                pip_value = pip / rate       # pip in JPY -> USD
            else:
                q2 = get(f"/v3/accounts/{ACCT}/pricing?instruments={quote}_USD")["prices"][0]
                rate = (float(q2["bids"][0]["price"]) + float(q2["asks"][0]["price"])) / 2
                pip_value = pip * rate       # pip in QUOTE -> USD
        except Exception:
            return 1000                      # unknown cross: old fixed size, never a guess
    units = int(TARGET_RISK_USD / (stop_pips * pip_value))
    return max(1, min(units, 1000))

def qualify(pair, side, arm=False, tf=TIMEFRAME):
    pip = 0.01 if "JPY" in pair else 0.0001
    dp = 3 if pip == 0.01 else 5
    cs = [c for c in get(f"/v3/instruments/{pair}/candles?count=15&granularity={tf}&price=M")["candles"]
          if c.get("complete")]
    if len(cs) < 12:
        print("not enough candles"); return False
    sp, bid, ask, sp_lo, sp_hi = median_spread(pair, pip)
    if sp is None:
        print(f"{pair}: not tradeable"); return False
    hi = max(float(c["mid"]["h"]) for c in cs)
    lo = min(float(c["mid"]["l"]) for c in cs)
    C_closes = [float(c["mid"]["c"]) for c in cs]
    avg = statistics.mean((float(c["mid"]["h"]) - float(c["mid"]["l"])) / pip for c in cs[-10:])
    ratio = ((hi - lo) / pip) / sp

    # entry sits at the MEASURED median pullback, never at a level that "looks right"
    if side == "long":
        run = float(cs[-10]["mid"]["h"]); depths = []
        for c in cs[-10:]:
            run = max(run, float(c["mid"]["h"])); depths.append((run - float(c["mid"]["l"])) / pip)
        med = statistics.median(depths)
        entry = round(ask - med * ENTRY_DEPTH * pip, dp)
        stop  = round(entry - max(avg * 2.0, STOP_FLOOR_PIPS) * pip, dp)
        tgt   = round(entry + (entry - stop) * 2.2, dp)
        risk, reward = (entry - stop) / pip, (tgt - entry) / pip
    else:
        run = float(cs[-10]["mid"]["l"]); depths = []
        for c in cs[-10:]:
            run = min(run, float(c["mid"]["l"])); depths.append((float(c["mid"]["h"]) - run) / pip)
        med = statistics.median(depths)
        entry = round(bid + med * ENTRY_DEPTH * pip, dp)
        stop  = round(entry + max(avg * 2.0, STOP_FLOOR_PIPS) * pip, dp)
        tgt   = round(entry - (stop - entry) * 2.2, dp)
        risk, reward = (stop - entry) / pip, (entry - tgt) / pip
    netR = (reward - sp) / (risk + sp)

    print(f"{pair} {side.upper()}  [{tf}]")
    r_lo, r_hi = ((hi-lo)/pip)/sp_hi, ((hi-lo)/pip)/sp_lo
    ratio_lo, ratio_hi = r_lo, r_hi
    marginal = " MARGINAL" if r_lo < MIN_RATIO <= r_hi else ""
    print(f"  range {(hi-lo)/pip:5.1f}p | spread {sp:.2f}p (median of {SPREAD_SAMPLES}, "
          f"{sp_lo:.2f}-{sp_hi:.2f}) | ratio {ratio:.1f}x [{r_lo:.1f}-{r_hi:.1f}]{marginal} | "
          f"avg bar {avg:.1f}p | med pullback {med:.1f}p")
    print(f"  entry {entry} | stop {stop} ({risk:.1f}p) | target {tgt} ({reward:.1f}p) | netR {netR:.2f}")

    # REVERTED 2026-08-31 10:39 (the operator): the lower-bound rule below was measured
    # against 464 windows and bought NOTHING — ratio >=5.0, >=5.5 and >=6.5 all
    # select for the same 1.20-1.22x forward range, so the extra strictness cost
    # ~25% of opportunities for zero improvement in signal.
    # the operator's point, which matters more: "You tightening rules on a system you are
    # just learning makes it difficult to learn regardless." Two hours of zero
    # fills is not discipline, it is starving the sample that teaches direction.
    # The POINT ESTIMATE clears the threshold again. The 9-sample median stays —
    # that is measurement PRECISION, not strictness.
    # THE OLD LOWER-BOUND RULE (kept commented, it was not wrong, just premature):
    # (2026-08-31 09:52) "ratio >= 5.0" is ILL-DEFINED on a noisy measurement: it
    # never said WHICH statistic must clear it. Using the point estimate meant the
    # same market read 4.8x and 5.5x sixty seconds apart on an IDENTICAL 7.7p range
    # — only the spread draw differed — so whether a trade happened depended on
    # which sample the arming call drew. Three setups evaporated that way tonight.
    # Requiring the lower bound is not a stricter threshold, it is a COMPLETE one:
    # "I must be confident the market pays", not "one draw hinted that it might".
    # This is a definitional fix, NOT a performance claim — 6 trades prove nothing.
    # STRUCTURE VETO (the operator's wave cycle, measured 2026-09-01): after a fresh
    # LEG the next hour reverts ~0.7 avg-bars. Entering IN the leg's direction
    # while it is still printing is chasing — the shape of most session losses.
    # Counter-leg entries are allowed (they align with the measured reversion).
    net = abs(C_closes[-1] - C_closes[-5]) / pip if len(C_closes) >= 5 else 0
    fresh_leg = "up" if (net > 2.2 * avg and C_closes[-1] > C_closes[-5]) else \
                "dn" if (net > 2.2 * avg) else None
    fails = []
    if fresh_leg == "up" and side == "long":
        fails.append(f"LEG_UP still printing ({net:.1f}p net) — no chasing")
    if fresh_leg == "dn" and side == "short":
        fails.append(f"LEG_DN still printing ({net:.1f}p net) — no chasing")
    if ratio < MIN_RATIO:
        fails.append(f"ratio {ratio:.1f}x [{ratio_lo:.1f}-{ratio_hi:.1f}] < {MIN_RATIO}")
    if netR  < MIN_NETR:  fails.append(f"netR {netR:.2f} < {MIN_NETR}")
    if risk <= avg:       fails.append(f"stop {risk:.1f}p inside avg bar {avg:.1f}p")
    if fails:
        print(f"  DECLINED: {'; '.join(fails)}")
        return False
    print("  QUALIFIES")
    if arm:
        cmd = "limitbuy" if side == "long" else "limitsell"
        u = risk_units(pair, pip, risk)
        # EXIT = TRAILING STOP FROM ENTRY, exchange-managed (decided with the operator
        # 2026-08-31). Measured on 1006 entries: fixed 2.2R target captures
        # +0.150R when right (needs 90.2% accuracy); trailing from entry at the
        # stop distance captures +0.653R (needs 66.9%). No fixed take-profit —
        # the 1-MIN monitoring is the discretionary exit layer on top.
        trail_dist = round(risk * pip, 3 if pip == 0.01 else 5)
        print(f"  sizing: {u} units for ~${TARGET_RISK_USD:.2f} risk over {risk:.1f}p")
        print(f"  exit: TRAILING stop, {risk:.1f}p behind best price (no fixed target)")
        subprocess.run(["python3", str(D / "fx_execute.py"), cmd, pair, str(u),
                        str(entry), str(stop), "", str(trail_dist)])
        # PARTIAL PROFIT (the operator, 2026-09-01: "start learning how to take profits
        # because [you] keep missing highs"). Backtested EV-NEUTRAL vs pure trail
        # (-0.105R vs -0.101R across 6746 entries) — banking half at +1R costs
        # nothing in expectancy and converts peak-then-retrace trades (four in a
        # row peaked +2 to +6 pips and banked ~nothing) into realized gains.
        # The plan is placed AFTER the fill by trade_watch.sh (a resting reduce
        # order before the fill would OPEN a position instead).
        half = max(1, u // 2)
        tp1 = round(entry + risk * pip, dp) if side == "long" else round(entry - risk * pip, dp)
        tp_side = "sell" if side == "long" else "buy"
        (D / ".fx_plan").write_text(f"{pair} {tp_side} {half} {tp1}\n")
        print(f"  partial: {tp_side} {half}u @ {tp1} (+1R) placed on fill")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    tf = TIMEFRAME
    if "--tf" in sys.argv:
        tf = sys.argv[sys.argv.index("--tf") + 1]
    ok = qualify(sys.argv[1].upper(), sys.argv[2].lower(), "--arm" in sys.argv, tf)
    sys.exit(0 if ok else 1)
