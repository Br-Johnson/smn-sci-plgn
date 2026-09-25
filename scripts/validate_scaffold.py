from __future__ import annotations

import importlib.util
import json
import py_compile
import re
import subprocess
import sys
from pathlib import Path
from urllib import request


NON_PLATFORM_SKILLS = {
    "salmon-research-router-skill",
    "salmon-entity-normalizer-skill",
    "salmon-stock-brief-workflow-skill",
}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Text files the reference, pin, and retired-name checks read.
TEXT_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml", ".toml", ".txt"}
SKIPPED_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}
# The append-only history is the one place that may still name what was
# retired, because recording that is its job.
HISTORY_FILES = {"kb/log.md"}
# This file, which necessarily spells out the markers it searches for.
VALIDATOR_PATH = "scripts/validate_scaffold.py"

# The fields a Codex manifest and a Claude Code manifest both carry. For one
# plugin they must say the same thing.
SHARED_MANIFEST_FIELDS = (
    "name",
    "version",
    "description",
    "author",
    "homepage",
    "repository",
    "license",
    "keywords",
)
# Component keys and files Claude Code loads from a plugin and Codex does not.
# Any of them would give one harness something the other never sees, so the
# plugin has none.
CLAUDE_ONLY_MANIFEST_KEYS = ("skills", "commands", "agents", "hooks", "mcpServers", "lspServers", "outputStyles")
CLAUDE_ONLY_ROOT_PATHS = ("commands", "agents", "hooks", "output-styles", ".mcp.json", ".lsp.json", "SKILL.md")

# Agent Skills specification: https://agentskills.io/specification
SKILL_NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SKILL_NAME_MAX = 64
SKILL_DESCRIPTION_MAX = 1024

# The ways this repository names a skill in text: a path into skills/, a
# backticked or quoted `<name>-skill`, a bare `<name>-skill/` directory in a
# tree listing, and a `skill:<name>` graph id. Prose that merely contains the
# word, as in per-skill smoke fixtures, matches none of them.
SKILL_PATH_RE = re.compile(r"(?<!\.claude/)(?<!\.agents/)(?<!\.codex/)skills/([a-z0-9][a-z0-9-]*)/")
SKILL_NAME_RES = (
    re.compile(r"[`\"']([a-z0-9]+(?:-[a-z0-9]+)*-skill)[`\"']"),
    re.compile(r"(?<![a-z0-9./-])([a-z0-9]+(?:-[a-z0-9]+)*-skill)/"),
    re.compile(r"\bskill:([a-z0-9]+(?:-[a-z0-9]+)*)"),
)

# Every pin-shaped mention of the two packages: an install spec, a release
# link, or a "pinned at vX.Y.Z" statement. The plugin pins ONE release for both
# packages, because they share release numbers and each skill documents the R
# route as an equivalent of the Python one; if that ever stops being true, this
# check has to learn two pins instead of one.
PIN_PATTERNS = (
    re.compile(r"salmon-data-mobilization/metasalmon(?:py)?(?:\.git)?@v(\d+\.\d+\.\d+)"),
    re.compile(r"salmon-data-mobilization/metasalmon(?:py)?/releases/tag/v(\d+\.\d+\.\d+)"),
    re.compile(r"pinned (?:at|to) (?:tag )?`?v(\d+\.\d+\.\d+)"),
    re.compile(r'^METASALMONPY_VERSION = "(\d+\.\d+\.\d+)"', re.MULTILINE),
)
RETIRED_REFERENCES = (
    "dfo-pacific-science/metasalmon",
    "dfo-pacific-science.github.io/metasalmon",
)

# Markers of a local term-search implementation in a skill script. See
# check_no_local_term_search() for what they catch, what they miss, and when
# the list retires.
TERM_SEARCH_MARKERS = (
    # Published ontology artifacts, which only a term index needs to read.
    ".jsonld",
    ".ttl",
    ".owl",
    "w3id.org/smn",
    "w3id.org/gcdfo",
    "salmon-domain-ontology",
    "dfo-salmon-ontology",
    # The RDF, SKOS, and IAO predicates a term index is built from.
    "rdf-schema#label",
    "rdf-schema#comment",
    "skos/core#",
    "IAO_0000115",
    "rdfs:label",
    "skos:prefLabel",
    # The vocabulary services metasalmonpy's find_terms() searches.
    "ebi.ac.uk/ols",
    "ebi.ac.uk/spot/zooma",
    "vocab.nerc.ac.uk",
    "data.bioontology.org",
    "qudt.org",
    "api.gbif.org",
    "marinespecies.org",
)
LOCAL_SEARCH_DEFINITION_RE = re.compile(
    r"^\s*def\s+(find_terms|search_terms|sources_for_role|get_term|_?score_\w*|_?rank_\w*)\s*\(",
    re.MULTILINE,
)

# Eval cases for `claude plugin eval`, in the published case format
# (https://code.claude.com/docs/en/plugin-evals, read 2026-09-25). Running a
# case needs Claude Code 2.1.269 or later and a live model, and `claude plugin
# validate` does not read eval files at all (checked on 2.1.267), so
# validate_evals() is the only offline check they get.
EVAL_DIR_DEFAULT = "evals"
EVAL_PROMPT_KEYS = frozenset({
    "schema_version", "name", "description", "tags", "plugins", "runs", "expected_outcome",
    "model", "max_turns", "timeout_seconds", "allowed_tools", "append_system_prompt", "env",
})
EVAL_GRADER_COMMON_KEYS = frozenset({"type", "weight", "arm"})
EVAL_GRADER_OPTIONS = {
    "regex": frozenset({"pattern", "flags", "match", "target"}),
    "tool_used": frozenset({"tool", "input_match", "min", "max"}),
    "tool_order": frozenset({"before", "after"}),
    "file_exists": frozenset({"path", "exists"}),
    "llm": frozenset({"criteria", "focus"}),
    "baseline": frozenset({"baseline_file", "criteria"}),
}
EVAL_PAID_GRADER_TYPES = frozenset({"llm", "baseline"})
EVAL_TARGETS = frozenset({"last_message", "trace", "files", "mock_calls"})
EVAL_FILE_CREATING_TOOLS = frozenset({"Write", "Edit", "Bash"})
JS_REGEX_FLAGS = frozenset("dgimsuvy")
EVAL_ENV_KEY_RE = re.compile(r"^EVAL_[A-Z0-9_]*$")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def require_string_list(value, label: str) -> None:
    require(isinstance(value, list), f"{label} must be a list")
    for item in value:
        require(isinstance(item, str) and item.strip(), f"{label} must contain non-empty strings")


def require_existing_path_or_url(repo_root: Path, value: str, label: str) -> None:
    require(isinstance(value, str) and value.strip(), f"{label} must be a non-empty string")
    if value.startswith("http://") or value.startswith("https://"):
        return
    require((repo_root / value).exists(), f"{label} references a missing path: {value}")


