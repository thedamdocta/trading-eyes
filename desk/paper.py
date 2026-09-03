#!/usr/bin/env python3
"""Paper desk for Coinbase — same rules, same fees, no money.

the operator (2026-09-01 23:05 ET): "if you can reproduce the fees that Coinbase will
give you, you can build a paper trade so you have more opportunities to trade
something on Coinbase while you wait on forex."

Products
  FUT  BIP-20DEC30-CDE nano perp, 1 contract = 0.01 BTC, whole contracts, both sides
  BTC  BTC-USD spot, USD-sized, LONG ONLY (matches the live desk)

Fees come from the account's real tier (get_transaction_summary) and are cached
in the state file; fallbacks are the values read on 2026-09-01: spot maker
0.04% / taker 0.085%, futures maker 0.095% / taker 0.10%.

Fill model — deliberately conservative
  * an entry limit fills only when a LATER 1-min bar trades THROUGH it (low < buy
    price / high > sell price), at the limit, as MAKER
  * a marketable limit (buy above / sell below the last price) fills at once at
    the last price as TAKER
  * a stop fills at stop -/+ SLIP as TAKER; a take-profit fills at the level as
    MAKER; if one bar touches both, the STOP wins
  * nothing fills on bars that closed before the order existed

Hand-made entries only, like live. The watcher just calls `tick`.

usage
  paper.py fbuy  N   price stop tp     paper.py fsell N   price stop tp
  paper.py buy   USD price stop tp     (spot, long only)
  paper.py cancel ID | close ID | stop ID price | status | state | tick | ledger
"""
import importlib.util, json, sys, time, uuid
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

D = Path(__file__).resolve().parent
STATE = D / "paper_state.json"
LEDGER = D / "paper_ledger.jsonl"
ET = ZoneInfo("America/New_York")

PROD = {"FUT": {"id": "BIP-20DEC30-CDE", "unit": 0.01, "shorts": True,  "max_risk": 2.75},
        "BTC": {"id": "BTC-USD",         "unit": 1.0,  "shorts": False, "max_risk": 0.60}}
FEE_FALLBACK = {"BTC": (0.0004, 0.00085), "FUT": (0.00095, 0.001)}
SLIP = 5.0            # $ per BTC on stop (market) fills — assumption, not measured
SPOT_MAX_USD = 25.0   # execute.py caps a single spot order at $25

_ex = None
def client():
    global _ex
    if _ex is None:
        spec = importlib.util.spec_from_file_location("ex", D / "execute.py")
        _ex = importlib.util.module_from_spec(spec); spec.loader.exec_module(_ex)
    return _ex.client()

def now_et(ts=None):
    return datetime.fromtimestamp(ts or time.time(), ET).strftime("%H:%M ET")

def load():
    if STATE.exists():
        return json.loads(STATE.read_text())
    return {"orders": [], "positions": [], "last_bar": {}, "fees": {}, "fees_ts": 0,
            "realized": 0.0, "fees_paid": 0.0, "n_closed": 0}

def save(s):
    STATE.write_text(json.dumps(s, indent=1))

def fees(s, prod):
    """(maker, taker) from the real account tier, refreshed daily."""
    if time.time() - s.get("fees_ts", 0) > 86400 or not s.get("fees"):
        try:
            c = client()
            sp = c.get_transaction_summary().to_dict().get("fee_tier", {})
            fu = c.get_transaction_summary(product_type="FUTURE").to_dict().get("fee_tier", {})
            s["fees"] = {"BTC": [float(sp["maker_fee_rate"]), float(sp["taker_fee_rate"])],
                         "FUT": [float(fu["maker_fee_rate"]), float(fu["taker_fee_rate"])]}
            s["fees_ts"] = time.time()
        except Exception:
            pass
    return tuple(s.get("fees", {}).get(prod) or FEE_FALLBACK[prod])

def last_price(prod):
    return float(client().get_product(PROD[prod]["id"]).to_dict()["price"])

def bars_since(prod, since):
    """Closed 1-min bars with start > since (epoch). Chunked under the 350 cap."""
    now = int(time.time()); end = now - (now % 60) - 1
    start = max(int(since) + 1, end - 300 * 60)
    cs = client().get_candles(PROD[prod]["id"], start=str(start), end=str(end),
                              granularity="ONE_MINUTE").to_dict()["candles"]
    out = [(int(c["start"]), float(c["high"]), float(c["low"]), float(c["close"]))
           for c in cs if int(c["start"]) > since and int(c["start"]) + 60 <= now]
    return sorted(out)

def qty_btc(prod, qty):
    return qty * PROD[prod]["unit"]

def fee_usd(s, prod, price, qty, taker):
    m, t = fees(s, prod)
    return price * qty_btc(prod, qty) * (t if taker else m)

