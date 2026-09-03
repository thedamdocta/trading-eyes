#!/usr/bin/env python3
"""FX minute desk — TradingView eyes (OANDA feed), OANDA execution.

Pair-aware: JPY pairs quote to 2-3 decimals with a 0.01 pip; everything else
quotes to 4-5 decimals with a 0.0001 pip. Getting that wrong silently produces
garbage sizing, so it is table-driven, not hardcoded.

Carries all three guards learned on the BTC desk 2026-08-30:
  1. staleness  — distinct-value count per bar (a frozen page OCRs perfectly)
  2. plausibility — reject implausible jumps (OCR digit flips read as moves)
  3. intra-bar levels — act at the level, not 60s later at the close

Usage:  python3 fx_desk.py USD_JPY <capture_dir>
"""
import json, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude/skills/vision/scripts"))
import ocr_engine as ocre
from PIL import Image

OUT = Path(__file__).resolve().parent
REGION = (937, 528, 190, 42)
STALE_S = 30

# pip: JPY pairs 0.01, everything else 0.0001. lo/hi are sanity bounds.
# max_jump is the plausibility gate as a FRACTION — FX moves far less per
# 4s read than crypto, so this is tighter than the BTC desk's 1%.
INSTRUMENTS = {
    "USD_JPY": {"re": r"(\d{3}\.\d{2,3})",  "pip": 0.01,   "lo": 100,  "hi": 200},
    "EUR_JPY": {"re": r"(\d{3}\.\d{2,3})",  "pip": 0.01,   "lo": 100,  "hi": 250},
    "GBP_JPY": {"re": r"(\d{3}\.\d{2,3})",  "pip": 0.01,   "lo": 150,  "hi": 300},
    "AUD_JPY": {"re": r"(\d{2,3}\.\d{2,3})","pip": 0.01,   "lo":  60,  "hi": 150},
    "EUR_USD": {"re": r"(1\.\d{4,5})",      "pip": 0.0001, "lo": 0.8,  "hi": 1.5},
    "GBP_USD": {"re": r"(1\.\d{4,5})",      "pip": 0.0001, "lo": 1.0,  "hi": 1.8},
    "AUD_USD": {"re": r"(0\.\d{4,5})",      "pip": 0.0001, "lo": 0.5,  "hi": 1.0},
    "NZD_USD": {"re": r"(0\.\d{4,5})",      "pip": 0.0001, "lo": 0.4,  "hi": 0.9},
    "USD_CAD": {"re": r"(1\.\d{4,5})",      "pip": 0.0001, "lo": 1.0,  "hi": 1.8},
    "USD_CHF": {"re": r"(0\.\d{4,5})",      "pip": 0.0001, "lo": 0.6,  "hi": 1.2},
    "EUR_GBP": {"re": r"(0\.\d{4,5})",      "pip": 0.0001, "lo": 0.7,  "hi": 1.0},
}
OHLC_REGION = (300, 52, 460, 22)   # TradingView chart legend
OHLC_RE_JPY   = r"\d{2,3}\.\d{2,3}"     # 159.812 / 114.448
OHLC_RE_MAJOR = r"\d\.\d{4,5}"           # 1.15909 / 0.71650
MAX_JUMP_FRAC = 0.003          # 0.3% between reads = OCR misread, not a move

_last_good = None
_last_candle = None

def read_price(buf, cfg):
    global _last_good
    segs = sorted((buf / "buffer").glob("seg_*.mp4"))
    if not segs:
        return None
    newest = segs[-1]
    if time.time() - newest.stat().st_mtime > STALE_S:
        return None                       # feed died — say blind, never guess
    frame = buf / "_fx_frame.png"
    r = subprocess.run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(newest),
                        "-frames:v", "1", str(frame)],
                       capture_output=True, timeout=25)
    if r.returncode != 0:
        return None
    global _last_candle
    _last_candle = read_ohlc(frame, cfg.get("_pair", ""))
    # API FIRST (2026-08-31): authoritative, cannot drift out of a crop box.
    v = api_price(cfg.get("_pair", ""))
    if v is not None and cfg["lo"] < v < cfg["hi"]:
        _last_good = v
        return v
    x, y, w, h = REGION
    Image.open(frame).crop((x, y, x + w, y + h)).save(buf / "_fx_px.png")
    res = ocre.text(str(buf / "_fx_px.png"))
    if not res.get("ok"):
        return None
    txt = " ".join(l["text"] for l in res.get("lines", []))
    m = re.search(cfg["re"], txt.replace(",", "").replace(" ", ""))
    if not m:
        return None
    v = float(m.group(1))
    if not (cfg["lo"] < v < cfg["hi"]):
        return None
    if _last_good is not None and abs(v - _last_good) / _last_good > MAX_JUMP_FRAC:
        print(f"  !! REJECTED implausible read {v} "
              f"({(v-_last_good)/_last_good*100:+.2f}% vs {_last_good}) — misread",
              flush=True)
        return None
    _last_good = v
    return v

