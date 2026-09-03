#!/usr/bin/env python3
"""BTC minute desk — TradingView eyes (Coinbase feed), Coinbase execution.

Reads price by vision every ~4s from the capture ring, closes a bar each
minute, and prints the context needed to judge it. Renders NO verdicts —
judgement is the agent's, not the script's.

Region 937,528,190,42 validated 2026-08-30: 6/6 clean reads, two exact
matches against the Coinbase API. Divergence vs API is a function of TAPE
SPEED (2s capture lag), not a constant: ~$0 quiet, up to ~$16 on a fast
move. TradingView is a REFERENCE for decisions, never a fill price.
"""
import json, re, subprocess, sys, time
from pathlib import Path

sys.path.insert(0, str(Path.home() / ".claude/skills/vision/scripts"))
import ocr_engine as ocre
from PIL import Image

BUF = Path(__file__).resolve().parent.parent / "run" / "cbdesk"
OUT = Path(__file__).resolve().parent
REGION = (937, 528, 190, 42)
STALE_S = 30

def read_price():
    segs = sorted((BUF / "buffer").glob("seg_*.mp4"))
    if not segs:
        return None
    newest = segs[-1]
    if time.time() - newest.stat().st_mtime > STALE_S:
        return None                      # feed died — say blind, never guess
    frame = BUF / "_desk_frame.png"
    r = subprocess.run(["ffmpeg", "-y", "-sseof", "-0.1", "-i", str(newest),
                        "-frames:v", "1", str(frame)],
                       capture_output=True, timeout=25)
    if r.returncode != 0:
        return None
    # OHLC costs a second crop+resize+OCR per cycle. Reading it every 4s
    # doubled the per-read work and pushed blind reads from ~2 to 8 per bar
    # (2026-08-31). A candle does not need 4s resolution — every 3rd cycle
    # (~12s) still gives several reads per minute bar at a third of the cost.
    global _last_candle, _ohlc_tick
    _ohlc_tick += 1
    if _ohlc_tick % 3 == 0:
        k = read_ohlc(frame)
        if k:
            _last_candle = k
    x, y, w, h = REGION
    Image.open(frame).crop((x, y, x + w, y + h)).save(BUF / "_desk_px.png")
    res = ocre.text(str(BUF / "_desk_px.png"))
    if not res.get("ok"):
        return None
    txt = " ".join(l["text"] for l in res.get("lines", []))
    m = re.search(r"(\d{5}\.\d{2})", txt.replace(",", "").replace(" ", ""))
    if not m:
        return None
    v = float(m.group(1))
    if not (10_000 < v < 500_000):
        return None
    # PLAUSIBILITY GATE. OCR confuses digits (measured: 77,712 -> 71,712,
    # a 7->1 flip that passed the wide range check and permanently corrupted
    # the session low by $6,000). BTC does not move >1% between two reads
    # ~4s apart, so anything that far from the previous good read is a
    # MISREAD, not a move. Reject it rather than poison hi/lo.
    global _last_good
    if _last_good is not None and abs(v - _last_good) / _last_good > 0.01:
        print(f"  !! REJECTED implausible read {v:,.2f} "
              f"({(v-_last_good)/_last_good*100:+.1f}% vs {_last_good:,.2f}) "
              f"— OCR misread, not a move", flush=True)
        return None
    _last_good = v
    return v

_last_good = None
_last_candle = None
_ohlc_tick = 0

LEVELS = OUT / "levels.json"

# VOLUME. the operator, 2026-08-30: a reversal without volume may just be a lower
# high forming. Price alone cannot tell those apart — the capitulation low
# tonight printed 2.49x average volume and the desk was blind to it.
# Vision stays the price feed; volume is a CONFIRMATION input, so the API is
# the right source (same split as the pair scanner: API filters, eyes trade).
_vol_client = None

