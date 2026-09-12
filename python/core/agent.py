from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Mapping

from python.tools.executor import ToolExecutor
from python.tools.registry import ToolRegistry


@dataclass
class AgentStep:
    index: int
    action: str
    tool: str | None = None
    arguments: dict[str, Any] = field(default_factory=dict)
    result: Any = None
    error: str | None = None


@dataclass
class AgentResult:
    answer: str
    provider: str
    model: str
    steps: list[AgentStep]
    status: str


class AutonomousAgent:
    """Bounded agent loop: PLAN -> ACT -> OBSERVE -> REFLECT -> FINAL.

    The model never executes Python directly. It can only request tools that are
    present in the ToolRegistry, and every run has a hard step limit.
    """

    def __init__(self, provider, tools: ToolRegistry, executor: ToolExecutor):
        self.provider = provider
        self.tools = tools
        self.executor = executor

    def run(
        self,
        task: str,
        project: str = "default",
        system: str | None = None,
        temperature: float = 0.2,
        max_steps: int = 6,
    ) -> AgentResult:
        if not task.strip():
            raise ValueError("La tarea no puede estar vacía.")
        max_steps = max(1, min(int(max_steps), 12))
        tools = self.tools.schemas()
        transcript: list[dict[str, Any]] = []
        steps: list[AgentStep] = []

        for index in range(1, max_steps + 1):
            prompt = self._build_decision_prompt(
                task=task,
                project=project,
                system=system,
                tools=tools,
                transcript=transcript,
                step=index,
                max_steps=max_steps,
            )
            raw = self.provider.generate(prompt, temperature=temperature)
            decision = self._parse_decision(raw)

            if decision is None:
                steps.append(AgentStep(index=index, action="final", result=raw))
                return AgentResult(raw, self.provider.name, self.provider.model, steps, "completed")

            action = str(decision.get("action", "final")).lower().strip()
            if action == "final":
                answer = str(decision.get("answer") or decision.get("result") or raw)
                steps.append(AgentStep(index=index, action="final", result=answer))
                return AgentResult(answer, self.provider.name, self.provider.model, steps, "completed")

            if action != "tool":
                answer = str(decision.get("answer") or raw)
                steps.append(AgentStep(index=index, action="final", result=answer))
                return AgentResult(answer, self.provider.name, self.provider.model, steps, "completed")

            tool_name = str(decision.get("tool", "")).strip()
            arguments = decision.get("arguments") or {}
            if not isinstance(arguments, dict):
                arguments = {}

            step = AgentStep(index=index, action="tool", tool=tool_name, arguments=arguments)
            result = self.executor.execute(tool_name, arguments)
            step.result = result.result
            step.error = result.error
            steps.append(step)
            transcript.append({
                "step": index,
                "action": "tool",
                "tool": tool_name,
                "arguments": arguments,
                "ok": result.ok,
                "result": result.result if result.ok else None,
                "error": result.error,
            })

        # A final synthesis gets one last model call only when the step budget
        # has been consumed; this call is not allowed to execute tools.
        prompt = self._build_final_prompt(task, transcript, project, system)
        answer = self.provider.generate(prompt, temperature=temperature)
        steps.append(AgentStep(index=max_steps + 1, action="final", result=answer))
        return AgentResult(answer, self.provider.name, self.provider.model, steps, "max_steps_reached")

    @staticmethod
    def _parse_decision(raw: str) -> dict[str, Any] | None:
        text = raw.strip()
        candidates = [text]
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        if match:
            candidates.insert(0, match.group(1))
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            candidates.append(text[start : end + 1])
        for candidate in candidates:
            try:
                value = json.loads(candidate)
                if isinstance(value, dict) and "action" in value:
                    return value
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _build_decision_prompt(self, task, project, system, tools, transcript, step, max_steps):
        tool_lines = "\n".join(
            f'- {tool["name"]}: {tool["description"]} | parameters={tool["parameters"]}'
            for tool in tools
        ) or "(sin herramientas disponibles)"
        history = json.dumps(transcript, ensure_ascii=False, default=str)
        return f"""SYSTEM:\n{system or 'Eres MiAI Autonomous Agent.'}\n\nPROJECT: {project}\n\nTASK:\n{task}\n\nSTEP: {step}/{max_steps}\n\nAVAILABLE TOOLS:\n{tool_lines}\n\nOBSERVATIONS:\n{history}\n\nINSTRUCTIONS:\nDecide el siguiente paso de forma autónoma. Nunca inventes resultados de herramientas.\nSolo puedes ejecutar herramientas incluidas en AVAILABLE TOOLS.\nNo ejecutes código arbitrario ni inventes nombres de herramientas.\nDevuelve EXCLUSIVAMENTE un objeto JSON válido, sin markdown, con una de estas formas:\n{{"action":"tool","tool":"nombre","arguments":{{...}}}}\n{{"action":"final","answer":"respuesta final para el usuario"}}\nSi la tarea ya puede responderse, usa action=final. No reveles cadena de pensamiento privada."""

    @staticmethod
    def _build_final_prompt(task, transcript, project, system):
        observations = json.dumps(transcript, ensure_ascii=False, default=str)
        return f"""SYSTEM:\n{system or 'Eres MiAI y debes entregar la respuesta final.'}\nPROJECT: {project}\nTASK: {task}\nOBSERVATIONS FROM TOOLS:\n{observations}\n\nEntrega únicamente la respuesta final para el usuario, clara, útil y suficientemente detallada. No reveles razonamiento interno privado."""
