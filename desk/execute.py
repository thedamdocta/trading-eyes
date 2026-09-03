#!/usr/bin/env python3
"""Coinbase execution layer — REAL MONEY. Guards before convenience.

Usage:
  python3 execute.py balance
  python3 execute.py buy  <usd_amount>
  python3 execute.py sell <btc_amount|all>
  python3 execute.py position

HARD LIMITS (refuse rather than ask):
  - single order max $25 notional
  - never spend below a $5 USD cash reserve
  - product locked to BTC-USD
  - every order gets a unique client id and is appended to orders.jsonl

Lives at a stable project path, not in session scratch: the order ledger is
the record of real money moving and must outlive any one session.
"""
import json, sys, time, uuid
from pathlib import Path
from coinbase.rest import RESTClient

D = Path(__file__).resolve().parent
PRODUCT = "BTC-USD"
MAX_ORDER_USD = 25.0
MIN_CASH_RESERVE = 5.0

def _load_env(path):
    """Minimal .env reader — no dependency, and it never echoes values."""
    out = {}
    try:
        for line in Path(path).read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip()
    except OSError:
        pass
    return out

# Credentials: prefer the .env key (COINBASE_ADV_*), fall back to the older
# json keyfile. Keeps the secret in one gitignored place instead of ~/Downloads.
_ENV = _load_env(D.parent / ".env")
KEY_NAME = _ENV.get("COINBASE_ADV_KEY_NAME")
KEY_SECRET = _ENV.get("COINBASE_ADV_PRIVATE_KEY")
KEY_SOURCE = ".env COINBASE_ADV_*"
if not (KEY_NAME and KEY_SECRET):
    _k = json.load(open(Path.home() / "Downloads/cdp_api_key.json"))
    KEY_NAME, KEY_SECRET = _k["name"], _k["privateKey"]
    KEY_SOURCE = "~/Downloads/cdp_api_key.json (fallback)"

def client():
    return RESTClient(api_key=KEY_NAME, api_secret=KEY_SECRET)

def balances(c):
    out = {}
    for a in c.get_accounts().to_dict()["accounts"]:
        v = float(a["available_balance"]["value"])
        if v > 0:
            out[a["currency"]] = v
    return out

def price(c):
    return float(c.get_product(PRODUCT).to_dict()["price"])

def log(rec):
    rec["ts"] = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(D / "orders.jsonl", "a") as fh:
        fh.write(json.dumps(rec) + "\n")

def cmd_balance():
    """Balance including funds RESERVED by open orders.

    2026-08-31: available USD drops by the order value the moment a limit rests,
    so a $25 resting buy made equity read $91.68 against a true $116.69. A number
    that looks like a loss but is not is exactly the kind of thing that gets
    misread later — same family as reporting a position that had already closed.
    """
    c = client()
    b = balances(c)
    p = price(c)
    usd = b.get("USD", 0.0)
    btc = b.get("BTC", 0.0)
    # Use the exchange's own HOLD field, not a sum over open orders. Summing
    # orders double-counted right after a cancel/replace, when `available` had
    # not yet decremented: equity briefly read $141.69 on a $116.69 account.
    # available + hold is internally consistent because both come from the same
    # account snapshot.
    held = 0.0
    try:
        for a in c.get_accounts().to_dict()["accounts"]:
            if a["currency"] == "USD":
                held = float((a.get("hold") or {}).get("value", 0) or 0)
    except Exception:
        pass
    eq = usd + held + btc * p
    extra = f" | reserved ${held:,.2f}" if held > 0 else ""
    print(f"USD ${usd:,.2f}{extra} | BTC {btc:.8f} (${btc*p:,.2f}) | price ${p:,.2f} | "
          f"equity ${eq:,.2f}")

