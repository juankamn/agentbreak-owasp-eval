"""Guarda trazas en JSONL e identifica ejecuciones ya registradas."""

from __future__ import annotations

import json
from pathlib import Path

from agentbreak.eval_lab.schemas import RunRecord


def run_key(record: RunRecord) -> tuple[str, str, str, str, int, str]:
    return (
        record.template_id,
        record.variant,
        record.model,
        record.policy,
        record.repetition,
        record.config_id,
    )


def load_records(path: Path) -> list[RunRecord]:
    if not path.exists():
        return []
    records: list[RunRecord] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(RunRecord.model_validate_json(line))
    return records


def completed_keys(path: Path) -> set[tuple[str, str, str, str, int, str]]:
    return {run_key(record) for record in load_records(path)}


def append_record(path: Path, record: RunRecord) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record.model_dump(), ensure_ascii=False) + "\n")
        handle.flush()
