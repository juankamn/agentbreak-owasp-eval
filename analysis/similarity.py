"""Token overlap between calibration and evaluation attack payloads.

The shared legitimate sentence is removed first. The audit asks whether an attack
mechanism leaked from calibration into evaluation, not whether both ask for the runbook.
"""

from __future__ import annotations

import re

from agentbreak.eval_lab.schemas import Template

_STOP = {
    "a",
    "al",
    "de",
    "del",
    "el",
    "en",
    "la",
    "las",
    "lo",
    "los",
    "que",
    "y",
    "un",
    "una",
    "por",
    "con",
    "sin",
    "para",
    "su",
    "se",
    "es",
    "o",
    "the",
    "on",
    "with",
}


def tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9_\-]+", text.lower())
    return {word for word in words if word not in _STOP and len(word) > 2}


def jaccard(left: str, right: str) -> float:
    a = tokens(left)
    b = tokens(right)
    if not a and not b:
        return 0.0
    return len(a & b) / len(a | b)


def attack_payload(template: Template) -> str:
    if template.a1 is None:
        return ""
    if template.surface == "user_message":
        return template.a1.user_message.replace(template.a0.user_message, " ")
    if template.surface == "retrieved_document":
        a0_ids = {doc.doc_id for doc in template.a0.documents}
        return " ".join(doc.body for doc in template.a1.documents if doc.doc_id not in a0_ids)
    if template.surface == "tool_output":
        chunks = []
        for asset_id, note in template.a1.scan_notes.items():
            chunks.append(note.replace(template.a0.scan_notes.get(asset_id, ""), " "))
        return " ".join(chunks)
    return ""


def max_cross_partition_similarity(templates: list[Template]) -> tuple[float, tuple[str, str] | None]:
    calibration = [item for item in templates if item.partition == "calibration" and item.a1 is not None]
    evaluation = [item for item in templates if item.partition == "evaluation" and item.a1 is not None]
    best = 0.0
    pair: tuple[str, str] | None = None
    for left in calibration:
        left_text = attack_payload(left)
        for right in evaluation:
            score = jaccard(left_text, attack_payload(right))
            if score > best:
                best = score
                pair = (left.template_id, right.template_id)
    return best, pair
