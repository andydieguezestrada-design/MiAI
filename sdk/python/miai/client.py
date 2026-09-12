import httpx

class MiAIClient:
    def __init__(self, base_url: str = "http://127.0.0.1:8000"):
        self.base_url = base_url.rstrip("/")

    def ask(self, message: str, project: str = "default",
            system: str | None = None, temperature: float = 0.7) -> str:
        response = httpx.post(
            f"{self.base_url}/ai/chat",
            json={
                "message": message,
                "project": project,
                "system": system,
                "temperature": temperature,
            },
            timeout=180,
        )
        response.raise_for_status()
        return response.json()["answer"]

    def analyze_image(self, image_base64: str, instruction: str = "Analiza detalladamente esta imagen.",
                      project: str = "default", system: str | None = None,
                      mime_type: str = "image/jpeg", temperature: float = 0.2) -> str:
        response = httpx.post(
            f"{self.base_url}/ai/vision",
            json={
                "image_base64": image_base64, "instruction": instruction,
                "project": project, "system": system, "mime_type": mime_type,
                "temperature": temperature,
            },
            timeout=240,
        )
        response.raise_for_status()
        return response.json()["answer"]

    def stream(self, message: str, project: str = "default", system: str | None = None,
               temperature: float = 0.7, session_id: str | None = None):
        """Itera fragmentos SSE de una respuesta de MiAI."""
        with httpx.stream("POST", f"{self.base_url}/ai/chat/stream", json={
            "message": message, "project": project, "system": system,
            "temperature": temperature, "session_id": session_id,
        }, timeout=240) as response:
            response.raise_for_status()
            import json
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event.get("type") == "token":
                    yield event.get("content", "")
                elif event.get("type") == "error":
                    raise RuntimeError(event.get("error", "Error de streaming"))

    def create_session(self, project: str = "default", title: str = "") -> dict:
        response = httpx.post(f"{self.base_url}/ai/sessions", json={"project": project, "title": title}, timeout=30)
        response.raise_for_status(); return response.json()

    def session_messages(self, session_id: str, limit: int = 50) -> list[dict]:
        response = httpx.get(f"{self.base_url}/ai/session/{session_id}/messages", params={"limit": limit}, timeout=30)
        response.raise_for_status(); return response.json()["messages"]
