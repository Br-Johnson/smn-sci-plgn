# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "pyyaml",
#     "jsonschema",
# ]
# ///
"""commons-card adapter: a JSON request on stdin, the commons' own checks on stdout.

The salmon knowledge commons keeps its rules and its checks in its own
repository: ``scripts/okf-check.py`` validates the bundle,
``scripts/ledger/ledger_table.py`` writes a card's in-card citation-ledger table
from ledger JSON, ``scripts/ledger/ledger_check.py --from-card`` checks that
table, and ``CONTRIBUTING.md`` says what an agent may merge. This script runs
those scripts as they stand at ``COMMONS_PIN``, against the cards in the user's
own clone of the commons, and returns what they print. Nothing here judges a
card.

The commons is private and this plugin is public, so the plugin carries none of
it. Each call copies the pinned files out of the clone's git objects into a
temporary directory, runs them from there with the clone as the working
directory, and deletes the directory. The clone's own copies of those files are
never run; where they differ from the pinned ones, ``checkout.drift`` lists
them and script actions stop before running. ``runtime`` and ``checklist``
remain available for inspection.

Run it with uv, which reads the block above and installs the two libraries the
commons' scripts import:

    echo '{"action":"runtime","commons_dir":"path/to/clone"}' \\
      | uv run -q skills/commons-card/scripts/commons_card.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from _common import emit, load_input, result_error  # noqa: E402

COMMONS_REPOSITORY = "salmon-data-mobilization/salmon-knowledge-commons"
# The commons' main as read on 2026-10-29. Moving the pin is a plugin change:
# read the three scripts' usage at the new commit, update
# references/ledger-file.md if the ledger keys changed, and run the live tests
# in tests/test_commons_card.py against a clone.
COMMONS_PIN = "20cd300512cddf378c3769bd21c4f346bed61046"

VALIDATOR = "scripts/okf-check.py"
TABLE_WRITER = "scripts/ledger/ledger_table.py"
CARD_CHECK = "scripts/ledger/ledger_check.py"
SCHEMA = "schema/concept.schema.json"
CHECKLIST = "CONTRIBUTING.md"
# Everything read from the pinned commit. The ledger directory comes whole,
# because ledger_check.py imports ledger_table.py from beside it.
PINNED_PATHS = (VALIDATOR, "scripts/ledger", SCHEMA, CHECKLIST)
REQUIRED_FILES = (VALIDATOR, TABLE_WRITER, CARD_CHECK, SCHEMA, CHECKLIST)

ACTIONS = ("runtime", "validate", "ledger_table", "check_card", "checklist")
GIT_TIMEOUT_SECONDS = 120
SCRIPT_TIMEOUT_SECONDS = 600


class RequestError(Exception):
    """A request the adapter cannot carry out, with the code it answers with."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            check=check,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except FileNotFoundError as exc:
        raise RequestError("no_git", "git is not on PATH; the adapter reads the pinned files with git") from exc
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise RequestError("git_error", f"git {' '.join(args)} failed in {root}: {detail}") from exc


def text(raw: bytes) -> str:
    return raw.decode("utf-8", errors="replace")