# PARTICIPATION (2026-08-31). OANDA candle "volume" is a TICK COUNT — the
# number of price updates in the bar — NOT traded size. Verified: 18-285
# ticks/min on USD_JPY, avg 185, and it tracks range closely, so it works as
# an activity proxy the way traded volume did on the BTC desk.
# LIMITATION, stated plainly: a single large fill is ONE tick. The 26x
# whale print caught on Coinbase would be INVISIBLE here. Activity, not size.
_tick_env = None

def ticks_now(pair):
    """(ticks in last closed bar, ratio vs 20-bar avg). Never breaks the desk."""
    global _tick_env
    try:
        import urllib.request, json as _json
        if _tick_env is None:
            e = {}
            for line in (OUT.parent / ".env").read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("="); e[k.strip()] = v.strip()
            _tick_env = e
        u = _tick_env["OANDA_API_URL"].rstrip("/")
        r = urllib.request.Request(
            f"{u}/v3/instruments/{pair}/candles?count=21&granularity=M1&price=M",
            headers={"Authorization": f"Bearer {_tick_env['OANDA_API_KEY']}"})
        with urllib.request.urlopen(r, timeout=15) as x:
            cs = _json.load(x)["candles"]
        # BUG FIX 2026-08-31: must use COMPLETE candles only. Reading the
        # still-forming bar gave a partial count (4 ticks vs a 185 average)
        # and understated every ratio. OANDA flags this explicitly.
        v = [c["volume"] for c in cs if c.get("complete")]
        if len(v) < 5:
            return None, None
        last = v[-1]; avg = sum(v[:-1]) / len(v[:-1])
        return last, (last / avg if avg else None)
    except Exception:
        return None, None

def api_price(pair):
    """Live mid from the OANDA API — the AUTHORITATIVE price source.

    WHY THIS EXISTS (2026-08-31, after a 2-minute blackout with a position on):
    price used to come from OCR of REGION, a FIXED box aimed at TradingView's
    right-axis price label. That label MOVES VERTICALLY with price. USD/JPY
    rallied 25 pips off the session low, the label climbed out of the box, and
    the desk went BLIND while short — 14 failed reads in a row.

    The box was never wrong; it was aimed at a moving target. And the number it
    was chasing is one the API already returns exactly, for free, on the same
    connection the desk uses for candles and ticks. OCR was inherited from the
    BTC/TradingView desk, where no API existed.

    Vision still earns its place — it reads CANDLE SHAPE off the legend, which
    no API call gives. But price is now API-first, OCR only as a fallback.
    """
    global _tick_env
    try:
        import urllib.request, json as _json
        if _tick_env is None:
            e = {}
            for line in (OUT.parent / ".env").read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("="); e[k.strip()] = v.strip()
            _tick_env = e
        u = _tick_env["OANDA_API_URL"].rstrip("/")
        r = urllib.request.Request(
            f"{u}/v3/accounts/{_tick_env['OANDA_ACCOUNT_ID']}/pricing?instruments={pair}",
            headers={"Authorization": f"Bearer {_tick_env['OANDA_API_KEY']}"})
        with urllib.request.urlopen(r, timeout=15) as x:
            q = _json.load(x)["prices"][0]
        if not q.get("tradeable"):
            return None
        return (float(q["bids"][0]["price"]) + float(q["asks"][0]["price"])) / 2
    except Exception:
        return None

