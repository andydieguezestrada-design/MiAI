import httpx
from python.models.base import ModelProvider


class OpenAICompatibleProvider(ModelProvider):
    name = "openai_compatible"

    def __init__(self, base_url: str, api_key: str, model: str, timeout: float = 120):
        self.base_url, self.api_key, self.model = base_url.rstrip("/"), api_key, model
        self.timeout = max(5, float(timeout))

    def generate(self, prompt: str, temperature: float = 0.7) -> str:
        if not self.base_url or not self.model:
            raise RuntimeError("MIAI_BASE_URL y MIAI_MODEL son obligatorios para openai_compatible.")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            response = httpx.post(f"{self.base_url}/chat/completions", headers=headers,
                                  json={"model": self.model, "messages": [{"role": "user", "content": prompt}], "temperature": temperature},
                                  timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, list):
                content = "".join(str(x.get("text", "")) if isinstance(x, dict) else str(x) for x in content)
            return str(content).strip()
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Error al consultar el servidor de modelo: {exc}") from exc


    def stream(self, prompt: str, temperature: float = 0.7, chunk_size: int = 256):
        if not self.base_url or not self.model:
            raise RuntimeError("MIAI_BASE_URL y MIAI_MODEL son obligatorios para openai_compatible.")
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        try:
            with httpx.stream("POST", f"{self.base_url}/chat/completions", headers=headers,
                              json={"model": self.model, "messages": [{"role": "user", "content": prompt}],
                                    "temperature": temperature, "stream": True}, timeout=self.timeout) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    payload = line[5:].strip()
                    if payload == "[DONE]":
                        break
                    try:
                        data = __import__("json").loads(payload)
                        delta = data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                        if isinstance(delta, str) and delta:
                            yield delta
                    except (ValueError, KeyError, IndexError, TypeError):
                        continue
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Error de streaming del servidor de modelo: {exc}") from exc
