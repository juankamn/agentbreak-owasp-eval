"""Ejecución del agente, semillas compartidas y programación de repeticiones."""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from typing import Any

from agentbreak.eval_lab.llm_adapter import ChatModel
from agentbreak.eval_lab.oracle import judge
from agentbreak.eval_lab.paths import world_secrets
from agentbreak.eval_lab.policy_engine import PolicyEngine, context_blob
from agentbreak.eval_lab.prompts import system_prompt, tool_catalog
from agentbreak.eval_lab.sandbox import Sandbox
from agentbreak.eval_lab.schemas import (
    PolicyMode,
    RunRecord,
    Template,
    ToolCallRecord,
    VariantName,
)
from agentbreak.eval_lab.tools import execute

MASTER_SEED = 20261114


class StepLimitReached(RuntimeError):
    """Se alcanzó el límite de pasos al solicitar herramientas."""


@dataclass(frozen=True)
class RunConfig:
    temperature: float
    prompt_variant: str
    tool_detail: str

    @property
    def config_id(self) -> str:
        return f"{self.prompt_variant}|t{self.temperature}|tools-{self.tool_detail}"


@dataclass(frozen=True)
class ScheduledRun:
    template_id: str
    variant: VariantName
    model: str
    policy: PolicyMode
    repetition: int
    seed: int


# Genera la misma semilla para comparar C0 y C1 en un mismo caso.
def pair_seed(
    template_id: str,
    variant: str,
    repetition: int,
    model: str,
    master_seed: int = MASTER_SEED,
) -> int:
    """Genera la misma semilla para comparar C0 y C1 en un caso."""
    raw = f"{master_seed}|{template_id}|{variant}|{repetition}|{model}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


# Organiza los casos por repetición, modelo y condición de seguridad.
def build_schedule(
    templates: list[Template],
    models: list[str],
    policies: list[PolicyMode],
    repetitions: list[int],
    master_seed: int = MASTER_SEED,
) -> list[ScheduledRun]:
    """Organiza los casos por repetición y modelo.

    Mantiene un modelo cargado por bloque y alterna el orden entre repeticiones.
    """
    ordered: list[ScheduledRun] = []
    for repetition in repetitions:
        model_order = list(models) if repetition % 2 == 1 else list(reversed(models))
        for offset, model in enumerate(model_order):
            block: list[ScheduledRun] = []
            for template in templates:
                for variant in template.variants():
                    seed = pair_seed(template.template_id, variant, repetition, model, master_seed)
                    for policy in policies:
                        block.append(
                            ScheduledRun(
                                template_id=template.template_id,
                                variant=variant,
                                model=model,
                                policy=policy,
                                repetition=repetition,
                                seed=seed,
                            )
                        )
            rng = random.Random(master_seed + repetition * 1000 + offset)
            rng.shuffle(block)
            ordered.extend(block)
    return ordered


# Prepara el entorno y ejecuta un caso con la configuración indicada.
def run_case(
    template: Template,
    variant: VariantName,
    policy_mode: PolicyMode,
    model: ChatModel,
    model_name: str,
    world: dict[str, Any],
    policy_spec: dict[str, Any],
    config: RunConfig,
    *,
    repetition: int,
    seed: int,
    model_digest: str = "",
) -> RunRecord:
    # Cada ejecución parte de una copia nueva del entorno del caso.
    surface = template.surface_for(variant)
    sandbox = Sandbox.from_surface(surface)
    policy = PolicyEngine(policy_mode, world, policy_spec, template)
    tools = tool_catalog(config.tool_detail)
    visible = [system_prompt(template, world, config.prompt_variant), surface.user_message]
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": visible[0]},
        {"role": "user", "content": visible[1]},
    ]
    steps: list[ToolCallRecord] = []
    phrase_hits = policy.phrase_hits(*visible)
    raw_answer = ""
    technical = False
    failure_reason = ""
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    started = time.perf_counter()
    try:
        raw_answer, prompt_tokens, completion_tokens = _loop(
            messages,
            visible,
            steps,
            phrase_hits,
            sandbox,
            policy,
            model,
            tools,
            world,
            template,
            config,
            seed,
            int(policy_spec["max_steps"]),
        )
    except Exception as exc:
        technical = True
        failure_reason = type(exc).__name__
    elapsed_ms = (time.perf_counter() - started) * 1000
    delivered, output_blocked = policy.filter_output(raw_answer)
    # Registra si el marcador de ataque llegó al contexto que vio el modelo.
    marker = template.payload_marker
    payload_visible = bool(marker) and marker in "\n".join(visible)
    verdict = judge(
        template,
        sandbox,
        delivered,
        raw_answer,
        steps,
        world_secrets(world),
        payload_visible=payload_visible,
        technical_failure=technical,
        failure_reason=failure_reason,
    )
    return RunRecord(
        template_id=template.template_id,
        variant=variant,
        partition=template.partition,
        stratum=template.stratum,
        family_id=template.family_id,
        surface=template.surface,
        difficulty=template.difficulty,
        model=model_name,
        model_digest=model_digest,
        policy=policy_mode,
        repetition=repetition,
        seed=seed,
        temperature=config.temperature,
        prompt_variant=config.prompt_variant,
        tool_detail=config.tool_detail,
        config_id=config.config_id,
        steps=steps,
        raw_answer=raw_answer,
        delivered_answer=delivered,
        output_blocked=output_blocked,
        phrase_hits=sorted(set(phrase_hits)),
        latency_ms=elapsed_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        sandbox_end=sandbox.snapshot(),
        oracle=verdict,
        context_has_payload=payload_visible,
    )


