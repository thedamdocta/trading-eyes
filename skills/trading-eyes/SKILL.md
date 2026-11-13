---
name: trading-eyes
description: Operate or improve the Trading Eyes market-observation desk and its Vision chart captures. Use for live chart observation, capture health, OCR calibration, and desk diagnostics. Observation does not authorize trading.
---

# Trading Eyes

This skill lives inside the Trading Eyes repository at `skills/trading-eyes/`.
Resolve this file's symlink before locating the repository two directories above
the skill folder. Set `TRADING_EYES_ROOT` to that repository's absolute path and
run commands from there. Do not assume the user's current directory is the desk.

## Choose the requested lane

- **Observation or engineering:** no mandate interview, account credentials,
  position request, execution module, or trading watcher is needed. Read the
  repository's `AGENTS.md`, `CLAUDE.md`, and `knowledge/CHART_EYES.md` as operating
  context. Their trading-session startup is for trading, not a read-only demo.
- **Trading:** first establish the user's current mandate using `CLAUDE.md`.
  Historical notes and sample permissions do not authorize orders. The shipped
  execution modules target OANDA practice and opt-in Coinbase only.

## Find and check the eyes

```bash
python3 "$TRADING_EYES_ROOT/desk/eyes_status.py"
VISION_ROOT=$(python3 "$TRADING_EYES_ROOT/desk/vision_runtime.py")
python3 "$VISION_ROOT/scripts/browser_watch.py" doctor
```

The resolver checks `VISION_SKILL_DIR` (explicit override), then the bundled
`skills/vision`, Codex, shared `.agents`, and Claude skill folders. An invalid
explicit override fails instead of silently selecting another installation.
Read the resolved Vision `SKILL.md` and `reference/BROWSER-WATCH.md` before capture.
Its dependencies and Python environment must match those used by the desk.

## Bounded live observation

Choose the requested public chart URL and a new, task-owned capture directory.
For an initial check, use a bounded run:

```bash
python3 "$VISION_ROOT/scripts/browser_watch.py" start \
  --dir "$CAPTURE_DIR" --url "$CHART_URL" \
  --interval 3 --max-frames 5 --max-runtime 35 --command-timeout 20
```

While capture runs, check transport health:

```bash
python3 "$TRADING_EYES_ROOT/desk/eyes_status.py" --capture-dir "$CAPTURE_DIR"
```

`tools_ready` only means dependencies were found. `FRESH_DECODABLE` means a recent
segment decoded; it does **not** prove that the page, symbol, price or timeframe is
correct or live. Inspect multiple timestamped frames with the harness's image
viewer (Codex: `view_image`) and confirm symbol, venue, timeframe, unobscured chart
and coherent changes. Report the sampled interval and gaps. A static price alone
is not proof of a frozen feed. A fresh screenshot of an error page is not market data.

For numeric extraction, use Vision's `region_calibrate.py` and `read_text.py`.
Read their references first. Existing desk crop coordinates were measured for a
particular TradingView layout; they are not a calibration for any other venue
or layout. Verify numeric
reads against visible digits and, when available, the same venue's public data.
Separate chart prices from fill prices. Surface access restrictions; do not
equate successful API authentication with venue eligibility.

## Lifecycle and continuity

Capture polling only observes at its actual cadence. It does not keep the agent
thinking after the turn ends. Long-running observation needs an explicitly
arranged runtime and event delivery; do not promise constant supervision merely
because a process exists. Use task-owned directories and stop only your own run:

```bash
python3 "$VISION_ROOT/scripts/browser_watch.py" stop --dir "$CAPTURE_DIR"
```

Bounded runs stop themselves. A later stale check is expected after stopping.
Record the run path, actual capture counts/times, inspected evidence, limitations
and edits in `memory/_SESSION_LOG.md`. Preserve existing local edits. For code
changes, run the focused tests and validate behavior, not just process liveness.