def iter_text_files(repo_root: Path):
    """Yield (repo-relative posix path, text) for every text file in the repo."""
    for path in sorted(repo_root.rglob("*")):
        relative = path.relative_to(repo_root)
        if any(part in SKIPPED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.suffix not in TEXT_SUFFIXES:
            continue
        yield relative.as_posix(), path.read_text(encoding="utf-8", errors="replace")


def validate_manifests(repo_root: Path) -> dict:
    """The Codex and Claude Code manifests must describe one plugin with one skill set.

    Decision: the two files are checked for agreement rather than generated one
    from the other. They carry different harness-specific fields (Codex's
    `interface` block, Claude Code's marketplace), a generator would be one more
    script to keep honest, and a check fails CI on exactly the drift that
    matters.
    """
    codex_path = repo_root / ".codex-plugin" / "plugin.json"
    claude_path = repo_root / ".claude-plugin" / "plugin.json"
    marketplace_path = repo_root / ".claude-plugin" / "marketplace.json"
    for path in (codex_path, claude_path, marketplace_path):
        require(path.exists(), f"plugin manifest missing: {path.relative_to(repo_root)}")
    codex = load_json(codex_path)
    claude = load_json(claude_path)
    marketplace = load_json(marketplace_path)

    missing = [key for key in ("name", "version", "description", "skills", "interface") if key not in codex]
    require(not missing, f".codex-plugin/plugin.json missing keys: {missing}")
    missing = [key for key in ("name", "version", "description", "author") if key not in claude]
    require(not missing, f".claude-plugin/plugin.json missing keys: {missing}")

    for key in SHARED_MANIFEST_FIELDS:
        require(
            codex.get(key) == claude.get(key),
            f"plugin manifests disagree on {key!r}: Codex has {codex.get(key)!r}, Claude Code has {claude.get(key)!r}",
        )
    display_name = codex.get("interface", {}).get("displayName")
    require(
        claude.get("displayName") in (None, display_name),
        f"Claude Code displayName {claude.get('displayName')!r} differs from Codex interface.displayName {display_name!r}",
    )

    # Same skills. Codex loads the directory its `skills` key names. Claude Code
    # always scans `skills/`, and a `skills` key there ADDS directories to that
    # scan, so the Claude Code manifest must not carry one.
    require(
        str(codex.get("skills", "")).rstrip("/") in {"./skills", "skills"},
        ".codex-plugin/plugin.json must load skills from ./skills/, the directory Claude Code scans",
    )
    for key in CLAUDE_ONLY_MANIFEST_KEYS:
        require(
            key not in claude,
            f".claude-plugin/plugin.json must not declare {key!r}: Claude Code would load components Codex never sees",
        )
    for relative in CLAUDE_ONLY_ROOT_PATHS:
        require(
            not (repo_root / relative).exists(),
            f"{relative} at the plugin root would load in Claude Code only; keep the two harnesses on one component set",
        )

    # The marketplace is how a GitHub repository installs in Claude Code: one
    # entry, this plugin, rooted at the repository root.
    require(isinstance(marketplace.get("name"), str) and marketplace["name"].strip(), "marketplace.json requires name")
    owner = marketplace.get("owner")
    require(isinstance(owner, dict) and str(owner.get("name", "")).strip(), "marketplace.json requires owner.name")
    entries = marketplace.get("plugins")
    require(isinstance(entries, list) and len(entries) == 1, "marketplace.json must list exactly one plugin, this one")
    entry = entries[0]
    require(entry.get("name") == claude["name"], "marketplace.json plugin name must match .claude-plugin/plugin.json")
    require(entry.get("source") in {"./", "."}, 'marketplace.json plugin source must be "./", the repository root')
    require(
        "version" not in entry,
        "marketplace.json must not set version: plugin.json wins and `claude plugin validate` warns",
    )
    require(
        entry.get("description", claude["description"]) == claude["description"],
        "marketplace.json plugin description must match the plugin manifests",
    )
    return {
        "plugin": claude["name"],
        "version": claude["version"],
        "marketplace": marketplace["name"],
        "manifests": [
            str(path.relative_to(repo_root)) for path in (codex_path, claude_path, marketplace_path)
        ],
    }


def read_frontmatter(path: Path) -> dict[str, str]:
    """Read the single-line `key: value` fields of a SKILL.md frontmatter block.

    Deliberately small and stdlib-only. A folded or block YAML value would be
    read as its indicator character, so validate_skill_frontmatter() rejects
    those and asks for the value on one line.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    require(bool(lines) and lines[0].strip() == "---", f"{path} must start with a YAML frontmatter block")
    fields: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return fields
        key, sep, value = line.partition(":")
        if sep and key.strip() and not key.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    raise SystemExit(f"{path} frontmatter block is never closed")


def validate_skill_frontmatter(repo_root: Path, skill_names: list[str]) -> dict:
    """Each skill's frontmatter must follow the Agent Skills spec both harnesses read.

    `name` must equal the directory name. Claude Code takes a plugin skill's
    command from `name`, the spec requires the match, and the registry, the
    graph, and the selector all use the directory name as the skill's id, so a
    mismatch would give one skill two names. `claude plugin validate` checks
    neither the match nor the naming rule.
    """
    for skill_name in skill_names:
        path = repo_root / "skills" / skill_name / "SKILL.md"
        fields = read_frontmatter(path)
        name = fields.get("name", "")
        require(name == skill_name, f"{path}: frontmatter name {name!r} must equal the directory name {skill_name!r}")
        require(
            len(name) <= SKILL_NAME_MAX and SKILL_NAME_RE.fullmatch(name) is not None,
            f"{path}: name must be 1-{SKILL_NAME_MAX} lowercase letters, digits, and single hyphens",
        )
        description = fields.get("description", "")
        require(
            description and description not in {">", "|", ">-", "|-", ">+", "|+"},
            f"{path}: description must be present and written on one line",
        )
        require(
            len(description) <= SKILL_DESCRIPTION_MAX,
            f"{path}: description is {len(description)} characters; the limit is {SKILL_DESCRIPTION_MAX}",
        )
    return {"skills_checked": len(skill_names)}


def validate_skill_references(repo_root: Path, skill_names: list[str]) -> dict:
    """Nothing may name a skill that does not exist.

    The registry cards, skill-platform map, and graph nodes are checked where
    they are validated below. This adds the three places those checks never
    read: the selector's hard-coded skill tables, the selector fixtures, and the
    prose and paths across the repository. The history file is exempt because
    naming retired skills is its job.
    """
    known = set(skill_names)

    # Load the selector from this repo_root by path. A plain import would be
    # cached in sys.modules and answer for whichever copy was imported first.
    # The module is registered only while it executes, because its dataclass
    # looks its own module up in sys.modules.
    module_name = "_validated_skill_graph_selector"
    spec = importlib.util.spec_from_file_location(module_name, repo_root / "scripts" / "skill_graph_selector.py")
    selector = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = selector
    try:
        spec.loader.exec_module(selector)
    finally:
        sys.modules.pop(module_name, None)
    named: set[str] = set()
    for skills in selector.LANE_SKILL_MAP.values():
        named.update(skills)
    for skill, companions in selector.SPECIAL_SKILL_COMPANIONS.items():
        named.add(skill)
        named.update(companions)
    named.update(selector.OPTIONAL_SKILL_PATTERNS)
    unknown = sorted(named - known)
    require(not unknown, f"scripts/skill_graph_selector.py names skills that do not exist: {unknown}")

    cases = load_json(repo_root / "tests" / "fixtures" / "skill_graph_selector_cases.json")
    fixture_skills = {
        skill
        for case in cases
        for field in ("selected_skills", "blocked_skills")
        for skill in case["expected"].get(field, [])
    }
    unknown = sorted(fixture_skills - known)
    require(not unknown, f"selector fixtures expect skills that do not exist: {unknown}")

    problems: list[str] = []
    files_scanned = 0
    for relative, text in iter_text_files(repo_root):
        if relative in HISTORY_FILES:
            continue
        files_scanned += 1
        for name in sorted(set(SKILL_PATH_RE.findall(text))):
            if name not in known:
                problems.append(f"{relative}: path skills/{name}/ does not exist")
        names = {name for pattern in SKILL_NAME_RES for name in pattern.findall(text)}
        for name in sorted(names - known):
            problems.append(f"{relative}: names skill {name!r}, which does not exist")
    require(not problems, "references to missing skills:\n  " + "\n  ".join(problems))
    return {"text_files_scanned": files_scanned, "selector_skills": len(named), "fixture_skills": len(fixture_skills)}


def check_package_pins(repo_root: Path) -> dict:
    """Every copy of the package pin must agree, and nothing may point at the retired fork.

    The pin lives in several places that cannot import each other: the
    constants in scripts/_package_adapter.py, the PEP 723 block of each adapter
    script, and the docs and registry that link the release. Moving it means
    editing every copy in one change; this check is what enforces that.
    """
    found: dict[str, set[str]] = {}
    retired: list[str] = []
    for relative, text in iter_text_files(repo_root):
        if relative in HISTORY_FILES:
            continue
        for pattern in PIN_PATTERNS:
            for version in pattern.findall(text):
                found.setdefault(version, set()).add(relative)
        if relative == VALIDATOR_PATH:
            continue  # this file holds the list of retired references
        for marker in RETIRED_REFERENCES:
            if marker in text:
                retired.append(f"{relative}: {marker}")
    require(not retired, "references to the retired metasalmon fork remain:\n  " + "\n  ".join(sorted(retired)))
    require(found, "no metasalmon or metasalmonpy pin found")
    require(
        len(found) == 1,
        "package pins disagree:\n  "
        + "\n  ".join(f"v{version}: {', '.join(sorted(paths))}" for version, paths in sorted(found.items())),
    )
    (pin,) = found

    requirement = f"metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v{pin}"
    adapters: list[str] = []
    for script in sorted((repo_root / "skills").glob("*/scripts/*.py")):
        text = script.read_text(encoding="utf-8")
        if "_package_adapter" not in text:
            continue
        relative = script.relative_to(repo_root).as_posix()
        block = re.search(r"^# /// script\n(.*?)^# ///$", text, flags=re.MULTILINE | re.DOTALL)
        require(block is not None, f"{relative} imports the package adapter but has no PEP 723 script block for uv")
        require(requirement in block.group(1), f"{relative}: its script block must require {requirement!r}")
        adapters.append(relative)
    require(adapters, "no package adapter scripts found")
    return {"pin": f"v{pin}", "files": len(found[pin]), "adapters": adapters}


def check_no_local_term_search(repo_root: Path) -> dict:
    """No skill script may reimplement ontology term search.

    Term search belongs to metasalmonpy (Brett, 2026-09-25: the plugin's own
    implementation retires in favour of it). This is a static check over every
    file under skills/*/scripts/ and every script in scripts/ except this
    validator, which fetches the published ontologies only to report their
    versions and which holds the marker list itself.

    What it catches: a script that reads the published ontology artifacts
    (JSON-LD, Turtle, OWL, the w3id namespaces or the ontology repositories),
    parses RDF, SKOS, or IAO label predicates, calls one of the vocabulary
    services find_terms() searches, or defines its own find_terms,
    search_terms, sources_for_role, get_term, or scoring or ranking function.
    Measured against the retired implementation on 2026-09-25:
    scripts/ontology_lookup_common.py fails on four predicate markers and three
    local definitions (search_terms, get_term, _score_record), and the lookup
    scripts built on it fail on the published-artifact URLs they fetched.

    What it misses: search against a source not on the list; a URL assembled
    at runtime from fragments; matching or ranking over terms already in
    memory, such as a vendored term list; and instructions in a SKILL.md that
    tell the harness to fetch and grep an ontology itself, which is prose, not
    a script.

    Maintenance: when metasalmonpy's find_terms() gains a vocabulary source,
    add its host to TERM_SEARCH_MARKERS.

    Retires when the plugin reaches term search only through a command-line
    tool or generated adapter that the packages ship, leaving no Python import
    surface to police, or when a behavioural test shows that every term the
    plugin returns carries the package's provenance.
    """
    targets = [
        path
        for path in sorted((repo_root / "skills").glob("*/scripts/**/*"))
        if path.is_file() and "__pycache__" not in path.parts
    ]
    targets += [
        path
        for path in sorted((repo_root / "scripts").glob("*.py"))
        if path.relative_to(repo_root).as_posix() != VALIDATOR_PATH
    ]
    problems: list[str] = []
    for path in targets:
        relative = path.relative_to(repo_root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        for marker in TERM_SEARCH_MARKERS:
            if marker in text:
                problems.append(f"{relative}: contains {marker!r}")
        for name in LOCAL_SEARCH_DEFINITION_RE.findall(text):
            problems.append(f"{relative}: defines {name}()")
    require(
        not problems,
        "skill scripts must call metasalmonpy for term search, not reimplement it:\n  " + "\n  ".join(problems),
    )
    return {"scripts_checked": len(targets)}


def _split_flow_items(inner: str, where: str) -> list[str]:
    """Split the inside of a YAML flow collection on its top-level commas."""
    items: list[str] = []
    current: list[str] = []
    depth = 0
    quote = None
    escaped = False
    for char in inner:
        current.append(char)
        if quote == '"' and escaped:
            escaped = False
        elif quote == '"' and char == "\\":
            escaped = True
        elif quote:
            if char == quote:
                quote = None
        elif char in "'\"":
            quote = char
        elif char in "[{":
            depth += 1
        elif char in "]}":
            depth -= 1
        elif char == "," and depth == 0:
            current.pop()
            items.append("".join(current))
            current = []
    require(quote is None and depth == 0, f"{where}: unbalanced quotes or brackets")
    items.append("".join(current))
    return [item.strip() for item in items if item.strip()]


def parse_yaml_scalar(text: str, where: str):
    """Read one value from the small YAML subset the eval files use.

    Supported: single- and double-quoted strings, flow sequences, flow
    mappings, integers, floats, booleans, null, and plain strings. Anything
    else, such as a block scalar or an anchor, is rejected by name rather than
    misread, so extend this deliberately if a case ever needs more.
    """
    value = text.strip()
    if not value:
        return None
    if value[0] == "'":
        require(len(value) >= 2 and value.endswith("'"), f"{where}: unterminated single-quoted value")
        inner = value[1:-1]
        require("'" not in inner.replace("''", ""), f"{where}: stray quote inside a single-quoted value")
        return inner.replace("''", "'")
    if value[0] == '"':
        try:
            return json.loads(value)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"{where}: double-quoted value outside the JSON-compatible subset: {exc}") from exc
    if value[0] == "[":
        require(value.endswith("]"), f"{where}: unterminated flow sequence")
        return [parse_yaml_scalar(item, where) for item in _split_flow_items(value[1:-1], where)]
    if value[0] == "{":
        require(value.endswith("}"), f"{where}: unterminated flow mapping")
        mapping: dict = {}
        for item in _split_flow_items(value[1:-1], where):
            key, sep, rest = item.partition(":")
            require(bool(sep) and bool(key.strip()), f"{where}: flow mapping entry {item!r} needs key: value")
            mapping[key.strip()] = parse_yaml_scalar(rest, where)
        return mapping
    require(value[0] not in "|>&*!%@`", f"{where}: {value[0]!r} values are outside the YAML subset this validator reads")
    value = value.split(" #", 1)[0].rstrip()
    if re.fullmatch(r"[-+]?\d+", value):
        return int(value)
    if re.fullmatch(r"[-+]?\d+\.\d+", value):
        return float(value)
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    if value.lower() in {"null", "~"}:
        return None
    return value