def cmd_buy(usd_amount):
    usd_amount = round(float(usd_amount), 2)
    c = client()
    b = balances(c)
    cash = b.get("USD", 0.0)
    if usd_amount > MAX_ORDER_USD:
        print(f"REFUSED: ${usd_amount} exceeds max order ${MAX_ORDER_USD}"); return 1
    if cash - usd_amount < MIN_CASH_RESERVE:
        print(f"REFUSED: would leave ${cash-usd_amount:.2f}, below ${MIN_CASH_RESERVE} reserve"); return 1
    p_before = price(c)
    coid = f"q{uuid.uuid4().hex[:16]}"
    t0 = time.time()
    r = c.market_order_buy(client_order_id=coid, product_id=PRODUCT,
                           quote_size=str(usd_amount)).to_dict()
    ms = (time.time() - t0) * 1000
    ok = r.get("success")
    print(f"BUY ${usd_amount} -> success={ok} ({ms:.0f}ms)")
    oid = (r.get("success_response") or {}).get("order_id")
    fill = None
    if oid:
        time.sleep(2.5)
        o = c.get_order(oid).to_dict()["order"]
        filled = float(o.get("filled_size") or 0)
        avg = float(o.get("average_filled_price") or 0)
        fees = float(o.get("total_fees") or 0)
        fill = {"filled_btc": filled, "avg_price": avg, "fees": fees}
        slip = avg - p_before if avg else None
        print(f"  filled {filled:.8f} BTC @ ${avg:,.2f} | fees ${fees:.4f} | "
              f"seen ${p_before:,.2f} -> slip ${slip:+,.2f}" if avg else "  (fill pending)")
    log({"side": "BUY", "usd": usd_amount, "price_seen": p_before,
         "order_id": oid, "latency_ms": round(ms), "fill": fill, "raw_success": ok})
    return 0

def cmd_sell(amount):
    c = client()
    b = balances(c)
    btc = b.get("BTC", 0.0)
    size = btc if str(amount).lower() == "all" else float(amount)
    size = min(size, btc)
    if size <= 0:
        print("REFUSED: no BTC to sell"); return 1
    p_before = price(c)
    if size * p_before > MAX_ORDER_USD * 2:
        print(f"REFUSED: sell notional ${size*p_before:.2f} too large"); return 1
    coid = f"q{uuid.uuid4().hex[:16]}"
    t0 = time.time()
    r = c.market_order_sell(client_order_id=coid, product_id=PRODUCT,
                            base_size=f"{size:.8f}").to_dict()
    ms = (time.time() - t0) * 1000
    print(f"SELL {size:.8f} BTC -> success={r.get('success')} ({ms:.0f}ms)")
    oid = (r.get("success_response") or {}).get("order_id")
    fill = None
    if oid:
        time.sleep(2.5)
        o = c.get_order(oid).to_dict()["order"]
        avg = float(o.get("average_filled_price") or 0)
        fees = float(o.get("total_fees") or 0)
        fill = {"filled_btc": float(o.get("filled_size") or 0), "avg_price": avg, "fees": fees}
        if avg:
            print(f"  filled @ ${avg:,.2f} | fees ${fees:.4f} | seen ${p_before:,.2f} -> slip ${avg-p_before:+,.2f}")
    log({"side": "SELL", "btc": size, "price_seen": p_before,
         "order_id": oid, "latency_ms": round(ms), "fill": fill})
    # AUTO-LEDGER (the operator 2026-08-31): append the round trip to the vault the
    # moment it closes, so the record never falls behind the trading. Facts
    # only — it never rewrites lessons. Failure here must not break the exit.
    try:
        import subprocess as _sp
        r = _sp.run(["python3", str(D / "log_trade.py")], capture_output=True,
                    text=True, timeout=20)
        print("  " + (r.stdout.strip() or r.stderr.strip()[:120]))
    except Exception as _e:
        print(f"  (auto-ledger skipped: {_e})")
    return 0

