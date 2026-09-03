#!/bin/bash
# Bring up the Trading Eyes desk: feeds first, then tell the agent to arm watchers.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; RUN="$DIR/run"; mkdir -p "$RUN"
FOCUS="${1:-USD_JPY}"
if ! pgrep -f "fx_desk.py" >/dev/null; then
  nohup python3 "$DIR/desk/fx_desk.py" "$FOCUS" "$RUN" >>"$RUN/fx_desk.out" 2>&1 &
  echo "started fx_desk.py ($FOCUS)"
else echo "fx_desk.py already running"; fi
if ! pgrep -f "fx_scan.py" >/dev/null; then
  nohup python3 "$DIR/desk/fx_scan.py" "$RUN/desk.log" >>"$RUN/fx_scan.out" 2>&1 &
  echo "started fx_scan.py"
else echo "fx_scan.py already running"; fi
echo ""
echo "FEEDS UP. Now arm the two watchers under your agent harness's Monitor"
echo "(so their events reach the agent) — from the agent, run:"
echo "  Monitor: bash \"$DIR/desk/trade_watch.sh\"            (desk watcher)"
echo "  Monitor: while true; do python3 \"$DIR/desk/coil_log.py\"; sleep 60; done   (coil logger)"
