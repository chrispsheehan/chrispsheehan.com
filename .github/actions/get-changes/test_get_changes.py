#!/usr/bin/env python3

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from get_changes import classify_paths, diff_range, resolve_compare_ref, resolve_workspace


ACTION_DIR = Path(__file__).resolve().parent


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Test User",
            "GIT_AUTHOR_EMAIL": "test@example.com",
            "GIT_COMMITTER_NAME": "Test User",
            "GIT_COMMITTER_EMAIL": "test@example.com",
        }
    )
    command = ["git", *args]
    if args and args[0] == "commit":
        command = ["git", "-c", "commit.gpgsign=false", *args]
    return subprocess.run(command, cwd=repo, check=True, text=True, capture_output=True, env=env)


class GetChangesTests(unittest.TestCase):
    def test_classify_paths(self) -> None:
        outputs = classify_paths(
            [
                "infra/modules/aws/example/main.tf",
                "infra/live/dev/aws/example/terragrunt.hcl",
                ".github/workflows/pull_request.yml",
                "lambdas/lambda_api/lambda_handler.py",
                "frontend/src/index.html",
                ".github/actions/get-changes/action.yml",
            ]
        )
        self.assertEqual(
            outputs,
            {
                "actions": "true",
                "terraform": "true",
                "terragrunt": "true",
                "github": "true",
                "lambdas": "true",
                "frontend": "true",
            },
        )

    def test_resolve_compare_ref_prefers_base_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            git(repo, "init", "-b", "main")
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "chore: init")
            old_cwd = Path.cwd()
            try:
                os.chdir(repo)
                with patch.dict(os.environ, {"GITHUB_WORKSPACE": str(repo)}):
                    compare_ref, warning = resolve_compare_ref("", "main")
            finally:
                os.chdir(old_cwd)
            self.assertEqual(compare_ref, "main")
            self.assertIsNone(warning)

    def test_workspace_resolution_prefers_github_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            old = os.environ.get("GITHUB_WORKSPACE")
            try:
                os.environ["GITHUB_WORKSPACE"] = str(repo)
                self.assertEqual(resolve_workspace().resolve(), repo.resolve())
            finally:
                if old is None:
                    os.environ.pop("GITHUB_WORKSPACE", None)
                else:
                    os.environ["GITHUB_WORKSPACE"] = old

    def test_cli_uses_pr_style_base_ref(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            repo.mkdir()
            git(repo, "init", "-b", "main")
            (repo / "README.md").write_text("hello\n", encoding="utf-8")
            git(repo, "add", "README.md")
            git(repo, "commit", "-m", "chore: init")
            base_sha = git(repo, "rev-parse", "HEAD").stdout.strip()
            git(repo, "checkout", "-b", "feature")
            target = repo / ".github" / "workflows"
            target.mkdir(parents=True)
            (target / "example.yml").write_text("name: Example\n", encoding="utf-8")
            git(repo, "add", ".")

            env = os.environ.copy()
            env["GITHUB_WORKSPACE"] = str(repo)
            result = subprocess.run(
                [
                    "python3",
                    str(ACTION_DIR / "get_changes.py"),
                    "--ref",
                    "main",
                    "--base-ref",
                    base_sha,
                ],
                cwd=repo,
                check=True,
                text=True,
                capture_output=True,
                env=env,
            )
            payload = json.loads(result.stdout)
            self.assertEqual(payload["baseRef"], base_sha)
            self.assertEqual(payload["compareRef"], base_sha)
            self.assertEqual(payload["diffRange"], diff_range(base_sha))
            self.assertEqual(payload["outputs"]["github"], "false")
            self.assertEqual(payload["outputs"]["actions"], "false")


if __name__ == "__main__":
    unittest.main()
