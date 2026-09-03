#!/usr/bin/env python3
"""Append the last completed round trip to the vault ledger. AUTOMATIC.

the operator, 2026-08-31: "document after every trade so you don't have to remind
yourself after five or six trades." Tonight proved the point — trades 1-4 were
logged, then I fell behind and backfilled 5-8 from memory in one batch.

IMPORTANT DISTINCTION (the operator's earlier correction): logging WHAT HAPPENED is
always right. REWRITING CONCLUSIONS off a small sample is not. This appends a
fact row to the ledger and touches nothing else — it never edits the lessons.

Automation over discipline: discipline is what slipped, so execute.py calls
this itself whenever a close leaves the book flat.
"""
import json, sys
from pathlib import Path

D = Path(__file__).resolve().parent
ORDERS = D / "orders.jsonl"
LEDGER = D.parent / "research" / "TRADING_LESSONS.md"
MARK = "<!-- auto-ledger -->"

def round_trips():
    """Pair BUY/SELL fills from the EXCHANGE, newest last.

    FIX 2026-08-31: this used to read the local orders.jsonl, which only
    records orders placed through execute.py. A resting LIMIT filling on the
    exchange closed a position with no local call, so the auto-ledger silently
    missed it — a hole in exactly the exit path the policy now prefers.
    Sourcing from the exchange catches every close however it happened.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("ex", D / "execute.py")
    mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    d = mod.client().list_orders(product_ids=["BTC-USD"], limit=60).to_dict()
    fills = []
    for o in d.get("orders", []):
        if o.get("status") != "FILLED":
            continue
        sz = float(o.get("filled_size") or 0)
        px = float(o.get("average_filled_price") or 0)
        if sz <= 0 or px <= 0:
            continue
        fills.append({"id": o["order_id"], "side": o["side"], "size": sz,
                      "px": px, "fees": float(o.get("total_fees") or 0),
                      "ts": (o.get("last_fill_time") or "")[:19].replace("T", " ")})
    fills.sort(key=lambda f: f["ts"])
    out, open_buy = [], None
    for f in fills:
        if f["side"] == "BUY":
            open_buy = f
        elif f["side"] == "SELL" and open_buy:
            gross = (f["px"] - open_buy["px"]) * min(open_buy["size"], f["size"])
            fees = open_buy["fees"] + f["fees"]
            out.append({"id": f["id"][:8], "ts": f["ts"],
                        "usd": round(open_buy["px"] * open_buy["size"]),
                        "entry": open_buy["px"], "exit": f["px"],
                        "pts": f["px"] - open_buy["px"], "gross": gross,
                        "fees": fees, "net": gross - fees})
            open_buy = None
    return out

def last_round_trip():
    rts = round_trips()
    return rts[-1] if rts else None

def main():
    trips = round_trips()
    if not trips:
        print("log_trade: no completed round trip found"); return 1
    logged = 0
    for t in trips:
        if not LEDGER.exists():
            print("log_trade: ledger not found"); return 1
        s = LEDGER.read_text()
        tag = f"{MARK}{t['id']}"
        if tag in s:
            continue
        row = (f"| {t['ts']} | ${t['usd']} | {t['entry']:,.2f} -> {t['exit']:,.2f} | "
               f"{t['pts']:+.0f} pts | {t['gross']:+.4f} | {t['fees']:.4f} | "
               f"**{t['net']:+.4f}** | {tag}\n")
        anchor = "## LIVE LEDGER — Coinbase real money (opened 2026-08-30)\n"
        hdr = ("\n### Auto-logged round trips (appended by `log_trade.py` on every close)\n\n"
               "| closed | size | entry -> exit | move | gross | fees | net | id |\n"
               "|---|---|---|---|---|---|---|---|\n")
        if "### Auto-logged round trips" not in s:
            s = s.replace(anchor, anchor + hdr)
        marker = "|---|---|---|---|---|---|---|---|\n"
        idx = s.index(marker) + len(marker)
        LEDGER.write_text(s[:idx] + row + s[idx:])
        print(f"log_trade: appended {t['pts']:+.0f} pts net {t['net']:+.4f} ({t['id']})")
        logged += 1
    print(f"log_trade: {logged} new round trip(s) logged")
    return 0

if __name__ == "__main__":
    sys.exit(main())
