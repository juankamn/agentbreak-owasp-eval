"""Calibration diagnostics. These numbers are not the confirmatory estimate."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _rate(rows, predicate) -> float | None:
    usable = [row for row in rows if not row.oracle.technical_failure]
    if not usable:
        return None
    return sum(1 for row in usable if predicate(row)) / len(usable)


def main() -> None:
    sys.path.insert(0, str(ROOT))
    sys.path.insert(0, str(ROOT / "src"))
    from agentbreak.eval_lab.telemetry_jsonl import load_records
    from analysis.metrics import paired_asr

    records = load_records(ROOT / "runs" / "calibration.jsonl")
    groups: dict[tuple[str, str, str], list] = defaultdict(list)
    for record in records:
        groups[(record.model, record.variant, record.policy)].append(record)
    cells = []
    for key in sorted(groups):
        rows = groups[key]
        cells.append(
            {
                "model": key[0],
                "variant": key[1],
                "policy": key[2],
                "n": len(rows),
                "technical": sum(1 for row in rows if row.oracle.technical_failure),
                "violation": _rate(rows, lambda row: row.oracle.violation),
                "utility": _rate(rows, lambda row: row.oracle.legitimate_completion),
                "undue_block": _rate(rows, lambda row: row.oracle.undue_block),
            }
        )
    c1_violations = Counter()
    undue_templates = Counter()
    for record in records:
        if record.oracle.technical_failure:
            continue
        if record.variant == "A1" and record.policy == "C1" and record.oracle.violation:
            c1_violations[f"{record.template_id}|{','.join(record.oracle.violation_kinds)}"] += 1
        if record.variant == "A0" and record.policy == "C1" and record.oracle.undue_block:
            undue_templates[record.template_id] += 1
    estimate = paired_asr(records)
    interval = None if estimate.interval is None else [estimate.interval.low, estimate.interval.high]
    payload = {
        "runs": len(records),
        "cells": cells,
        "calibration_paired_asr": {
            "asr_c0": estimate.asr_c0,
            "asr_c1": estimate.asr_c1,
            "difference": estimate.difference,
            "interval": interval,
            "templates": estimate.templates,
            "label": estimate.label,
        },
        "c1_attack_violations": c1_violations.most_common(),
        "c1_clean_undue_blocks": undue_templates.most_common(),
    }
    destination = ROOT / "manifest" / "calibration_summary.json"
    destination.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
