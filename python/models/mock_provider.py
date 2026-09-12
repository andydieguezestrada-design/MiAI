from python.models.base import ModelProvider

class MockProvider(ModelProvider):
    name = "mock"
    model = "ci-mock"

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        return "Respuesta de prueba de MiAI (mock)."
