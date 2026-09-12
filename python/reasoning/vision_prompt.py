from __future__ import annotations


def build_vision_prompt(
    instruction: str,
    project: str,
    system: str | None = None,
    project_profile: str = "",
    memory_context: str = "",
    retrieved_context: str = "",
) -> str:
    parts = [
        "Eres el motor de visión de MiAI.",
        "Analiza la imagen proporcionada con precisión y responde a la instrucción del usuario.",
        "No inventes elementos que no sean visibles. Distingue observación directa de inferencia.",
        "La respuesta debe ser detallada, estructurada y útil; evita respuestas genéricas o banales.",
        f"Proyecto: {project}",
    ]
    if system:
        parts.append(f"Instrucciones del sistema: {system}")
    if project_profile:
        parts.append(f"Perfil del proyecto:\n{project_profile}")
    if memory_context:
        parts.append(f"Memoria relevante:\n{memory_context}")
    if retrieved_context:
        parts.append(f"Conocimiento recuperado:\n{retrieved_context}")
    parts.append(
        "Cuando sea pertinente, organiza el análisis por: composición, sujetos/objetos, geometría y relaciones espaciales, "
        "detalles importantes, texto visible, iluminación/valores, incertidumbres, problemas y recomendaciones."
    )
    parts.append(f"Instrucción del usuario:\n{instruction}")
    return "\n\n".join(parts)
