"""Carga el catálogo de casos. Las pruebas de selección de modelos están fuera de estas carpetas."""

from __future__ import annotations

from pathlib import Path

from agentbreak.eval_lab.paths import load_json, repo_root
from agentbreak.eval_lab.schemas import Template


def catalog_files() -> list[Path]:
    root = repo_root() / "catalog"
    files = sorted((root / "calibration").glob("*.json"))
    files.extend(sorted((root / "evaluation").glob("*.json")))
    return files


def load_catalog() -> list[Template]:
    return [Template.model_validate(load_json(path)) for path in catalog_files()]


def by_id(templates: list[Template]) -> dict[str, Template]:
    return {template.template_id: template for template in templates}
