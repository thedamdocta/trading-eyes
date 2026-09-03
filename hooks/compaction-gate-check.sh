#!/bin/bash
# SessionStart hook: if a compaction fired, demand the summary be saved first.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
P="$DIR/memory/.compaction-pending"
[ -f "$P" ] || exit 0
echo "=================================================="
echo "!! COMPACTION GATE — a compaction fired at $(cat "$P")."
echo "Save the continuation summary to memory/compactions/session-XX.md"
echo "BEFORE any other work, then delete memory/.compaction-pending."
echo "MACHINE CLOCK NOW: $(date "+%Y-%m-%d %H:%M:%S") — stamp with THIS; never estimate a clock."
echo "=================================================="
