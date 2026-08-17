from __future__ import annotations

import plistlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MacScheduleTests(unittest.TestCase):
    def test_schedule_has_primary_run_and_recovery_checks(self) -> None:
        template = (ROOT / "scripts/com.zjukop.githubhot.daily.plist.template").read_text(
            encoding="utf-8"
        )
        rendered = template.replace("__REPO_DIR__", str(ROOT)).replace(
            "__LOG_DIR__", str(ROOT / ".local/logs")
        )
        config = plistlib.loads(rendered.encode("utf-8"))

        self.assertEqual(
            config["StartCalendarInterval"],
            [
                {"Hour": 10, "Minute": 0},
                {"Hour": 12, "Minute": 0},
                {"Hour": 18, "Minute": 0},
            ],
        )


if __name__ == "__main__":
    unittest.main()
