# Trading Eyes

**A complete agent trading desk: eyes, hands, judgment, and memory — built so
an AI agent can pick it up and trade a human's mandate out of the box.**

Trading Eyes is not a bot that trades for you. It is the full operating
system an agent needs to trade *with* you: live market feeds and a
multi-pair scanner (the eyes), venue execution with mechanical risk
structure (the hands), a three-timeframe wave-structure strategy with its
measured evidence attached (the judgment), and hooks that give the agent
persistence across sessions (the memory). Everything here was built and
tested live on an OANDA practice account by an agent trading under human
direction; the lessons in `knowledge/` carry their sample sizes and their
scars.

## What your agent gets

- **Eyes** — `fx_desk.py` (focus-pair 1-min bars), `fx_scan.py` (11-pair
  basket scanner with tradeability alerts), `coil_log.py` (compression-break
  logger with automatic 15/30/60m outcome scoring), and the bundled
  [vision skill](skills/vision/) for reading charts and screens over time.
- **Hands** — `fx_execute.py`: limits, stops, venue-managed trailing stops,
  partial take-profits via a one-line plan file, order/position truth.
- **Judgment** — `structure.py`: M15 tide / M5 wave / M1 moment phase reads;
  `knowledge/`: the strategy, exits, and every measured finding with n=.
- **Memory** — hooks that inject the living lessons file into every session,
  a compaction gate so context loss never loses the thread, session logs,
  and a call ledger that scores every decision — including the declined ones.

## Quickstart

```bash
git clone https://github.com/YOURNAME/trading-eyes && cd trading-eyes
./install.sh          # wires hooks + safe permissions, creates .env
# fill .env with OANDA PRACTICE credentials (free account at oanda.com)
./doctor.sh           # verifies venue, feeds, config
# open your agent (e.g. Claude Code) in this directory:
#   it reads CLAUDE.md, interviews YOU for your mandate, then runs the desk
./desk-up.sh          # start the feeds; the agent arms its watchers
```

## Your mandate, not ours

At first run the agent interviews you — risk unit, venue, pairs, session
window, approval model — and writes `MANDATE.md` (never committed). The
strategy is the system's; the risk and the rules are **yours**. Defaults are
maximally safe: practice venue, smallest viable size, one position at a
time, everything logged.

## Safety posture

- Practice-only by default; live requires explicit reconfiguration.
- The Coinbase module (real money, no practice mode) ships **disabled** —
  see `knowledge/COINBASE_NOTES.md`.
- The agent cannot approve its own escalations; that is a hard rule in
  `CLAUDE.md`, and the permission template only whitelists read/practice
  commands.
- No secrets in the repo, ever: `.env` is gitignored, `scrub-check.sh`
  guards the tree.

## The knowledge (start here to understand the strategy)

| file | what it holds |
|---|---|
| [knowledge/STRATEGY.md](knowledge/STRATEGY.md) | the tide/wave/moment stack and the stall entry |
| [knowledge/EXITS.md](knowledge/EXITS.md) | partial +1R, venue trail, hard stop — and the replay that proved it |
| [knowledge/LESSONS.md](knowledge/LESSONS.md) | the living lessons doc, tiered by evidence |
| [knowledge/CASE_STUDIES.md](knowledge/CASE_STUDIES.md) | the 11 trades and the declines that taught the system |
| [knowledge/TOPOLOGY.md](knowledge/TOPOLOGY.md) | the four-process runtime and the log contract |
| [knowledge/LEDGER_FORMAT.md](knowledge/LEDGER_FORMAT.md) | every file format the desk reads/writes |

## Requirements

Python 3.10+ (desk is stdlib-only), bash, an OANDA practice account. The
vision skill has optional extras (ffmpeg, numpy, Pillow) — its own
`INSTALL.md` and `--doctor` handle them.

MIT license. Trade safe: this is a practice-account learning system, not
financial advice, and past measurements are not future returns.
