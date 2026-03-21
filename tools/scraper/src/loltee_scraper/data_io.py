from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def load_existing_dataset(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None

    try:
        with path.open(encoding="utf-8") as handle:
            payload = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"[WARN] Failed to load existing dataset {path}: {exc}")
        return None

    return payload if isinstance(payload, dict) else None


def write_json(path: Path, payload: Dict[str, Any]) -> None:
    ensure_parent_dir(path)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)


def build_last_success_path(path: Path) -> Path:
    return path.with_name(f"{path.stem}.last_success{path.suffix}")


def update_last_success_backup(path: Path, payload: Dict[str, Any]) -> None:
    backup_path = build_last_success_path(path)
    write_json(backup_path, payload)
    print(f"[INFO] Updated last-success backup: {backup_path}")


def is_partial_dataset(payload: Optional[Dict[str, Any]]) -> bool:
    if not isinstance(payload, dict):
        return False

    meta = payload.get("meta")
    if not isinstance(meta, dict):
        return False

    return bool(meta.get("is_partial"))


def count_champions(data: Any) -> int:
    if not isinstance(data, dict):
        return 0

    return sum(len(champions) for champions in data.values() if isinstance(champions, list))
