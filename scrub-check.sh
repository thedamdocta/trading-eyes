#!/bin/bash
# Pre-publish check: refuse to bless the tree if private identifiers remain.
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATTERNS='devon|Devon|Quell|QUELL|thedamdocta@|101-001-[0-9]|/Users/'
hits=$(grep -rInE "$PATTERNS" "$DIR" \
  --exclude-dir=.git --exclude-dir=run --exclude-dir=__pycache__ --exclude-dir=.venv-clip \
  --exclude=scrub-check.sh --exclude=.env 2>/dev/null)
if [ -n "$hits" ]; then echo "SCRUB FAIL:"; echo "$hits" | head -40; exit 1; fi
echo "SCRUB CLEAN — no private identifiers in the tree."
