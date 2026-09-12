from python.models.vision import VisionProvider


class MockVisionProvider(VisionProvider):
    name = "mock_vision"
    model = "ci-mock-vision"

    def analyze(self, prompt: str, image_base64: str, mime_type: str = "image/jpeg", temperature: float = 0.2) -> str:
        return "Análisis visual de prueba de MiAI (mock)."
