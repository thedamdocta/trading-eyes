#!/usr/bin/env python3
"""FX breadth scanner — finds WHICH pair deserves the eyes right now.

The machine advantage is breadth, not speed (the operator, 2026-08-30): a human
cannot track 11 pairs at once, and sitting on one dozing instrument is how
an hour gets wasted while ten others move.

Design: the OANDA API is the cheap FILTER across all pairs; the vision desk
is the precise EXECUTION on the one worth trading. Scanning is not a
decision, so it does not need eyes — but the trade does.

The metric is RANGE / SPREAD: how many times over the recent range paid the
transaction toll. Under 1x is untradeable by construction no matter how good
the read — that is exactly what made 2 correct crypto reads lose money.

Writes to the shared desk log so the existing monitor picks it up.
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

D = Path(__file__).resolve().parent
PAIRS = ["EUR_USD","USD_JPY","GBP_USD","AUD_USD","NZD_USD","USD_CAD",
         "USD_CHF","EUR_JPY","GBP_JPY","AUD_JPY","EUR_GBP"]
MIN_RANGE_PIPS = 8.0     # a move worth taking
MIN_RATIO      = 5.0     # must clear the toll several times over
PERIOD_S       = 60

def _env():
    out = {}
    for line in (D.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("="); out[k.strip()] = v.strip()
    return out

E = _env()
URL, TOK, ACCT = E["OANDA_API_URL"].rstrip("/"), E["OANDA_API_KEY"], E["OANDA_ACCOUNT_ID"]
LOG = Path(sys.argv[1]) if len(sys.argv) > 1 else D / "scan.log"

def get(path):
    r = urllib.request.Request(URL + path, headers={"Authorization": f"Bearer {TOK}"})
    with urllib.request.urlopen(r, timeout=25) as x:
        return json.load(x)

def say(msg):
    line = msg + "\n"
    with open(LOG, "a") as fh:
        fh.write(line)
    sys.stdout.write(line); sys.stdout.flush()

def scan():
    out = []
    pr = get(f"/v3/accounts/{ACCT}/pricing?instruments={','.join(PAIRS)}")["prices"]
    spreads = {}
    for p in pr:
        if p.get("bids") and p.get("asks") and p.get("tradeable"):
            pip = 0.01 if "JPY" in p["instrument"] else 0.0001
            spreads[p["instrument"]] = (
                float(p["asks"][0]["price"]) - float(p["bids"][0]["price"])) / pip
    for inst in PAIRS:
        sp = spreads.get(inst)
        if not sp:
            continue
        try:
            c = get(f"/v3/instruments/{inst}/candles?count=15&granularity=M5&price=M")["candles"]
        except (urllib.error.HTTPError, urllib.error.URLError):
            continue                       # one bad pair must not kill the scan
        if not c:
            continue
        pip = 0.01 if "JPY" in inst else 0.0001
        hi = max(float(x["mid"]["h"]) for x in c)
        lo = min(float(x["mid"]["l"]) for x in c)
        last = float(c[-1]["mid"]["c"])
        rng = (hi - lo) / pip
        out.append({"pair": inst, "range": rng, "spread": sp,
                    "ratio": rng / sp, "last": last,
                    "from_hi": (last - hi) / pip, "from_lo": (last - lo) / pip})
    out.sort(key=lambda r: r["ratio"], reverse=True)
    return out

def main():
    say("FX SCAN UP — 11 pairs, ranked by 15m range/spread "
        f"(alert at >={MIN_RANGE_PIPS}p and >={MIN_RATIO}x)")
    announced = {}
    while True:
        try:
            rows = scan()
        except Exception as e:
            say(f"FX SCAN WARN — {type(e).__name__}: {e}")
            time.sleep(PERIOD_S); continue
        now = time.time()
        # The routine ranking is low-value in a dead tape and costs a wake-up
        # every minute. Print it every 5 min; QUALIFYING pairs still alert
        # immediately below. Signal stays instant, noise drops 5x.
        if now - announced.get("_ranking", 0) > 300:
            announced["_ranking"] = now
            top = ", ".join(f"{r['pair']}:{r['range']:.0f}p/{r['ratio']:.1f}x"
                            for r in rows[:4])
            say(f"FX SCAN {time.strftime('%H:%M')} | {top}")
        for r in rows:
            if r["range"] >= MIN_RANGE_PIPS and r["ratio"] >= MIN_RATIO:
                # re-announce a given pair at most every 10 min
                if now - announced.get(r["pair"], 0) > 600:
                    announced[r["pair"]] = now
                    say(f"FX !! LIVE PAIR — {r['pair']} 15m range {r['range']:.1f}p "
                        f"@ {r['spread']:.1f}p spread = {r['ratio']:.1f}x toll | "
                        f"last {r['last']}, {r['from_hi']:+.1f}p from hi, "
                        f"{r['from_lo']:+.1f}p from lo || AGENT: worth the eyes?")
        time.sleep(PERIOD_S)

if __name__ == "__main__":
    main()
