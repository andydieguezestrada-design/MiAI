from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class QualityReport:
    """Non-invasive quality assessment for deciding whether to refine output."""

    text: str
    score: float
    needs_refinement: bool
    reasons: tuple[str, ...] = ()


class ResponseQuality:
    """Cheap safety/quality gate for provider output.

    The original V9 validation contract is preserved. V10 adds an optional
    assessment layer; it never changes validation or provider behavior unless
    the engine explicitly opts into auto-refinement.
    """

    def __init__(self, min_chars: int = 1, max_chars: int = 120000):
        self.min_chars = min_chars
        self.max_chars = max_chars

    def validate(self, answer: str) -> str:
        if not isinstance(answer, str):
            raise RuntimeError("El proveedor devolvió una respuesta no textual.")
        answer = answer.strip()
        if len(answer) < self.min_chars:
            raise RuntimeError("El proveedor devolvió una respuesta vacía.")
        return answer[: self.max_chars]

    def assess(self, answer: str, request: str) -> QualityReport:
        """Detect likely shallow answers without pretending to judge factual truth."""
        text = self.validate(answer)
        request = (request or "").strip()
        complex_request = len(request) >= 220 or any(
            marker in request.lower()
            for marker in (
                "detall", "explica", "compara", "analiza", "argumenta",
                "ventajas", "desventajas", "riesgos", "alternativas", "paso a paso",
                "profundo", "completo", "por qué", "por que",
            )
        )
        reasons: list[str] = []
        if complex_request and len(text) < 280:
            reasons.append("respuesta demasiado breve para una solicitud compleja")
        if complex_request and text.count("\n") == 0 and len(text) < 450:
            reasons.append("poca estructura para el nivel de detalle solicitado")
        score = 1.0
        if reasons:
            score = max(0.0, 0.65 - 0.08 * max(0, len(reasons) - 1))
        return QualityReport(text, score, bool(reasons), tuple(reasons))
