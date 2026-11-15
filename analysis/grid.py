"""Pick the calibration configuration by clean-task utility, never by attack resistance."""

from __future__ import annotations

from collections import defaultdict

from agentbreak.eval_lab.schemas import RunRecord


def select_config(records: list[RunRecord]) -> dict[str, object]:
    clean = [record for record in records if record.variant == "A0" and record.policy == "C0"]
    by_config: dict[str, dict[str, list[RunRecord]]] = defaultdict(lambda: defaultdict(list))
    for record in clean:
        by_config[record.config_id][record.model].append(record)
    best_id = ""
    best_key: tuple[float, float] | None = None
    details: dict[str, dict[str, float]] = {}
    for config_id, by_model in by_config.items():
        if len(by_model) < 2:
            continue
        utilities = []
        latencies = []
        per_model: dict[str, float] = {}
        for model, rows in by_model.items():
            utility = sum(1 for row in rows if row.oracle.legitimate_completion) / len(rows)
            per_model[model] = utility
            utilities.append(utility)
            latencies.extend(row.latency_ms for row in rows)
        details[config_id] = per_model
        minimum = min(utilities)
        median_latency = sorted(latencies)[len(latencies) // 2]
        key = (minimum, -median_latency)
        if best_key is None or key > best_key:
            best_key = key
            best_id = config_id
    if not best_id:
        return {"config_id": None, "label": "no estimable", "by_model": {}}
    return {"config_id": best_id, "label": "selected_by_min_utility", "by_model": details[best_id]}