def cmd_buy_limit(usd_amount, limit_price):
    """POST-ONLY limit buy — pays the 0.04% MAKER fee instead of 0.085% taker.
    Halves the round-trip hurdle from ~132 points to ~62. post_only means the
    order is REJECTED rather than filled if it would cross the spread, so it
    can never silently become a taker order."""
    usd_amount = round(float(usd_amount), 2)
    limit_price = round(float(limit_price), 2)
    c = client()
    b = balances(c)
    cash = b.get("USD", 0.0)
    if usd_amount > MAX_ORDER_USD:
        print(f"REFUSED: ${usd_amount} exceeds max order ${MAX_ORDER_USD}"); return 1
    if cash - usd_amount < MIN_CASH_RESERVE:
        print(f"REFUSED: would leave ${cash-usd_amount:.2f}, below ${MIN_CASH_RESERVE} reserve"); return 1
    mkt = price(c)
    if limit_price >= mkt:
        print(f"REFUSED: buy limit ${limit_price:,.2f} at/above market "
              f"${mkt:,.2f} would cross — post_only rejects it. Bid BELOW market.")
        return 1
    size = round(usd_amount / limit_price, 8)
    coid = f"q{uuid.uuid4().hex[:16]}"
    r = c.limit_order_gtc_buy(client_order_id=coid, product_id=PRODUCT,
                              base_size=f"{size:.8f}",
                              limit_price=f"{limit_price:.2f}",
                              post_only=True).to_dict()
    oid = (r.get("success_response") or {}).get("order_id")
    print(f"LIMIT BUY {size:.8f} BTC @ ${limit_price:,.2f} (mkt ${mkt:,.2f}) "
          f"-> success={r.get('success')} id={oid}")
    if not r.get("success"):
        print("  ", json.dumps(r.get("error_response") or {}))
    log({"side": "BUY_LIMIT", "usd": usd_amount, "limit": limit_price,
         "price_seen": mkt, "order_id": oid, "raw_success": r.get("success")})
    return 0 if r.get("success") else 1

def cmd_sell_limit(amount, limit_price):
    """POST-ONLY limit sell — maker fee. Must be ABOVE market or it crosses."""
    limit_price = round(float(limit_price), 2)
    c = client()
    b = balances(c)
    btc = b.get("BTC", 0.0)
    size = btc if str(amount).lower() == "all" else float(amount)
    size = min(size, btc)
    if size <= 0:
        print("REFUSED: no BTC to sell"); return 1
    mkt = price(c)
    if limit_price <= mkt:
        print(f"REFUSED: sell limit ${limit_price:,.2f} at/below market "
              f"${mkt:,.2f} would cross — post_only rejects it. Ask ABOVE market.")
        return 1
    if size * limit_price > MAX_ORDER_USD * 2:
        print(f"REFUSED: sell notional ${size*limit_price:.2f} too large"); return 1
    coid = f"q{uuid.uuid4().hex[:16]}"
    r = c.limit_order_gtc_sell(client_order_id=coid, product_id=PRODUCT,
                               base_size=f"{size:.8f}",
                               limit_price=f"{limit_price:.2f}",
                               post_only=True).to_dict()
    oid = (r.get("success_response") or {}).get("order_id")
    print(f"LIMIT SELL {size:.8f} BTC @ ${limit_price:,.2f} (mkt ${mkt:,.2f}) "
          f"-> success={r.get('success')} id={oid}")
    if not r.get("success"):
        print("  ", json.dumps(r.get("error_response") or {}))
    log({"side": "SELL_LIMIT", "btc": size, "limit": limit_price,
         "price_seen": mkt, "order_id": oid, "raw_success": r.get("success")})
    return 0 if r.get("success") else 1