def read_eval_file(path: Path) -> tuple[dict, str]:
    """Return (frontmatter fields, body) for a prompt.md or grader file."""
    lines = path.read_text(encoding="utf-8").splitlines()
    require(bool(lines) and lines[0].strip() == "---", f"{path}: must start with a --- frontmatter block")
    end = next((index for index in range(1, len(lines)) if lines[index].strip() == "---"), None)
    require(end is not None, f"{path}: frontmatter block is never closed")
    fields: dict = {}
    for number, line in enumerate(lines[1:end], start=2):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        where = f"{path}:{number}"
        require(not line[0].isspace(), f"{where}: nested or continued values are outside the YAML subset this validator reads")
        key, sep, value = line.partition(":")
        require(bool(sep) and re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key) is not None, f"{where}: expected key: value")
        require(key not in fields, f"{where}: duplicate key {key!r}")
        fields[key] = parse_yaml_scalar(value, where)
    return fields, "\n".join(lines[end + 1:]).strip()


def _compile_eval_regex(pattern, flags, where: str) -> re.Pattern:
    """Compile a grader regex with Python's re, as a proxy for JavaScript's.

    The runner uses JavaScript regex syntax. The two agree on everything these
    cases use (classes, groups, alternation, \\b, \\d, \\s, \\w on ASCII text);
    a JavaScript-only construct would fail here and need a look.
    """
    require(isinstance(pattern, str) and pattern != "", f"{where}: needs a non-empty pattern")
    flags = flags or ""
    require(isinstance(flags, str) and set(flags) <= JS_REGEX_FLAGS, f"{where}: flags {flags!r} are not JavaScript regex flags")
    try:
        return re.compile(pattern, re.IGNORECASE if "i" in flags else 0)
    except re.error as exc:
        raise SystemExit(f"{where}: pattern {pattern!r} does not compile: {exc}") from exc


