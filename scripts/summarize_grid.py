"""Write the eight-config utility table. Not an attack-resistance ranking."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path

from agentbreak.eval_lab.telemetry_jsonl import load_records

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    records = load_records(ROOT / "runs" / "grid120.jsonl")
    grouped: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for record in records:
        grouped[record.config_id][record.model].append(record)
    rows = []
    for config_id, by_model in sorted(grouped.items()):
        per_model = {}
        latencies: list[float] = []
        for model, model_rows in by_model.items():
            utility = sum(1 for row in model_rows if row.oracle.legitimate_completion) / len(model_rows)
            per_model[model] = {
                "n": len(model_rows),
                "utility": utility,
                "violation_rate": sum(1 for row in model_rows if row.oracle.violation) / len(model_rows),
            }
            latencies.extend(row.latency_ms for row in model_rows)
        latencies.sort()
        rows.append(
            {
                "config_id": config_id,
                "min_utility": min(item["utility"] for item in per_model.values()),
                "median_latency_ms": latencies[len(latencies) // 2],
                "by_model": per_model,
            }
        )
    rows.sort(key=lambda item: (-item["min_utility"], item["median_latency_ms"]))
    destination = ROOT / "manifest" / "grid120_summary.json"
    destination.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print(f"{row['config_id']} min={row['min_utility']:.3f} med_ms={row['median_latency_ms']:.0f}")


if __name__ == "__main__":
    main()
