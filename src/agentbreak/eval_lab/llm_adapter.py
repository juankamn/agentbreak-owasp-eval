"""Model adapters. Tests use the scripted model. Ollama is imported only when called."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class ProposedCall:
    name: str
    arguments: dict[str, Any]
    call_id: str


@dataclass
class ModelTurn:
    content: str = ""
    tool_calls: list[ProposedCall] = field(default_factory=list)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class ChatModel(Protocol):
    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
        seed: int,
    ) -> ModelTurn: ...


class ScriptedToolModel:
    """Returns a fixed script. Each chat() consumes one turn and stops on the last one."""

    def __init__(self, turns: list[dict[str, Any]]) -> None:
        if not turns:
            raise ValueError("the script needs at least one turn")
        self.turns = turns
        self.seen: list[list[dict[str, Any]]] = []
        self.index = 0

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
        seed: int,
    ) -> ModelTurn:
        del tools, temperature, seed
        self.seen.append(messages)
        turn = self.turns[min(self.index, len(self.turns) - 1)]
        self.index += 1
        calls = [
            ProposedCall(
                name=item["name"],
                arguments=dict(item.get("arguments", {})),
                call_id=item.get("id", f"call-{self.index}-{offset}"),
            )
            for offset, item in enumerate(turn.get("tool_calls", []))
        ]
        return ModelTurn(content=str(turn.get("content", "")), tool_calls=calls)


class OllamaToolModel:
    """One local model, called through langchain-ollama bind_tools."""

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        temperature: float,
        seed: int,
    ) -> ModelTurn:
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
        from langchain_ollama import ChatOllama

        llm = ChatOllama(
            model=self.model_name,
            temperature=temperature,
            num_predict=400,
            seed=seed,
        )
        bound = llm.bind_tools(tools)
        response = bound.invoke(_to_langchain(messages, SystemMessage, HumanMessage, AIMessage, ToolMessage))
        calls = []
        for item in response.tool_calls or []:
            calls.append(
                ProposedCall(
                    name=str(item.get("name", "")),
                    arguments=dict(item.get("args") or {}),
                    call_id=str(item.get("id") or f"call-{len(calls)}"),
                )
            )
        usage = getattr(response, "usage_metadata", None) or {}
        return ModelTurn(
            content=str(response.content or ""),
            tool_calls=calls,
            prompt_tokens=_usage_count(usage, "input_tokens"),
            completion_tokens=_usage_count(usage, "output_tokens"),
        )


def _usage_count(usage: Any, key: str) -> int | None:
    if isinstance(usage, dict) and usage.get(key) is not None:
        return int(usage[key])
    return None


def _to_langchain(messages: list[dict[str, Any]], system: Any, human: Any, ai: Any, tool: Any) -> list[Any]:
    converted = []
    for message in messages:
        role = message["role"]
        content = message.get("content", "")
        if role == "system":
            converted.append(system(content=content))
        elif role == "user":
            converted.append(human(content=content))
        elif role == "assistant":
            converted.append(ai(content=content, tool_calls=message.get("lc_tool_calls", [])))
        elif role == "tool":
            converted.append(tool(content=content, tool_call_id=message["tool_call_id"]))
        else:
            raise ValueError(f"unknown role {role}")
    return converted