# ------------------------------------------------------------------ orders
def place(prod, side, qty, price, stop, tp):
    s = load(); p = PROD[prod]
    side = side.upper()
    assert side in ("BUY", "SELL")
    if side == "SELL" and not p["shorts"]:
        print("REFUSED: spot desk is long-only"); return 1
    price, stop, tp = float(price), float(stop), float(tp)
    if prod == "FUT":
        qty = int(qty)
        if qty < 1: print("REFUSED: whole contracts"); return 1
    else:
        usd = float(qty)
        if usd > SPOT_MAX_USD: print(f"REFUSED: spot cap ${SPOT_MAX_USD:.0f}"); return 1
        qty = usd / price                      # BTC amount
    if side == "BUY" and not stop < price < tp:
        print("REFUSED: long needs stop < price < tp"); return 1
    if side == "SELL" and not tp < price < stop:
        print("REFUSED: short needs tp < price < stop"); return 1
    risk = abs(price - stop) * qty_btc(prod, qty)
    if risk > p["max_risk"] + 1e-9:
        print(f"REFUSED: risk ${risk:.2f} > cap ${p['max_risk']:.2f} for {prod}"); return 1
    if any(x["prod"] == prod for x in s["positions"]) or any(x["prod"] == prod for x in s["orders"]):
        print(f"REFUSED: {prod} already has an order or position (one at a time)"); return 1
    o = {"id": uuid.uuid4().hex[:6], "prod": prod, "side": side, "qty": qty, "price": price,
         "stop": stop, "tp": tp, "ts": int(time.time()), "risk": risk}
    lp = last_price(prod)
    marketable = (side == "BUY" and price >= lp) or (side == "SELL" and price <= lp)
    if marketable:
        _open(s, o, lp, taker=True, ts=int(time.time()))
        print(f"PAPER FILLED {o['id']} {side} {prod} {fmt_qty(prod, qty)} @ {lp:,.2f} (marketable, taker) "
              f"stop {stop:,.2f} tp {tp:,.2f} risk ${risk:.2f}")
    else:
        s["orders"].append(o)
        s["last_bar"].setdefault(prod, int(time.time()) // 60 * 60 - 60)
        print(f"PAPER ORDER {o['id']} {side} {prod} {fmt_qty(prod, qty)} limit {price:,.2f} "
              f"stop {stop:,.2f} tp {tp:,.2f} risk ${risk:.2f} (last {lp:,.2f})")
    save(s); return 0

def fmt_qty(prod, qty):
    return f"{int(qty)}c" if prod == "FUT" else f"{qty:.6f} BTC"

def _open(s, o, fill, taker, ts):
    f = fee_usd(s, o["prod"], fill, o["qty"], taker)
    s["fees_paid"] += f
    s["positions"].append({"id": o["id"], "prod": o["prod"], "side": o["side"], "qty": o["qty"],
                           "entry": fill, "stop": o["stop"], "tp": o["tp"], "opened": ts,
                           "fee_in": f, "risk": abs(fill - o["stop"]) * qty_btc(o["prod"], o["qty"]),
                           "mfe": 0.0, "mae": 0.0})
    s["last_bar"][o["prod"]] = max(s["last_bar"].get(o["prod"], 0), ts // 60 * 60)

def _close(s, pos, fill, taker, ts, why):
    f = fee_usd(s, pos["prod"], fill, pos["qty"], taker)
    sgn = 1 if pos["side"] == "BUY" else -1
    gross = (fill - pos["entry"]) * sgn * qty_btc(pos["prod"], pos["qty"])
    net = gross - pos["fee_in"] - f
    R = net / pos["risk"] if pos["risk"] else 0.0
    s["fees_paid"] += f; s["realized"] += net; s["n_closed"] += 1
    s["positions"] = [x for x in s["positions"] if x["id"] != pos["id"]]
    row = {"id": pos["id"], "prod": pos["prod"], "side": pos["side"], "qty": pos["qty"],
           "entry": pos["entry"], "exit": fill, "stop": pos["stop"], "tp": pos["tp"], "why": why,
           "opened": now_et(pos["opened"]), "closed": now_et(ts), "gross": round(gross, 4),
           "fees": round(pos["fee_in"] + f, 4), "net": round(net, 4), "R": round(R, 2),
           "mfe": round(pos["mfe"], 2), "mae": round(pos["mae"], 2)}
    with LEDGER.open("a") as fh:
        fh.write(json.dumps(row) + "\n")
    print(f"PAPER CLOSED {pos['id']} {pos['side']} {pos['prod']} {why} @ {fill:,.2f} | "
          f"gross {gross:+.2f} fees {pos['fee_in'] + f:.2f} net {net:+.2f} = {R:+.2f}R "
          f"(mfe {pos['mfe']:+.0f} mae {pos['mae']:+.0f})")

# ------------------------------------------------------------------ tick
def tick(verbose=False):
    s = load(); events = 0
    prods = {x["prod"] for x in s["orders"]} | {x["prod"] for x in s["positions"]}
    for prod in prods:
        since = s["last_bar"].get(prod, int(time.time()) // 60 * 60 - 120)
        bars = bars_since(prod, since)
        for (t, h, l, c) in bars:
            # entries first (a fill and its stop can both happen in one bar — stop wins)
            for o in list(s["orders"]):
                if o["prod"] != prod or o["ts"] > t + 59:
                    continue
                if (o["side"] == "BUY" and l < o["price"]) or (o["side"] == "SELL" and h > o["price"]):
                    s["orders"].remove(o); _open(s, o, o["price"], taker=False, ts=t); events += 1
                    print(f"PAPER FILLED {o['id']} {o['side']} {prod} {fmt_qty(prod, o['qty'])} @ "
                          f"{o['price']:,.2f} (maker) {now_et(t)}")
            for pos in list(s["positions"]):
                if pos["prod"] != prod or pos["opened"] > t + 59:
                    continue
                sgn = 1 if pos["side"] == "BUY" else -1
                pos["mfe"] = max(pos["mfe"], ((h if sgn > 0 else l) - pos["entry"]) * sgn)
                pos["mae"] = min(pos["mae"], ((l if sgn > 0 else h) - pos["entry"]) * sgn)
                if sgn > 0:
                    if l <= pos["stop"]:   _close(s, pos, pos["stop"] - SLIP, True, t, "STOP"); events += 1
                    elif h > pos["tp"]:    _close(s, pos, pos["tp"], False, t, "TP"); events += 1
                else:
                    if h >= pos["stop"]:   _close(s, pos, pos["stop"] + SLIP, True, t, "STOP"); events += 1
                    elif l < pos["tp"]:    _close(s, pos, pos["tp"], False, t, "TP"); events += 1
            s["last_bar"][prod] = t
    save(s)
    if verbose:
        print(status_line(s))
    return 0

def status_line(s=None):
    s = s or load()
    parts = []
    for pos in s["positions"]:
        lp = last_price(pos["prod"]); sgn = 1 if pos["side"] == "BUY" else -1
        upl = (lp - pos["entry"]) * sgn * qty_btc(pos["prod"], pos["qty"])
        parts.append(f"{pos['id']} {pos['side']} {pos['prod']} {fmt_qty(pos['prod'], pos['qty'])} "
                     f"@ {pos['entry']:,.0f} now {lp:,.0f} uPL {upl:+.2f} ({upl / pos['risk']:+.2f}R) "
                     f"stop {pos['stop']:,.0f} tp {pos['tp']:,.0f}")
    for o in s["orders"]:
        parts.append(f"{o['id']} {o['side']} {o['prod']} limit {o['price']:,.0f} resting")
    book = " | ".join(parts) if parts else "flat"
    return (f"PAPER {book} | closed {s['n_closed']} net {s['realized']:+.2f} fees {s['fees_paid']:.2f}")

def cancel(oid):
    s = load(); n = len(s["orders"])
    s["orders"] = [o for o in s["orders"] if o["id"] != oid]
    save(s); print("cancelled" if len(s["orders"]) < n else "no such order"); return 0

def close(pid):
    s = load()
    for pos in s["positions"]:
        if pos["id"] == pid:
            _close(s, pos, last_price(pos["prod"]), True, int(time.time()), "HAND"); save(s); return 0
    print("no such position"); return 1

def move_stop(pid, price):
    s = load()
    for pos in s["positions"]:
        if pos["id"] == pid:
            pos["stop"] = float(price); save(s); print(f"stop -> {float(price):,.2f}"); return 0
    print("no such position"); return 1

def ledger():
    if not LEDGER.exists():
        print("no paper trades"); return 0
    rows = [json.loads(x) for x in LEDGER.read_text().splitlines() if x.strip()]
    for r in rows:
        print(f"{r['opened']}-{r['closed']} {r['side']:4} {r['prod']} {r['why']:4} "
              f"{r['entry']:,.0f}->{r['exit']:,.0f} net {r['net']:+.2f} {r['R']:+.2f}R")
    Rs = [r["R"] for r in rows]
    print(f"{len(rows)} trades, {sum(1 for r in Rs if r > 0)} wins, net ${sum(r['net'] for r in rows):+.2f}, "
          f"avg {sum(Rs) / len(Rs):+.2f}R")
    return 0

if __name__ == "__main__":
    a = sys.argv[1:] or ["status"]
    cmd = a[0]
    if cmd == "fbuy":    sys.exit(place("FUT", "BUY", *a[1:5]))
    elif cmd == "fsell": sys.exit(place("FUT", "SELL", *a[1:5]))
    elif cmd == "buy":   sys.exit(place("BTC", "BUY", *a[1:5]))
    elif cmd == "cancel": sys.exit(cancel(a[1]))
    elif cmd == "close": sys.exit(close(a[1]))
    elif cmd == "stop":  sys.exit(move_stop(a[1], a[2]))
    elif cmd == "tick":  sys.exit(tick("-v" in a))
    elif cmd == "state": print("OPEN" if load()["positions"] else "FLAT")
    elif cmd == "ledger": sys.exit(ledger())
    else: print(status_line())
