#!/usr/bin/env python3
"""Verify a public GitHub archive download without invoking Git."""

from __future__ import annotations

import argparse
import io
import urllib.request
import zipfile


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="GitHub owner/repository")
    parser.add_argument("--ref", default="main")
    parser.add_argument("--skill-path", required=True)
    args = parser.parse_args()

    url = f"https://codeload.github.com/{args.repo}/zip/{args.ref}"
    request = urllib.request.Request(
        url, headers={"User-Agent": "company-skills-marketplace-download-test"}
    )
    with urllib.request.urlopen(request, timeout=90) as response:
        payload = response.read()
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        expected_suffix = f"/{args.skill_path.strip('/')}/SKILL.md"
        matches = [name for name in archive.namelist() if name.endswith(expected_suffix)]
        if len(matches) != 1:
            raise SystemExit(
                f"expected one {expected_suffix}, found {len(matches)} in public archive"
            )
        content = archive.read(matches[0]).decode("utf-8")
        if not content.startswith("---\n") or "name:" not in content:
            raise SystemExit("downloaded SKILL.md has invalid frontmatter")
    print(
        f"Public no-Git archive test passed for {args.repo}@{args.ref}: {args.skill_path}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
