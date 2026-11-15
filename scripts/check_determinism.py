"""Replay 5 percent of finished traces with the same seed. Does not append to traces.jsonl."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRACES = ROOT / "runs" / "traces.jsonl"
OUT = ROOT / "manifest" / "determinism.json"
FRACTION = 0.05


def _fingerprint(record: object) -> dict[str, object]:
    steps = record.steps  # type: ignore[attr-defined]
    oracle = record.oracle  # type: ignore[attr-defined]
    return {
        "calls": [
            {
                "name": step.name,
                "arguments": step.arguments,
                "executed": step.executed,
                "blocked": step.blocked,
            }
            for step in steps
        ],
        "raw_answer": record.raw_answer,  # type: ignore[attr-defined]
        "delivered_answer": record.delivered_answer,  # type: ignore[attr-defined]
        "output_blocked": record.output_blocked,  # type: ignore[attr-defined]
        "violation": oracle.violation,
        "violation_kinds": list(oracle.violation_kinds),
        "utility": oracle.legitimate_completion,
        "undue_block": oracle.undue_block,
        "technical_failure": oracle.technical_failure,
    }


def _load() -> list[object]:
    from agentbreak.eval_lab.schemas import RunRecord

    records: list[object] = []
    for line in TRACES.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(RunRecord.model_validate_json(line))
    return records


def main() -> None:
    sys.path.insert(0, str(ROOT / "src"))
    sys.path.insert(0, str(ROOT))
    from agentbreak.eval_lab.catalog_io import by_id, load_catalog
    from agentbreak.eval_lab.llm_adapter import OllamaToolModel
    from agentbreak.eval_lab.paths import load_policy_spec, load_world
    from agentbreak.eval_lab.runner import MASTER_SEED, RunConfig, run_case

    records = _load()
    ordered = sorted(
        records,
        key=lambda row: (row.template_id, row.variant, row.model, row.policy, row.repetition),  # type: ignore[attr-defined]
    )
    size = round(len(ordered) * FRACTION)
    picked = random.Random(MASTER_SEED).sample(ordered, size)
    picked.sort(key=lambda row: (row.model, row.template_id, row.variant, row.policy, row.repetition))  # type: ignore[attr-defined]
    catalog = by_id([item for item in load_catalog() if item.partition == "evaluation"])
    world = load_world()
    spec = load_policy_spec()
    adapters: dict[str, OllamaToolModel] = {}
    identical = 0
    same_decision = 0
    by_model: dict[str, dict[str, int]] = {}
    mismatches: list[dict[str, str]] = []
    for index, original in enumerate(picked, start=1):
        adapter = adapters.setdefault(original.model, OllamaToolModel(original.model))  # type: ignore[attr-defined]
        config = RunConfig(
            temperature=original.temperature,  # type: ignore[attr-defined]
            prompt_variant=original.prompt_variant,  # type: ignore[attr-defined]
            tool_detail=original.tool_detail,  # type: ignore[attr-defined]
        )
        replay = run_case(
            catalog[original.template_id],  # type: ignore[attr-defined]
            original.variant,  # type: ignore[attr-defined]
            original.policy,  # type: ignore[attr-defined]
            adapter,
            original.model,  # type: ignore[attr-defined]
            world,
            spec,
            config,
            repetition=original.repetition,  # type: ignore[attr-defined]
            seed=original.seed,  # type: ignore[attr-defined]
            model_digest=original.model_digest,  # type: ignore[attr-defined]
        )
        left = _fingerprint(original)
        right = _fingerprint(replay)
        model_row = by_model.setdefault(original.model, {"n": 0, "identical": 0, "same_decision": 0})  # type: ignore[attr-defined]
        model_row["n"] += 1
        decision_keys = ("calls", "violation", "violation_kinds", "utility", "undue_block", "technical_failure")
        decisions_match = all(left[key] == right[key] for key in decision_keys)
        if decisions_match:
            same_decision += 1
            model_row["same_decision"] += 1
        if left == right:
            identical += 1
            model_row["identical"] += 1
        elif len(mismatches) < 12:
            mismatches.append(
                {
                    "template_id": original.template_id,  # type: ignore[attr-defined]
                    "variant": original.variant,  # type: ignore[attr-defined]
                    "model": original.model,  # type: ignore[attr-defined]
                    "policy": original.policy,  # type: ignore[attr-defined]
                    "repetition": str(original.repetition),  # type: ignore[attr-defined]
                }
            )
        print(
            f"{index}/{size} {original.template_id} {original.variant} {original.policy} "  # type: ignore[attr-defined]
            f"{original.model} identical={left == right}",  # type: ignore[attr-defined]
            flush=True,
        )
    payload = {
        "fraction": FRACTION,
        "sample_seed": MASTER_SEED,
        "n": size,
        "identical_traces": identical,
        "same_decision": same_decision,
        "by_model": by_model,
        "mismatch_examples": mismatches,
        "note": (
            "Latency is ignored. A trace matches when the tool sequence, the answer, "
            "and the oracle flags match. The replay is not appended to runs/traces.jsonl."
        ),
    }
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"n": size, "identical_traces": identical, "same_decision": same_decision}))


if __name__ == "__main__":
    main()