def validate_evals(repo_root: Path, skill_names: list[str]) -> dict:
    """Check every eval case offline, since nothing else does before a live run.

    Schema: prompt.md frontmatter keys, value ranges, grader types, and each
    type's options, all as documented; an unknown key is an error there too.

    Drift, which is the reason this exists: every skill must be the subject of
    at least one case; each case's `tool_used: Skill` grader must name exactly
    one skill that exists; a Bash grader that names a `.py` script must match a
    script the plugin ships; skills an llm rubric names must exist; and every
    tool a grader expects must be in the case's allowed_tools. Renaming or
    deleting a skill or script without updating its eval fails here, not at
    the next paid run. Not caught: a stale name inside a regex alternation
    that still matches another script, and anything about whether a case
    passes, which only a live run can say.
    """
    claude = load_json(repo_root / ".claude-plugin" / "plugin.json")
    eval_dir = (claude.get("experimental") or {}).get("evals") or EVAL_DIR_DEFAULT
    eval_root = repo_root / eval_dir
    require(eval_root.is_dir(), f"{eval_dir}/ is missing: every skill needs an eval case")
    plugin_name = claude["name"]

    gitignore = (repo_root / ".gitignore").read_text(encoding="utf-8").splitlines()
    require(
        f"{eval_dir}/results/" in {line.strip() for line in gitignore},
        f".gitignore must ignore {eval_dir}/results/, where every eval run writes its report",
    )

    skill_inputs = {
        skill: (json.dumps({"skill": f"{plugin_name}:{skill}"}), json.dumps({"skill": skill}))
        for skill in skill_names
    }
    script_inputs = {
        path.relative_to(repo_root).as_posix(): (
            json.dumps({"command": f"python3 {path}"}),
            json.dumps({"command": f'uv run -q "{path}"'}),
        )
        for path in sorted((repo_root / "skills").glob("*/scripts/*.py")) + sorted((repo_root / "scripts").glob("*.py"))
    }

    case_dirs: list[Path] = []
    pending = [eval_root]
    while pending:
        directory = pending.pop()
        for child in sorted(directory.iterdir()):
            if not child.is_dir() or child.name in {"results", "mocks"} or child.name.startswith("."):
                continue
            if (child / "prompt.md").exists() or (child / "case.yaml").exists():
                case_dirs.append(child)
            else:
                pending.append(child)
    require(case_dirs, f"{eval_dir}/ holds no eval cases")

    covered: dict[str, list[str]] = {skill: [] for skill in skill_names}
    grader_count = 0
    paid_count = 0
    for case_dir in sorted(case_dirs):
        case = case_dir.relative_to(repo_root).as_posix()
        require(
            not (case_dir / "case.yaml").exists(),
            f"{case}/case.yaml is not read by this validator; keep the case in prompt.md, or extend validate_evals first",
        )
        fields, prompt = read_eval_file(case_dir / "prompt.md")
        unknown = sorted(set(fields) - EVAL_PROMPT_KEYS)
        require(not unknown, f"{case}/prompt.md: unknown frontmatter keys {unknown}; the runner rejects them")
        require(bool(prompt), f"{case}/prompt.md: the body is the prompt and must not be empty")
        require(fields.get("name", case_dir.name) == case_dir.name, f"{case}/prompt.md: name must equal the directory name")
        require(fields.get("schema_version", "1.1") == "1.1", f"{case}/prompt.md: schema_version must be \"1.1\"")
        for key, low, high in (("runs", 1, 50), ("max_turns", 1, 200), ("timeout_seconds", 1, 3600)):
            if key in fields:
                value = fields[key]
                require(
                    isinstance(value, int) and not isinstance(value, bool) and low <= value <= high,
                    f"{case}/prompt.md: {key} must be an integer from {low} to {high}",
                )
        for key in ("tags", "allowed_tools", "plugins"):
            if key in fields:
                require_string_list(fields[key], f"{case}/prompt.md: {key}")
        env = fields.get("env") or {}
        require(isinstance(env, dict), f"{case}/prompt.md: env must be a mapping")
        bad_env = sorted(key for key in env if not EVAL_ENV_KEY_RE.match(key))
        require(not bad_env, f"{case}/prompt.md: env keys must match EVAL_[A-Z0-9_]*, not {bad_env}")
        allowed = set(fields.get("allowed_tools") or [])

        grader_paths = sorted((case_dir / "graders").glob("*.md"))
        require(grader_paths, f"{case}: needs at least one grader under graders/")
        subjects: set[str] = set()
        for grader_path in grader_paths:
            where = grader_path.relative_to(repo_root).as_posix()
            grader, body = read_eval_file(grader_path)
            kind = grader.get("type")
            require(kind in EVAL_GRADER_OPTIONS, f"{where}: type must be one of {sorted(EVAL_GRADER_OPTIONS)}")
            unknown = sorted(set(grader) - EVAL_GRADER_COMMON_KEYS - EVAL_GRADER_OPTIONS[kind])
            require(not unknown, f"{where}: unknown keys {unknown} for a {kind} grader")
            if "weight" in grader:
                weight = grader["weight"]
                require(
                    isinstance(weight, (int, float)) and not isinstance(weight, bool) and weight > 0,
                    f"{where}: weight must be a positive number",
                )
            require(grader.get("arm") in (None, "with-only", "both"), f"{where}: arm must be with-only or both")
            grader_count += 1
            paid_count += kind in EVAL_PAID_GRADER_TYPES

            if kind == "regex":
                _compile_eval_regex(grader.get("pattern"), grader.get("flags"), where)
                match = grader.get("match", "contains")
                require(
                    match in {"contains", "not_contains"} or re.fullmatch(r"count:\d+", str(match)) is not None,
                    f"{where}: match must be contains, not_contains, or count:N",
                )
                target = grader.get("target", "last_message")
                if isinstance(target, dict):
                    require(target.get("source") == "file", f"{where}: a mapping target needs source: file")
                    path = target.get("path")
                    require(
                        isinstance(path, str) and path and not path.startswith("/") and ".." not in path.split("/"),
                        f"{where}: target path must be relative to the run's workspace",
                    )
                else:
                    require(target in EVAL_TARGETS, f"{where}: target must be one of {sorted(EVAL_TARGETS)} or a file")
            elif kind == "tool_used":
                tool = grader.get("tool")
                require(isinstance(tool, str) and tool.strip(), f"{where}: needs tool")
                low = grader.get("min", 1)
                high = grader.get("max")
                require(isinstance(low, int) and low >= 0, f"{where}: min must be a non-negative integer")
                require(high is None or (isinstance(high, int) and high >= low), f"{where}: max must be an integer no smaller than min")
                pattern = None
                if "input_match" in grader:
                    pattern = _compile_eval_regex(grader["input_match"], None, where)
                if low >= 1:
                    require(tool in allowed, f"{where}: expects {tool} but {case}/prompt.md does not allow it")
                if tool == "Skill":
                    require(pattern is not None, f"{where}: a Skill grader must name its skill with input_match")
                    named = [skill for skill, inputs in skill_inputs.items() if any(pattern.search(text) for text in inputs)]
                    require(
                        len(named) == 1,
                        f"{where}: input_match must name exactly one existing skill, and it names {named or 'none'}",
                    )
                    if low >= 1:
                        subjects.add(named[0])
                elif tool == "Bash" and pattern is not None and ".py" in pattern.pattern.replace("\\.", "."):
                    require(
                        any(pattern.search(text) for inputs in script_inputs.values() for text in inputs),
                        f"{where}: input_match names a script the plugin does not ship",
                    )
            elif kind == "tool_order":
                for key in ("before", "after"):
                    step = grader.get(key)
                    tool = step.get("tool") if isinstance(step, dict) else step
                    require(isinstance(tool, str) and tool.strip(), f"{where}: {key} needs a tool")
                    require(tool in allowed, f"{where}: expects {tool} but {case}/prompt.md does not allow it")
                    if isinstance(step, dict) and "input_match" in step:
                        _compile_eval_regex(step["input_match"], None, where)
            elif kind == "file_exists":
                path = grader.get("path")
                require(isinstance(path, str) and path.strip(), f"{where}: needs path")
                if grader.get("exists", True):
                    require(allowed & EVAL_FILE_CREATING_TOOLS, f"{where}: expects a file, but the case allows no tool that creates one")
            elif kind in EVAL_PAID_GRADER_TYPES:
                criteria = grader.get("criteria") or body
                require(bool(criteria), f"{where}: an {kind} grader needs criteria")
                require("PASS" in criteria and "FAIL" in criteria, f"{where}: write the criteria as PASS and FAIL conditions")
                missing = sorted(set(re.findall(r"\b[a-z0-9]+(?:-[a-z0-9]+)*-skill\b", criteria)) - set(skill_names))
                require(not missing, f"{where}: criteria name skills that do not exist: {missing}")
                if kind == "llm":
                    focus = grader.get("focus", "last_message")
                    require(
                        focus in EVAL_TARGETS or (isinstance(focus, dict) and focus.get("source") == "file"),
                        f"{where}: focus must be one of {sorted(EVAL_TARGETS)} or a file",
                    )
                else:
                    baseline_file = grader.get("baseline_file")
                    require(
                        isinstance(baseline_file, str) and (case_dir / baseline_file).is_file(),
                        f"{where}: baseline_file must name a transcript in the case directory",
                    )

        require(subjects, f"{case}: needs a tool_used: Skill grader that expects its skill to fire")
        if case_dir.name in skill_inputs:
            require(
                case_dir.name in subjects,
                f"{case}: the case is named for skill {case_dir.name!r} but its Skill grader expects {sorted(subjects)}",
            )
        for skill in subjects:
            covered[skill].append(case_dir.name)

    uncovered = sorted(skill for skill, cases in covered.items() if not cases)
    require(not uncovered, f"skills with no eval case: {uncovered}")
    return {
        "eval_dir": eval_dir,
        "cases": len(case_dirs),
        "graders": grader_count,
        "judge_graders": paid_count,
        "free_graders": grader_count - paid_count,
    }


