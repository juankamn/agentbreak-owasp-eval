"""Catalog and trace models. Validators live here so the JSON stays declarative."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, model_validator

Partition = Literal["calibration", "evaluation"]
Stratum = Literal["LLM01", "LLM02", "LLM03", "BENIGN"]
Surface = Literal["user_message", "retrieved_document", "tool_output", "none"]
Difficulty = Literal["low", "medium", "high"]
RoleName = Literal["client_contact", "analyst", "engagement_lead"]
TaskType = Literal["consulting", "privileged"]
VariantName = Literal["A0", "A1"]
PolicyMode = Literal["C0", "C1"]


class Document(BaseModel):
    doc_id: str
    title: str
    body: str


class SurfaceContent(BaseModel):
    user_message: str
    documents: list[Document] = Field(default_factory=list)
    scan_notes: dict[str, str] = Field(default_factory=dict)


class UtilityCheck(BaseModel):
    required_tools: list[str] = Field(default_factory=list)
    ticket_asset: str | None = None
    report_recipient: str | None = None
    answer_contains_any: list[str] = Field(default_factory=list)
    remediation_asset: str | None = None
    credential_asset: str | None = None


class Template(BaseModel):
    template_id: str
    partition: Partition
    stratum: Stratum
    family_id: str
    surface: Surface
    difficulty: Difficulty
    role: RoleName
    engagement_id: str
    task_type: TaskType
    approval_granted: bool
    legitimate_task: str
    prohibited_calls: list[dict[str, str]] = Field(default_factory=list)
    prohibited_markers: list[str] = Field(default_factory=list)
    protected_assets: list[str] = Field(default_factory=list)
    authorized_report_recipients: list[str] = Field(default_factory=list)
    utility_check: UtilityCheck
    secondary_labels: list[str] = Field(default_factory=list)
    payload_marker: str = ""
    a0: SurfaceContent
    a1: SurfaceContent | None = None
    owasp_2026: str
    notes: str = ""

    @model_validator(mode="after")
    def attack_templates_have_a_pair(self) -> Template:
        if self.stratum == "BENIGN" and self.a1 is not None:
            raise ValueError(f"{self.template_id} is benign and must not include A1")
        if self.stratum != "BENIGN" and self.a1 is None:
            raise ValueError(f"{self.template_id} is an attack template and needs A1")
        if self.stratum != "BENIGN" and self.payload_marker == "":
            raise ValueError(f"{self.template_id} needs a payload marker")
        return self

    def variants(self) -> list[VariantName]:
        if self.a1 is None:
            return ["A0"]
        return ["A0", "A1"]

    def surface_for(self, variant: VariantName) -> SurfaceContent:
        if variant == "A1":
            if self.a1 is None:
                raise ValueError(f"{self.template_id} has no A1")
            return self.a1
        return self.a0


class ToolCallRecord(BaseModel):
    name: str
    arguments: dict[str, Any]
    executed: bool
    blocked: bool
    shadow_blocked: bool = False
    reasons: list[str] = Field(default_factory=list)
    result_preview: str = ""


class OracleVerdict(BaseModel):
    violation: bool
    violation_kinds: list[str] = Field(default_factory=list)
    unsafe_proposal: bool
    legitimate_completion: bool
    deviation_without_violation: bool
    undue_block: bool
    payload_reached_model: bool
    payload_followed: bool
    technical_failure: bool
    failure_reason: str = ""


class RunRecord(BaseModel):
    template_id: str
    variant: VariantName
    partition: Partition
    stratum: Stratum
    family_id: str
    surface: Surface
    difficulty: Difficulty
    model: str
    model_digest: str = ""
    policy: PolicyMode
    repetition: int
    seed: int
    temperature: float
    prompt_variant: str
    tool_detail: str
    config_id: str
    steps: list[ToolCallRecord] = Field(default_factory=list)
    raw_answer: str = ""
    delivered_answer: str = ""
    output_blocked: bool = False
    phrase_hits: list[str] = Field(default_factory=list)
    latency_ms: float = 0.0
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    sandbox_end: dict[str, Any] = Field(default_factory=dict)
    oracle: OracleVerdict
    context_has_payload: bool = False
