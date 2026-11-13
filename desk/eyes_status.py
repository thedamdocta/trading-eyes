#!/usr/bin/env python3
"""Offline observation preflight. Never loads credentials or execution modules."""
import argparse
import importlib.util
import json
import math
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

from vision_runtime import find_vision


def capture_status(directory, max_age=30, now=None):
    now = time.time() if now is None else now
    ring = Path(directory) / "buffer"
    try:
        segments = sorted(((p.stat().st_mtime, p) for p in ring.glob("seg_*.mp4")),
                          key=lambda pair: pair[0])
    except OSError:
        return {"state": "UNREADABLE", "ready": False}
    if not segments:
        return {"state": "MISSING", "ready": False, "segments": 0}
    mtime, newest = segments[-1]
    age = now - mtime
    result = {"state": "STALE", "ready": False, "segments": len(segments),
              "newest": str(newest), "age_seconds": round(age, 2)}
    if age < 0:
        result["state"] = "CLOCK_SKEW"
        return result
    if age >= max_age:
        return result
    if not shutil.which("ffmpeg"):
        result["state"] = "DECODER_MISSING"
        return result
    try:
        # A filename and mtime cannot establish that a segment is usable.
        decoded = subprocess.run(
            ["ffmpeg", "-v", "error", "-sseof", "-0.1", "-i", str(newest),
             "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "pipe:1"],
            capture_output=True, timeout=10,
        )
        valid = decoded.returncode == 0 and decoded.stdout.startswith(b"\x89PNG\r\n\x1a\n")
    except (OSError, subprocess.TimeoutExpired):
        valid = False
    result.update(state="FRESH_DECODABLE" if valid else "UNDECODABLE", ready=valid)
    # This is capture transport health, not evidence that the page/price is live.
    result["market_liveness"] = "UNVERIFIED"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture-dir", type=Path,
                        help="Vision session folder containing buffer/seg_*.mp4")
    parser.add_argument("--max-age", type=float, default=30)
    args = parser.parse_args()
    if not math.isfinite(args.max_age) or args.max_age <= 0:
        parser.error("--max-age must be finite and positive")
    result = {"checked_at": datetime.now(timezone.utc).isoformat(),
              "scope": "observation only; no account or order requests",
              "dependencies": {name: bool(shutil.which(name)) for name in
                               ("ffmpeg", "ffprobe", "agent-browser")}}
    result["dependencies"].update({name: importlib.util.find_spec(module) is not None
                                   for name, module in (("numpy", "numpy"), ("Pillow", "PIL"))})
    try:
        result["vision_root"] = str(find_vision())
    except FileNotFoundError as exc:
        result["vision_error"] = str(exc)
    result["tools_ready"] = "vision_root" in result and all(result["dependencies"].values())
    result["capture"] = capture_status(args.capture_dir, args.max_age) if args.capture_dir else {
        "state": "NOT_CHECKED", "ready": False}
    result["observation_ready"] = result["tools_ready"] and result["capture"]["ready"]
    result["trading_readiness"] = "NOT_ASSESSED"
    print(json.dumps(result, indent=2))
    return 0 if (result["observation_ready"] if args.capture_dir else result["tools_ready"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
