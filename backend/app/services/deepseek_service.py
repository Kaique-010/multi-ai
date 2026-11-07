import httpx

from app.core.config import configuracoes


class DeepSeekService:

    def __init__(self):
        self.api_key = configuracoes.deepseek_api_key
        self.model = configuracoes.deepseek_model
        self.base_url = configuracoes.deepseek_base_url.rstrip("/")

    async def perguntar(self, mensagem: str) -> str:

        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY não configurada.")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Você é um assistente de inteligência artificial. Responda em português brasileiro.",
                },
                {
                    "role": "user",
                    "content": mensagem,
                },
            ],
        }

        async with httpx.AsyncClient(timeout=60.0) as cliente:
            resposta = await cliente.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )

            resposta.raise_for_status()

            dados = resposta.json()

            return dados["choices"][0]["message"]["content"]