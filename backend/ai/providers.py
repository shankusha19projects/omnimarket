"""AI provider abstraction. The backend owns all credentials; the browser never sees them.

- anthropic: official `anthropic` SDK, default model `claude-opus-5`, adaptive thinking,
  server-side refusal fallbacks (`fallbacks: "default"`).
- openai / ollama: optional alternatives (raw HTTP; model configurable via AI_MODEL).
- offline: deterministic, rule-based analyst used when no AI provider is configured.
  Its output is clearly labeled as not LLM-generated.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from backend.config import env, has_secret
from backend.utils import http, provider_health
from backend.utils.http import ProviderError


@dataclass
class AIResult:
    text: str
    provider: str
    model: str
    usage: dict[str, Any] | None = None
    note: str | None = None


class AIProvider(ABC):
    name = "base"
    default_model = ""

    def model(self) -> str:
        return env("AI_MODEL") or self.default_model

    @abstractmethod
    def available(self) -> bool: ...

    @abstractmethod
    async def complete(self, system: str, messages: list[dict[str, str]], max_tokens: int = 16000) -> AIResult: ...


class AnthropicProvider(AIProvider):
    name = "anthropic"
    default_model = "claude-opus-5"

    def available(self) -> bool:
        return has_secret("ANTHROPIC_API_KEY")

    async def complete(self, system: str, messages: list[dict[str, str]], max_tokens: int = 16000) -> AIResult:
        import anthropic

        model = self.model()
        client = anthropic.AsyncAnthropic(api_key=env("ANTHROPIC_API_KEY"), timeout=300, max_retries=2)
        provider_health.record_request("anthropic")
        try:
            resp = await client.beta.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system,
                messages=messages,
                thinking={"type": "adaptive"},
                output_config={"effort": "high"},
                betas=["server-side-fallback-2026-07-01"],
                extra_body={"fallbacks": "default"},
            )
        except anthropic.RateLimitError as exc:
            provider_health.record_failure("anthropic", "rate limited", rate_limited=True)
            raise ProviderError("anthropic", "rate limited — retry shortly", 429) from exc
        except anthropic.AuthenticationError as exc:
            provider_health.record_failure("anthropic", "authentication failed")
            raise ProviderError("anthropic", "API key rejected (401). Check ANTHROPIC_API_KEY.", 401) from exc
        except anthropic.APIStatusError as exc:
            provider_health.record_failure("anthropic", f"HTTP {exc.status_code}")
            raise ProviderError("anthropic", f"API error {exc.status_code}: {getattr(exc, 'message', exc)}", exc.status_code) from exc
        except anthropic.APIConnectionError as exc:
            provider_health.record_failure("anthropic", "connection error")
            raise ProviderError("anthropic", "could not reach the Anthropic API") from exc
        finally:
            await client.close()
        provider_health.record_success("anthropic")
        if resp.stop_reason == "refusal":
            cat = getattr(getattr(resp, "stop_details", None), "category", None)
            return AIResult("The model declined this request" + (f" (category: {cat})." if cat else "."), self.name, resp.model,
                            note="refusal")
        text = "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")
        note = "Response truncated at max_tokens." if resp.stop_reason == "max_tokens" else None
        usage = {"input_tokens": resp.usage.input_tokens, "output_tokens": resp.usage.output_tokens}
        return AIResult(text.strip(), self.name, resp.model, usage, note)


class OpenAIProvider(AIProvider):
    name = "openai"
    default_model = "gpt-4.1"

    def available(self) -> bool:
        return has_secret("OPENAI_API_KEY")

    async def complete(self, system: str, messages: list[dict[str, str]], max_tokens: int = 16000) -> AIResult:
        model = self.model()
        data = await http.request("openai", "POST", "https://api.openai.com/v1/chat/completions", timeout=240, retries=0,
                                  headers={"Authorization": f"Bearer {env('OPENAI_API_KEY')}"},
                                  json_body={"model": model, "max_completion_tokens": min(max_tokens, 16000),
                                             "messages": [{"role": "system", "content": system}, *messages]})
        choice = (data.get("choices") or [{}])[0]
        return AIResult((choice.get("message") or {}).get("content", "").strip(), self.name, data.get("model", model), data.get("usage"))


class OllamaProvider(AIProvider):
    name = "ollama"
    default_model = "llama3.1"

    def available(self) -> bool:
        return (env("AI_PROVIDER") or "").lower() == "ollama"

    async def complete(self, system: str, messages: list[dict[str, str]], max_tokens: int = 16000) -> AIResult:
        base = (env("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        model = self.model()
        data = await http.request("ollama", "POST", f"{base}/api/chat", timeout=300, retries=0,
                                  json_body={"model": model, "stream": False, "messages": [{"role": "system", "content": system}, *messages]})
        return AIResult(((data.get("message") or {}).get("content") or "").strip(), self.name, model)


PROVIDERS: dict[str, AIProvider] = {p.name: p for p in (AnthropicProvider(), OpenAIProvider(), OllamaProvider())}


def active_provider() -> AIProvider | None:
    choice = (env("AI_PROVIDER") or "auto").lower()
    if choice == "none":
        return None
    if choice in PROVIDERS:
        p = PROVIDERS[choice]
        return p if p.available() else None
    for name in ("anthropic", "openai", "ollama"):
        if PROVIDERS[name].available():
            return PROVIDERS[name]
    return None


def ai_status() -> dict[str, Any]:
    p = active_provider()
    return {
        "configured_choice": env("AI_PROVIDER") or "auto",
        "active": p.name if p else None,
        "model": p.model() if p else None,
        "providers": [{"id": k, "available": v.available(), "default_model": v.default_model} for k, v in PROVIDERS.items()],
        "offline_mode": p is None,
    }