def volume_now():
    """(last closed 1m volume, ratio vs 20-bar average). Never breaks the desk."""
    global _vol_client
    try:
        if _vol_client is None:
            import importlib.util
            spec = importlib.util.spec_from_file_location("ex", OUT / "execute.py")
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            _vol_client = mod.client()
        now = int(time.time())
        cs = _vol_client.get_candles(product_id="BTC-USD", start=str(now - 1500),
                                     end=str(now), granularity="ONE_MINUTE").to_dict()["candles"]
        cs = sorted(cs, key=lambda x: int(x["start"]))
        if len(cs) < 5:
            return None, None
        # BUG FIX 2026-08-31: Coinbase returns the STILL-FORMING candle as the
        # last element. Reading it compared a partial bar against complete
        # ones, so ratios were understated — and inconsistently, depending on
        # when in the minute the call landed. Some "0.02x thin" readings
        # tonight were artifacts, not dead markets. Drop any candle under 60s
        # old and use the last COMPLETE one.
        cutoff = now - 60
        done = [x for x in cs if int(x["start"]) <= cutoff]
        if len(done) < 5:
            return None, None
        vols = [float(x["volume"]) for x in done]
        last = vols[-1]
        avg = sum(vols[:-1]) / len(vols[:-1])
        return last, (last / avg if avg else None)
    except Exception:
        return None, None          # volume is a nice-to-have, never a blocker

OHLC_REGION = (300, 52, 460, 22)   # TradingView chart legend, right of the symbol

def read_ohlc(frame_path):
    """Read the REAL candle from the chart legend — O/H/L/C as TradingView
    renders it, not reconstructed from 4-second price samples.

    the operator, 2026-08-31: 'are you able to identify candles with your vision?'
    The answer was no, and the gap was mine — one region was calibrated on day
    one and nothing else was ever looked for. The legend was showing full OHLC
    the whole time. Without it there is no body, no wick, no direction, so a
    death candle can only be inferred from API volume after the fact.

    OCR renders the leading 'O' as a zero, so parse POSITIONALLY: the first
    four price-shaped numbers in the legend are O, H, L, C.
    """
    try:
        x, y, w, h = OHLC_REGION
        crop = Image.open(frame_path).crop((x, y, x + w, y + h))
        crop = crop.resize((crop.width * 3, crop.height * 3), Image.LANCZOS)
        tmp = Path(frame_path).with_name("_ohlc_px.png")
        crop.save(tmp)
        res = ocre.text(str(tmp))
        if not res.get("ok"):
            return None
        txt = " ".join(l["text"] for l in res.get("lines", []))
        nums = re.findall(r"\d{2},\d{3}\.\d{2}", txt)
        if len(nums) < 4:
            return None
        o, hi_, lo_, c = (float(n.replace(",", "")) for n in nums[:4])
        if not (lo_ <= o <= hi_ and lo_ <= c <= hi_):
            return None                      # incoherent read, refuse it
        return {"o": o, "h": hi_, "l": lo_, "c": c,
                "body": c - o, "rng": hi_ - lo_,
                "upper": hi_ - max(o, c), "lower": min(o, c) - lo_}
    except Exception:
        return None

def describe_candle(k):
    """Name the shape, the way a person reading the chart would."""
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
    return (f"{d} {shape} body {k['body']:+.0f} rng {rng:.0f} "
            f"wick^{k['upper']:.0f} v{k['lower']:.0f}")

def check_levels(p):
    """INTRA-BAR alerting. the operator, 2026-08-30: managing on bar closes means
    acting ~60s late, at the exact moment the market moves — the close is a
    scheduled decision point the whole crowd acts on. The eye reads every ~4s;
    use it. Levels are armed per-trade via levels.json and DISARM on fire so
    they cannot spam. Alert lines start with 'BTC ' so the existing monitor
    filter picks them up without a restart."""
    try:
        cfg = json.loads(LEVELS.read_text())
    except (OSError, ValueError):
        return
    fired, note = [], cfg.get("note", "")
    above, below = cfg.get("above"), cfg.get("below")
    if above is not None and p >= above:
        print(f"BTC !! INTRA-BAR ALERT — price {p:,.2f} crossed ABOVE "
              f"{above:,.2f} [{note}] — ACT NOW, do not wait for the close",
              flush=True)
        fired.append("above")
    if below is not None and p <= below:
        print(f"BTC !! INTRA-BAR ALERT — price {p:,.2f} crossed BELOW "
              f"{below:,.2f} [{note}] — ACT NOW, do not wait for the close",
              flush=True)
        fired.append("below")
    if fired:
        for k in fired:
            cfg.pop(k, None)
        try:
            LEVELS.write_text(json.dumps(cfg))
        except OSError:
            pass

