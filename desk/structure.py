#!/usr/bin/env python3
"""Which PHASE of the operator's wave cycle is a pair in right now?

  python3 structure.py USD_JPY        ->  LEG_UP | LEG_DN | BUILDUP_HI | BUILDUP_LO | CONSOL
  python3 structure.py BTC            ->  same read on the Coinbase futures tape ($ = pips)

the operator (2026-09-01): "price structures come in waves... after the rally it goes
into a consolidation, then the consolidation goes into a build-up, then the next
leg — and it just repeats. Understanding the structure tells you when to exit."

MEASURED across 8,772 M5 bars / 6 pairs (~5 days), next-hour drift in avg-bars:
    after LEG_UP      -0.75   (the market SNAPS BACK after a sharp leg)
    after LEG_DN      +0.72
    after BUILD-UP    ~0.00
    in CONSOLIDATION  ~0.00   (68% of all bars — most of the time nothing is owed)

The one mechanical rule this licenses (and it is a VETO, not a signal):
NEVER ENTER IN THE DIRECTION OF A LEG THAT IS STILL PRINTING. Chasing a fresh
leg fights ~0.7 bars of expected reversion — this was the shape of most of the
session's losses, and the operator called it on trade three: "you were trying to ride
a shoot up that already passed."

Phase definitions (all computable from closed bars, no lookahead):
  LEG:       |close_now - close_4_bars_ago| > 2.2x the 12-bar average bar range
  BUILD-UP:  6-bar range < 60% of the prior 12-bar range, AND price coiled in
             the outer third of the 24-bar range (pressure against an edge)
  CONSOL:    everything else
"""
import json, statistics, sys, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent

def _env():
    e = {}
    for line in (D.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("="); e[k.strip()] = v.strip()
    return e

E = _env()
URL, TOK = E["OANDA_API_URL"].rstrip("/"), E["OANDA_API_KEY"]

def get(p):
    r = urllib.request.Request(URL + p, headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(r, timeout=20) as x:
        return json.load(x)

_BTC_GRAN = {"M1": "ONE_MINUTE", "M5": "FIVE_MINUTE", "M15": "FIFTEEN_MINUTE"}
_BTC_SEC = {"M1": 60, "M5": 300, "M15": 900}

def _btc_bars(tf):
    """Last 30 CLOSED bars of the futures contract (BIP-20DEC30-CDE) via the
    Coinbase client in execute.py. Same shape as the OANDA path: H, L, C lists."""
    import importlib.util, time
    spec = importlib.util.spec_from_file_location("ex", D / "execute.py")
    ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(ex)
    now = int(time.time()); sec = _BTC_SEC[tf]
    end = now - (now % sec)                      # drop the still-forming bar
    cs = ex.client().get_candles("BIP-20DEC30-CDE", start=str(end - 32 * sec),
        end=str(end - 1), granularity=_BTC_GRAN[tf]).to_dict()["candles"]
    cs = sorted(cs, key=lambda c: int(c["start"]))[-30:]
    return ([float(c["high"]) for c in cs], [float(c["low"]) for c in cs],
            [float(c["close"]) for c in cs])

def phase(pair, tf="M5"):
    if pair.upper() == "BTC":
        pip = 1.0                                # "pips" are dollars on BTC
        H, L, C = _btc_bars(tf)
        cs = C
    else:
        pip = 0.01 if "JPY" in pair else 0.0001
        cs = [c for c in get(f"/v3/instruments/{pair}/candles?count=30&granularity={tf}"
                             f"&price=M")["candles"] if c.get("complete")]
        H = [float(c["mid"]["h"]) for c in cs]
        L = [float(c["mid"]["l"]) for c in cs]
        C = [float(c["mid"]["c"]) for c in cs]
    if len(cs) < 25:
        return "UNKNOWN", ""
    i = len(cs) - 1
    avg = statistics.mean((H[j] - L[j]) / pip for j in range(i - 11, i + 1))
    net = abs(C[i] - C[i - 4]) / pip
    if net > 2.2 * avg:
        ph = "LEG_UP" if C[i] > C[i - 4] else "LEG_DN"
        return ph, f"leg {net:.1f}p vs avg bar {avg:.1f}p — DO NOT CHASE; reversion ~0.7 bars expected"
    r6 = (max(H[i-5:i+1]) - min(L[i-5:i+1])) / pip
    r12 = (max(H[i-17:i-5]) - min(L[i-17:i-5])) / pip
    hi24 = max(H[i-23:i+1]); lo24 = min(L[i-23:i+1]); span = (hi24 - lo24) or 1e-9
    pos = (C[i] - lo24) / span
    if r12 > 0 and r6 < 0.6 * r12 and (pos > 0.67 or pos < 0.33):
        ph = "BUILDUP_HI" if pos > 0.67 else "BUILDUP_LO"
        return ph, f"coil {r6:.1f}p vs prior {r12:.1f}p at {'top' if pos>0.67 else 'bottom'} of range — watch the break"
    return "CONSOL", f"digesting; 6-bar {r6:.1f}p, position {pos*100:.0f}% of 24-bar range"

def stack(pair):
    """All three frames at once. FRACTAL, measured 2026-09-01 (4 pairs, ~5 days):
    snap-back after a leg exists at every level (M1 -0.29/+0.37, M5 -1.09/+0.72
    in avg-bars) but M15 UP-legs did NOT revert (+0.05) — the big frame is the
    TIDE, the small frames are waves inside it. Recipe: trade WITH the M15 leg
    direction, enter on M5 pullback completion (never mid-leg), time it on M1."""
    out = {}
    for tf in ("M1", "M5", "M15"):
        out[tf] = phase(pair, tf)
    tide = out["M15"][0]
    wave = out["M5"][0]
    if tide.startswith("LEG_UP") or tide == "BUILDUP_HI":
        bias = "LONG bias (M15 tide up)"
    elif tide.startswith("LEG_DN") or tide == "BUILDUP_LO":
        bias = "SHORT bias (M15 tide down)"
    else:
        bias = "no tide — M15 consolidating, waves cut both ways"
    return out, bias

if __name__ == "__main__":
    pair = (sys.argv[1] if len(sys.argv) > 1 else "USD_JPY").upper()
    out, bias = stack(pair)
    for tf in ("M15", "M5", "M1"):
        ph, why = out[tf]
        print(f"  {tf:4} {ph:11} {why}")
    print(f"  >>> {bias}")
