#!/usr/bin/env python3
"""Log a DIRECTIONAL CALL and score it later. Direction only — no entry, no stop, no fees.

  python3 call.py log USD_JPY down "5 down bodies, no lower wicks, 1.9x volume"
  python3 call.py score            # score every call old enough, print accuracy

WHY THIS EXISTS (the operator, 2026-08-31 10:39):
  "I don't necessarily care about profitability right now. I care more about if
   you can get the directions right because that's majority of the battle."

P&L conflates FOUR skills: reading direction, choosing an entry, sizing a stop,
and paying the toll. Six trades tonight lost money while several of the READS
were right — trade 4 was stopped by an intra-bar spike and price then went my way.
This file isolates the one that the operator says matters most, and it scores against
plain forward price at fixed horizons, so no stop, spread, or fill can flatter or
punish a call that was actually correct.

A call is RIGHT at horizon h if price moved >= MIN_MOVE pips in the called
direction by then. Moves smaller than that are noise and score as FLAT — being
"right" by 0.3 pips is not a read, it is a coin landing on its edge.
"""
import calendar, json, sys, time, urllib.request
from pathlib import Path

D = Path(__file__).resolve().parent
LOG = D / "calls.jsonl"
HORIZONS = (15, 30, 60)         # minutes — fits 5-min decision bars (3/6/12 bars)
MIN_MOVE = 4.0                  # pips — ~1x M5 avg bar; smaller is noise, scores FLAT

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
    with urllib.request.urlopen(r, timeout=25) as x:
        return json.load(x)

def pip_of(p): return 0.01 if "JPY" in p else 0.0001

def mid(pair):
    q = get(f"/v3/accounts/{ACCT}/pricing?instruments={pair}")["prices"][0]
    return (float(q["bids"][0]["price"]) + float(q["asks"][0]["price"])) / 2

def cmd_log(pair, direction, why):
    pair = pair.upper(); direction = direction.lower()
    if direction not in ("up", "down"):
        print("direction must be up|down"); return 1
    px = mid(pair)
    rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "epoch": int(time.time()),
           "pair": pair, "dir": direction, "price": px, "why": why}
    with open(LOG, "a") as fh:
        fh.write(json.dumps(rec) + "\n")
    print(f"CALL {pair} {direction.upper()} @ {px} — {why}")
    return 0

def _fwd(pair, epoch, minutes):
    """Extreme reached in the called direction's favour, and the close, at horizon."""
    pip = pip_of(pair)
    # 5000 M1 candles (~3.5 days), not 200 (~3.3h). At 200 any call older than a
    # few hours silently scored "?" and dropped out of the sample — which defeats
    # the entire point of accumulating direction evidence. Found 2026-08-31 when
    # two of four logged calls were already unscoreable.
    cs = get(f"/v3/instruments/{pair}/candles?count=5000&granularity=M1&price=M")["candles"]
    rows = [c for c in cs if c.get("complete")]
    # OANDA candle times are UTC -> calendar.timegm, NOT time.mktime (which is
    # local and silently shifted every window by the UTC offset). Fixed with the
    # dead-parse line that used to sit here and crashed the scorer, 2026-08-31.
    out = [(calendar.timegm(time.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S")), c)
           for c in rows]
    win = [c for st, c in out if epoch <= st <= epoch + minutes * 60]
    if not win:
        return None, None
    hi = max(float(c["mid"]["h"]) for c in win)
    lo = min(float(c["mid"]["l"]) for c in win)
    close = float(win[-1]["mid"]["c"])
    return (hi, lo), close

def cmd_score():
    if not LOG.exists():
        print("no calls logged yet"); return 0
    calls = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    now = int(time.time())
    tally = {h: {"right": 0, "wrong": 0, "flat": 0} for h in HORIZONS}
    print(f"{'time':9} {'pair':8} {'dir':5} " + " ".join(f"{h:>5}m" for h in HORIZONS) + "  why")
    for c in calls:
        pip = pip_of(c["pair"]); marks = []
        for h in HORIZONS:
            if now < c["epoch"] + h * 60 + 60:
                marks.append("  --"); continue
            ext, close = _fwd(c["pair"], c["epoch"], h)
            if ext is None:
                marks.append("   ?"); continue
            hi, lo = ext
            fav = (hi - c["price"]) / pip if c["dir"] == "up" else (c["price"] - lo) / pip
            adv = (close - c["price"]) / pip if c["dir"] == "up" else (c["price"] - close) / pip
            if adv >= MIN_MOVE:
                marks.append(f"{adv:+5.1f}"); tally[h]["right"] += 1
            elif adv <= -MIN_MOVE:
                marks.append(f"{adv:+5.1f}"); tally[h]["wrong"] += 1
            else:
                marks.append(f"{adv:+5.1f}"); tally[h]["flat"] += 1
        print(f"{c['ts'][11:]:9} {c['pair']:8} {c['dir']:5} " + " ".join(marks) + f"  {c['why'][:44]}")
    print()
    for h in HORIZONS:
        t = tally[h]; n = t["right"] + t["wrong"] + t["flat"]
        if not n: continue
        decided = t["right"] + t["wrong"]
        acc = f"{t['right']/decided*100:.0f}%" if decided else "n/a"
        print(f"  {h:>2}m horizon: {t['right']} right / {t['wrong']} wrong / {t['flat']} flat "
              f"(>= {MIN_MOVE}p)  -> {acc} of decided calls")
    return 0

if __name__ == "__main__":
    if len(sys.argv) < 2: print(__doc__); sys.exit(1)
    if sys.argv[1] == "log":   sys.exit(cmd_log(sys.argv[2], sys.argv[3], " ".join(sys.argv[4:])))
    elif sys.argv[1] == "score": sys.exit(cmd_score())
    else: print(__doc__); sys.exit(1)
