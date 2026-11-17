"""Selecciona dos modelos locales a partir de las pruebas iniciales."""

from __future__ import annotations


def developer_of(model_name: str) -> str:
    lowered = model_name.lower()
    if "qwen" in lowered:
        return "alibaba"
    if "llama" in lowered:
        return "meta"
    if "gemma" in lowered:
        return "google"
    if "mistral" in lowered or "ministral" in lowered:
        return "mistral"
    if lowered.startswith("phi"):
        return "microsoft"
    if "granite" in lowered:
        return "ibm"
    return "unknown"


def choose_models(rows: list[dict[str, object]], minimum_valid_rate: float = 0.5) -> dict[str, object]:
    """Selecciona dos modelos que cumplan los criterios y prioriza desarrolladores distintos."""
    fitting = [
        row
        for row in rows
        if row.get("fits") is True and float(row.get("valid_call_rate", 0)) >= minimum_valid_rate
    ]
    ranked = sorted(
        fitting,
        key=lambda row: (
            -float(row["valid_call_rate"]),
            -float(row.get("utility_rate", 0)),
            float(row.get("median_latency_ms", 10**9)),
        ),
    )
    chosen: list[dict[str, object]] = []
    seen: set[str] = set()
    for row in ranked:
        developer = str(row.get("developer") or developer_of(str(row["model"])))
        if developer in seen:
            continue
        chosen.append(row)
        seen.add(developer)
        if len(chosen) == 2:
            return {"models": [row["model"] for row in chosen], "same_developer": False, "rule": "two_developers"}
    if len(ranked) >= 2:
        fallback = ranked[:2]
        return {
            "models": [row["model"] for row in fallback],
            "same_developer": True,
            "rule": "sunday_same_developer",
        }
    return {"models": [row["model"] for row in ranked], "same_developer": True, "rule": "insufficient_models"}
