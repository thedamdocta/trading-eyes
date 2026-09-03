#!/bin/bash
# SessionStart hook: inject the living lessons document into every session.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
L="$DIR/knowledge/LESSONS.md"
[ -f "$L" ] || exit 0
echo "=== TRADING LESSONS (living doc: knowledge/LESSONS.md) ==="
echo "Tiers = confidence: T1 user-taught | T2 measured | T3 provisional, NOT law."
cat "$L"
[ -f "$DIR/MANDATE.md" ] && { echo; echo "=== YOUR USER'S MANDATE (MANDATE.md) ==="; cat "$DIR/MANDATE.md"; } \
  || echo ">>> No MANDATE.md — run the onboarding interview in CLAUDE.md before trading."