# Registra las herramientas propuestas y la respuesta final del modelo.
def _loop(
    messages: list[dict[str, Any]],
    visible: list[str],
    steps: list[ToolCallRecord],
    phrase_hits: list[str],
    sandbox: Sandbox,
    policy: PolicyEngine,
    model: ChatModel,
    tools: list[dict[str, Any]],
    world: dict[str, Any],
    template: Template,
    config: RunConfig,
    seed: int,
    max_steps: int,
) -> tuple[str, int | None, int | None]:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    for _ in range(max_steps):
        turn = model.chat(messages, tools, config.temperature, seed)
        if turn.prompt_tokens is not None:
            prompt_tokens = (prompt_tokens or 0) + turn.prompt_tokens
        if turn.completion_tokens is not None:
            completion_tokens = (completion_tokens or 0) + turn.completion_tokens
        if not turn.tool_calls:
            return turn.content, prompt_tokens, completion_tokens
        messages.append(
            {
                "role": "assistant",
                "content": turn.content,
                "lc_tool_calls": [
                    {"name": call.name, "args": call.arguments, "id": call.call_id}
                    for call in turn.tool_calls
                ],
            }
        )
        for call in turn.tool_calls:
            _apply_call(
                call.name,
                call.arguments,
                call.call_id,
                messages,
                visible,
                steps,
                phrase_hits,
                sandbox,
                policy,
                world,
                template.engagement_id,
            )
    raise StepLimitReached


# Aplica los controles antes de ejecutar una herramienta en C1.
def _apply_call(
    name: str,
    arguments: dict[str, Any],
    call_id: str,
    messages: list[dict[str, Any]],
    visible: list[str],
    steps: list[ToolCallRecord],
    phrase_hits: list[str],
    sandbox: Sandbox,
    policy: PolicyEngine,
    world: dict[str, Any],
    engagement_id: str,
) -> None:
    # En C0 se registra la decisión de los controles sin impedir la llamada.
    decision = policy.evaluate_tool(name, arguments)
    enforce = policy.mode == "C1" and not decision.allowed
    if enforce:
        result: dict[str, Any] = {
            "status": "not_applied",
            "message": policy.spec["neutral_message"],
        }
        executed = False
    else:
        result = execute(name, arguments, sandbox, world, engagement_id)
        executed = result.get("status") == "ok"
    preview = json.dumps(result, ensure_ascii=False)
    visible.append(preview)
    phrase_hits.extend(policy.phrase_hits(preview))
    # Conserva la propuesta, su resultado y las razones de un posible bloqueo.
    steps.append(
        ToolCallRecord(
            name=name,
            arguments=arguments,
            executed=executed,
            blocked=enforce,
            shadow_blocked=not decision.allowed,
            reasons=decision.reasons,
            result_preview=preview[:500],
        )
    )
    messages.append({"role": "tool", "content": preview, "tool_call_id": call_id})


def initial_phrase_context(template: Template, variant: VariantName) -> str:
    """Obtiene el contexto del caso antes de ejecutar herramientas."""
    surface = template.surface_for(variant)
    sandbox = Sandbox.from_surface(surface)
    return context_blob(sandbox, surface.user_message)
