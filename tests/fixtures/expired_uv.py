#!/usr/bin/env python3
"""A local uv process fixture; the SDK itself is real and already installed."""
import json
import os
from pathlib import Path
import sys

args = sys.argv[1:]
if args[:4] != ["run", "-q", "--no-project", "--with"] or args[5] != "python":
    raise SystemExit("unexpected uv fixture command")
child_args = args[6:]
log = Path(os.environ["SMN_TEST_UV_LOG"])
if child_args == ["-c", "import sys; print(sys.executable)"]:
    # Model a runtime that is valid only while uv owns the process. Returning
    # its path cannot extend that lifetime into the next invocation.
    temporary_python = log.parent / "expired-python"
    temporary_python.write_text("temporary runtime\n")
    print(temporary_python)
    temporary_python.unlink()
    mode = "expired-path"
else:
    mode = "execute"
with log.open("a") as handle:
    handle.write(json.dumps({"mode": mode}) + "\n")
if mode == "execute":
    python = os.environ["SMN_TEST_ACTIVE_PYTHON"]
    os.execv(python, [python, *child_args])
