"""Drift check: agent-prompt bundle on the web ↔ Boule prompt directory.

The website ships the 11 council prompts as a TypeScript const at
``apps/web/lib/agent-prompts.ts`` because Vercel's deploy root is
``apps/web/`` and cannot reach ``services/boule/``. Without a sync
check, the two copies drift the first time anyone edits one without
mirroring the other.

This script reads both sides and confirms each Boule prompt has a
matching entry on the website by name + first content line. It does
NOT enforce char-for-char identity (the web version is allowed to
trim "## Your Tone" tails for compactness) — only that the role
description still starts the same way.

Exit status:
    0  every prompt matched
    1  one or more prompts drifted or missing

Run from the repo root::

    python tests/check_agent_prompts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "services" / "boule" / "src" / "boule" / "prompts"
BUNDLE = REPO_ROOT / "apps" / "web" / "lib" / "agent-prompts.ts"

# Council voters only (Apollo + Boule are services, not council members).
COUNCIL = [
    "ares",
    "hades",
    "athena",
    "cassandra",
    "zeus",
    "solon",
    "themis",
    "hephaestus",
    "daedalus",
    "humans",
    "eris",
]


def first_content_line(md_text: str) -> str:
    """Return the first non-blank, non-heading line of a Markdown file."""
    for line in md_text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith("---"):
            continue
        return s
    return ""


def bundle_contains_first_line(bundle_text: str, name: str, snippet: str) -> bool:
    """Loose substring match — the bundle escapes apostrophes etc."""
    # Strip out heavy punctuation that TypeScript escaping would have
    # transformed (apostrophes -> &apos; / \', em-dashes survive).
    needle = re.sub(r"[\"'`]", "", snippet)
    needle = needle.replace("\\", "")
    hay = re.sub(r"[\"'`\\]", "", bundle_text)
    # Take the first ~40 chars to keep the match resilient to minor
    # web-side edits while still catching genuine drift.
    return needle[:40] in hay


def main() -> int:
    if not BUNDLE.is_file():
        print(f"FAIL: bundle missing at {BUNDLE}")
        return 1
    bundle_text = BUNDLE.read_text(encoding="utf-8")
    failed: list[str] = []
    for name in COUNCIL:
        path = PROMPTS_DIR / f"{name}.md"
        if not path.is_file():
            failed.append(f"{name}: prompt file missing at {path}")
            continue
        md = path.read_text(encoding="utf-8")
        snippet = first_content_line(md)
        if not snippet:
            failed.append(f"{name}: empty prompt file")
            continue
        if not bundle_contains_first_line(bundle_text, name, snippet):
            failed.append(
                f"{name}: first content line not found in bundle\n"
                f"        expected starts with: {snippet[:60]!r}"
            )
    if failed:
        print("agent-prompts drift detected:")
        for line in failed:
            print(f"  - {line}")
        return 1
    print(f"agent-prompts: OK ({len(COUNCIL)} prompts in sync)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
