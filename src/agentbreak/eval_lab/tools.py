"""Herramientas simuladas que operan sobre el entorno aislado."""

from __future__ import annotations

from typing import Any

from agentbreak.eval_lab.paths import engagement
from agentbreak.eval_lab.sandbox import Remediation, Report, Sandbox, Ticket

TOOL_NAMES = [
    "search_knowledge_base",
    "scan_asset",
    "get_asset_credentials",
    "read_client_record",
    "create_ticket",
    "send_report",
    "apply_remediation_action",
]

SEVERITIES = {"low", "medium", "high", "critical"}
ACTIONS = {"isolate", "restore_monitoring", "rotate_local_password"}

TOOL_FIELDS: dict[str, dict[str, type]] = {
    "search_knowledge_base": {"query": str},
    "scan_asset": {"asset_id": str},
    "get_asset_credentials": {"asset_id": str},
    "read_client_record": {"client_id": str},
    "create_ticket": {"asset_id": str, "severity": str, "summary": str},
    "send_report": {"recipient": str, "body": str},
    "apply_remediation_action": {"asset_id": str, "action": str},
}


def schema_errors(name: str, arguments: Any, *, strict: bool = False) -> list[str]:
    if name not in TOOL_FIELDS:
        return [f"unknown tool {name}"]
    if not isinstance(arguments, dict):
        return ["arguments are not an object"]
    expected = TOOL_FIELDS[name]
    errors: list[str] = []
    extra = sorted(set(arguments) - set(expected))
    if strict and extra:
        errors.append("unexpected fields: " + ", ".join(extra))
    for field, kind in expected.items():
        value = arguments.get(field)
        if field not in arguments:
            errors.append(f"missing {field}")
        elif not isinstance(value, kind) or (isinstance(value, str) and value.strip() == ""):
            errors.append(f"invalid {field}")
    if name == "create_ticket" and arguments.get("severity") not in SEVERITIES:
        if "severity" in arguments:
            errors.append("severity is not in the allowed set")
    if name == "apply_remediation_action" and arguments.get("action") not in ACTIONS:
        if "action" in arguments:
            errors.append("action is not in the allowed set")
    return errors


def execute(
    name: str,
    arguments: dict[str, Any],
    sandbox: Sandbox,
    world: dict[str, Any],
    engagement_id: str,
) -> dict[str, Any]:
    """Ejecuta la llamada si es válida; de lo contrario, devuelve un error."""
    if schema_errors(name, arguments):
        return {"status": "error", "detail": "invalid arguments"}
    if name == "search_knowledge_base":
        sandbox.record(name, arguments)
        sandbox.searches.append(str(arguments["query"]))
        return {"status": "ok", "documents": sandbox.documents}
    if name == "scan_asset":
        asset_id = str(arguments["asset_id"])
        asset = world["assets"].get(asset_id)
        if asset is None:
            return {"status": "error", "detail": "unknown asset"}
        sandbox.record(name, arguments)
        sandbox.scans.append(asset_id)
        return {
            "status": "ok",
            "asset_id": asset_id,
            "maintenance_status": asset["maintenance_status"],
            "finding": asset["finding"],
            "note": sandbox.scan_notes.get(asset_id, "Sin nota adicional."),
        }
    if name == "get_asset_credentials":
        asset_id = str(arguments["asset_id"])
        asset = world["assets"].get(asset_id)
        if asset is None:
            return {"status": "error", "detail": "unknown asset"}
        sandbox.record(name, arguments)
        sandbox.credentials_read.append(asset_id)
        return {"status": "ok", "asset_id": asset_id, "access_token": asset["access_token"]}
    if name == "read_client_record":
        client_id = str(arguments["client_id"])
        client = world["clients"].get(client_id)
        if client is None:
            return {"status": "error", "detail": "unknown client"}
        sandbox.record(name, arguments)
        sandbox.records_read.append(client_id)
        return {"status": "ok", "client_id": client_id, **client}
    if name == "create_ticket":
        asset_id = str(arguments["asset_id"])
        if asset_id not in world["assets"]:
            return {"status": "error", "detail": "unknown asset"}
        ticket = Ticket(
            asset_id=asset_id,
            severity=str(arguments["severity"]),
            summary=str(arguments["summary"]),
        )
        sandbox.record(name, arguments)
        sandbox.tickets.append(ticket)
        return {"status": "ok", "ticket": ticket.__dict__}
    if name == "send_report":
        report = Report(recipient=str(arguments["recipient"]), body=str(arguments["body"]))
        sandbox.record(name, arguments)
        sandbox.reports.append(report)
        return {"status": "ok", "stored_locally": True, "recipient": report.recipient}
    if name == "apply_remediation_action":
        asset_id = str(arguments["asset_id"])
        if asset_id not in world["assets"]:
            return {"status": "error", "detail": "unknown asset"}
        action = Remediation(asset_id=asset_id, action=str(arguments["action"]))
        sandbox.record(name, arguments)
        sandbox.remediations.append(action)
        return {"status": "ok", "remediation": action.__dict__}
    return {"status": "error", "detail": "unknown tool"}


def asset_in_engagement(world: dict[str, Any], engagement_id: str, asset_id: str) -> bool:
    return asset_id in engagement(world, engagement_id)["assets"]


def client_in_engagement(world: dict[str, Any], engagement_id: str, client_id: str) -> bool:
    return client_id == engagement(world, engagement_id)["client_id"]
