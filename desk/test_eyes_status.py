"""Behavior checks for dependency routing and observation health failures."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from eyes_status import capture_status
from vision_runtime import find_vision


class EyesStatusTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def vision(self, path):
        (path / "scripts").mkdir(parents=True)
        for name in ("ocr_engine.py", "see.py", "browser_watch.py"):
            (path / "scripts" / name).touch()
        return path.resolve()

    def segment(self, name="seg_1.mp4", mtime=100):
        ring = self.root / "buffer"
        ring.mkdir(exist_ok=True)
        p = ring / name
        p.write_bytes(b"invalid video")
        os.utime(p, (mtime, mtime))
        return p

    def test_bundled_vision_precedes_harness_install(self):
        self.vision(self.root / ".claude/skills/vision")
        expected = self.vision(self.root / "skills/vision")
        self.assertEqual(find_vision(self.root, self.root, {}), expected)

    def test_codex_home_and_explicit_override(self):
        expected = self.vision(self.root / "custom/skills/vision")
        self.assertEqual(find_vision(self.root, self.root,
                         {"CODEX_HOME": str(self.root / "custom")}), expected)
        override = self.vision(self.root / "other")
        self.assertEqual(find_vision(self.root, self.root,
                         {"VISION_SKILL_DIR": str(override)}), override)

    def test_invalid_override_does_not_silently_fallback(self):
        self.vision(self.root / "skills/vision")
        with self.assertRaises(FileNotFoundError):
            find_vision(self.root, self.root,
                        {"VISION_SKILL_DIR": str(self.root / "missing")})

    def test_missing_capture_is_not_ready(self):
        self.assertFalse(capture_status(self.root)["ready"])

    def test_stale_and_future_capture_are_not_ready(self):
        self.segment()
        self.assertEqual(capture_status(self.root, now=130)["state"], "STALE")
        self.assertEqual(capture_status(self.root, now=99)["state"], "CLOCK_SKEW")

    @patch("eyes_status.shutil.which", return_value="ffmpeg")
    @patch("eyes_status.subprocess.run")
    def test_decode_failure_and_timeout_are_not_ready(self, run, which):
        self.segment()
        run.return_value = subprocess.CompletedProcess([], 1, b"", b"bad video")
        self.assertEqual(capture_status(self.root, now=101)["state"], "UNDECODABLE")
        run.side_effect = subprocess.TimeoutExpired("ffmpeg", 10)
        self.assertFalse(capture_status(self.root, now=101)["ready"])

    @patch("eyes_status.shutil.which", return_value="ffmpeg")
    @patch("eyes_status.subprocess.run")
    def test_fresh_capture_does_not_claim_market_liveness(self, run, which):
        self.segment("seg_9.mp4", 80)
        expected = self.segment("seg_1.mp4", 100)
        run.return_value = subprocess.CompletedProcess([], 0, b"\x89PNG\r\n\x1a\n", b"")
        result = capture_status(self.root, now=101)
        self.assertTrue(result["ready"])
        self.assertEqual(result["newest"], str(expected))
        self.assertEqual(result["market_liveness"], "UNVERIFIED")


if __name__ == "__main__":
    unittest.main()
