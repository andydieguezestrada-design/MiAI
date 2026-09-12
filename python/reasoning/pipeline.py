from __future__ import annotations

from typing import Any


class ReasoningPipeline:
    """Builds structured prompts without exposing private chain-of-thought."""

    @staticmethod
    def _depth_policy(message: str) -> str:
        text = (message or "").strip().lower()
        complex_markers = (
            "detall", "profund", "compara", "analiza", "argumenta", "riesgos",
            "alternativas", "paso a paso", "ventajas", "desventajas", "completo",
            "por qué", "por que",
        )
        return "DEEP" if len(text) >= 220 or any(m in text for m in complex_markers) else "STANDARD"

    def build_prompt(
        self,
        message: str,
        memory_context: list[dict[str, Any]] | None = None,
        system: str | None = None,
        project_profile: str | None = None,
        retrieved_context: str | None = None,
        tool_schemas: list[dict[str, Any]] | None = None,
    ) -> str:
        sections = [
            "SYSTEM:",
            system or "Eres MiAI, un asistente general reutilizable.",
        ]

        if project_profile:
            sections += ["\nPROJECT PROFILE:", project_profile]

        if memory_context:
            sections.append("\nRECENT MEMORY:")
            if isinstance(memory_context, str):
                sections.append(memory_context)
            else:
                sections.extend(
                    f"- {item['role']}: {item['content']}" for item in memory_context
                )

        if retrieved_context:
            sections += ["\nRETRIEVED CONTEXT:", retrieved_context]

        if tool_schemas:
            sections.append("\nAVAILABLE TOOLS:")
            for tool in tool_schemas:
                sections.append(
                    f"- {tool['name']}: {tool['description']} "
                    f"Parameters: {tool['parameters']}"
                )
            sections.append(
                "\nTOOL POLICY:\n"
                "Usa una herramienta solo cuando aporte valor. "
                "No inventes resultados de herramientas. "
                "Las herramientas se ejecutan fuera del modelo."
            )

        depth = self._depth_policy(message)
        sections += [
            "\nUSER:",
            message,
            f"\nRESPONSE DEPTH: {depth}",
            "QUALITY CONTRACT:",
            "Responde directamente a lo pedido. Prioriza precisión, contexto, utilidad y argumentos verificables.",
            "No inventes hechos. Distingue datos conocidos, inferencias y supuestos cuando sea relevante.",
            "No reveles razonamiento interno privado ni cadenas de pensamiento.",
        ]
        if depth == "DEEP":
            sections += [
                "DEEP RESPONSE POLICY:",
                "Descompón el problema internamente y cubre las dimensiones relevantes antes de responder.",
                "Explica conclusiones y criterios de decisión de forma resumida y útil, sin revelar pensamiento interno privado.",
                "Si existen alternativas, riesgos, límites o incertidumbres relevantes, inclúyelos.",
                "Evita respuestas genéricas, repetitivas o excesivamente cortas para una solicitud que pide profundidad.",
                "FINAL CHECK: verifica que la respuesta cubra los puntos solicitados antes de terminar.",
            ]
        else:
            sections.append("Responde con claridad y suficiente profundidad para la pregunta.")
        return "\n".join(sections)