def find_clone(request: dict, pin: str) -> dict:
    """The clone to run against, how it was found, and how it relates to the pin."""
    if request.get("commons_dir"):
        start, found_by = str(request["commons_dir"]), "commons_dir"
    elif os.environ.get("SALMON_COMMONS_DIR"):
        start, found_by = os.environ["SALMON_COMMONS_DIR"], "SALMON_COMMONS_DIR"
    else:
        start, found_by = os.getcwd(), "the working directory"
    where = Path(start).expanduser()
    pointer = f"pass commons_dir, or set SALMON_COMMONS_DIR, to a clone of {COMMONS_REPOSITORY}"
    if not where.is_dir():
        raise RequestError("no_checkout", f"{where} (from {found_by}) is not a directory; {pointer}")
    top = git(where, "rev-parse", "--show-toplevel", check=False)
    if top.returncode != 0:
        raise RequestError("no_checkout", f"{where} (from {found_by}) is not inside a git clone; {pointer}")
    root = Path(text(top.stdout).strip())
    if git(root, "cat-file", "-e", f"{pin}^{{commit}}", check=False).returncode != 0:
        raise RequestError(
            "pin_missing",
            f"the clone at {root} (from {found_by}) does not contain the pinned commons commit {pin}. "
            f"If it is a clone of {COMMONS_REPOSITORY}, fetch its main there "
            f"(git -C {root} fetch origin main) and run again; if it is not, {pointer}",
        )
    drift = text(git(root, "diff", "-z", "--name-only", pin, "--", *PINNED_PATHS).stdout)
    return {
        "path": str(root),
        "found_by": found_by,
        "head": text(git(root, "rev-parse", "HEAD").stdout).strip(),
        "contains_pin": git(root, "merge-base", "--is-ancestor", pin, "HEAD", check=False).returncode == 0,
        "drift": sorted(name for name in drift.split("\0") if name),
    }


