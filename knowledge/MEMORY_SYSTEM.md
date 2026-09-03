# The memory system — how this desk survives context loss

An agent's context window is mortal: sessions end, context compacts, and
an agent that trusts its own memory loses the thread mid-trade. This desk
assumes memory WILL be lost and builds persistence out of files and hooks.
Understand the loop — you are its custodian.

## The loop

1. **`hooks/lessons-inject.sh` (SessionStart)** — every session begins with
   `knowledge/LESSONS.md` and your user's `MANDATE.md` injected into
   context. You wake up already knowing the strategy's scars and your
   user's rules, even with zero conversation history.
2. **`hooks/compaction-gate-set.sh` (PreCompact)** — the moment the harness
   compacts your context, a flag file is armed.
3. **`hooks/compaction-gate-check.sh` (SessionStart)** — if the flag is
   set, your FIRST action is saving the continuation summary to
   `memory/compactions/session-XX.md`, stamped with the machine clock
   (`date` — never an estimated time), then clearing the flag. The
   compaction summary holds detail that exists nowhere else; save it
   before it evaporates. Only then work.
4. **`memory/_SESSION_LOG.md`** — at session end and after significant
   decisions, append: what happened, what was decided and why, what is
   open. The next session (or the next agent) reads the last entries at
   startup.
5. **The ledgers** (`calls.jsonl`, `fx_orders.jsonl`, `coils.jsonl`) — the
   objective record. Calls score themselves; the venue holds position
   truth. When your memory and the ledger disagree, the ledger wins.
6. **`knowledge/LESSONS.md` is LIVING** — after a trade teaches something,
   write it, with its tier and sample size. After evidence kills a lesson,
   delete or demote it. This file is the strategy's accumulated reps; a
   lesson that stops being true and stays written poisons every future
   session that injects it.

## Claude Code specifics

- `install.sh` wires everything into `.claude/settings.local.json` —
  **hooks load at session START. After install, open a NEW session** (or
  run `/hooks` once) or none of this is active. `doctor.sh` cannot see
  hook state from outside; verify by checking a new session opens with
  the lessons banner.
- Do not edit a hook script while a session that loaded it is mid-turn.
- The compaction gate depends on the flag file surviving between sessions;
  never gitignore or delete `memory/` structure.

## The discipline the machinery cannot do for you

Hooks deliver memory; they do not create it. Write the session log. Save
the compaction FIRST. Log every call including declines and cancels.
Stamp times from the clock, not from your sense of elapsed work. The
system's memory is exactly as good as what you write into it.
