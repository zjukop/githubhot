import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from datetime import date
from pathlib import Path

from githubhot.pipeline import missing_publish_dates
from githubhot.storage import write_candidates
from test_reporting import repo


class PipelineTests(unittest.TestCase):
    def test_daily_script_handles_empty_pending_date_list_with_nounset(self) -> None:
        script = (Path(__file__).parents[1] / "scripts" / "run_daily_local.sh").read_text(encoding="utf-8")
        self.assertIn('"${PENDING_DATES[@]-}"', script)
        self.assertIn('[[ -n "${PUBLISH_DATE}" ]] || continue', script)

    def test_empty_history_schedules_target_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(
                missing_publish_dates(Path(directory), date(2026, 8, 16)),
                [date(2026, 8, 16)],
            )

    def test_finds_gaps_from_first_publication_through_target(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            month = root / "2026" / "08"
            month.mkdir(parents=True)
            for day in (13, 14):
                (month / f"2026-08-{day:02d}.md").write_text("daily", encoding="utf-8")
            self.assertEqual(
                missing_publish_dates(root, date(2026, 8, 16)),
                [date(2026, 8, 15), date(2026, 8, 16)],
            )

    def test_backfill_limit_is_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "2026" / "08" / "2026-08-01.md"
            first.parent.mkdir(parents=True)
            first.write_text("daily", encoding="utf-8")
            self.assertEqual(
                missing_publish_dates(root, date(2026, 8, 10), limit=2),
                [date(2026, 8, 2), date(2026, 8, 3)],
            )

    def test_candidate_metadata_uses_explicit_publication_date(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "candidates.json"
            write_candidates(path, [repo()], "query", date(2026, 8, 15))
            payload = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(payload["generated_at"], "2026-08-15")

    def test_timeout_runner_returns_124(self) -> None:
        script = Path(__file__).parents[1] / "scripts" / "run_with_timeout.py"
        result = subprocess.run(
            [sys.executable, str(script), "0.05", sys.executable, "-c", "import time; time.sleep(1)"],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(result.returncode, 124)
        self.assertIn("timed out", result.stderr)

    def test_pull_failure_does_not_block_generation_or_social_drafts(self) -> None:
        source_root = Path(__file__).parents[1]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scripts = root / "scripts"
            fake_bin = root / "fake-bin"
            scripts.mkdir()
            fake_bin.mkdir()
            shutil.copy2(source_root / "scripts" / "run_daily_local.sh", scripts / "run_daily_local.sh")
            (scripts / "run_social_browser_drafts.sh").write_text(
                "#!/bin/bash\ntouch \"$GITHUBHOT_TEST_ROOT/browser-ran\"\n",
                encoding="utf-8",
            )
            fake_git = fake_bin / "git"
            fake_git.write_text(
                textwrap.dedent(
                    """\
                    #!/bin/bash
                    echo "$*" >> "$GITHUBHOT_TEST_ROOT/git-calls"
                    if [[ "$1 $2" == "diff --quiet" ]]; then exit 0; fi
                    if [[ "$1 $2 $3" == "diff --cached --quiet" ]]; then
                      [[ -f "$GITHUBHOT_TEST_ROOT/staged" ]] && exit 1
                      exit 0
                    fi
                    if [[ "$1" == "pull" ]]; then exit 1; fi
                    if [[ "$1" == "add" ]]; then touch "$GITHUBHOT_TEST_ROOT/staged"; exit 0; fi
                    if [[ "$1" == "commit" ]]; then rm -f "$GITHUBHOT_TEST_ROOT/staged"; exit 0; fi
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            (fake_bin / "gh").write_text("#!/bin/bash\necho token\n", encoding="utf-8")
            (fake_bin / "security").write_text("#!/bin/bash\necho secret\n", encoding="utf-8")
            (fake_bin / "rg").write_text("#!/bin/bash\nexit 1\n", encoding="utf-8")
            (fake_bin / "python3").write_text(
                textwrap.dedent(
                    """\
                    #!/bin/bash
                    if [[ "$1" == */run_with_timeout.py ]]; then
                      shift 2
                      exec "$@"
                    fi
                    if [[ "$1 $2 $3" == "-m githubhot pending" ]]; then
                      echo 2026-08-16
                      exit 0
                    fi
                    if [[ "$1 $2 $3" == "-m githubhot digest" ]]; then
                      mkdir -p daily/2026/08
                      echo digest > daily/2026/08/2026-08-16.md
                      exit 0
                    fi
                    if [[ "$1 $2 $3" == "-m githubhot syndicate" ]]; then
                      touch "$GITHUBHOT_TEST_ROOT/social-ran"
                      exit 1
                    fi
                    exit 0
                    """
                ),
                encoding="utf-8",
            )
            for path in [scripts / "run_daily_local.sh", scripts / "run_social_browser_drafts.sh", *fake_bin.iterdir()]:
                path.chmod(0o755)
            env = os.environ.copy()
            env.update(
                {
                    "GITHUBHOT_BIN_DIR": str(fake_bin),
                    "GITHUBHOT_TEST_ROOT": str(root),
                    "GITHUBHOT_RETRY_ATTEMPTS": "3",
                    "GITHUBHOT_RETRY_DELAY_SECONDS": "0",
                    "GITHUBHOT_GITHUB_FALLBACK_IP": "",
                }
            )
            result = subprocess.run(
                ["bash", str(scripts / "run_daily_local.sh")],
                cwd=root,
                env=env,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((root / "git-calls").read_text(encoding="utf-8").count("pull --ff-only"), 3)
            self.assertTrue((root / "social-ran").exists())
            self.assertTrue((root / "browser-ran").exists())
            self.assertIn("social draft generation failed", result.stdout)
            self.assertIn("git pull unavailable; continuing", result.stdout)
            self.assertIn("run completed successfully", result.stdout)


if __name__ == "__main__":
    unittest.main()
