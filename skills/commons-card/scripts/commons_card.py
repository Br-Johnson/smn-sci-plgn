"""Thin read-only transport to an explicitly supplied, pinned commons checkout.

No card/schema/ledger logic lives here. Pin checks concern a trusted host's
tool bytes; they are not filesystem isolation, authentication or custody.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

PIN = "1b7594e6263933e08ae196b4374373eb907c137f"
CLOSURE_HASHES = {
    "scripts/okf-check.py": "42dd704d1413cbfd13f746710f20df1b74ea3162ce02a683333786ce705f6f52",
    "scripts/ledger/ledger_table.py": "45947e8f4407e9d656d8f6bca3341c177191a03d84d49328262e3456c9290503",
    "scripts/ledger/ledger_check.py": "71371edd2da0c998bb4e1d00be464b2ec528a4d227a50d5e53501d95a82cceb2",
    "schema/concept.schema.json": "bd4ff9748e4995e693e89097f560884948f23f60331776a592054e75fb6f7953",
    "CONTRIBUTING.md": "6a6b35329b73c9bc66da8db3e3797df8b120724dec3d792353e1e10ae7f03588",
    "scripts/ledger/README.md": "04661de4492c664e27ece6239e3abf302bdc033a28704756739f7381743811af",
}
OUTPUT_KINDS = {
    "validate": "validation_findings",
    "preview": "ledger_preview",
    "check": "ledger_structure",
    "checklist": "contribution_checklist",
}
CHECKLIST = """Checklist attributed to pinned commons CONTRIBUTING.md:
- Use a branch and PR; never push main (lines 8-9, 98-102).
- Give every claim a matching source footnote; preserve sources, gaps and caveats (lines 18-22, 50).
- Distinguish limited-search negatives; name overturning evidence; prefer primary sources and respect licences (lines 51-59).
- Never assert your own verification (lines 37-46).
- Human approval governs schema/tools/rules, contexts, human verification, stable promotion and public access (lines 24-31).
- Agents never mint ontology terms; record proposals and rejection evidence under the existing gap rules (lines 33-35, 78-88).
This is a contribution checklist, not verification or publication approval.
"""


class AdapterError(Exception):
    """A fixed transport refusal, without caller document contents."""


def path_checked(raw: str | Path, *, base: Path | None = None, directory=False, label="input") -> Path:
    path = Path(raw)
    if ".." in path.parts:
        raise AdapterError(f"{label} must not contain parent traversal")
    if not path.is_absolute():
        path = (base or Path.cwd()) / path
    path = Path(os.path.abspath(path))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise AdapterError(f"{label} must not use symlinks")
    if base is not None and not path.is_relative_to(base):
        raise AdapterError(f"{label} must stay inside the explicit workspace")
    if not (path.is_dir() if directory else path.is_file()):
        kind = "directory" if directory else "file"
        raise AdapterError(f"{label} must be an existing {kind}")
    return path


def pinned_checkout(raw: str) -> Path:
    checkout = path_checked(raw, directory=True, label="commons checkout")
    # rev-parse is read-only; caller Git environment overrides cannot redirect it.
    git_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    result = subprocess.run(
        ["git", "-C", str(checkout), "rev-parse", "--show-toplevel", "HEAD"],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False, env=git_env,
    )
    if result.returncode != 0:
        raise AdapterError("commons checkout is not a readable Git checkout")
    lines = result.stdout.splitlines()
    if len(lines) != 2 or Path(lines[0]) != checkout or lines[1] != PIN:
        raise AdapterError("commons checkout does not match the required pin")
    for relative, expected in CLOSURE_HASHES.items():
        file = path_checked(relative, base=checkout, label="pinned tool or governance file")
        if hashlib.sha256(file.read_bytes()).hexdigest() != expected:
            raise AdapterError("pinned tool or governance file bytes do not match")
    return checkout


def workspace_checked(raw: str, checkout: Path) -> Path:
    workspace = path_checked(raw, directory=True, label="workspace")
    if workspace.is_relative_to(checkout) or checkout.is_relative_to(workspace):
        raise AdapterError("workspace must not overlap the commons checkout")

    def unreadable(_error):
        raise AdapterError("workspace paths could not be inspected")

    # The upstream validator scans Markdown recursively. Do not let a symlink
    # route those reads outside the caller's explicitly selected bundle.
    for parent, directories, files in os.walk(workspace, followlinks=False, onerror=unreadable):
        for name in directories + files:
            if (Path(parent) / name).is_symlink():
                raise AdapterError("workspace must not contain symlinks")
        for name in files:
            if not (Path(parent) / name).is_file():
                raise AdapterError("workspace inputs must be regular files")
    return workspace


def execute(args) -> dict:
    if args.action == "checklist":
        if args.workspace or args.card or args.ledger:
            raise AdapterError("checklist accepts only the explicit commons checkout")
    elif not args.workspace:
        raise AdapterError("this action requires an explicit workspace")
    elif args.action == "validate" and (args.card or args.ledger):
        raise AdapterError("validate accepts the whole workspace, without card or ledger options")
    elif args.action == "preview" and (not args.card or not args.ledger):
        raise AdapterError("preview requires explicit cards and ledgers")
    elif args.action == "check" and (not args.card or args.ledger):
        raise AdapterError("check requires explicit cards and accepts no external ledgers")
    checkout = pinned_checkout(args.commons_checkout)
    if args.action == "checklist":
        return {"returncode": 0, "stdout": CHECKLIST, "stderr": ""}
    workspace = workspace_checked(args.workspace, checkout)
    cards = [str(path_checked(value, base=workspace, label="card")) for value in args.card]
    ledgers = [str(path_checked(value, base=workspace, label="ledger")) for value in args.ledger]
    if args.action == "validate":
        argv = [str(checkout / "scripts/okf-check.py"), "--schema",
                str(checkout / "schema/concept.schema.json"), "--json", "--", str(workspace)]
    elif args.action == "preview":
        argv = [str(checkout / "scripts/ledger/ledger_table.py"), "--dry-run"]
        for ledger in ledgers:
            argv += ["--ledger", ledger]
        argv += ["--", *cards]
    else:
        argv = [str(checkout / "scripts/ledger/ledger_check.py"), "--from-card", "--", *cards]
    result = subprocess.run(
        [sys.executable, "-I", "-B", *argv], cwd=workspace,
        capture_output=True, text=True, encoding="utf-8", timeout=60, check=False,
    )
    return {"returncode": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("action", choices=OUTPUT_KINDS)
    parser.add_argument("--commons-checkout", required=True)
    parser.add_argument("--workspace")
    parser.add_argument("--card", action="append", default=[])
    parser.add_argument("--ledger", action="append", default=[])
    args = parser.parse_args(argv)
    output = {"action": args.action, "pin": PIN, "output_kind": OUTPUT_KINDS[args.action], "structural_only": True}
    try:
        output.update(execute(args))
    except AdapterError as exc:
        output.update(returncode=2, error=str(exc))
    except (OSError, UnicodeError):
        output.update(returncode=2, error="required paths or processes could not be read or started")
    except subprocess.TimeoutExpired:
        output.update(returncode=2, error="required process did not finish within the timeout")
    print(json.dumps(output, ensure_ascii=True, sort_keys=True))
    return output["returncode"]


if __name__ == "__main__":
    sys.exit(main())