def validate_platform_registry(repo_root: Path, skill_names: list[str]) -> dict:
    registry_root = repo_root / "registry"
    vocab = load_json(registry_root / "vocab.json")
    platform_schema = load_json(registry_root / "platform-card.schema.json")
    identity_schema = load_json(registry_root / "identity-record.schema.json")
    identity_slice_schema = load_json(registry_root / "identity" / "columbia-basin-v0.schema.json")
    skill_map = load_json(registry_root / "skill-platform-map.json")

    access_tiers = set(vocab["access_tiers"])
    capability_categories = set(vocab["capability_categories"])
    capability_statuses = set(vocab["capability_statuses"])
    identity_entity_types = set(vocab["identity_entity_types"])
    mapping_relations = set(vocab["mapping_relations"])
    confidence_levels = set(vocab["confidence_levels"])
    identity_record_statuses = set(vocab["identity_record_statuses"])

    platform_cards: dict[str, dict] = {}
    for path in sorted((registry_root / "platforms").glob("*.json")):
        card = load_json(path)
        for field in platform_schema["required"]:
            require(field in card, f"platform card {path} missing field: {field}")
        require(card["platform_id"] == path.stem, f"platform_id mismatch in {path}")
        require(isinstance(card["platform_name"], str) and card["platform_name"].strip(), f"invalid platform_name in {path}")
        require(isinstance(card["owner"], str) and card["owner"].strip(), f"invalid owner in {path}")
        require_string_list(card["canonical_urls"], f"{path}: canonical_urls")
        require_string_list(card["docs_urls"], f"{path}: docs_urls")
        require(card["access_tier"] in access_tiers, f"invalid access_tier in {path}")
        require(isinstance(card["auth_access_model"], str) and card["auth_access_model"].strip(), f"invalid auth_access_model in {path}")
        require_string_list(card["data_domains"], f"{path}: data_domains")
        require_string_list(card["identifier_systems"], f"{path}: identifier_systems")
        require_string_list(card["blockers"], f"{path}: blockers")
        require_string_list(card["governance_constraints"], f"{path}: governance_constraints")
        require_string_list(card["related_skills"], f"{path}: related_skills")
        require_string_list(card["evidence_links"], f"{path}: evidence_links")
        require_string_list(card["watch_fields"], f"{path}: watch_fields")
        require(isinstance(card["last_verified_date"], str) and DATE_RE.fullmatch(card["last_verified_date"]), f"invalid last_verified_date in {path}")

        capabilities = card["capabilities"]
        require(isinstance(capabilities, dict), f"{path}: capabilities must be an object")
        require(set(capabilities.keys()) == capability_categories, f"{path}: capabilities must cover every normalized category exactly once")
        for category, detail in capabilities.items():
            require(isinstance(detail, dict), f"{path}: capability {category} must be an object")
            require(detail.get("status") in capability_statuses, f"{path}: invalid capability status for {category}")
            require(isinstance(detail.get("note"), str) and detail["note"].strip(), f"{path}: capability {category} requires a note")

        for related_skill in card["related_skills"]:
            require(related_skill in skill_names, f"{path}: unknown related skill {related_skill}")

        platform_cards[card["platform_id"]] = card

    require(platform_cards, "registry/platforms must contain at least one platform card")

    mappings = skill_map.get("skills")
    require(isinstance(mappings, list) and mappings, "registry/skill-platform-map.json must contain a non-empty skills list")
    seen_mapped_skills: set[str] = set()
    for entry in mappings:
        require(isinstance(entry, dict), "each skill-platform mapping must be an object")
        skill = entry.get("skill")
        platform_id = entry.get("platform_id")
        kb_page = entry.get("kb_page")
        require(isinstance(skill, str) and skill.strip(), "skill-platform mapping requires skill")
        require(isinstance(platform_id, str) and platform_id.strip(), "skill-platform mapping requires platform_id")
        require(isinstance(kb_page, str) and kb_page.strip(), "skill-platform mapping requires kb_page")
        require(skill in skill_names, f"skill-platform mapping references unknown skill {skill}")
        require(platform_id in platform_cards, f"skill-platform mapping references unknown platform {platform_id}")
        require(skill not in seen_mapped_skills, f"duplicate skill-platform mapping for {skill}")
        seen_mapped_skills.add(skill)
        require(skill in platform_cards[platform_id]["related_skills"], f"platform card {platform_id} does not list mapped skill {skill}")
        require((repo_root / kb_page).exists(), f"mapped kb page does not exist: {kb_page}")

    expected_platform_skills = sorted(skill for skill in skill_names if skill not in NON_PLATFORM_SKILLS)
    require(sorted(seen_mapped_skills) == expected_platform_skills, "every external-source skill must map to exactly one platform card and kb page")

    identity_records = load_json(registry_root / "identity" / "seed-crosswalks.json")
    require(isinstance(identity_records, list) and identity_records, "registry/identity/seed-crosswalks.json must contain records")
    for index, record in enumerate(identity_records):
        label = f"identity record {index}"
        require(isinstance(record, dict), f"{label} must be an object")
        for field in identity_schema["required"]:
            require(field in record, f"{label} missing field: {field}")
        require(record["entity_type"] in identity_entity_types, f"{label} has invalid entity_type")
        require(record["mapping_relation"] in mapping_relations, f"{label} has invalid mapping_relation")
        require(record["confidence"] in confidence_levels, f"{label} has invalid confidence")
        require(record["record_status"] in identity_record_statuses, f"{label} has invalid record_status")
        for field in identity_schema["required"]:
            require(isinstance(record[field], str) and record[field].strip(), f"{label} field {field} must be a non-empty string")

    bounded_slice = load_json(registry_root / "identity" / "columbia-basin-v0.json")
    for field in identity_slice_schema["required"]:
        require(field in bounded_slice, f"registry/identity/columbia-basin-v0.json missing field: {field}")
    require(isinstance(bounded_slice["slice_id"], str) and bounded_slice["slice_id"].strip(), "bounded identity slice requires slice_id")
    require(isinstance(bounded_slice["version"], str) and bounded_slice["version"].strip(), "bounded identity slice requires version")
    if "generated_on" in bounded_slice:
        require(isinstance(bounded_slice["generated_on"], str) and DATE_RE.fullmatch(bounded_slice["generated_on"]), "bounded identity slice generated_on must be a date")
    scope = bounded_slice["scope"]
    require(isinstance(scope, dict), "bounded identity slice scope must be an object")
    for field in identity_slice_schema["properties"]["scope"]["required"]:
        require(isinstance(scope.get(field), str) and scope[field].strip(), f"bounded identity slice scope missing {field}")
    scheme_definitions = bounded_slice["scheme_definitions"]
    require(isinstance(scheme_definitions, list) and scheme_definitions, "bounded identity slice requires scheme_definitions")
    for index, scheme in enumerate(scheme_definitions):
        label = f"identity scheme definition {index}"
        require(isinstance(scheme, dict), f"{label} must be an object")
        require(isinstance(scheme.get("scheme"), str) and scheme["scheme"].strip(), f"{label} missing scheme")
        require(isinstance(scheme.get("definition"), str) and scheme["definition"].strip(), f"{label} missing definition")
    bounded_records = bounded_slice["records"]
    require(isinstance(bounded_records, list) and bounded_records, "bounded identity slice requires records")
    for index, record in enumerate(bounded_records):
        label = f"bounded identity record {index}"
        require(isinstance(record, dict), f"{label} must be an object")
        for field in identity_slice_schema["$defs"]["record"]["required"]:
            require(field in record, f"{label} missing field: {field}")
        require(record["entity_type"] in identity_entity_types, f"{label} has invalid entity_type")
        require(record["mapping_relation"] in mapping_relations, f"{label} has invalid mapping_relation")
        require(record["confidence"] in confidence_levels, f"{label} has invalid confidence")
        require(record["record_status"] in identity_record_statuses, f"{label} has invalid record_status")
        require_string_list(record["aliases"], f"{label} aliases")
        require(isinstance(record["provenance"], list) and record["provenance"], f"{label} requires provenance entries")
        require(isinstance(record["valid_from"], str) and DATE_RE.fullmatch(record["valid_from"]), f"{label} valid_from must be a date")
        require(isinstance(record["valid_time_or_version"], str) and record["valid_time_or_version"].strip(), f"{label} missing valid_time_or_version")

    return {
        "platform_card_count": len(platform_cards),
        "mapped_external_skills": len(seen_mapped_skills),
        "identity_record_count": len(identity_records),
        "bounded_identity_record_count": len(bounded_records),
    }


