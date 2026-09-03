#!/usr/bin/env python3
"""One 1-minute bar for the instrument CURRENTLY HELD. Empty if flat.

WHY (2026-08-31 20:14): the desk's chart capture watches ONE pair (USD/JPY) but a
position can be in any pair. Holding AUD/USD, every in-trade line I was shown
described USD/JPY — the in-trade monitoring the operator asked for (price action,
structure, volume on the 1-min) was pointed at the wrong instrument, and I only
noticed by reading the numbers closely.

Restarting the capture mid-trade would blind the desk on an open position, so
this pulls the held pair's bar from the API instead. Works for any instrument,
needs no capture change, and cannot drift out of sync with what is actually open.
"""
import json, statistics, sys, time, urllib.request
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
URL, TOK, ACCT = E["OANDA_API_URL"].rstrip("/"), E["OANDA_API_KEY"], E["OANDA_ACCOUNT_ID"]

def get(p):
    r = urllib.request.Request(URL + p, headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(r, timeout=15) as x:
        return json.load(x)

def main():
    trades = get(f"/v3/accounts/{ACCT}/openTrades").get("trades", [])
    if not trades:
        return 0
    t = trades[0]
    pair = t["instrument"]; pip = 0.01 if "JPY" in pair else 0.0001
    entry = float(t["price"]); units = int(t["currentUnits"])
    ts = t.get("trailingStopLossOrder") or {}
    sl = (t.get("stopLossOrder") or {}).get("price")
    cs = [c for c in get(f"/v3/instruments/{pair}/candles?count=12&granularity=M1"
                         f"&price=M")["candles"] if c.get("complete")]
    if len(cs) < 3:
        return 0
    vols = [c["volume"] for c in cs]; va = statistics.mean(vols) or 1
    c = cs[-1]; o, h, l, cl = (float(c["mid"][k]) for k in "ohlc")
    body = (cl - o) / pip; rng = (h - l) / pip or 0.01
    up = (h - max(o, cl)) / pip; low = (min(o, cl) - l) / pip
    shape = ("strong" if abs(body) > rng * 0.6 else
             "doji" if abs(body) < rng * 0.2 else "normal")
    if up > rng * 0.5:   shape = "shooting-star(rejected highs)"
    elif low > rng * 0.5: shape = "hammer(rejected lows)"
    vr = c["volume"] / va
    tag = " ACTIVE" if vr >= 1.5 else (" quiet" if vr < 0.6 else "")
    side = "long" if units > 0 else "short"
    fav = (cl - entry) / pip if units > 0 else (entry - cl) / pip
    last5 = ",".join(f"{float(x['mid']['c']):.5f}" if pip == 0.0001
                     else f"{float(x['mid']['c']):.3f}" for x in cs[-5:])
    # ET timestamp from the candle itself (server=UTC; ET=UTC-4). I was hand-
    # labeling minutes in updates and drifted 7 min ahead of the operator's clock.
    # Machine clock (the operator 2026-09-01: the bar's own stamp is its OPEN time,
    # a minute behind the wall clock). His Mac's clock is the authority.
    et = time.strftime("%H:%M", time.localtime())
    print(f"[{et} ET] HELD {pair} {side} C={cl:.5f} body{body:+.1f}p rng{rng:.1f}p "
          f"up^{up:.1f} low_{low:.1f} | ticks {c['volume']} ({vr:.2f}x{tag}) "
          f"| {shape} | {fav:+.1f}p vs entry {entry} | stop {sl} trail {ts.get('trailingStopValue')}")
    print(f"     last5: {last5}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
