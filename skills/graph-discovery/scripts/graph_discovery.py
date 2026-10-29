# /// script
# requires-python = ">=3.13"
# dependencies = [
#   "smn-data-graph @ git+https://github.com/salmon-data-mobilization/smn-data-graph@4036bad502ac0319e1207f233386ac7f766de2f6#subdirectory=python",
# ]
# ///
"""Thin local read-only discovery; admission and permissions belong to the caller."""
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
from _common import emit, result_error  # noqa: E402

GRAPH_COMMIT = "4036bad502ac0319e1207f233386ac7f766de2f6"
GRAPH_REQUIREMENT = (
    "smn-data-graph @ git+https://github.com/salmon-data-mobilization/"
    f"smn-data-graph@{GRAPH_COMMIT}#subdirectory=python"
)
# SHA-256 of the sorted compact JSON {relative Python path: file SHA-256}
# for python/src/salmongraph at GRAPH_COMMIT. This also checks local wheels
# whose distribution version alone cannot establish the reviewed source.
GRAPH_SOURCE_DIGEST = "70b0ed91edb72a92f8b5e413909599a1c444de65fba864e155dcda353935308f"
MAX_INPUT_BYTES = 65_536


class Refusal(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def graph_runtime():
    try:
        distribution = importlib.metadata.distribution("smn-data-graph")
        import salmongraph
        from salmongraph import config, discovery
    except (ImportError, importlib.metadata.PackageNotFoundError):
        raise Refusal("missing_package", "Use uv run with this script's pinned Python 3.13+ graph dependency, or an isolated matching wheel environment.") from None
    root = Path(salmongraph.__file__).resolve().parent
    hashes = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(root.rglob("*.py"))}
    digest = hashlib.sha256(json.dumps(hashes, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    runtime = {"package": "smn-data-graph", "package_version": distribution.version,
        "source_commit": GRAPH_COMMIT, "pinned_requirement": GRAPH_REQUIREMENT,
        "source_digest": digest, "matches_pin": distribution.version == "0.1.0" and digest == GRAPH_SOURCE_DIGEST,
        "pyoxigraph_version": importlib.metadata.version("pyoxigraph"),
        "python_version": sys.version.split()[0],
        "namespace": {"base": config.current().base, "profile_base": config.current().profile_base,
            "sdpv": config.current().sdpv}}
    if not runtime["matches_pin"] or runtime["pyoxigraph_version"] != "0.5.13":
        raise Refusal("runtime_mismatch", "Installed graph source or PyOxigraph differs from the reviewed immutable pin; no query ran.")
    return discovery, runtime


def read_binding(value: dict) -> tuple[Path, list[str], dict]:
    selected = value.get("binding_file") or os.environ.get("SALMON_GRAPH_BINDING")
    if not isinstance(selected, str) or not selected:
        raise Refusal("binding_required", "Select a local admitted store/project binding with binding_file or SALMON_GRAPH_BINDING.")
    path = Path(selected).expanduser().resolve()
    try:
        if path.stat().st_size > MAX_INPUT_BYTES:
            raise Refusal("invalid_binding", "The local binding exceeds 65536 bytes.")
        raw = path.read_bytes()
        binding = json.loads(raw)
    except (OSError, ValueError):
        raise Refusal("binding_unavailable", "The selected local binding is absent, unreadable or invalid JSON.") from None
    required = {"store_dir", "project_datasets", "admitted", "read_authorized"}
    if not isinstance(binding, dict) or set(binding) != required:
        raise Refusal("invalid_binding", "Binding requires exactly store_dir, project_datasets, admitted and read_authorized.")
    if binding["admitted"] is not True or binding["read_authorized"] is not True:
        raise Refusal("access_unavailable", "Caller confirmation of store admission and current read permission is required.")
    datasets = binding["project_datasets"]
    if (not isinstance(datasets, list) or not 1 <= len(datasets) <= 128
            or any(not isinstance(iri, str) or not iri for iri in datasets)):
        raise Refusal("invalid_binding", "Binding project_datasets must contain 1..128 absolute dataset IRIs.")
    store = binding["store_dir"]
    if not isinstance(store, str) or not store or "://" in store:
        raise Refusal("invalid_binding", "Binding store_dir must select an existing local directory.")
    target = Path(store).expanduser()
    target = (target if target.is_absolute() else path.parent / target).resolve()
    if not target.is_dir():
        raise Refusal("store_unavailable", "The bound local store directory is unavailable; no store is created or acquired.")
    return target, datasets, {
        "sha256": hashlib.sha256(raw).hexdigest(),
        "permission_basis": "caller_supplied_admission_and_read_authorization_not_independent_acl_proof",
        "project_datasets": datasets,
    }


def main() -> None:
    try:
        raw = sys.stdin.buffer.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise Refusal("invalid_input", "Request exceeds 65536 bytes.")
        try:
            value = json.loads(raw)
        except ValueError:
            raise Refusal("invalid_input", "Expected one JSON object on stdin.") from None
        if not isinstance(value, dict):
            raise Refusal("invalid_input", "Expected one JSON object on stdin.")
        action = value.get("action", "discover")
        fields = {"action"} if action == "runtime" else {
            "action", "binding_file", "families", "graphs", "include_pending", "limit", "relationship_kinds"}
        if set(value) - fields:
            raise Refusal("invalid_input", "Unknown request field; store and project datasets belong only in the local binding.")
        if action not in ("runtime", "discover"):
            raise Refusal("unsupported_action", "Supported actions are runtime and discover.")
        kinds = value.get("relationship_kinds")
        if isinstance(kinds, list) and any(kind in ("scoped_mapping", "suggestion") for kind in kinds):
            if value.get("include_pending") is not True:
                raise Refusal("pending_opt_in_required", "Saved scoped_mapping/suggestion discovery requires include_pending=true; it never grants shared acceptance or equivalence.")
        # Establish caller scope before importing the graph engine or opening a store.
        bound = read_binding(value) if action == "discover" else None
        discovery, runtime = graph_runtime()
        if action == "runtime":
            emit({"ok": True, "runtime": runtime})
            return
        store, datasets, binding = bound
        kwargs = {key: value[key] for key in ("families", "graphs", "include_pending", "limit", "relationship_kinds") if key in value}
        try:
            result = discovery.discover(store, project_datasets=datasets, **kwargs)
        except (ValueError, TypeError):
            raise Refusal("invalid_query_or_store", "The graph library refused the query or could not open the existing read-only store; check documented controls, dataset IRIs and namespace configuration.") from None
        answer = {"ok": result["query_status"] == "complete", "runtime": runtime, "binding": binding, "result": result}
        if not answer["ok"]:
            answer["error"] = {"code": "incomplete_evidence", "message": "The upstream graph query refused incomplete evidence; no usable discovery paths are asserted."}
        emit(answer)
    except Refusal as exc:
        emit(result_error(exc.code, str(exc)))
    except Exception:
        emit(result_error("graph_unavailable", "Local graph discovery failed; no fallback, acquisition, mutation or source-derived diagnostics are emitted."))


if __name__ == "__main__":
    main()
