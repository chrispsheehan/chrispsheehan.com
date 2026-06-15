#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path


CATEGORY_PREFIXES = {
    "actions": (".github/actions/",),
    "terraform": ("infra/modules/",),
    "terragrunt": ("infra/",),
    "github": (".github/",),
    "lambdas": ("lambdas/",),
    "frontend": ("frontend/",),
}


def resolve_workspace() -> Path:
    workspace = os.environ.get("GITHUB_WORKSPACE")
    if workspace:
        return Path(workspace)
    current = Path.cwd().resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".git").exists():
            return candidate
    return current


def git(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", f"safe.directory={resolve_workspace()}", *args],
        cwd=resolve_workspace(),
        check=check,
        text=True,
        capture_output=True,
    )


def ref_exists(ref: str) -> bool:
    return git("rev-parse", "--verify", ref, check=False).returncode == 0


def resolve_compare_ref(base_ref: str, ref: str) -> tuple[str, str | None]:
    candidates = [candidate for candidate in (base_ref, ref, f"origin/{ref}") if candidate]
    for candidate in candidates:
        if ref_exists(candidate):
            return candidate, None
    return "HEAD^", f"No compare ref found for base_ref='{base_ref}' or ref='{ref}', falling back to HEAD^"


def diff_range(compare_ref: str) -> str:
    return f"{compare_ref}...HEAD"


def changed_files(compare_ref: str) -> list[str]:
    result = git("diff", "--name-only", diff_range(compare_ref), check=False)
    if result.returncode not in (0, 1):
        raise RuntimeError(result.stderr.strip() or f"git diff failed for {diff_range(compare_ref)}")
    return [line for line in result.stdout.splitlines() if line]


def classify_paths(paths: list[str]) -> dict[str, str]:
    outputs: dict[str, str] = {}
    for category, prefixes in CATEGORY_PREFIXES.items():
        outputs[category] = "true" if any(path.startswith(prefixes) for path in paths) else "false"
    return outputs


def write_outputs(outputs: dict[str, str]) -> None:
    github_output = os.environ.get("GITHUB_OUTPUT")
    if not github_output:
        return
    with Path(github_output).open("a", encoding="utf-8") as handle:
        for key, value in outputs.items():
            handle.write(f"{key}={value}\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Detect changed repo areas from git diff")
    parser.add_argument("--ref", default=os.environ.get("REF", "main"))
    parser.add_argument("--base-ref", default=os.environ.get("BASE_REF", ""))
    parser.add_argument("--format", choices=("json", "pretty"), default="json")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    workspace = resolve_workspace()
    if not (workspace / ".git").exists():
        raise RuntimeError(f"Not a git repository: {workspace}")
    compare_ref, warning = resolve_compare_ref(args.base_ref, args.ref)
    paths = changed_files(compare_ref)
    outputs = classify_paths(paths)
    write_outputs(outputs)

    payload = {
        "workspace": str(workspace),
        "ref": args.ref,
        "baseRef": args.base_ref,
        "compareRef": compare_ref,
        "diffRange": diff_range(compare_ref),
        "changedFiles": paths,
        "outputs": outputs,
    }

    if warning:
        print(f"warning: {warning}", file=os.sys.stderr)

    if args.format == "pretty":
        print(f"workspace: {payload['workspace']}")
        print(f"ref: {payload['ref']}")
        print(f"base_ref: {payload['baseRef']}")
        print(f"compare_ref: {payload['compareRef']}")
        print(f"diff_range: {payload['diffRange']}")
        print("changed_files:")
        for path in payload["changedFiles"]:
            print(f"- {path}")
        print("outputs:")
        for key, value in payload["outputs"].items():
            print(f"- {key}: {value}")
    else:
        print(json.dumps(payload))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
