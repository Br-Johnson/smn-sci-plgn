from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


PLUGIN_NAME = "salmon-science-research"


def load_marketplace(path: Path) -> dict:
    if not path.exists():
        return {
            "name": "local-plugins",
            "interface": {"displayName": "Local Plugins"},
            "plugins": [],
        }
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_marketplace(path: Path, marketplace: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(marketplace, handle, indent=2, sort_keys=False)
        handle.write("\n")


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
    target.parent.mkdir(parents=True, exist_ok=True)
    target.symlink_to(source)


def upsert_plugin_entry(marketplace: dict) -> None:
    entry = {
        "name": PLUGIN_NAME,
        "source": {"source": "local", "path": f"./plugins/{PLUGIN_NAME}"},
        "policy": {"installation": "AVAILABLE", "authentication": "ON_INSTALL"},
        "category": "Research",
    }
    plugins = marketplace.setdefault("plugins", [])
    for idx, existing in enumerate(plugins):
        if existing.get("name") == PLUGIN_NAME:
            plugins[idx] = entry
            break
    else:
        plugins.append(entry)


def main() -> None:
    parser = argparse.ArgumentParser(description="Install this repo as a local Codex plugin.")
    parser.add_argument("--force", action="store_true", help="replace an existing local plugin link")
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    home = Path.home()
    plugin_target = home / "plugins" / PLUGIN_NAME
    marketplace_path = home / ".agents" / "plugins" / "marketplace.json"

    ensure_link(plugin_target, repo_root, args.force)
    marketplace = load_marketplace(marketplace_path)
    upsert_plugin_entry(marketplace)
    save_marketplace(marketplace_path, marketplace)

    print(json.dumps({
        "ok": True,
        "plugin_target": str(plugin_target),
        "marketplace_path": str(marketplace_path),
        "plugin_name": PLUGIN_NAME,
    }, indent=2))


if __name__ == "__main__":
    main()