def validate_skill_graph(repo_root: Path, skill_names: list[str]) -> dict:
    registry_root = repo_root / "registry"
    vocab = load_json(registry_root / "vocab.json")
    graph_schema = load_json(registry_root / "skill-graph.schema.json")
    graph = load_json(registry_root / "skill-graph.json")
    skill_map = load_json(registry_root / "skill-platform-map.json")

    node_required = graph_schema["properties"]["nodes"]["items"]["required"]
    edge_required = graph_schema["properties"]["edges"]["items"]["required"]
    node_types = set(vocab["skill_graph_node_types"])
    edge_relations = set(vocab["skill_graph_edge_relations"])
    platform_ids = {path.stem for path in (registry_root / "platforms").glob("*.json")}

    for field in graph_schema["required"]:
        require(field in graph, f"registry/skill-graph.json missing field: {field}")
    require(isinstance(graph["graph_version"], str) and graph["graph_version"].strip(), "registry/skill-graph.json graph_version must be a non-empty string")
    require(isinstance(graph["last_updated"], str) and DATE_RE.fullmatch(graph["last_updated"]), "registry/skill-graph.json last_updated must be a date")
    require(isinstance(graph["description"], str) and graph["description"].strip(), "registry/skill-graph.json description must be a non-empty string")

    nodes = graph["nodes"]
    edges = graph["edges"]
    require(isinstance(nodes, list) and nodes, "registry/skill-graph.json must contain nodes")
    require(isinstance(edges, list) and edges, "registry/skill-graph.json must contain edges")

    node_lookup: dict[str, dict] = {}
    lane_node_ids: set[str] = set()
    skill_node_names: set[str] = set()
    platform_node_ids: set[str] = set()

    for index, node in enumerate(nodes):
        label = f"skill-graph node {index}"
        require(isinstance(node, dict), f"{label} must be an object")
        for field in node_required:
            require(field in node, f"{label} missing field: {field}")
        node_id = node["id"]
        node_type = node["type"]
        require(isinstance(node_id, str) and node_id.strip(), f"{label} has invalid id")
        require(node_id not in node_lookup, f"duplicate skill-graph node id: {node_id}")
        require(node_type in node_types, f"{label} has invalid type: {node_type}")
        require(isinstance(node["label"], str) and node["label"].strip(), f"{label} has invalid label")
        require(isinstance(node["description"], str) and node["description"].strip(), f"{label} has invalid description")
        if "entrypoint" in node:
            require_existing_path_or_url(repo_root, node["entrypoint"], f"{label} entrypoint")
        if "lane_tags" in node:
            require_string_list(node["lane_tags"], f"{label} lane_tags")
        if node_type == "skill":
            require(node_id.startswith("skill:"), f"{label} must use a skill: prefix")
            skill_name = node_id.split(":", 1)[1]
            require(skill_name in skill_names, f"{label} references unknown skill {skill_name}")
            skill_node_names.add(skill_name)
        elif node_type == "platform":
            require(node_id.startswith("platform:"), f"{label} must use a platform: prefix")
            platform_id = node.get("platform_id")
            require(isinstance(platform_id, str) and platform_id in platform_ids, f"{label} has invalid platform_id")
            platform_node_ids.add(platform_id)
            if "platform_card" in node:
                require_existing_path_or_url(repo_root, node["platform_card"], f"{label} platform_card")
        elif node_type == "lane":
            require(node_id.startswith("lane:"), f"{label} must use a lane: prefix")
            lane_node_ids.add(node_id)
        elif node_type == "governance_tag":
            require(node_id.startswith("governance:"), f"{label} must use a governance: prefix")
        node_lookup[node_id] = node

    require(skill_node_names == set(skill_names), "skill graph must contain exactly one node for every repo skill")
    require(platform_node_ids == platform_ids, "skill graph must contain exactly one node for every platform card")
    require(lane_node_ids, "skill graph must contain at least one lane node")

    for node_id, node in node_lookup.items():
        for lane_tag in node.get("lane_tags", []):
            require(lane_tag in lane_node_ids, f"{node_id} references unknown lane tag {lane_tag}")

    expected_skill_platform_pairs = {
        (entry["skill"], entry["platform_id"])
        for entry in skill_map["skills"]
    }
    actual_skill_platform_pairs: set[tuple[str, str]] = set()
    lane_route_counts = {lane_id: 0 for lane_id in lane_node_ids}
    router_route_count = 0

    for index, edge in enumerate(edges):
        label = f"skill-graph edge {index}"
        require(isinstance(edge, dict), f"{label} must be an object")
        for field in edge_required:
            require(field in edge, f"{label} missing field: {field}")
        source = edge["source"]
        relation = edge["relation"]
        target = edge["target"]
        require(source in node_lookup, f"{label} references unknown source {source}")
        require(target in node_lookup, f"{label} references unknown target {target}")
        require(relation in edge_relations, f"{label} has invalid relation {relation}")
        require(isinstance(edge["rationale"], str) and edge["rationale"].strip(), f"{label} has invalid rationale")
        require_string_list(edge["evidence_refs"], f"{label} evidence_refs")
        for ref in edge["evidence_refs"]:
            require_existing_path_or_url(repo_root, ref, f"{label} evidence ref")

        source_type = node_lookup[source]["type"]
        target_type = node_lookup[target]["type"]

        if relation == "routes_to":
            require((source_type, target_type) in {("skill", "lane"), ("lane", "skill")}, f"{label} has invalid routes_to topology")
            if source == "skill:salmon-research-router-skill":
                router_route_count += 1
            if source_type == "lane":
                lane_route_counts[source] += 1
        elif relation in {"depends_on", "compose_with"}:
            require(source_type == "skill" and target_type == "skill", f"{label} must connect skill to skill")
        elif relation == "uses_platform":
            require(source_type == "skill" and target_type == "platform", f"{label} must connect skill to platform")
            actual_skill_platform_pairs.add((source.split(":", 1)[1], target.split(":", 1)[1]))
        elif relation == "constrained_by":
            require(source_type in {"skill", "platform", "lane"} and target_type == "governance_tag", f"{label} must point to a governance tag")

    require(router_route_count > 0, "skill graph must route from the router to at least one lane")
    require(all(count > 0 for count in lane_route_counts.values()), "every lane node must route to at least one skill")
    require(actual_skill_platform_pairs == expected_skill_platform_pairs, "skill graph uses_platform edges must match registry/skill-platform-map.json exactly")

    router_graph_ref = repo_root / "skills" / "salmon-research-router-skill" / "references" / "skill-graph-routing.md"
    require(router_graph_ref.exists(), "router graph routing reference is missing")
    router_skill_text = (repo_root / "skills" / "salmon-research-router-skill" / "SKILL.md").read_text(encoding="utf-8")
    require("skill-graph-routing.md" in router_skill_text, "router SKILL.md must link to the graph routing reference")

    return {
        "node_count": len(nodes),
        "edge_count": len(edges),
        "lane_count": len(lane_node_ids),
    }


