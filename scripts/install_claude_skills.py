from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


def ensure_link(target: Path, source: Path, force: bool) -> None:
    if target.is_symlink() and target.resolve() == source.resolve():
        return
    if target.exists() or target.is_symlink():
        if not force:
            raise SystemExit(f"{target} already exists; rerun with --force to replace it")
        if target.is_dir() and not target.is_symlink():
            shutil.rmtree(target)
        else:
            target.unlink()
    target.symlink_to(source)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install the repo skills into ~/.claude/skills.")
    parser.add_argument("--force", action="store_true", help="replace existing skill links")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    skills_root = repo_root / "skills"
    claude_root = Path.home() / ".claude" / "skills"
    claude_root.mkdir(parents=True, exist_ok=True)

    installed: list[str] = []
    for skill_dir in sorted(skills_root.iterdir()):
        if not skill_dir.is_dir():
            continue
        if not (skill_dir / "SKILL.md").exists():
            continue
        target = claude_root / skill_dir.name
        ensure_link(target, skill_dir, args.force)
        installed.append(skill_dir.name)

    print(json.dumps({"ok": True, "installed_skills": installed}, indent=2))


if __name__ == "__main__":
    main()