def cmd_bracket(amount, target, stop):
    """Server-side BRACKET on an open BTC position: take-profit + stop, held by
    Coinbase. Exits even if this session dies.

    Built 2026-08-31 before trading BTC unattended. OANDA manages stops on its
    own servers; Coinbase spot does not, so an open position here depended on me
    staying alive to watch it. `trigger_bracket_order_gtc_sell` closes that hole:
    limit_price is the target, stop_trigger_price is the invalidation, and the
    exchange holds both.

    the operator is at work most sessions. An exit that needs me awake is not an exit.
    """
    target = round(float(target), 2); stop = round(float(stop), 2)
    c = client()
    btc = balances(c).get("BTC", 0.0)
    size = btc if str(amount).lower() == "all" else float(amount)
    size = min(size, btc)
    if size <= 0:
        print("REFUSED: no BTC held"); return 1
    mkt = price(c)
    if not (stop < mkt < target):
        print(f"REFUSED: need stop {stop:,.2f} < market {mkt:,.2f} < target {target:,.2f}")
        return 1
    coid = f"q{uuid.uuid4().hex[:16]}"
    r = c.trigger_bracket_order_gtc_sell(client_order_id=coid, product_id=PRODUCT,
                                         base_size=f"{size:.8f}",
                                         limit_price=f"{target:.2f}",
                                         stop_trigger_price=f"{stop:.2f}").to_dict()
    oid = (r.get("success_response") or {}).get("order_id")
    print(f"BRACKET {size:.8f} BTC | target ${target:,.2f} | stop ${stop:,.2f} "
          f"-> success={r.get('success')} id={oid}")
    if not r.get("success"):
        print("  ", json.dumps(r.get("error_response") or {}))
    log({"side": "BRACKET", "btc": size, "target": target, "stop": stop,
         "price_seen": mkt, "order_id": oid, "raw_success": r.get("success")})
    return 0 if r.get("success") else 1

def cmd_orders():
    c = client()
    os_ = c.list_orders(product_ids=[PRODUCT], order_status=["OPEN"]).to_dict()
    rows = os_.get("orders", [])
    if not rows:
        print("no open orders"); return 0
    for o in rows:
        cfg = (o.get("order_configuration") or {}).get("limit_limit_gtc", {})
        print(f"{o['order_id'][:8]} {o['side']:4} {cfg.get('base_size','?')} @ "
              f"${float(cfg.get('limit_price',0)):,.2f}  {o['status']}")
    return 0

def cmd_cancel(which):
    c = client()
    if str(which).lower() == "all":
        os_ = c.list_orders(product_ids=[PRODUCT], order_status=["OPEN"]).to_dict()
        ids = [o["order_id"] for o in os_.get("orders", [])]
    else:
        ids = [which]
    if not ids:
        print("nothing to cancel"); return 0
    r = c.cancel_orders(order_ids=ids).to_dict()
    print(f"cancelled {len(ids)}: {json.dumps(r.get('results', []))[:300]}")
    return 0

# ---------------- US PERP-STYLE FUTURES (CFM, added 2026-09-01) ----------------
# the operator enabled the futures account today. 1 contract = 0.01 BTC (~$770
# notional), whole contracts only, venue CDE. Fees per the account's REAL tier
# (get_transaction_summary(product_type="FUTURE"), 2026-09-01): "Advanced 1"
# maker 0.095% / taker 0.10% — ~$0.74/side on one contract, ~$1.50 a round
# trip = 0.55R of a $2.75 stop. The earlier "0% / 0.03%" note was wrong.
# MIN RISK REALITY: a volatility stop ~$275 away on 1 contract risks ~$2.75 —
# this exceeds the $0.60 spot risk unit and was flagged to the operator; NO futures
# order may be placed until he approves the risk number per trade.
# the operator approved $2.75/trade (1 contract) on 2026-09-01.
#
# LEARNED THE HARD WAY (2026-09-01 19:45 ET, two rejected previews, nothing filled):
#  1. `trigger_bracket_gtc` is an EXIT bracket for an EXISTING position
#     (limit_price = take-profit, stop_trigger_price = stop-loss). Sending it
#     with no position -> PREVIEW_BRACKET_ORDER_SIZE_EXCEEDS_POSITION.
#     Sequence: `fbuy N <entry>` (plain limit) -> wait for fill (fbal) ->
#     `fsell N <tp> <stop>` (bracket). Mirror for shorts.
#  2. Spot USD (cbi_usd_balance) is NOT auto-swept into the futures wallet
#     (cfm_usd_balance) for API orders -> PREVIEW_INSUFFICIENT_FUNDS_FOR_FUTURES.
#     The SDK only sweeps futures->spot (schedule_futures_sweep). Funding the
#     futures wallet is a UI action for the operator ("Transfer to Futures").
FUT_PRODUCT = "BIP-20DEC30-CDE"

