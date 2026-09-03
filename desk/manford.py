#!/usr/bin/env python3
"""Manford Golden — FAITHFUL implementation from the source PDF (not the 417-combo
mutant that got backtested in Feb 2026; the operator 2026-09-01: "we weren't able to
build it properly in the past").

  python3 manford.py USD_JPY 03:00        # London open, ET
  python3 manford.py GBP_USD 08:00        # NY FX open
  python3 manford.py BTC 09:30            # BTC at the equities open (Coinbase)

The PDF, as written:
  1. Higher-TF trend first — only trade WITH it (our wave-stack tide covers this)
  2. PRIMARY ZONE = high/low of the FIRST 5 candles from the session open (1-min)
  3. Entry needs ALL THREE, IN ORDER:
     A. close breaks out of the zone
     B. RETEST that holds — price returns to the broken edge, never CLOSES back
        inside the zone
     C. "3+2": bullish = 3 red closes then 2 green; enter at close of the 5th
  4. Stop at/around the broken zone edge. Target 3:1 OR the secondary levels
     (previous day's high/low). the operator: the edge is in identifying the zone and
     the retest ACCURATELY — this file is that identification, nothing else.
Advisory only: it prints the state machine; entries stay hand-made via qualify.
"""
import json, statistics, sys, time, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

D = Path(__file__).resolve().parent
ET = timezone(timedelta(hours=-4))

