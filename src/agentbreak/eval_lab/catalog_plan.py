"""Define las familias de calibración y evaluación en particiones separadas."""

from __future__ import annotations

CALIBRATION_FAMILIES: dict[str, list[str]] = {
    "LLM01": ["LLM01-USER-DIRECT", "LLM01-USER-SPLIT"],
    "LLM02": ["LLM02-DOC-TOKEN", "LLM02-DOC-SUMMARY"],
    "LLM03": ["LLM03-TOOL-ACTION", "LLM03-TOOL-SKIP"],
    "BENIGN": ["BENIGN-LOOKUP", "BENIGN-SCAN-TICKET"],
}

EVALUATION_FAMILIES: dict[str, list[str]] = {
    "LLM01": [
        "LLM01-DOC-INDIRECT",
        "LLM01-DOC-ENCODED",
        "LLM01-TOOL-NOTE",
        "LLM01-TOOL-INVISIBLE",
    ],
    "LLM02": [
        "LLM02-USER-DIRECT",
        "LLM02-USER-PRETEXT",
        "LLM02-TOOL-FORWARD",
        "LLM02-TOOL-CROSSTENANT",
    ],
    "LLM03": [
        "LLM03-USER-DIRECT",
        "LLM03-USER-TEMP",
        "LLM03-DOC-UNSOLICITED",
        "LLM03-DOC-OFFTASK",
    ],
    "BENIGN": [
        "BENIGN-REPORT",
        "BENIGN-CREDS",
        "BENIGN-REMEDIATE",
        "BENIGN-VOCAB",
    ],
}

FAMILY_SURFACE: dict[str, str] = {
    "LLM01-USER-DIRECT": "user_message",
    "LLM01-USER-SPLIT": "user_message",
    "LLM01-DOC-INDIRECT": "retrieved_document",
    "LLM01-DOC-ENCODED": "retrieved_document",
    "LLM01-TOOL-NOTE": "tool_output",
    "LLM01-TOOL-INVISIBLE": "tool_output",
    "LLM02-DOC-TOKEN": "retrieved_document",
    "LLM02-DOC-SUMMARY": "retrieved_document",
    "LLM02-USER-DIRECT": "user_message",
    "LLM02-USER-PRETEXT": "user_message",
    "LLM02-TOOL-FORWARD": "tool_output",
    "LLM02-TOOL-CROSSTENANT": "tool_output",
    "LLM03-TOOL-ACTION": "tool_output",
    "LLM03-TOOL-SKIP": "tool_output",
    "LLM03-USER-DIRECT": "user_message",
    "LLM03-USER-TEMP": "user_message",
    "LLM03-DOC-UNSOLICITED": "retrieved_document",
    "LLM03-DOC-OFFTASK": "retrieved_document",
    "BENIGN-LOOKUP": "none",
    "BENIGN-SCAN-TICKET": "none",
    "BENIGN-REPORT": "none",
    "BENIGN-CREDS": "none",
    "BENIGN-REMEDIATE": "none",
    "BENIGN-VOCAB": "none",
}

FAMILY_DIFFICULTY: dict[str, str] = {
    "LLM01-USER-DIRECT": "low",
    "LLM01-USER-SPLIT": "medium",
    "LLM01-DOC-INDIRECT": "medium",
    "LLM01-DOC-ENCODED": "high",
    "LLM01-TOOL-NOTE": "medium",
    "LLM01-TOOL-INVISIBLE": "high",
    "LLM02-DOC-TOKEN": "medium",
    "LLM02-DOC-SUMMARY": "high",
    "LLM02-USER-DIRECT": "low",
    "LLM02-USER-PRETEXT": "medium",
    "LLM02-TOOL-FORWARD": "medium",
    "LLM02-TOOL-CROSSTENANT": "high",
    "LLM03-TOOL-ACTION": "medium",
    "LLM03-TOOL-SKIP": "high",
    "LLM03-USER-DIRECT": "low",
    "LLM03-USER-TEMP": "medium",
    "LLM03-DOC-UNSOLICITED": "medium",
    "LLM03-DOC-OFFTASK": "high",
    "BENIGN-LOOKUP": "low",
    "BENIGN-SCAN-TICKET": "medium",
    "BENIGN-REPORT": "medium",
    "BENIGN-CREDS": "medium",
    "BENIGN-REMEDIATE": "medium",
    "BENIGN-VOCAB": "medium",
}
