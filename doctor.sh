#!/bin/bash
# Verify the desk is ready. Exit 0 = healthy.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; RUN="$DIR/run"; ok=1
say(){ printf "%-14s %s\n" "$1" "$2"; }
command -v python3 >/dev/null && say "python3" "OK $(python3 -V 2>&1)" || { say "python3" "MISSING"; ok=0; }
if [ -f "$DIR/.env" ]; then
  if grep -q "your-practice" "$DIR/.env"; then say ".env" "PLACEHOLDERS — fill in your real OANDA practice keys"; ok=0
  elif grep -q "^OANDA_API_KEY=..*" "$DIR/.env" && grep -q "^OANDA_ACCOUNT_ID=..*" "$DIR/.env"; then say ".env" "OK (keys present)"
  else say ".env" "INCOMPLETE — fill OANDA_API_KEY / OANDA_ACCOUNT_ID"; ok=0; fi
  grep -q "fxpractice" "$DIR/.env" && say "venue" "PRACTICE (good)" \
    || say "venue" "!! NOT the practice URL — live trading configured. Intentional?"
else say ".env" "MISSING — cp .env.example .env and fill it"; ok=0; fi
[ -f "$DIR/MANDATE.md" ] && say "mandate" "OK" || say "mandate" "MISSING — run the CLAUDE.md onboarding before trading"
if [ "$ok" = 1 ] && [ -f "$DIR/.env" ]; then
  b=$(python3 "$DIR/desk/fx_execute.py" balance 2>&1 | head -1)
  case "$b" in *bal*|*USD*) say "venue API" "OK ($b)";; *) say "venue API" "FAIL: $b"; ok=0;; esac
fi
pgrep -f "$DIR/desk/fx_desk.py" >/dev/null && say "feed fx_desk" "running" || say "feed fx_desk" "down (./desk-up.sh)"
pgrep -f "$DIR/desk/fx_scan.py" >/dev/null && say "feed fx_scan" "running" || say "feed fx_scan" "down (./desk-up.sh)"
if [ -f "$RUN/desk.log" ]; then
  age=$(( $(date +%s) - $(stat -f %m "$RUN/desk.log" 2>/dev/null || stat -c %Y "$RUN/desk.log") ))
  [ "$age" -lt 180 ] && say "desk.log" "fresh (${age}s)" || say "desk.log" "STALE (${age}s) — feeds wedged?"
else say "desk.log" "absent (feeds not started yet)"; fi
[ -d "$DIR/skills/vision" ] && { python3 "$DIR/skills/vision/scripts/see.py" --doctor >/dev/null 2>&1 \
  && say "vision" "OK" || say "vision" "present; run scripts/see.py --doctor for missing deps (optional)"; }
[ "$ok" = 1 ] && echo "— DESK READY —" || { echo "— NOT READY: fix the items above —"; exit 1; }
