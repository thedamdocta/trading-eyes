"""Find the shared Vision installation without depending on an agent harness."""
import os
import sys
from pathlib import Path


def find_vision(repo=None, home=None, environ=None):
    repo = Path(repo) if repo is not None else Path(__file__).resolve().parents[1]
    home = Path(home) if home is not None else Path.home()
    env = os.environ if environ is None else environ
    override = env.get("VISION_SKILL_DIR")
    candidates = [Path(override).expanduser()] if override else [
        repo / "skills/vision",
        Path(env.get("CODEX_HOME", str(home / ".codex"))) / "skills/vision",
        home / ".agents/skills/vision",
        home / ".claude/skills/vision",
    ]
    for root in candidates:
        if all((root / "scripts" / name).is_file()
               for name in ("ocr_engine.py", "see.py", "browser_watch.py")):
            return root.resolve()
    raise FileNotFoundError(
        "Vision installation missing or incomplete. Set VISION_SKILL_DIR to "
        "the skill folder containing scripts/ocr_engine.py, see.py and browser_watch.py."
    )


def load_ocr():
    sys.path.insert(0, str(find_vision() / "scripts"))
    import ocr_engine
    return ocr_engine


if __name__ == "__main__":
    try:
        print(find_vision())
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)
