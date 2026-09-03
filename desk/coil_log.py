#!/usr/bin/env python3
"""Log EVERY coil break across the basket — traded or not — and score them.

  python3 coil_log.py            # scan once (runs at most once per minute; safe in a loop)
  python3 coil_log.py score      # score every logged break at 15/30/60m, cut by
                                 # tide / tick burst / day direction / timeframe

WHY THIS EXISTS (the operator, 2026-09-02 11:35): "Was there something you identified
that could be replicable for these patterns so maybe we can try catching the
next one?" The three best moves of the night (00:51 traded +0.9R, 01:41 declined
+42p, 09:19 declined +74p) shared one shape — a coil at the edge of the range,
broken in the day's direction, on a burst of ticks with a strong body. The two
rules that declined them ("leg too old", "M15 no tide") each rest on n<=4. Only
the ones I happened to notice were ever logged; n=3 decides nothing.

This is a NOTEBOOK, not a bot. It never places an order. It writes every break
of the shape to coils.jsonl with the conditions attached, so `score` can ask,
with numbers: does the tide matter? does the burst? does the day's direction?

SHAPE (see detect()): a shelf inside the prior 8 bars, tested >= 2 times, broken
by a closed bar with a real body, from the outer half of the 24-bar range.
Logged with: squeeze (6-bar / prior 12-bar range), tick burst vs the 12-bar
mean, body share, M15/M5 phase (tide with / against / none), pips from the
day's open (day with / against / flat).
Each record also carries `rebreak`: how many logged breaks of the same level
(±3 pips, same pair) sit in the prior 3h — 0 is a FIRST break. See REBREAK_*.
Every qualifying break is logged — quiet ones too — because "does the burst
matter?" needs the quiet breaks in the sample. Only breaks with burst >= 1.4x
AND body >= 60% are echoed to the watcher (those are the ones worth eyes).

Watcher hook (trade_watch.sh, add at the next restart — do NOT edit the script
while it is running under Monitor):
  CL=".../desk/coil_log.py"   then in the loop:  cl=$(python3 "$CL" 2>/dev/null); [ -n "$cl" ] && echo "$cl"
Until then it runs under its own Monitor loop (started 2026-09-02).
"""
import calendar, json, statistics, sys, time
from pathlib import Path

D = Path(__file__).resolve().parent
sys.path.insert(0, str(D))
import call as C                      # get(), mid(), pip_of(), _fwd(), HORIZONS, MIN_MOVE
import structure as S                 # phase()
from fx_scan import PAIRS

LOG   = D / "coils.jsonl"
STATE = D / ".coil_state.json"
TF_SEC = {"M1": 60, "M5": 300}
SUPPRESS_BARS = 10                    # one log per pair/tf per 10 bars — a re-break is the same shelf
N_SHELF   = 8                         # the level must sit inside the prior 8 bars
TOUCH_TOL = 0.25                      # a "touch" = within 0.25 avg-bar of the extreme; need >= 2
MIN_BODY  = 0.5                       # break bar body >= half its range — a direction, not a wick
ECHO_BURST, ECHO_BODY = 1.4, 0.6      # only the full shape is echoed to the watcher; the rest logs silently
DAY_FLAT_PIPS = 10.0                  # |pips from day open| below this = "flat"
REBREAK_HOURS, REBREAK_TOL = 3, 3.0   # re-break = a logged break of the same pair within 3 pips of this
                                      # edge in the prior 3h (older than 10 min, so the M1+M5 pair of one
                                      # break does not count itself). Added 2026-09-02 14:55 (the operator: "Ok you
                                      # can make the edit if you believe it will help") after AUD_USD broke
                                      # the same 0.7168-0.7170 level 11 times in 2.5h and every one failed,
                                      # while the two big USD_JPY winners (01:41, 09:19) were FIRST breaks.

def _state():
    try: return json.loads(STATE.read_text())
    except Exception: return {"last_min": "", "seen": {}}

def _bars(pair, tf, n=40):
    cs = [c for c in C.get(f"/v3/instruments/{pair}/candles?count={n}&granularity={tf}&price=M")["candles"]
          if c.get("complete")]
    O = [float(c["mid"]["o"]) for c in cs]; H = [float(c["mid"]["h"]) for c in cs]
    L = [float(c["mid"]["l"]) for c in cs]; Cc = [float(c["mid"]["c"]) for c in cs]
    V = [c["volume"] for c in cs]; T = [c["time"][:19] for c in cs]
    return O, H, L, Cc, V, T

