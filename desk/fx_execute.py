#!/usr/bin/env python3
"""OANDA execution layer — practice account. Guards before convenience.

Usage:
  python3 fx_execute.py balance
  python3 fx_execute.py price   <PAIR>
  python3 fx_execute.py buy     <PAIR> <units>
  python3 fx_execute.py sell    <PAIR> <units>      (short — FX allows it)
  python3 fx_execute.py close   <PAIR>
  python3 fx_execute.py positions

SIZING NOTE (the operator's standing rule): the Primary practice account holds
~$1.05M. Trade it AS IF IT HELD $100. MAX_UNITS caps a position at 1,000
units, which on USD/JPY risks roughly $0.07 per pip — the right scale for
building rhythm, not for exploiting a fake balance.

HARD LIMITS (refuse rather than ask):
  - max 1,000 units per position
  - majors and liquid crosses only, no exotics
  - practice endpoint only; refuses if the URL is not api-fxpractice
  - every order appended to fx_orders.jsonl
"""
import json, sys, time, urllib.request, urllib.error
from pathlib import Path

D = Path(__file__).resolve().parent
MAX_UNITS = 1000
ALLOWED = {"EUR_USD","USD_JPY","GBP_USD","AUD_USD","NZD_USD","USD_CAD",
           "USD_CHF","EUR_JPY","GBP_JPY","AUD_JPY","EUR_GBP"}

def _env():
    out = {}
    for line in (D.parent / ".env").read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("="); out[k.strip()] = v.strip()
    return out

E = _env()
URL = E["OANDA_API_URL"].rstrip("/")
TOK = E["OANDA_API_KEY"]
ACCT = E["OANDA_ACCOUNT_ID"]

if "fxpractice" not in URL:
    print(f"REFUSED: endpoint {URL} is not the practice environment."); sys.exit(2)