def extract_pinned(root: Path, pin: str, dest: Path) -> None:
    """Copy PINNED_PATHS as they stand at the pin out of the clone's objects."""
    listing = text(git(root, "ls-tree", "-r", "-z", pin, "--", *PINNED_PATHS).stdout)
    names = []
    for record in filter(None, listing.split("\0")):
        meta, name = record.split("\t", 1)
        _mode, kind, obj = meta.split()
        if kind != "blob":
            continue
        target = (dest / name).resolve()
        if dest.resolve() not in target.parents:
            raise RequestError("git_error", f"the pinned tree names a path outside its own root: {name}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(git(root, "cat-file", "blob", obj).stdout)
        names.append(name)
    missing = [name for name in REQUIRED_FILES if name not in names]
    if missing:
        raise RequestError("pin_incomplete", f"the pinned commit {pin} has no {', '.join(missing)}")


def run_pinned(clone: dict, staged: Path, pin: str, script: str, args: list[str]) -> dict:
    """Run one pinned script with the clone as its working directory."""
    try:
        proc = subprocess.run(
            [sys.executable, str(staged / script), *args],
            cwd=clone["path"],
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise RequestError("timeout", f"{script} did not finish within {SCRIPT_TIMEOUT_SECONDS} seconds") from exc
    out = {
        "ran": {
            "script": script,
            "commit": pin,
            "args": [
                arg.replace(str(staged), "<pinned>").replace(str(staged.parent), "<scratch>") for arg in args
            ],
        },
        "exit_code": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
    if proc.returncode == 0:
        return {"ok": True, **out}
    if "ModuleNotFoundError" in proc.stderr:
        out["hint"] = (
            "The commons' scripts import PyYAML and jsonschema. Run this adapter with uv run, "
            "which installs both from the script block at its top."
        )
    return result_error("nonzero_exit", f"{script} exited {proc.returncode}; its output is in stdout and stderr", **out)


def flag(request: dict, key: str) -> bool:
    value = request.get(key, False)
    if not isinstance(value, bool):
        raise RequestError("invalid_input", f"{key} must be true or false")
    return value


def path_list(request: dict, key: str) -> list[str]:
    values = request.get(key)
    if not isinstance(values, list) or not values or not all(isinstance(v, str) and v.strip() for v in values):
        raise RequestError("invalid_input", f"{key} must be a non-empty list of paths")
    return values


def resolve_in(root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    return (path if path.is_absolute() else root / path).resolve()


def card_paths(request: dict, clone: dict) -> list[str]:
    """Cards as the commons' own commands take them: relative to the clone's root."""
    root = Path(clone["path"]).resolve()
    cards = []
    for value in path_list(request, "cards"):
        full = resolve_in(root, value)
        if root not in full.parents:
            raise RequestError("outside_checkout", f"{value} is not inside the clone at {root}")
        if not full.is_file():
            raise RequestError("missing_file", f"{value} is not a file in the clone at {root}")
        cards.append(full.relative_to(root).as_posix())
    return cards


def ledger_paths(request: dict, clone: dict) -> list[str]:
    root = Path(clone["path"]).resolve()
    ledgers = []
    for value in path_list(request, "ledgers"):
        full = resolve_in(root, value)
        if not full.is_file():
            raise RequestError("missing_file", f"ledger {value} is not a file (a relative path is read from {root})")
        ledgers.append(str(full))
    return ledgers


def validate(request: dict, clone: dict, staged: Path, pin: str, scratch: Path) -> dict:
    mode = "--gaps" if flag(request, "gaps") else "--json"
    result = run_pinned(clone, staged, pin, VALIDATOR, [".", mode, "--schema", str(staged / SCHEMA)])
    try:
        result["output"] = json.loads(result["stdout"])
    except json.JSONDecodeError:
        return result
    del result["stdout"]
    return result


def ledger_table(request: dict, clone: dict, staged: Path, pin: str, scratch: Path) -> dict:
    cards = card_paths(request, clone)
    ledgers = ledger_paths(request, clone)
    write = flag(request, "write")
    report = scratch / "report.json"
    args = [part for ledger in ledgers for part in ("--ledger", ledger)]
    args += ["--report", str(report), *([] if write else ["--dry-run"]), *cards]
    result = run_pinned(clone, staged, pin, TABLE_WRITER, args)
    result["write"] = write
    try:
        result["report"] = json.loads(report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        pass  # the script stopped before writing its report; stderr says why
    return result


def check_card(request: dict, clone: dict, staged: Path, pin: str, scratch: Path) -> dict:
    cards = card_paths(request, clone)
    args = ["--from-card", *(["--checked-only"] if flag(request, "checked_only") else []), *cards]
    return run_pinned(clone, staged, pin, CARD_CHECK, args)


def checklist(request: dict, clone: dict, staged: Path, pin: str, scratch: Path) -> dict:
    return {
        "ok": True,
        "path": CHECKLIST,
        "commit": pin,
        "text": (staged / CHECKLIST).read_text(encoding="utf-8"),
        "differs_in_checkout": CHECKLIST in clone["drift"],
    }


HANDLERS = {
    "validate": validate,
    "ledger_table": ledger_table,
    "check_card": check_card,
    "checklist": checklist,
}


def handle(request: object, pin: str = COMMONS_PIN) -> dict:
    """Answer one request. ``pin`` exists for the tests, which build a clone of their own."""
    if not isinstance(request, dict):
        return result_error("invalid_input", "expected a JSON object")
    action = request.get("action", "runtime")
    base: dict = {"action": action, "pin": {"repository": COMMONS_REPOSITORY, "commit": pin}}
    if action not in ACTIONS:
        return result_error("invalid_action", f"action must be one of {', '.join(ACTIONS)}", **base)
    if action == "runtime":
        base["python"] = sys.version.split()[0]
        base["dependencies"] = {
            name: importlib.util.find_spec(module) is not None
            for name, module in (("pyyaml", "yaml"), ("jsonschema", "jsonschema"))
        }
    try:
        base["checkout"] = clone = find_clone(request, pin)
        if action == "runtime":
            return {"ok": True, **base}
        if action != "checklist" and clone["drift"]:
            raise RequestError(
                "upstream_drift",
                "The clone's tools, schema or contribution rules differ from this plugin's pin. "
                "No script ran: a historical check cannot establish readiness against the current rules. "
                "Inspect runtime and checklist, then update the plugin to a reviewed compatible pin.",
            )
        with tempfile.TemporaryDirectory(prefix="commons-card-") as scratch:
            staged = Path(scratch) / "pinned"
            extract_pinned(Path(clone["path"]), pin, staged)
            return {**base, **HANDLERS[action](request, clone, staged, pin, Path(scratch))}
    except RequestError as exc:
        return result_error(exc.code, str(exc), **base)


def main() -> None:
    try:
        payload = load_input()
    except Exception as exc:  # noqa: BLE001
        emit(result_error("invalid_input", str(exc)))
        return
    emit(handle(payload))


if __name__ == "__main__":
    main()
