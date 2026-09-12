from python.core.quality import ResponseQuality
from python.reasoning.pipeline import ReasoningPipeline


def test_deep_reasoning_prompt_is_depth_aware():
    prompt = ReasoningPipeline().build_prompt(
        "Analiza detalladamente este problema, compara las alternativas y explica por qué recomendarías una."
    )
    assert "RESPONSE DEPTH: DEEP" in prompt
    assert "DEEP RESPONSE POLICY" in prompt
    assert "No reveles razonamiento interno privado" in prompt


def test_quality_flags_shallow_complex_answer():
    report = ResponseQuality().assess(
        "Es una buena opción porque tiene ventajas.",
        "Analiza detalladamente las ventajas, desventajas, riesgos y alternativas y explica por qué.",
    )
    assert report.needs_refinement
    assert report.reasons
