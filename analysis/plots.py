"""Figures for a finished trace file. An empty file produces no numbers."""

from __future__ import annotations

from pathlib import Path

from agentbreak.eval_lab.schemas import RunRecord


def write_asr_bars(records: list[RunRecord], path: Path) -> bool:
    attacks = [record for record in records if record.variant == "A1" and not record.oracle.technical_failure]
    if not attacks:
        return False
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    policies = ["C0", "C1"]
    rates = []
    for policy in policies:
        rows = [record for record in attacks if record.policy == policy]
        rates.append(sum(1 for record in rows if record.oracle.violation) / len(rows) if rows else 0.0)
    path.parent.mkdir(parents=True, exist_ok=True)
    figure, axis = plt.subplots(figsize=(4.5, 3.2))
    axis.bar(policies, rates, color=["#4C78A8", "#F58518"])
    axis.set_ylim(0, 1)
    axis.set_ylabel("ASR")
    axis.set_title("ASR por corrida en A1")
    figure.tight_layout()
    figure.savefig(path, dpi=120)
    plt.close(figure)
    return True