def main():
    closes, hi, lo = [], None, None
    print("BTC DESK UP — eyes TradingView(COINBASE:BTCUSD), exec Coinbase spot",
          flush=True)
    tracked = int(time.time()) // 60
    last, reads, blind = None, 0, 0
    bar_candle = None
    seen = []          # every value read inside the current bar
    stale_streak = 0   # consecutive bars whose price never moved at all
    while True:
        now = int(time.time()) // 60
        p = read_price()
        if p is not None:
            last, reads = p, reads + 1
            seen.append(p)
            # BUG FIX 2026-08-31: printing at the top of a new minute showed the
            # NEWLY-OPENED bar (O=H=L=C, zero range) instead of the one that just
            # closed. Keep the last candle that actually had a range.
            if _last_candle and _last_candle["rng"] > 0:
                bar_candle = _last_candle
            check_levels(p)          # INTRA-BAR: act now, not at the close
            hi = p if hi is None else max(hi, p)
            lo = p if lo is None else min(lo, p)
        else:
            blind += 1
        if now > tracked:
            t = tracked * 60
            hhmm = time.strftime("%H:%M", time.localtime(t))
            if last is not None and reads > 0:
                # STALENESS GUARD. A frozen page OCRs perfectly — 100% read
                # rate on a dead number. BTC does not print the same cent for
                # a whole minute, so zero movement across >=5 reads means the
                # feed died, not that the market went quiet. (Cost of not
                # having this: 3 bars traded-ready on a 6-min-old price.)
                distinct = len(set(seen))
                frozen = distinct == 1 and reads >= 5
                stale_streak = stale_streak + 1 if frozen else 0
                closes.append((t, last))
                rec = [f"{c:,.0f}" for _, c in closes[-6:]]
                win = [c for _, c in closes[-5:]]
                rng = f"${max(win)-min(win):,.0f}" if len(win) >= 2 else "n/a"
                flag = ""
                if stale_streak >= 2:
                    flag = (f" || *** STALE FEED — price frozen {stale_streak} "
                            f"bars. DO NOT TRADE. RESTART CAPTURE. ***")
                elif frozen:
                    flag = " || WARN: no movement this bar — watching for stale"
                vol, vratio = volume_now()
                if vratio is None:
                    vtxt = "vol n/a"
                else:
                    # >1.5x on a move = participation; <0.6x = drifting on nothing
                    tag = "HEAVY" if vratio >= 1.5 else ("thin" if vratio < 0.6 else "")
                    vtxt = f"vol {vol:.1f} ({vratio:.2f}x{' ' + tag if tag else ''})"
                cand = describe_candle(bar_candle)
                ctxt = f" | {cand}" if cand else ""
                print(f"BTC {hhmm} C={last:,.2f} ({reads}r,{blind}b,{distinct}d) | "
                      f"{vtxt}{ctxt} | last6: {','.join(rec)} | 5bar-range {rng} | "
                      f"sess hi {hi:,.0f} lo {lo:,.0f} | "
                      f"from-hi {last-hi:+,.0f} from-lo {last-lo:+,.0f} "
                      f"|| AGENT: read it, act or stand down{flag}", flush=True)
                with open(OUT / "btc_bars.jsonl", "a") as fh:
                    fh.write(json.dumps({"t": t, "c": last, "reads": reads,
                                         "blind": blind, "distinct": distinct,
                                         "stale_streak": stale_streak,
                                         "vol": vol, "vol_ratio": vratio}) + "\n")
            else:
                print(f"BTC {hhmm} BLIND — no usable reads ({blind} failed). "
                      f"CHECK THE FEED.", flush=True)
            tracked, last, reads, blind, seen = now, None, 0, 0, []
            bar_candle = None
        time.sleep(4)

if __name__ == "__main__":
    main()
