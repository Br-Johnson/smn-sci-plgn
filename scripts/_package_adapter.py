"""Shared plumbing for the plugin's two package adapters.

``skills/salmon-terms/scripts/salmon_terms.py`` and
``skills/metasalmon-skill/scripts/metasalmon_api.py`` call the released
metasalmonpy package and hand back what it returns. This module holds the parts
they share: importing the package, describing the runtime, turning the
package's pandas objects into JSON-ready values, and recording the warnings the
package raises.

It holds no salmon-domain logic and must not grow any. Which sources to search,
how to rank or filter terms, and what makes a package valid all belong to
metasalmon and metasalmonpy; ``check_no_local_term_search()`` in
``scripts/validate_scaffold.py`` fails the build if a skill script starts doing
that work itself.

Stdlib only at import time, so a plain ``python3`` run without the package can
still report the problem as JSON rather than a traceback.
"""

from __future__ import annotations

import contextlib
import json
import sys
import warnings
from typing import Any, Iterator

from _common import result_error, write_raw

# The one release this plugin is pinned to, for both packages.
#
# The Python requirement is also written in the PEP 723 block at the top of each
# adapter script, because that block is static TOML and cannot import this
# constant. `check_package_pins()` in scripts/validate_scaffold.py fails when any
# copy of either pin disagrees with the others, so moving the pin means editing
# every copy in one change, which is the point.
METASALMONPY_VERSION = "0.5.0"
METASALMONPY_REQUIREMENT = (
    "metasalmonpy @ git+https://github.com/salmon-data-mobilization/metasalmonpy@v0.5.0"
)
METASALMON_R_REF = "salmon-data-mobilization/metasalmon@v0.5.0"


class InvalidRequest(ValueError):
    """Malformed adapter controls, distinct from a package validation error."""


def request_bool(payload: dict[str, Any], key: str, default: bool) -> bool:
    """JSON controls must be booleans: the text 'false' is not true."""
    value = payload.get(key, default)
    if not isinstance(value, bool):
        raise InvalidRequest(f"{key} must be a JSON boolean")
    return value


def request_string(
    payload: dict[str, Any], key: str, default: str | None = None
) -> str | None:
    """Do not turn arrays or objects into plausible paths, queries, or roles."""
    value = payload.get(key, default)
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidRequest(f"{key} must be a string")
    return value.strip()


def request_string_list(payload: dict[str, Any], key: str) -> list[str] | None:
    """A list is passed through; a single string must not become characters."""
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise InvalidRequest(f"{key} must be an array of non-empty strings")
    return value


def request_positive_int(payload: dict[str, Any], key: str, default: int) -> int:
    value = payload.get(key, default)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise InvalidRequest(f"{key} must be a positive JSON integer")
    return value


def validate_common_request(payload: dict[str, Any], default_action: str) -> None:
    """Reject malformed controls before importing or calling the package."""
    if not request_string(payload, "action", default_action):
        raise InvalidRequest("action must be a non-empty string")
    request_bool(payload, "save_raw", False)
    path = request_string(payload, "raw_output_path")
    if path is not None and not path:
        raise InvalidRequest("raw_output_path must be a non-empty string")


def save_response(
    response: dict[str, Any], payload: dict[str, Any], default_name: str
) -> None:
    """Keep one JSON response, with the package findings, if saving fails."""
    if not response.get("ok"):
        return
    try:
        response["raw_output_path"] = write_raw(
            response,
            requested=request_bool(payload, "save_raw", False),
            raw_output_path=request_string(payload, "raw_output_path"),
            default_name=default_name,
        )
    except (OSError, TypeError, ValueError) as exc:
        response["ok"] = False
        response["raw_output_path"] = None
        response["error"] = {"code": "raw_output_failed", "message": str(exc)}


def import_metasalmonpy() -> Any | None:
    """Return the metasalmonpy module, or ``None`` when it cannot be imported."""
    try:
        import metasalmonpy  # noqa: PLC0415 - imported late on purpose, see module docstring
    except ImportError:
        return None
    return metasalmonpy


def missing_package_error(script_path: str) -> dict[str, Any]:
    """The JSON error a plain ``python3`` run gets when metasalmonpy is absent."""
    return result_error(
        "missing_package",
        "metasalmonpy is not importable in this Python environment.",
        hint=(
            f'Run the script with uv instead: uv run "{script_path}". uv reads the '
            "script's inline metadata and installs the pinned release into a cached, "
            "isolated environment."
        ),
        pinned_requirement=METASALMONPY_REQUIREMENT,
    )


def runtime_info(module: Any) -> dict[str, Any]:
    """Which Python and which metasalmonpy actually produced a response."""
    version = getattr(module, "__version__", None)
    return {
        "python_version": sys.version.split()[0],
        "package": "metasalmonpy",
        "package_version": version,
        "pinned_version": METASALMONPY_VERSION,
        "pinned_requirement": METASALMONPY_REQUIREMENT,
        "matches_pin": version == METASALMONPY_VERSION,
    }


def pin_warnings(runtime: dict[str, Any]) -> list[str]:
    """A warning when the imported package is not the pinned release."""
    if runtime.get("matches_pin"):
        return []
    return [
        f"metasalmonpy {runtime.get('package_version')} is installed, but this plugin is "
        f"pinned to {METASALMONPY_VERSION}. Run the adapter with `uv run` to use the "
        "pinned release."
    ]


def to_json_value(value: Any) -> Any:
    """A JSON-ready copy of a pandas object; other values pass through.

    DataFrames become a list of row objects and Series an object keyed by index.
    pandas' own ``to_json`` does the conversion, so missing values become
    ``null`` and timestamps become ISO 8601 text exactly as pandas renders them.
    """
    if value is None:
        return None
    if hasattr(value, "to_json") and hasattr(value, "columns"):
        return json.loads(value.to_json(orient="records", date_format="iso"))
    if hasattr(value, "to_json") and hasattr(value, "index"):
        return json.loads(value.to_json(date_format="iso"))
    if isinstance(value, dict):
        return {str(key): to_json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_json_value(item) for item in value]
    return value


@contextlib.contextmanager
def captured_warnings() -> Iterator[list[str]]:
    """Collect the package's warnings as text instead of printing them.

    The list is filled when the ``with`` block exits, including when it exits
    with an exception, so a failed call still reports what the package said
    before it failed.
    """
    messages: list[str] = []
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        try:
            yield messages
        finally:
            messages.extend(str(item.message) for item in caught)