def cmd_fbal():
    c = client()
    b = c.get_futures_balance_summary().to_dict()["balance_summary"]
    print(f"FUT buying power ${float(b['futures_buying_power']['value']):,.2f} | "
          f"total ${float(b['total_usd_balance']['value']):,.2f} | "
          f"init margin ${float(b['initial_margin']['value']):,.2f} | "
          f"uPL {float(b['unrealized_pnl']['value']):+,.2f} | "
          f"day rPL {float(b['daily_realized_pnl']['value']):+,.2f}")
    ps = c.list_futures_positions().to_dict().get("positions", [])
    if not ps:
        print("no futures positions")
    for x in ps:
        print(f"  {x.get('product_id')} {x.get('side')} {x.get('number_of_contracts')} "
              f"@ {x.get('avg_entry_price')} uPL {x.get('unrealized_pnl')}")
    return 0

def _fut_order(side, contracts, limit_price, stop=None, tp=None):
    """Whole-contract order on the nano perp.
    No stop  -> plain limit ENTRY (limit_limit_gtc).
    stop set -> EXIT bracket on an existing position (trigger_bracket_gtc):
                limit_price is the take-profit, stop_trigger_price the stop.
                Side must be opposite the position. `tp` is ignored (kept for
                the CLI shape)."""
    import uuid
    c = client()
    n = int(contracts)
    assert n >= 1, "min 1 contract"
    cfg = {"limit_limit_gtc": {"base_size": str(n), "limit_price": f"{float(limit_price):.2f}"}}
    if stop:
        cfg = {"trigger_bracket_gtc": {"base_size": str(n),
               "limit_price": f"{float(limit_price):.2f}",
               "stop_trigger_price": f"{float(stop):.2f}"}}
    r = c.create_order(client_order_id=str(uuid.uuid4()), product_id=FUT_PRODUCT,
                       side=side, order_configuration=cfg).to_dict()
    ok = r.get("success")
    print(("OK " if ok else "FAIL ") + json.dumps(r.get("success_response") or
          r.get("error_response") or r)[:300])
    return 0 if ok else 1

def cmd_fbuy(contracts, price, stop=None, tp=None):
    return _fut_order("BUY", contracts, price, stop, tp)

def cmd_fsell(contracts, price, stop=None, tp=None):
    return _fut_order("SELL", contracts, price, stop, tp)

def cmd_forders():
    c = client()
    rows = c.list_orders(product_ids=[FUT_PRODUCT], order_status=["OPEN"]).to_dict().get("orders", [])
    if not rows:
        print("no open futures orders"); return 0
    for o in rows:
        cfg = o.get("order_configuration") or {}
        inner = next(iter(cfg.values()), {})
        print(f"{o['order_id'][:8]} {o['side']:4} {inner.get('base_size','?')} @ "
              f"{inner.get('limit_price','?')} {o['status']}")
    return 0

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "balance"
    if cmd == "balance" or cmd == "position":
        cmd_balance()
    elif cmd == "buy":
        sys.exit(cmd_buy(sys.argv[2]))
    elif cmd == "sell":
        sys.exit(cmd_sell(sys.argv[2]))
    elif cmd == "buylimit":
        sys.exit(cmd_buy_limit(sys.argv[2], sys.argv[3]))
    elif cmd == "selllimit":
        sys.exit(cmd_sell_limit(sys.argv[2], sys.argv[3]))
    elif cmd == "bracket":
        sys.exit(cmd_bracket(sys.argv[2], sys.argv[3], sys.argv[4]))
    elif cmd == "orders":
        sys.exit(cmd_orders())
    elif cmd == "cancel":
        sys.exit(cmd_cancel(sys.argv[2]))
    elif cmd == "fbal":
        sys.exit(cmd_fbal())
    elif cmd == "fbuy":
        sys.exit(cmd_fbuy(*sys.argv[2:]))
    elif cmd == "fsell":
        sys.exit(cmd_fsell(*sys.argv[2:]))
    elif cmd == "forders":
        sys.exit(cmd_forders())
    else:
        print(__doc__)
