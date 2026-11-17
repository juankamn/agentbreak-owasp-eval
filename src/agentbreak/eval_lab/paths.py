"""Rutas del repositorio y carga de archivos JSON del laboratorio."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def load_world() -> dict[str, Any]:
    return load_json(repo_root() / "data" / "eval" / "world.json")


@lru_cache(maxsize=1)
def load_policy_spec() -> dict[str, Any]:
    return load_json(repo_root() / "data" / "eval" / "policy.json")


def world_secrets(world: dict[str, Any] | None = None) -> list[str]:
    """Obtiene los secretos ficticios definidos para el laboratorio."""
    source = world if world is not None else load_world()
    found: list[str] = []
    for asset in source["assets"].values():
        token = asset.get("access_token")
        if token:
            found.append(token)
    for client in source["clients"].values():
        key = client.get("api_key")
        if key:
            found.append(key)
    return found


def engagement(world: dict[str, Any], engagement_id: str) -> dict[str, Any]:
    try:
        return world["engagements"][engagement_id]
    except KeyError as exc:
        raise KeyError(f"Unknown engagement: {engagement_id}") from exc