def detect(pair, tf):
    """A SHELF BREAK: the last closed bar closes beyond the extreme of the prior
    8 bars, that extreme was tested at least twice (a level that held), the break
    starts from the outer half of the 24-bar range, and the break bar is a real
    directional bar (body >= half its range). Compression (6-bar vs prior 12-bar
    range) is RECORDED, not required — replaying today's USD_JPY M1 showed the
    09:19 break (+74p) had a 0.87 ratio, so a strict <0.6 coil rule misses the
    very shape this file exists to study. `score` cuts by it instead."""
    O, H, L, Cc, V, T = _bars(pair, tf)
    i = len(Cc) - 1
    if i < 30: return None
    pip = C.pip_of(pair)
    avg = statistics.mean((H[j] - L[j]) / pip for j in range(i - 12, i)) or 0.01
    lo = min(L[i-N_SHELF:i]); hi = max(H[i-N_SHELF:i])
    n_lo = sum(1 for j in range(i - N_SHELF, i) if (L[j] - lo) / pip <= TOUCH_TOL * avg)
    n_hi = sum(1 for j in range(i - N_SHELF, i) if (hi - H[j]) / pip <= TOUCH_TOL * avg)
    hi24 = max(H[i-24:i]); lo24 = min(L[i-24:i]); span = (hi24 - lo24) or 1e-9
    pos = (Cc[i-1] - lo24) / span
    if Cc[i] < lo and n_lo >= 2 and pos < 0.5:   d, edge, side = "down", lo, "bottom"
    elif Cc[i] > hi and n_hi >= 2 and pos > 0.5: d, edge, side = "up", hi, "top"
    else: return None
    rng = (H[i] - L[i]) / pip or 0.01
    body = abs(Cc[i] - O[i]) / pip / rng
    if (d == "up") != (Cc[i] > O[i]) or body < MIN_BODY: return None
    r6  = (max(H[i-6:i]) - min(L[i-6:i])) / pip
    r12 = (max(H[i-18:i-6]) - min(L[i-18:i-6])) / pip
    burst = V[i] / (statistics.mean(V[i-12:i]) or 1)
    return {"tf": tf, "dir": d, "edge": edge, "side": side, "touches": max(n_lo, n_hi),
            "coil": round(r6, 1), "prior": round(r12, 1), "squeeze": round(r6 / r12, 2) if r12 else None,
            "burst": round(burst, 2), "body": round(body, 2), "bar": T[i], "close": Cc[i]}

def _rebreaks(pair, edge, epoch, pip):
    """How many times this level already broke (either direction) — 0 = a first break."""
    n = 0
    try:
        for l in LOG.read_text().splitlines():
            if not l.strip(): continue
            r = json.loads(l)
            if (r["pair"] == pair and epoch - REBREAK_HOURS * 3600 <= r["epoch"] < epoch - 600
                    and abs(r["edge"] - edge) / pip <= REBREAK_TOL):
                n += 1
    except FileNotFoundError:
        pass
    return n

def context(pair, d):
    pip = C.pip_of(pair)
    m15, _ = S.phase(pair, "M15"); m5, _ = S.phase(pair, "M5")
    if m15 in ("LEG_UP", "BUILDUP_HI"):   tide = "with" if d == "up" else "against"
    elif m15 in ("LEG_DN", "BUILDUP_LO"): tide = "with" if d == "down" else "against"
    else: tide = "none"
    dc = C.get(f"/v3/instruments/{pair}/candles?count=1&granularity=D&price=M")["candles"][-1]
    day = (float(dc["mid"]["c"]) - float(dc["mid"]["o"])) / pip
    if abs(day) < DAY_FLAT_PIPS: dayrel = "flat"
    else: dayrel = "with" if (day > 0) == (d == "up") else "against"
    return {"m15": m15, "m5": m5, "tide": tide, "day_pips": round(day, 1), "day": dayrel}

def scan():
    st = _state()
    now_min = time.strftime("%Y-%m-%d %H:%M")
    if st.get("last_min") == now_min: return 0           # the watcher loops faster than the bars close
    st["last_min"] = now_min
    tfs = ["M1"] + (["M5"] if int(now_min[-2:]) % 5 == 0 else [])
    seen = st.setdefault("seen", {})
    for pair in PAIRS:
        for tf in tfs:
            try: h = detect(pair, tf)
            except Exception: continue
            if not h: continue
            key = f"{pair}:{tf}"
            last = seen.get(key, 0)
            bar_epoch = calendar.timegm(time.strptime(h["bar"], "%Y-%m-%dT%H:%M:%S"))   # OANDA times are UTC
            if bar_epoch - last < SUPPRESS_BARS * TF_SEC[tf]: continue
            try: ctx = context(pair, h["dir"])
            except Exception: ctx = {"m15": "?", "m5": "?", "tide": "?", "day_pips": 0.0, "day": "?"}
            px = C.mid(pair); now = int(time.time())
            rb = _rebreaks(pair, h["edge"], now, C.pip_of(pair))
            rec = {"ts": time.strftime("%Y-%m-%d %H:%M:%S"), "epoch": now,
                   "pair": pair, "dir": h["dir"], "price": px, **h, **ctx, "rebreak": rb}
            with open(LOG, "a") as fh: fh.write(json.dumps(rec) + "\n")
            seen[key] = bar_epoch
            if h["burst"] < ECHO_BURST or h["body"] < ECHO_BODY: continue
            fmt = ".3f" if "JPY" in pair else ".5f"
            print(f"COIL {tf} {pair} {h['dir'].upper()} break {h['edge']:{fmt}} | coil {h['coil']}p/{h['prior']}p "
                  f"@{h['side']} squeeze {h['squeeze']} | ticks {h['burst']}x body {h['body']*100:.0f}% | M15 {ctx['m15']} "
                  f"(tide {ctx['tide']}) M5 {ctx['m5']} | day {ctx['day_pips']:+.0f}p ({ctx['day']})"
                  + (f" | RE-BREAK x{rb}" if rb else " | first break"))
    STATE.write_text(json.dumps(st))
    return 0

