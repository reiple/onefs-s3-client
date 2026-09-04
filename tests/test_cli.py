import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def test_main_help_runs_when_invoked_as_script_path(self) -> None:
        result = subprocess.run(
            [sys.executable, str(ROOT / "src" / "main.py"), "--help"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Dell PowerScale OneFS S3 client", result.stdout)


if __name__ == "__main__":
    unittest.main()