def _tradeable(pair):
    """Ask the VENUE whether the market is open. Distinguishes a dead feed from
    a closed market — see the staleness block. Never breaks the desk."""
    global _tick_env
    try:
        import urllib.request, json as _json
        if _tick_env is None:
            e = {}
            for line in (OUT.parent / ".env").read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, _, v = line.partition("="); e[k.strip()] = v.strip()
            _tick_env = e
        u = _tick_env["OANDA_API_URL"].rstrip("/")
        r = urllib.request.Request(
            f"{u}/v3/accounts/{_tick_env['OANDA_ACCOUNT_ID']}/pricing?instruments={pair}",
            headers={"Authorization": f"Bearer {_tick_env['OANDA_API_KEY']}"})
        with urllib.request.urlopen(r, timeout=10) as x:
            return bool(_json.load(x)["prices"][0].get("tradeable"))
    except Exception:
        return True          # unknown -> assume open, keep the louder warning

def read_ohlc(frame_path, pair):
    """Real candle from the chart legend — O/H/L/C as TradingView renders it,
    not reconstructed from 4s samples. Ported from the BTC desk 2026-08-31 at
    the operator's suggestion so forex is ready before the London session.

    OCR renders the leading 'O' as a zero, so parse POSITIONALLY: the first
    four price-shaped numbers are O, H, L, C. Number format is PAIR-AWARE —
    a JPY cross and a major look nothing alike and one regex cannot do both.
    """
    try:
        rx = OHLC_RE_JPY if "JPY" in pair else OHLC_RE_MAJOR
        x, y, w, h = OHLC_REGION
        crop = Image.open(frame_path).crop((x, y, x + w, y + h))
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
        tmp = Path(frame_path).with_name("_fx_ohlc_px.png")
        crop.save(tmp)
        res = ocre.text(str(tmp))
        if not res.get("ok"):
            return None
        txt = " ".join(l["text"] for l in res.get("lines", []))
        nums = re.findall(rx, txt.replace(",", ""))
        if len(nums) < 4:
            return None
        o, hi_, lo_, c = (float(n) for n in nums[:4])
        if not (lo_ <= o <= hi_ and lo_ <= c <= hi_):
            return None                       # incoherent, refuse it
        return {"o": o, "h": hi_, "l": lo_, "c": c, "body": c - o,
                "rng": hi_ - lo_, "upper": hi_ - max(o, c),
                "lower": min(o, c) - lo_}
    except Exception:
        return None

def describe_candle(k, pip):
    """Name the shape the way a person reading the chart would, in PIPS."""
    if not k or k["rng"] <= 0:
        return ""
    body, rng = abs(k["body"]), k["rng"]
    d = "UP" if k["body"] > 0 else ("DOWN" if k["body"] < 0 else "flat")
    if body / rng < 0.15:
        shape = "doji"
    elif k["lower"] > body * 2 and k["upper"] < body:
        shape = "hammer(rejected lows)"
    elif k["upper"] > body * 2 and k["lower"] < body:
        shape = "shooting-star(rejected highs)"
    elif body / rng > 0.7:
        shape = "strong-body"
    else:
        shape = "normal"
    return (f"{d} {shape} body {k['body']/pip:+.1f}p rng {rng/pip:.1f}p "
            f"wick^{k['upper']/pip:.1f} v{k['lower']/pip:.1f}")

def check_levels(p, pair, pip):
    """Intra-bar alerting — act at the level, not at the close."""
    lv = OUT / f"levels_{pair}.json"
    try:
        cfg = json.loads(lv.read_text())
    except (OSError, ValueError):
        return
    fired, note = [], cfg.get("note", "")
    for key, hit in (("above", cfg.get("above") is not None and p >= cfg.get("above", 1e9)),
                     ("below", cfg.get("below") is not None and p <= cfg.get("below", -1e9))):
        if hit:
            print(f"FX !! INTRA-BAR ALERT — {pair} {p} crossed {key.upper()} "
                  f"{cfg[key]} [{note}] — ACT NOW, do not wait for the close",
                  flush=True)
            fired.append(key)
    if fired:
        for k in fired:
            cfg.pop(k, None)
        try:
            lv.write_text(json.dumps(cfg))
        except OSError:
            pass