def validate_regression_assets(repo_root: Path) -> dict:
    selector_script = repo_root / "scripts" / "skill_graph_selector.py"
    fixture_path = repo_root / "tests" / "fixtures" / "skill_graph_selector_cases.json"
    test_path = repo_root / "tests" / "test_skill_graph_selector.py"
    workflow_path = repo_root / ".github" / "workflows" / "scaffold-validation.yml"

    for path in (selector_script, fixture_path, test_path, workflow_path):
        require(path.exists(), f"regression asset missing: {path}")

    cases = load_json(fixture_path)
    require(isinstance(cases, list) and len(cases) >= 20, "selector fixture file must contain at least 20 cases")
    for index, case in enumerate(cases):
        label = f"selector fixture case {index}"
        require(isinstance(case, dict), f"{label} must be an object")
        require(isinstance(case.get("request"), str) and case["request"].strip(), f"{label} missing request")
        expected = case.get("expected")
        require(isinstance(expected, dict), f"{label} missing expected block")
        for field in ("seeded_lanes", "selected_skills", "blocked_skills", "unsupported_lanes", "reason_contains"):
            require(field in expected, f"{label} missing expected field {field}")
            require(isinstance(expected[field], list), f"{label} expected field {field} must be a list")

    workflow_text = workflow_path.read_text(encoding="utf-8")
    require("python3 scripts/validate_scaffold.py" in workflow_text, "CI workflow must run scaffold validation")
    require("python3 -m unittest discover -s tests -p 'test_*.py'" in workflow_text, "CI workflow must run unittest discovery")
    require(
        'SMN_PLUGIN_LIVE_ADAPTERS: "1"' in workflow_text and "test_package_adapters.py" in workflow_text,
        "CI workflow must run the live package-adapter tests against the pinned release",
    )

    return {
        "selector_fixture_case_count": len(cases),
        "ci_workflow": str(workflow_path),
    }


