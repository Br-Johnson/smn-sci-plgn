from __future__ import annotations

import json
import py_compile
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    manifest_path = repo_root / ".codex-plugin" / "plugin.json"
    skills_root = repo_root / "skills"

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    required_top = ["name", "version", "description", "skills", "interface"]
    missing = [key for key in required_top if key not in manifest]
    if missing:
        raise SystemExit(f"plugin manifest missing keys: {missing}")

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

    print(json.dumps({
        "ok": True,
        "manifest": str(manifest_path),
        "skill_count": len(skill_names),
        "skills": skill_names,
        "python_files_compiled": len(python_files),
    }, indent=2))


if __name__ == "__main__":
    main()