def main():
    pair = sys.argv[1] if len(sys.argv) > 1 else "USD_JPY"
    buf = Path(sys.argv[2])
    cfg = dict(INSTRUMENTS[pair]); cfg["_pair"] = pair
    pip = cfg["pip"]
    fmt = "{:.3f}" if pip == 0.01 else "{:.5f}"
    closes, hi, lo = [], None, None
    print(f"FX DESK UP — {pair} | eyes TradingView(OANDA feed), exec OANDA | "
          f"pip={pip}", flush=True)
    tracked = int(time.time()) // 60
    last, reads, blind, seen, stale_streak = None, 0, 0, [], 0
    while True:
        now = int(time.time()) // 60
        p = read_price(buf, cfg)
        if p is not None:
            last, reads = p, reads + 1
            seen.append(p)
            check_levels(p, pair, pip)
            hi = p if hi is None else max(hi, p)
            lo = p if lo is None else min(lo, p)
        else:
            blind += 1
        if now > tracked:
            t = tracked * 60
            hhmm = time.strftime("%H:%M", time.localtime(t))
            if last is not None and reads > 0:
                distinct = len(set(seen))
                frozen = distinct == 1 and reads >= 5
                stale_streak = stale_streak + 1 if frozen else 0
                closes.append((t, last))
                rec = [fmt.format(c) for _, c in closes[-5:]]
                win = [c for _, c in closes[-5:]]
                rng = f"{(max(win)-min(win))/pip:.1f}p" if len(win) >= 2 else "n/a"
                flag = ""
                if stale_streak >= 2:
                    # A frozen price has TWO very different causes and they need
                    # opposite responses (2026-08-31 17:00 ET): a DEAD FEED means
                    # restart capture; a CLOSED MARKET means do nothing and wait.
                    # The desk cried "STALE FEED — RESTART CAPTURE" during OANDA's
                    # daily 17:00 ET rollover break, when capture was 1s fresh and
                    # the market was simply shut (tradeable=false, 1 tick/bar).
                    # Restarting a healthy capture mid-break would have been the
                    # wrong action taken confidently. Ask the venue which it is.
                    if not _tradeable(pair):
                        flag = (f" || MARKET CLOSED (venue says not tradeable) — "
                                f"frozen {stale_streak} bars is EXPECTED. Feed is fine, "
                                f"do NOT restart. Positions hold on server-side stops.")
                    else:
                        flag = (f" || *** STALE FEED — frozen {stale_streak} bars, "
                                f"venue IS tradeable. DO NOT TRADE. RESTART CAPTURE. ***")
                elif frozen:
                    flag = " || WARN: no movement this bar"
                tk, tr = ticks_now(pair)
                if tr is None:
                    ttxt = ""
                else:
                    tag = "ACTIVE" if tr >= 1.5 else ("quiet" if tr < 0.6 else "")
                    ttxt = f" | ticks {tk} ({tr:.2f}x{' ' + tag if tag else ''})"
                cand = describe_candle(_last_candle, pip)
                ctxt = f" | {cand}" if cand else ""
                # OVERNIGHT MODE (2026-08-31): unattended for ~10h means ~600
                # wake-ups, which exhausts context and forces compaction. Print
                # every bar to the log (the record stays complete), but only
                # emit the MONITOR-visible "FX " prefix when the bar carries
                # signal: heavy/thin volume, a wide range, or a named shape.
                import os as _os
                quiet = (_os.environ.get("FX_OVERNIGHT") == "1"
                         and (vratio is None or 0.6 <= vratio < 1.5)
                         and (rngpips := (max(win)-min(win))/pip if len(win)>=2 else 0) < 12
                         and not cand)
                prefix = "fx " if quiet else "FX "
                print(f"{prefix}{pair} {hhmm} C={fmt.format(last)} "
                      f"({reads}r,{blind}b,{distinct}d){ttxt}{ctxt} | last5: {','.join(rec)} | "
                      f"5bar-range {rng} | sess hi {fmt.format(hi)} lo {fmt.format(lo)} | "
                      f"from-hi {(last-hi)/pip:+.1f}p from-lo {(last-lo)/pip:+.1f}p"
                      f"{flag}", flush=True)
                with open(OUT / f"fx_bars_{pair}.jsonl", "a") as fh:
                    fh.write(json.dumps({"t": t, "pair": pair, "c": last,
                                         "reads": reads, "blind": blind,
                                         "distinct": distinct}) + "\n")
            else:
                print(f"FX {pair} {hhmm} BLIND — no usable reads ({blind} failed). "
                      f"CHECK THE FEED.", flush=True)
            tracked, last, reads, blind, seen = now, None, 0, 0, []
        time.sleep(4)

if __name__ == "__main__":
    main()