def req(path, method="GET", body=None):
    r = urllib.request.Request(
        URL + path, method=method,
        data=json.dumps(body).encode() if body else None,
        headers={"Authorization": f"Bearer {TOK}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(r, timeout=25) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        return {"_error": e.code, "_body": e.read().decode()[:400]}

def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(D / "fx_orders.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")

def pip_of(pair):
    return 0.01 if "JPY" in pair else 0.0001

def cmd_price(pair):
    d = req(f"/v3/accounts/{ACCT}/pricing?instruments={pair}")
    p = d["prices"][0]
    b, a = float(p["bids"][0]["price"]), float(p["asks"][0]["price"])
    print(f"{pair} bid {b} ask {a} | spread {(a-b)/pip_of(pair):.1f} pips | "
          f"tradeable={p.get('tradeable')}")
    return b, a

def cmd_balance():
    s = req(f"/v3/accounts/{ACCT}/summary")["account"]
    print(f"bal {float(s['balance']):,.2f} {s['currency']} | NAV {float(s['NAV']):,.2f} | "
          f"unrealised {float(s['unrealizedPL']):+,.2f} | openTrades {s['openTradeCount']} | "
          f"marginAvail {float(s['marginAvailable']):,.2f}")

def cmd_positions():
    d = req(f"/v3/accounts/{ACCT}/openPositions")
    ps = d.get("positions", [])
    if not ps:
        print("no open positions"); return
    for p in ps:
        for side in ("long", "short"):
            u = int(p[side]["units"])
            if u:
                print(f"{p['instrument']} {side} {u} units @ {p[side]['averagePrice']} "
                      f"| unrealised {float(p[side]['unrealizedPL']):+.4f}")

def cmd_trade(pair, units, side):
    pair = pair.upper()
    if pair not in ALLOWED:
        print(f"REFUSED: {pair} not in the majors/liquid-crosses list (no exotics)"); return 1
    units = int(units)
    if units <= 0 or units > MAX_UNITS:
        print(f"REFUSED: {units} units outside 1..{MAX_UNITS} (size as if $100)"); return 1
    signed = units if side == "buy" else -units
    b, a = cmd_price(pair)
    t0 = time.time()
    r = req(f"/v3/accounts/{ACCT}/orders", "POST",
            {"order": {"type": "MARKET", "instrument": pair,
                       "units": str(signed), "timeInForce": "FOK",
                       "positionFill": "DEFAULT"}})
    ms = (time.time() - t0) * 1000
    if "_error" in r:
        print(f"ORDER FAILED {r['_error']}: {r['_body']}")
        log({"side": side, "pair": pair, "units": signed, "error": r}); return 1
    fill = r.get("orderFillTransaction")
    if not fill:
        print(f"NO FILL: {json.dumps(r)[:300]}")
        log({"side": side, "pair": pair, "units": signed, "raw": r}); return 1
    px = float(fill["price"])
    seen = a if side == "buy" else b
    print(f"{side.upper()} {units} {pair} -> filled @ {px} ({ms:.0f}ms) | "
          f"seen {seen} | slip {(px-seen)/pip_of(pair):+.2f} pips")
    log({"side": side, "pair": pair, "units": signed, "fill": px,
         "seen": seen, "latency_ms": round(ms), "id": fill.get("id")})
    return 0

def cmd_limit(pair, units, side, price, stop=None, tp=None, trail=None):
    """Resting LIMIT entry, optionally with stop-loss and take-profit attached.

    Built 2026-08-31 after the session's most expensive recurring failure:
    four correct directional reads produced no trade because the alert-then-
    verify loop is too slow to catch shallow dips. A dip touched the entry
    level at 04:53, recovered within seconds, and by the time the check ran
    the price was gone. A RESTING order would have filled on that wick.

    Manual alerts remain right for DECIDING. A resting order is right for
    EXECUTING a level already decided on.
    """
    pair = pair.upper()
    if pair not in ALLOWED:
        print(f"REFUSED: {pair} not in majors/liquid crosses (no exotics)"); return 1
    units = int(units)
    if units <= 0 or units > MAX_UNITS:
        print(f"REFUSED: {units} outside 1..{MAX_UNITS} (size as if $100)"); return 1
    signed = units if side == "buy" else -units
    dp = 3 if "JPY" in pair else 5
    order = {"type": "LIMIT", "instrument": pair, "units": str(signed),
             "price": f"{float(price):.{dp}f}", "timeInForce": "GTC",
             "positionFill": "DEFAULT"}
    if stop:
        order["stopLossOnFill"] = {"price": f"{float(stop):.{dp}f}", "timeInForce": "GTC"}
    if tp and str(tp).strip():
        order["takeProfitOnFill"] = {"price": f"{float(tp):.{dp}f}", "timeInForce": "GTC"}
    if trail and str(trail).strip():
        # OANDA enforces a per-instrument MINIMUM trailing distance (5.0 pips on
        # the majors). A 4.8p trail was silently rejected with LIMIT_ORDER_REJECT
        # on 2026-08-31 — the limit was known hours earlier and never coded in.
        # Widen to the broker minimum rather than fail; a slightly wider trail is
        # strictly better than no order.
        try:
            mi = req(f"/v3/accounts/{ACCT}/instruments?instruments={pair}")
            mn = float(mi["instruments"][0]["minimumTrailingStopDistance"])
            if float(trail) < mn:
                print(f"  trail {float(trail):.5f} below broker minimum {mn:.5f} — widening")
                trail = mn
        except Exception as _e:
            pass
        # TRAILING STOP, managed by OANDA (2026-08-31, the operator: "there may be a reason
        # why trailing stops are always recommended so maybe we just do that then").
        # Measured across 1006 gate-qualified entries: a fixed 2.2R take-profit
        # captures only +0.150R of a correct read and needs 90.2% direction accuracy
        # to break even. Trailing from entry at 2x the average bar captures +0.653R
        # and needs 66.9%. Measured direction accuracy is ~69% — the only rule tested
        # that clears a reachable bar.
        # EXCHANGE-MANAGED ON PURPOSE: it keeps working while nobody is watching,
        # which is the actual constraint (the operator is at work most sessions).
        order["trailingStopLossOnFill"] = {"distance": f"{float(trail):.{dp}f}",
                                           "timeInForce": "GTC"}
    r = req(f"/v3/accounts/{ACCT}/orders", "POST", {"order": order})
    if "_error" in r:
        print(f"LIMIT FAILED {r['_error']}: {r['_body']}"); return 1
    tx = r.get("orderCreateTransaction") or {}
    print(f"LIMIT {side.upper()} {units} {pair} @ {price} "
          f"(stop {stop}, tp {tp}, trail {trail}) -> id {tx.get('id')}")
    log({"side": f"{side}_limit", "pair": pair, "units": signed,
         "price": float(price), "stop": stop, "tp": tp, "trail": trail,
         "id": tx.get("id")})
    return 0

def cmd_orders():
    d = req(f"/v3/accounts/{ACCT}/pendingOrders")
    os_ = [o for o in d.get("orders", []) if o.get("type") in ("LIMIT", "STOP")]
    if not os_:
        print("no pending orders"); return 0
    for o in os_:
        print(f"  {o['id']} {o['type']} {o['instrument']} {o['units']} @ {o.get('price')}")
    return 0

def cmd_cancel(which):
    d = req(f"/v3/accounts/{ACCT}/pendingOrders")
    ids = [o["id"] for o in d.get("orders", [])] if str(which).lower() == "all" else [which]
    if not ids:
        print("nothing to cancel"); return 0
    for i in ids:
        r = req(f"/v3/accounts/{ACCT}/orders/{i}/cancel", "PUT")
        print(f"  cancelled {i}" if "_error" not in r else f"  FAILED {i}: {r['_body'][:80]}")
    return 0

def cmd_close(pair):
    pair = pair.upper()
    d = req(f"/v3/accounts/{ACCT}/openPositions")
    tgt = [p for p in d.get("positions", []) if p["instrument"] == pair]
    if not tgt:
        print(f"REFUSED: no open position in {pair}"); return 1
    p = tgt[0]
    body = {}
    if int(p["long"]["units"]):
        body["longUnits"] = "ALL"
    if int(p["short"]["units"]):
        body["shortUnits"] = "ALL"
    r = req(f"/v3/accounts/{ACCT}/positions/{pair}/close", "PUT", body)
    if "_error" in r:
        print(f"CLOSE FAILED {r['_error']}: {r['_body']}"); return 1
    for k in ("longOrderFillTransaction", "shortOrderFillTransaction"):
        f = r.get(k)
        if f:
            print(f"CLOSED {f.get('units')} {pair} @ {f.get('price')} | "
                  f"realised {float(f.get('pl', 0)):+.4f}")
            log({"side": "close", "pair": pair, "fill": float(f["price"]),
                 "pl": float(f.get("pl", 0)), "units": f.get("units")})
    return 0

if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else "balance"
    if c == "balance":     cmd_balance()
    elif c == "positions": cmd_positions()
    elif c == "price":     cmd_price(sys.argv[2].upper())
    elif c == "buy":       sys.exit(cmd_trade(sys.argv[2], sys.argv[3], "buy"))
    elif c == "sell":      sys.exit(cmd_trade(sys.argv[2], sys.argv[3], "sell"))
    elif c == "close":     sys.exit(cmd_close(sys.argv[2]))
    elif c == "limitbuy":  sys.exit(cmd_limit(sys.argv[2], sys.argv[3], "buy", sys.argv[4],
                                              sys.argv[5] if len(sys.argv)>5 else None,
                                              sys.argv[6] if len(sys.argv)>6 else None,
                                              sys.argv[7] if len(sys.argv)>7 else None))
    elif c == "limitsell": sys.exit(cmd_limit(sys.argv[2], sys.argv[3], "sell", sys.argv[4],
                                              sys.argv[5] if len(sys.argv)>5 else None,
                                              sys.argv[6] if len(sys.argv)>6 else None,
                                              sys.argv[7] if len(sys.argv)>7 else None))
    elif c == "orders":    sys.exit(cmd_orders())
    elif c == "cancel":    sys.exit(cmd_cancel(sys.argv[2]))
    else:                  print(__doc__)
