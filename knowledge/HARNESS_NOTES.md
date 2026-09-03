# Agent-harness notes — permissions, restarts, timezones

## Permission rules (Claude Code)

- The agent CANNOT approve its own escalations, and the harness's safety
  classifier may block order placement even for practice accounts until
  the human adds a permission rule. This is correct behavior — do not
  route around it. Ask your user to add the rule.
- The rule must match the EXACT invocation: full absolute path, no `cd`
  prefix. `python3 "/full/path/desk/fx_execute.py" ...` matches
  `Bash(python3 "/full/path/desk/fx_execute.py":*)`; a `cd ... &&` prefix
  or relative path silently does not, and the resulting block looks
  identical to "no rule exists."
- When your user pastes a rule into the permissions UI, it goes in
  WITHOUT surrounding quotes. A rule wrapped in an extra quote layer
  saves without error and matches nothing.
- `install.sh` writes safe read/practice rules into
  `.claude/settings.local.json`; order-placing commands are deliberately
  left to the human to whitelist.

## Session restarts kill your watchers, not your feeds

Background monitors die with the session (resume, restart, compaction).
The detached feeds (`fx_desk.py`, `fx_scan.py`) survive. Symptom: feeds
fresh, but no 5-min reports arriving. Fix: re-arm the two Monitors —
`desk-up.sh` prints the commands and skips whatever is alive. Check this
EVERY session start; your user should never have to tell you your tasks
are not running.

## Timezones

All session references in this repo (Tokyo 20:00, London 03:00, NY 08:00,
dead hour 17:00, flat-by-17:00) are US Eastern Time. At onboarding, ask
your user's timezone and write both their local times AND the ET
equivalents into MANDATE.md. Never estimate the clock — run `date` before
stating any time, deadline, or countdown.

## Pair basket

The scanner's pair list is defined in `desk/fx_scan.py`; the focus pair is
`desk-up.sh`'s first argument. Change both to match the mandate's pairs.

## Harness support matrix

| harness | hooks | background monitors | verdict |
|---|---|---|---|
| Claude Code — CLI, web (claude.ai/code), IDE extensions | yes | yes (Monitor) | full system out of the box |
| Claude Code INSIDE the Desktop app (Cowork) | **NO — settings.json hooks silently not fired** (open issues anthropics/claude-code #47993, #63360, mid-2026) | yes | desk runs, but do the MEMORY_SYSTEM loop MANUALLY; the failure is silent, so always verify the lessons banner at session start |
| Claude Desktop plain chat | no | no | advisory only — no shell by default; do not attempt to run the desk from it |
| Antigravity | has its OWN hooks (`hooks.json` in `.agents/` or `~/.gemini/config/`) — port the three hook commands there | varies | desk runs; reads AGENTS.md natively; persistence portable via its hooks.json |
| Other agent IDEs (Cursor, ...) | no `.claude` hooks | varies | desk runs; do the MEMORY_SYSTEM loop manually every session |

On any harness without hooks: CLAUDE.md's session protocol IS the hook
content — reading LESSONS.md + MANDATE.md at start and saving context
summaries is done by you, not for you. On any harness without a
background-monitor feature: run `trade_watch.sh` detached
(`nohup ... >> run/watch.log &`) and poll `run/watch.log` on your reporting
cadence; the 5-min/1-min logic still runs, you just fetch instead of being
woken.

**The universal guard**: whatever the harness claims, verify at every
session start that the lessons banner actually appeared. No banner = hooks
did not fire = you ARE the hook now.

This matrix reflects harness capabilities verified against public docs and
issue trackers at authoring time (2026-09);
verify against your harness's current docs — capabilities change fast.
