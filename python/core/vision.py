from __future__ import annotations

import os
from dataclasses import dataclass

from python.models.vision_factory import create_vision_provider
from python.reasoning.vision_prompt import build_vision_prompt
from python.core.quality import ResponseQuality


@dataclass
class VisionResult:
    answer: str
    provider: str
    model: str
    project: str


class VisionEngine:
    def __init__(self, memory, rag, provider=None):
        self.provider = provider or create_vision_provider()
        self.memory = memory
        self.rag = rag
        self.max_image_base64_chars = int(os.getenv("MIAI_MAX_IMAGE_BASE64_CHARS", "15000000"))
        self.quality = ResponseQuality()

    @staticmethod
    def _normalize_image(image_base64: str) -> str:
        value = image_base64.strip()
        if value.startswith("data:") and ";base64," in value:
            value = value.split(";base64,", 1)[1]
        return value.strip()

    def analyze(
        self,
        image_base64: str,
        instruction: str,
        project: str = "default",
        system: str | None = None,
        mime_type: str = "image/jpeg",
        temperature: float = 0.2,
    ) -> VisionResult:
        project = project.strip() or "default"
        image_base64 = self._normalize_image(image_base64)
        if not image_base64:
            raise ValueError("image_base64 no puede estar vacío.")
        if len(image_base64) > self.max_image_base64_chars:
            raise ValueError(
                "La imagen supera el límite configurado de MiAI "
                f"({self.max_image_base64_chars} caracteres Base64)."
            )

        mime_type = mime_type.strip().lower()
        if not mime_type.startswith("image/"):
            raise ValueError("mime_type debe corresponder a una imagen.")

        instruction = instruction.strip() or "Analiza detalladamente esta imagen."
        retrieved = self.memory.search(project, instruction)
        memory_context = "\n".join(f"{item['role']}: {item['content']}" for item in retrieved)
        knowledge = self.rag.search(instruction, project=project, limit=6)
        knowledge_context = "\n".join(
            f"[knowledge:{item['title']}] {item['content']}" for item in knowledge
        )
        prompt = build_vision_prompt(
            instruction=instruction,
            project=project,
            system=system,
            project_profile=self.memory.get_profile(project),
            memory_context=memory_context,
            retrieved_context=knowledge_context,
        )
        answer = self.provider.analyze(prompt, image_base64, mime_type, temperature)
        if os.getenv("MIAI_AUTO_REFINE", "true").lower() in {"1", "true", "yes", "on"}:
            report = self.quality.assess(answer, instruction)
            if report.needs_refinement:
                refine_prompt = (
                    "Revisa el análisis visual anterior y produce una versión más completa y específica. "
                    "Incluye únicamente observaciones sustentadas por la imagen, separa observación de inferencia "
                    "y responde exactamente a la instrucción. No inventes detalles.\n\n"
                    f"INSTRUCCIÓN:\n{instruction}\n\nANÁLISIS ANTERIOR:\n{answer}"
                )
                answer = self.provider.analyze(refine_prompt, image_base64, mime_type, temperature)
        answer = self.quality.validate(answer)

        # Store only the task/result, never the image itself.
        self.memory.add(project, "user", instruction, kind="vision_task")
        self.memory.add(project, "assistant", answer, kind="vision_result")
        return VisionResult(answer, self.provider.name, self.provider.model, project)
