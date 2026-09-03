#!/bin/bash
# Trading Eyes installer: wires hooks + permissions into the agent's settings.
set -e
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Trading Eyes — install"
[ -f "$DIR/.env" ] || { cp "$DIR/.env.example" "$DIR/.env"; echo "created .env — FILL IN your OANDA practice keys before trading"; }
mkdir -p "$DIR/run" "$DIR/memory/compactions"
[ -f "$DIR/memory/_SESSION_LOG.md" ] || printf "# Session Log\n\n" > "$DIR/memory/_SESSION_LOG.md"
# Wire hooks into project-local agent settings (Claude Code convention).
mkdir -p "$DIR/.claude"
sed "s|__REPO__|$DIR|g" "$DIR/hooks/settings.template.json" > "$DIR/.claude/settings.local.json"
echo "wrote .claude/settings.local.json (hooks + safe permission rules, paths filled)"
# Vision skill (optional, recommended): the agent's eyes for charts/screens over time.
if [ ! -d "$DIR/skills/vision" ]; then
  git clone --depth 1 https://github.com/thedamdocta/vision-skill "$DIR/skills/vision" 2>/dev/null \
    && echo "cloned vision skill" || echo "vision skill clone skipped (offline? clone it later)"
fi
echo
echo "Next steps:"
echo "  1. Fill $DIR/.env with your OANDA PRACTICE credentials"
echo "  2. ./doctor.sh          — verify everything"
echo "  3. Open your agent in this directory; it will run the CLAUDE.md onboarding"
echo "  4. ./desk-up.sh         — start the feeds; the agent arms the watchers"
