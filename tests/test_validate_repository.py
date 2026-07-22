from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_repository.py"


class RepositoryValidationTests(unittest.TestCase):
    def make_copy(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        destination = Path(temporary.name) / "repo"
        shutil.copytree(
            ROOT,
            destination,
            ignore=shutil.ignore_patterns(".git", "__pycache__", ".pytest_cache"),
        )
        return temporary, destination

    def run_validator(self, root: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), str(root)],
            text=True,
            capture_output=True,
            encoding="utf-8",
            check=False,
        )

    def test_repository_is_valid(self) -> None:
        result = self.run_validator(ROOT)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_skill_path_fails(self) -> None:
        temporary, root = self.make_copy()
        self.addCleanup(temporary.cleanup)
        catalog_path = root / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["packages"][0]["skillPaths"][0] += "-missing"
        catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing SKILL.md", result.stdout)

    def test_invalid_platform_fails(self) -> None:
        temporary, root = self.make_copy()
        self.addCleanup(temporary.cleanup)
        catalog_path = root / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["packages"][0]["platforms"] = ["windows", "amiga"]
        catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("invalid platforms", result.stdout)

    def test_incomplete_dependency_fails(self) -> None:
        temporary, root = self.make_copy()
        self.addCleanup(temporary.cleanup)
        catalog_path = root / "catalog.json"
        catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        catalog["packages"][0]["dependencies"] = [
            {
                "name": "Node.js",
                "purpose": "Example runtime",
                "required": True,
                "modifiesSystem": True,
                "detect": {"windows": "node --version"},
                "install": {"windows": "winget install Node.js"},
                "verify": {"windows": "node --version"},
            }
        ]
        catalog_path.write_text(
            json.dumps(catalog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing", result.stdout)

    def test_secret_pattern_fails(self) -> None:
        temporary, root = self.make_copy()
        self.addCleanup(temporary.cleanup)
        (root / "leaked.txt").write_text(
            "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEFGH", encoding="utf-8"
        )
        result = self.run_validator(root)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("possible GitHub token", result.stdout)


if __name__ == "__main__":
    unittest.main()
