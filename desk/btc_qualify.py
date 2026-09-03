#!/usr/bin/env python3
"""The gate, for BTC-USD on Coinbase. Same three tests as qualify.py.

  python3 btc_qualify.py long          # evaluate on the 5-min chart
  python3 btc_qualify.py long --arm    # place a POST-ONLY maker limit if it passes

WHY (the operator, 2026-08-31 13:40): "Forex may be flat for some time due to volume...
your focus may have to switch to Coinbase until another market open since these
times are historically flat with forex." Confirmed by measurement — GBP/USD
bar/spread falls 1.70x (10:00 ET) -> 0.85x (13:00) -> 0.45x (16:00). BTC has no
session structure.

REAL MONEY. Differences from the FX desk, all deliberate:
  - MAKER ONLY. post_only both sides: 0.04%+0.04% = ~$63 round trip on BTC at
    78.6k, versus $134 taker/taker. Measured 5-min bar is ~$183, so maker gives
    bar/cost 2.90x and taker only 1.37x. Taker is not worth trading.
  - Coinbase has NO server-side trailing stop, so the trail is managed by the
    desk. That means an open BTC position depends on this session being alive —
    stated plainly because it is the one real weakness versus OANDA.
  - execute.py caps a single order at $25 and holds a $5 cash reserve.
"""
import json, statistics, subprocess, sys, time, importlib.util
from pathlib import Path

D = Path(__file__).resolve().parent
MIN_RATIO, MIN_NETR = 5.0, 1.1
MIN_RANGE_USD = 250      # Rule 4 (the operator revised 2026-09-01 midday): maker-only
# exits cut the round trip to ~62pts, so the floor is calibrated to THAT toll,
# not the taker-era 132 (at ~30% capture, 250pt range ~= 75pt capture > 62).
# Original 400 floor was belt-and-suspenders vs a hurdle maker exits removed
# and cost reps. Exits stay MAKER-ONLY: bracket target is a limit; never a
# market exit except a true emergency. 7/7 sub-hurdle captures lost.
TARGET_RISK_USD = 0.60          # ~0.5% of a $117 account
MAX_USD = 25.0

spec = importlib.util.spec_from_file_location("ex", D / "execute.py")
ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)

def candles(gran="FIVE_MINUTE", mins=5, n=60):
    c = ex.client(); now = int(time.time())
    r = c.get_candles(product_id="BTC-USD", start=str(now - mins*60*n),
                      end=str(now), granularity=gran).to_dict()
    cs = list(reversed(r.get("candles", [])))
    return [{"o":float(x["open"]),"h":float(x["high"]),"l":float(x["low"]),
             "c":float(x["close"]),"v":float(x["volume"])} for x in cs]

def qualify(side, arm=False):
    cs = candles()
    if len(cs) < 20:
        print("not enough candles"); return False
    c = ex.client()
    fees = c.get_transaction_summary().to_dict().get("fee_tier", {})
    mk = float(fees.get("maker_fee_rate", 0.004))
    px = ex.price(c)
    cost = px * mk * 2                       # maker in + maker out
    hi = max(x["h"] for x in cs[-15:]); lo = min(x["l"] for x in cs[-15:])
    rng = hi - lo
    avg = statistics.mean(x["h"] - x["l"] for x in cs[-10:])
    ratio = rng / cost
    # entry at the MEASURED median pullback, same as FX
    if side == "long":
        run = cs[-10]["h"]; d = []
        for x in cs[-10:]:
            run = max(run, x["h"]); d.append(run - x["l"])
        med = statistics.median(d)
        entry = round(px - med, 2); stop = round(entry - avg*2, 2)
        risk = entry - stop; reward = risk * 2.2
    else:
        run = cs[-10]["l"]; d = []
        for x in cs[-10:]:
            run = min(run, x["l"]); d.append(x["h"] - run)
        med = statistics.median(d)
        entry = round(px + med, 2); stop = round(entry + avg*2, 2)
        risk = stop - entry; reward = risk * 2.2
    netR = (reward - cost) / (risk + cost)
    print(f"BTC-USD {side.upper()}  [5-min]")
    print(f"  range ${rng:,.0f} | maker round trip ${cost:,.0f} | ratio {ratio:.1f}x | "
          f"avg bar ${avg:,.0f} | med pullback ${med:,.0f}")
    print(f"  entry ${entry:,.2f} | stop ${stop:,.2f} (${risk:,.0f}) | netR {netR:.2f}")
    fails = []
    if rng < MIN_RANGE_USD: fails.append(f"range ${rng:,.0f} < ${MIN_RANGE_USD} minimum")
    if ratio < MIN_RATIO: fails.append(f"ratio {ratio:.1f} < {MIN_RATIO}")
    if netR < MIN_NETR:   fails.append(f"netR {netR:.2f} < {MIN_NETR}")
    if risk <= avg:       fails.append("stop inside one bar")
    if side == "short":   fails.append("SPOT ONLY — cannot short BTC on Coinbase")
    if fails:
        print(f"  DECLINED: {'; '.join(fails)}"); return False
    usd = min(MAX_USD, TARGET_RISK_USD / (risk / entry))
    print(f"  QUALIFIES | size ${usd:.2f} for ~${TARGET_RISK_USD:.2f} risk")
    if arm:
        subprocess.run(["python3", str(D / "execute.py"), "buylimit",
                        f"{usd:.2f}", f"{entry:.2f}"])
    return True

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    sys.exit(0 if qualify(sys.argv[1].lower(), "--arm" in sys.argv) else 1)
