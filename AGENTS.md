# Trading Eyes — agent entry point

This project is agent-operated. **Your operating manual is [CLAUDE.md](CLAUDE.md)**
— read it in full before doing anything, then follow its onboarding and
session-start protocol exactly.

If your harness is not Claude Code, also read
[knowledge/HARNESS_NOTES.md](knowledge/HARNESS_NOTES.md) § "Harness support
matrix" — on harnesses without session hooks, the persistence loop described
in [knowledge/MEMORY_SYSTEM.md](knowledge/MEMORY_SYSTEM.md) is YOUR
responsibility to perform manually, every session: read the lessons and
mandate at start, save context summaries before they evaporate, write the
session log at end. The hooks are automation for a discipline; the
discipline is the requirement.
