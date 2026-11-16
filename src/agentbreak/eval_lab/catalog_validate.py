"""Structural checks for the 120-template bank. They do not score model behavior."""

from __future__ import annotations

from agentbreak.eval_lab.catalog_plan import (
    CALIBRATION_FAMILIES,
    EVALUATION_FAMILIES,
    FAMILY_SURFACE,
)
from agentbreak.eval_lab.schemas import Template


class CatalogError(ValueError):
    pass


def validate_templates(templates: list[Template]) -> None:
    errors: list[str] = []
    if len(templates) != 120:
        errors.append(f"expected 120 templates, found {len(templates)}")
    ids = [item.template_id for item in templates]
    if len(ids) != len(set(ids)):
        errors.append("duplicated template ids")
    for stratum in ("LLM01", "LLM02", "LLM03", "BENIGN"):
        count = sum(1 for item in templates if item.stratum == stratum)
        if count != 30:
            errors.append(f"{stratum} has {count} templates, expected 30")
    calib = [item for item in templates if item.partition == "calibration"]
    evaluation = [item for item in templates if item.partition == "evaluation"]
    if len(calib) != 40 or len(evaluation) != 80:
        errors.append(f"partition sizes {len(calib)} and {len(evaluation)}")
    _families(errors, calib, CALIBRATION_FAMILIES)
    _families(errors, evaluation, EVALUATION_FAMILIES)
    calib_names = {item.family_id for item in calib}
    eval_names = {item.family_id for item in evaluation}
    overlap = calib_names & eval_names
    if overlap:
        errors.append("family in both partitions: " + ", ".join(sorted(overlap)))
    _surfaces(errors, evaluation)
    for item in templates:
        _payload(errors, item)
    if errors:
        raise CatalogError("\n".join(errors))


def _families(errors: list[str], templates: list[Template], expected: dict[str, list[str]]) -> None:
    found: dict[str, list[str]] = {}
    for item in templates:
        found.setdefault(item.family_id, []).append(item.template_id)
    expected_names = {name for names in expected.values() for name in names}
    if set(found) != expected_names:
        errors.append(f"families {sorted(found)} != {sorted(expected_names)}")
    for name, members in found.items():
        if len(members) != 5:
            errors.append(f"{name} has {len(members)} templates")
        if FAMILY_SURFACE.get(name) != templates_surface(templates, name):
            errors.append(f"{name} surface does not match the plan")


def templates_surface(templates: list[Template], family_id: str) -> str | None:
    surfaces = {item.surface for item in templates if item.family_id == family_id}
    if len(surfaces) != 1:
        return None
    return surfaces.pop()


def _surfaces(errors: list[str], evaluation: list[Template]) -> None:
    attacks = [item for item in evaluation if item.stratum != "BENIGN"]
    for surface in ("user_message", "retrieved_document", "tool_output"):
        count = sum(1 for item in attacks if item.surface == surface)
        if count != 20:
            errors.append(f"evaluation surface {surface} has {count} attack templates")


def _payload(errors: list[str], template: Template) -> None:
    if template.stratum == "BENIGN":
        return
    marker = template.payload_marker
    a0 = _blob(template, "A0")
    a1 = _blob(template, "A1")
    if marker in a0:
        errors.append(f"{template.template_id} A0 contains the payload marker")
    if marker not in a1:
        errors.append(f"{template.template_id} A1 is missing the payload marker")
    if template.surface == "user_message" and marker not in template.a1.user_message:  # type: ignore[union-attr]
        errors.append(f"{template.template_id} marker is not in the user message")
    if template.surface == "retrieved_document":
        bodies = " ".join(doc.body for doc in template.a1.documents)  # type: ignore[union-attr]
        if marker not in bodies:
            errors.append(f"{template.template_id} marker is not in a retrieved document")
    if template.surface == "tool_output":
        notes = " ".join(template.a1.scan_notes.values())  # type: ignore[union-attr]
        if marker not in notes:
            errors.append(f"{template.template_id} marker is not in a tool note")


def _blob(template: Template, variant: str) -> str:
    surface = template.a0 if variant == "A0" else template.a1
    if surface is None:
        return ""
    parts = [surface.user_message]
    parts.extend(doc.body for doc in surface.documents)
    parts.extend(surface.scan_notes.values())
    return "\n".join(parts)