def _bucket_burst(b): return "<1.0x" if b < 1.0 else ("1.0-1.4x" if b < 1.4 else ">=1.4x")

_M1 = {}
def _fwd(pair, epoch, minutes):
    """call._fwd re-fetches 5000 M1 candles on EVERY call; at 68 records x 3
    horizons that is 200+ pulls and OANDA answered 504 (2026-09-02 14:00).
    One pull per pair, cached for the run; a failed pull scores nothing for
    that pair instead of killing the whole report."""
    if pair not in _M1:
        try:
            cs = C.get(f"/v3/instruments/{pair}/candles?count=5000&granularity=M1&price=M")["candles"]
            _M1[pair] = [(calendar.timegm(time.strptime(c["time"][:19], "%Y-%m-%dT%H:%M:%S")), c)
                         for c in cs if c.get("complete")]
        except Exception as e:
            print(f"  ! {pair}: candle fetch failed ({e}); skipped"); _M1[pair] = None
    if not _M1[pair]: return None, None
    win = [c for st, c in _M1[pair] if epoch <= st <= epoch + minutes * 60]
    if not win: return None, None
    close = float(win[-1]["mid"]["c"])
    return close, close

def score():
    if not LOG.exists(): print("no coil breaks logged yet"); return 0
    recs = [json.loads(l) for l in LOG.read_text().splitlines() if l.strip()]
    now = int(time.time()); rows = []
    print(f"{'time':9} {'tf':3} {'pair':8} {'dir':5} " + " ".join(f"{h:>5}m" for h in C.HORIZONS)
          + "  burst body  tide     day      M15")
    for r in recs:
        if now < r["epoch"] + 60 * 60 + 60: continue          # wait for the 60m horizon
        pip = C.pip_of(r["pair"]); adv = {}
        for h in C.HORIZONS:
            ext, close = _fwd(r["pair"], r["epoch"], h)
            if ext is None: continue
            adv[h] = (close - r["price"]) / pip if r["dir"] == "up" else (r["price"] - close) / pip
        if len(adv) < len(C.HORIZONS): continue
        rows.append((r, adv))
        print(f"{r['ts'][11:]:9} {r['tf']:3} {r['pair']:8} {r['dir']:5} "
              + " ".join(f"{adv[h]:+5.1f}" for h in C.HORIZONS)
              + f"  {r['burst']:4.2f} {r['body']*100:4.0f}%  {r['tide']:8} {r['day']:8} {r['m15']}")
    if not rows: print("nothing old enough to score yet"); return 0
    def cut(name, keyf):
        print(f"\n  by {name}:")
        groups = {}
        for r, adv in rows: groups.setdefault(keyf(r), []).append(adv)
        for g in sorted(groups):
            a = groups[g]; n = len(a)
            for h in (30, 60):
                right = sum(1 for x in a if x[h] >= C.MIN_MOVE); wrong = sum(1 for x in a if x[h] <= -C.MIN_MOVE)
                dec = right + wrong; acc = f"{right/dec*100:.0f}%" if dec else "n/a"
                mean = statistics.mean(x[h] for x in a)
                print(f"    {g:10} n={n:<3} {h}m: {right}R/{wrong}W/{n-dec}F acc {acc:>4} mean {mean:+.1f}p")
    cut("tide (M15 with / against / none)", lambda r: r["tide"])
    cut("tick burst", lambda r: _bucket_burst(r["burst"]))
    cut("day direction", lambda r: r["day"])
    cut("timeframe", lambda r: r["tf"])
    cut("body >= 60%", lambda r: "strong" if r["body"] >= 0.6 else "weak")
    cut("re-break (first = level not broken in prior 3h)", lambda r: "first" if r.get("rebreak", 0) == 0 else f"re-break x{min(r.get('rebreak', 0), 3)}{'+' if r.get('rebreak', 0) > 3 else ''}")
    return 0

if __name__ == "__main__":
    sys.exit(score() if len(sys.argv) > 1 and sys.argv[1] == "score" else scan())
