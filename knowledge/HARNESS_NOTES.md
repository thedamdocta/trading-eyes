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
