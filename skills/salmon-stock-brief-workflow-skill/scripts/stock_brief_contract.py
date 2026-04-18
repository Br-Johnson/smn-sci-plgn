#!/usr/bin/env python3
"""Render or validate the salmon stock brief contract.

Stdlib-only helper for scaffold validation.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys
from dataclasses import dataclass


MAIN_SECTIONS = [
    "Request",
    "Brief target",
    "Bottom line",
    "Evidence",
    "Provenance",
    "Caveats and failure modes",
    "Open questions",
]

EVIDENCE_SECTIONS = [
    "Assessment and status",
    "Telemetry, passage, and movement",
    "Hatchery, harvest, and management",
    "Habitat, ocean, and climate context",
    "Literature and report context",
    "Contradictions and unresolved items",
]


@dataclass
class Finding:
    kind: str
    message: str


HEADING_RE = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")


def render_template() -> str:
    lines = [
        "# Salmon Stock Brief",
        "",
        "## Request",
        "- user_request:",
        "- date:",
        "- scope:",
        "",
        "## Brief target",
        "- normalized_target:",
        "- aliases:",
        "- resolution_status: confirmed | candidate | unresolved",
        "- notes:",
        "",
        "## Bottom line",
        "-",
        "",
        "## Evidence",
        "### Assessment and status",
        "-",
        "",
        "### Telemetry, passage, and movement",
        "-",
        "",
        "### Hatchery, harvest, and management",
        "-",
        "",
        "### Habitat, ocean, and climate context",
        "-",
        "",
        "### Literature and report context",
        "-",
        "",
        "### Contradictions and unresolved items",
        "-",
        "",
        "## Provenance",
        "- source:",
        "- retrieved:",
        "- source_type:",
        "- note:",
        "",
        "## Caveats and failure modes",
        "-",
        "",
        "## Open questions",
        "-",
    ]
    return "\n".join(lines)


def load_text(path: str | None) -> str:
    if path and path != "-":
        return pathlib.Path(path).read_text(encoding="utf-8")
    return sys.stdin.read()


def parse_headings(text: str) -> list[tuple[int, str]]:
    headings: list[tuple[int, str]] = []
    for line in text.splitlines():
        match = HEADING_RE.match(line)
        if match:
            headings.append((len(match.group(1)), match.group(2).strip()))
    return headings


def validate(text: str) -> list[Finding]:
    findings: list[Finding] = []
    headings = parse_headings(text)
    position = 0

    def consume(level: int, title: str) -> bool:
        nonlocal position
        for idx in range(position, len(headings)):
            found_level, found_title = headings[idx]
            if found_level == level and found_title == title:
                position = idx + 1
                return True
        return False

    for section in MAIN_SECTIONS:
        if not consume(2, section):
            findings.append(Finding("missing", f"Missing or out-of-order section: {section}"))

        if section == "Evidence":
            for evidence_section in EVIDENCE_SECTIONS:
                if not consume(3, evidence_section):
                    findings.append(Finding("missing", f"Missing or out-of-order evidence section: {evidence_section}"))

    return findings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", help="Markdown brief to validate")
    parser.add_argument("--template", action="store_true", help="Render the contract template")
    args = parser.parse_args()

    if args.template:
        sys.stdout.write(render_template())
        sys.stdout.write("\n")
        return 0

    if args.path or not sys.stdin.isatty():
        text = load_text(args.path)
        findings = validate(text)
        if findings:
            for finding in findings:
                print(f"{finding.kind}: {finding.message}")
            return 1

        print("ok: contract sections present")
        return 0

    sys.stdout.write(render_template())
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
