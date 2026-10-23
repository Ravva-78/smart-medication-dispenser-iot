"""Runs tests/js/camera_queue.check.mjs with Node: real behavioural coverage for the browser camera queue
(single-flight, exclusive access for Stage B, error text, cancellation). Skipped if Node is not installed."""
import shutil
import subprocess
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "js" / "camera_queue.check.mjs"


@unittest.skipUnless(shutil.which("node"), "Node.js not installed")
class TestCameraQueueJs(unittest.TestCase):
    def test_queue_behaviour(self):
        r = subprocess.run(["node", str(CHECK)], capture_output=True, text=True, timeout=60)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("camera queue checks passed", r.stdout)


if __name__ == "__main__":
    unittest.main()
