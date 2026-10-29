"""Portable Codex/Claude entry point to the offline private bundle contract."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from workbench_project import main

if __name__ == "__main__":
    sys.exit(main())