def env():
    e = {}
    for line in (D.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("="); e[k.strip()] = v.strip()
    return e

def fx_candles(pair, frm, to):
    e = env()
    url = (f"{e['OANDA_API_URL'].rstrip('/')}/v3/instruments/{pair}/candles"
           f"?granularity=M1&price=M&from={frm.isoformat()}&to={to.isoformat()}")
    r = urllib.request.Request(url, headers={"Authorization": f"Bearer {e['OANDA_API_KEY']}"})
    with urllib.request.urlopen(r, timeout=30) as x:
        cs = json.load(x)["candles"]
    def et_stamp(t):  # OANDA stamps are UTC; report in ET like the BTC path
        return datetime.fromisoformat(t[:19]).replace(tzinfo=timezone.utc).astimezone(ET).strftime("%H:%M")
    return [{"t": et_stamp(c["time"]), "o": float(c["mid"]["o"]), "h": float(c["mid"]["h"]),
             "l": float(c["mid"]["l"]), "c": float(c["mid"]["c"])} for c in cs if c.get("complete")]

def btc_candles(frm, to):
    import importlib.util
    spec = importlib.util.spec_from_file_location("ex", D / "execute.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    cs = []
    t = frm  # Coinbase caps requests at 350 candles: chunk in 5h windows
    from datetime import timedelta as _td
    while t < to:
        t2 = min(t + _td(hours=5), to)
        cs += mod.client().get_candles("BIP-20DEC30-CDE", start=str(int(t.timestamp())),
            end=str(int(t2.timestamp())), granularity="ONE_MINUTE").to_dict()["candles"]
        t = t2
    cs = sorted(cs, key=lambda x: int(x["start"]))
    return [{"t": datetime.fromtimestamp(int(c["start"]), ET).strftime("%H:%M"),
             "o": float(c["open"]), "h": float(c["high"]), "l": float(c["low"]),
             "c": float(c["close"])} for c in cs]

def run(inst, open_hhmm):
    today = datetime.now(ET).date()
    hh, mm = map(int, open_hhmm.split(":"))
    o = datetime(today.year, today.month, today.day, hh, mm, tzinfo=ET)
    end = min(o + timedelta(hours=4), datetime.now(ET))
    cache = D / f".manford_sec_{inst}_{today}"
    yday = None
    if inst.upper() == "BTC":
        bars = btc_candles(o, end)
        if not cache.exists():
            yday = btc_candles(o - timedelta(days=1), o)
    else:
        bars = fx_candles(inst, o.astimezone(timezone.utc), end.astimezone(timezone.utc))
        if not cache.exists():
            yday = fx_candles(inst, (o - timedelta(days=1)).astimezone(timezone.utc), o.astimezone(timezone.utc))
    if len(bars) < 10:
        print(f"{inst}: only {len(bars)} bars since {open_hhmm} ET — too early"); return
    if cache.exists():
        sec_hi, sec_lo = map(float, cache.read_text().split())
    else:
        sec_hi = max(b["h"] for b in yday) if yday else 0.0
        sec_lo = min(b["l"] for b in yday) if yday else 0.0
        cache.write_text(f"{sec_hi} {sec_lo}")
    zone = bars[:5]
    zh, zl = max(b["h"] for b in zone), min(b["l"] for b in zone)
    print(f"{inst} session {open_hhmm} ET | PRIMARY ZONE {zl:,.5g}–{zh:,.5g} "
          f"(first 5 bars, {zone[0]['t']}–{zone[4]['t']})")
    if sec_hi: print(f"  secondary: prev-24h hi {sec_hi:,.6g} lo {sec_lo:,.6g}")
    state, side, level = "WAIT_BREAK", None, None
    seq, signal = [], None
    for b in bars[5:]:
        if state == "WAIT_BREAK":
            if b["c"] > zh: state, side, level = "WAIT_RETEST", "bull", zh; print(f"  {b['t']} BREAKOUT UP    close {b['c']:,.6g} > zone high")
            elif b["c"] < zl: state, side, level = "WAIT_RETEST", "bear", zl; print(f"  {b['t']} BREAKOUT DOWN  close {b['c']:,.6g} < zone low")
        elif state == "WAIT_RETEST":
            inside = (b["c"] < zh) if side == "bull" else (b["c"] > zl)
            if inside:
                state = "WAIT_BREAK"; print(f"  {b['t']} FAILED — closed back inside the zone; breakout void, rearming")
                continue
            touched = (b["l"] <= level) if side == "bull" else (b["h"] >= level)
            if touched:
                state = "WAIT_32"; seq = []; print(f"  {b['t']} RETEST HELD at {level:,.6g} (wick touched, close stayed out)")
        elif state == "WAIT_32":
            if (b["c"] < zh and side == "bull") or (b["c"] > zl and side == "bear"):
                state = "WAIT_BREAK"; print(f"  {b['t']} FAILED after retest — closed back inside; rearming"); continue
            seq.append("R" if b["c"] < b["o"] else "G" if b["c"] > b["o"] else "D")
            want = ("R","R","R","G","G") if side == "bull" else ("G","G","G","R","R")
            if len(seq) >= 5 and tuple(seq[-5:]) == want:
                entry = b["c"]; stop = level
                risk = abs(entry - stop); tgt = entry + 3*risk if side == "bull" else entry - 3*risk
                print(f"  {b['t']} *** 3+2 COMPLETE — {side.upper()} SIGNAL ***")
                print(f"      entry {entry:,.6g} | stop {stop:,.6g} (zone edge, risk {risk:,.4g}) "
                      f"| 3:1 target {tgt:,.6g} | secondary exit {sec_hi if side=='bull' else sec_lo:,.6g}")
                state = "SIGNALED"
                signal = {"side": side, "entry": entry, "stop": stop, "tgt": tgt, "bar": b["t"],
                          "sec": sec_hi if side == "bull" else sec_lo}
    if state != "SIGNALED":
        print(f"  end state: {state}" + (f" ({side}, level {level:,.6g})" if side else "") +
              (f" | 3+2 progress: {''.join(seq[-5:])}" if seq else ""))
        return None
    return signal

MIN_RISK_PIPS = 3.0   # below this the ~1.5p spread is half the R — the EUR_GBP
                      # London "edge" (+1.86R on 0.4-3.8p stops) was exactly this
                      # fiction. Refuse rather than widen: widening changes the
                      # strategy under test.
STALE_MIN = 4         # the signal bar must be this fresh; Manford enters at
                      # the close of the 5th bar, not an hour later

def arm(inst, open_hhmm):
    """Place the Manford trade AS WRITTEN (the operator, 2026-09-01 18:40: "use the
    manford golden strategy for the London open... test it tonight"):
    market-equivalent entry at the signal, stop at the zone edge, take-profit
    at 3:1 — or the secondary level if it sits between +1R and 3:1. NO trail,
    NO partial: the backtest that justified this lane used these exits, and
    the test is only honest if the live trade does too. $0.20 risk via
    qualify.risk_units. FX only — BTC signals go through execute.py futures
    by hand. Called by hand after the wave-stack check, never by the watcher."""
    import importlib.util, subprocess
    if inst.upper() == "BTC":
        print("BTC: arm by hand through execute.py fbuy/fsell (futures)"); return 1
    sig = run(inst, open_hhmm)
    if not sig:
        print("no signal — nothing to arm"); return 1
    now = datetime.now(ET)
    hh, mm = map(int, sig["bar"].split(":"))
    bar_t = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    age = (now - bar_t).total_seconds() / 60 - 1          # bar stamp is open-time
    if age > STALE_MIN:
        print(f"STALE: signal bar {sig['bar']} is {age:.0f}m old — Manford enters at the "
              f"close of the 5th bar. Not arming."); return 1
    pip = 0.01 if "JPY" in inst else 0.0001
    risk_p = abs(sig["entry"] - sig["stop"]) / pip
    if risk_p < MIN_RISK_PIPS:
        print(f"REFUSED: {risk_p:.1f}p risk < {MIN_RISK_PIPS}p floor — spread would be half the R"); return 1
    spec = importlib.util.spec_from_file_location("q", D / "qualify.py")
    q = importlib.util.module_from_spec(spec); spec.loader.exec_module(q)
    units = q.risk_units(inst, pip, risk_p)
    tp = sig["tgt"]
    sec = sig["sec"]
    one_r = sig["entry"] + (risk_p * pip if sig["side"] == "bull" else -risk_p * pip)
    if sec and ((sig["side"] == "bull" and one_r < sec < tp) or (sig["side"] == "bear" and tp < sec < one_r)):
        tp = sec; print(f"  secondary level {sec:,.6g} sits between +1R and 3:1 — using it as target")
    px = q.get(f"/v3/accounts/{q.ACCT}/pricing?instruments={inst}")["prices"][0]
    bid, ask = float(px["bids"][0]["price"]), float(px["asks"][0]["price"])
    entry = ask if sig["side"] == "bull" else bid       # limit at the touch = fills now
    dp = 3 if pip == 0.01 else 5
    cmd = "limitbuy" if sig["side"] == "bull" else "limitsell"
    print(f"  ARM {cmd} {units}u {inst} @ {entry:.{dp}f} | stop {sig['stop']:.{dp}f} ({risk_p:.1f}p) "
          f"| tp {tp:.{dp}f} | no trail (Manford exits)")
    return subprocess.run(["python3", str(D / "fx_execute.py"), cmd, inst, str(units),
                           f"{entry:.{dp}f}", f"{sig['stop']:.{dp}f}", f"{tp:.{dp}f}", ""]).returncode

if __name__ == "__main__":
    inst = sys.argv[1].upper(); opn = sys.argv[2] if len(sys.argv) > 2 else "09:30"
    if "--arm" in sys.argv:
        sys.exit(arm(inst, opn))
    run(inst, opn)