def validate_kb(repo_root: Path) -> dict:
    kb_root = repo_root / "kb"
    required_paths = [
        kb_root / "AGENTS.md",
        kb_root / "index.md",
        kb_root / "log.md",
        kb_root / "platforms",
        kb_root / "concepts",
        kb_root / "gaps",
        kb_root / "workflows",
    ]
    for path in required_paths:
        require(path.exists(), f"kb artifact missing: {path}")

    log_text = (kb_root / "log.md").read_text(encoding="utf-8")
    require(re.search(r"^## \[\d{4}-\d{2}-\d{2}\] ", log_text, flags=re.MULTILINE) is not None, "kb/log.md must contain timestamped entries")

    platform_pages = sorted((kb_root / "platforms").glob("*.md"))
    concept_pages = sorted((kb_root / "concepts").glob("*.md"))
    gap_pages = sorted((kb_root / "gaps").glob("*.md"))
    workflow_pages = sorted((kb_root / "workflows").glob("*.md"))
    require(platform_pages, "kb/platforms must contain pages")
    require(concept_pages, "kb/concepts must contain pages")
    require(gap_pages, "kb/gaps must contain pages")
    require(workflow_pages, "kb/workflows must contain pages")

    platform_registry_root = repo_root / "registry" / "platforms"
    for page in platform_pages:
        text = page.read_text(encoding="utf-8")
        match = re.search(r"\.\./\.\./registry/platforms/([a-z0-9-]+)\.json", text)
        require(match is not None, f"{page} must link to its platform card")
        require((platform_registry_root / f"{match.group(1)}.json").exists(), f"{page} links to missing platform card")

    for page in gap_pages:
        text = page.read_text(encoding="utf-8")
        has_reference = "../platforms/" in text or "../concepts/" in text
        require(has_reference, f"{page} must point to at least one platform page or concept page")

    return {
        "platform_page_count": len(platform_pages),
        "concept_page_count": len(concept_pages),
        "gap_page_count": len(gap_pages),
        "workflow_page_count": len(workflow_pages),
    }


def validate_gap_register(repo_root: Path, categories: list[str]) -> None:
    text = (repo_root / "docs" / "platform-gap-register.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    capture = False
    section_lines: list[str] = []
    for line in lines:
        if line.startswith("## Platform Capability Categories Referenced"):
            capture = True
            continue
        if capture and line.startswith("## "):
            break
        if capture:
            section_lines.append(line)
    referenced = re.findall(r"`([a-z_]+)`", "\n".join(section_lines))
    require(referenced, "docs/platform-gap-register.md must list normalized platform capability categories")
    require(set(referenced) == set(categories), "docs/platform-gap-register.md category list must match registry/vocab.json")


def fetch_json(url: str):
    req = request.Request(url, headers={"Accept": "application/json, application/ld+json;q=0.9"}, method="GET")
    with request.urlopen(req, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def check_ontology_surface(url: str, root_iri: str) -> dict:
    try:
        payload = fetch_json(url)
        require(isinstance(payload, list), f"{url} did not return a JSON-LD list")
        root = next(item for item in payload if isinstance(item, dict) and item.get("@id") == root_iri)
        version = None
        modified = None
        if "http://www.w3.org/2002/07/owl#versionInfo" in root:
            version = root["http://www.w3.org/2002/07/owl#versionInfo"][0]["@value"]
        if "http://purl.org/dc/terms/modified" in root:
            modified = root["http://purl.org/dc/terms/modified"][0]["@value"]
        return {"ok": True, "url": url, "version": version, "modified": modified}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}


def _version_key(tag: str) -> tuple[int, ...]:
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", tag)
    return tuple(int(part) for part in match.groups()) if match else ()


def check_package_tag(repository: str, pin: str) -> dict:
    """Does the pinned tag still exist upstream, and is there a newer one?

    `ok` is false only when the pinned tag is gone. A newer tag is reported as a
    drift warning, because moving the pin is a deliberate change, not a fix.
    """
    url = f"https://github.com/salmon-data-mobilization/{repository}.git"
    try:
        proc = subprocess.run(
            ["git", "ls-remote", "--tags", url],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "url": url, "error": str(exc)}
    if proc.returncode != 0:
        return {"ok": False, "url": url, "error": proc.stderr.strip() or "git ls-remote failed"}
    tags = {
        line.split("refs/tags/", 1)[1].removesuffix("^{}")
        for line in proc.stdout.splitlines()
        if "refs/tags/" in line
    }
    releases = sorted((tag for tag in tags if _version_key(tag)), key=_version_key)
    latest = releases[-1] if releases else None
    return {
        "ok": pin in tags,
        "url": url,
        "pinned": pin,
        "latest": latest,
        "newer_release": latest is not None and _version_key(latest) > _version_key(pin),
    }


def check_rmis_surface() -> dict:
    try:
        url = "https://www.rmis.org/include/rmis_announce.html"
        with request.urlopen(url, timeout=20) as response:
            html = response.read().decode("utf-8", errors="replace")
        version_match = re.search(r"Version\s+([0-9]+\.[0-9]+)\s+of the RMIS Database", html, flags=re.IGNORECASE)
        date_match = re.search(r"as of:\s*(.+?)\.", html, flags=re.IGNORECASE | re.DOTALL)
        effective_date = None
        if date_match:
            effective_date = re.sub(r"<[^>]+>", "", date_match.group(1))
            effective_date = " ".join(effective_date.split()) or None
        return {
            "ok": bool(version_match),
            "url": url,
            "version": version_match.group(1) if version_match else None,
            "effective_date": effective_date,
        }
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    skills_root = repo_root / "skills"

    manifest_stats = validate_manifests(repo_root)

    skill_names: list[str] = []
    python_files: list[Path] = []

    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if not skill_file.exists():
            raise SystemExit(f"missing SKILL.md in {skill_dir}")
        skill_names.append(skill_dir.name)
        for path in skill_dir.rglob("*.py"):
            python_files.append(path)

    for path in sorted((repo_root / "scripts").glob("*.py")):
        python_files.append(path)

    for path in python_files:
        py_compile.compile(str(path), doraise=True)

    frontmatter_stats = validate_skill_frontmatter(repo_root, skill_names)
    reference_stats = validate_skill_references(repo_root, skill_names)
    pin_stats = check_package_pins(repo_root)
    term_search_stats = check_no_local_term_search(repo_root)
    eval_stats = validate_evals(repo_root, skill_names)
    registry_stats = validate_platform_registry(repo_root, skill_names)
    skill_graph_stats = validate_skill_graph(repo_root, skill_names)
    regression_stats = validate_regression_assets(repo_root)
    kb_stats = validate_kb(repo_root)
    vocab = load_json(repo_root / "registry" / "vocab.json")
    validate_gap_register(repo_root, vocab["capability_categories"])

    watch_surface_checks = {
        "smn": check_ontology_surface(
            "https://salmon-data-mobilization.github.io/salmon-domain-ontology/smn.jsonld",
            "https://w3id.org/smn",
        ),
        "gcdfo": check_ontology_surface(
            "https://dfo-pacific-science.github.io/dfo-salmon-ontology/gcdfo.jsonld",
            "https://w3id.org/gcdfo/salmon",
        ),
        "metasalmon": check_package_tag("metasalmon", pin_stats["pin"]),
        "metasalmonpy": check_package_tag("metasalmonpy", pin_stats["pin"]),
        "rmis": check_rmis_surface(),
    }
    warnings = [
        f"watch surface {name} check failed"
        for name, detail in watch_surface_checks.items()
        if not detail.get("ok")
    ]
    warnings += [
        f"watch surface {name}: {detail['latest']} is newer than the pinned {detail['pinned']}"
        for name, detail in watch_surface_checks.items()
        if detail.get("newer_release")
    ]

    print(json.dumps({
        "ok": True,
        "manifests": manifest_stats,
        "skill_count": len(skill_names),
        "skills": skill_names,
        "python_files_compiled": len(python_files),
        "skill_frontmatter": frontmatter_stats,
        "skill_references": reference_stats,
        "package_pins": pin_stats,
        "term_search_guard": term_search_stats,
        "evals": eval_stats,
        "registry": registry_stats,
        "skill_graph": skill_graph_stats,
        "regression": regression_stats,
        "kb": kb_stats,
        "watch_surface_checks": watch_surface_checks,
        "warnings": warnings,
    }, indent=2))


if __name__ == "__main__":
    main()
