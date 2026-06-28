"""LangChain chat model factory with provider switch (Ollama | OpenRouter | OpenAI)."""

from functools import lru_cache

from langchain_openai import ChatOpenAI

from app.config import get_settings


@lru_cache
def get_llm() -> ChatOpenAI:
    """Return a ChatOpenAI configured for the selected provider.

    All providers are OpenAI-compatible; Ollama and OpenRouter just override
    base_url (+ key), so a single ChatOpenAI client serves all three.
    """
    settings = get_settings()

    if settings.llm_provider == "ollama":
        # Local Ollama: OpenAI-compatible endpoint at /v1, no real key, no rate limit.
        return ChatOpenAI(
            model=settings.llm_model,
            api_key="ollama",
            base_url=f"{settings.ollama_base_url}/v1",
            temperature=0.2,
            timeout=180,
        )

    if settings.llm_provider == "openrouter":
        if not settings.openrouter_api_key:
            raise ValueError(
                "OPENROUTER_API_KEY tanımlı değil. .env dosyasını doldurun."
            )
        # OpenRouter needs namespaced ids (e.g. "openai/gpt-4o-mini").
        # Normalize a bare OpenAI-style name so the spec default still works.
        model = settings.llm_model
        if "/" not in model:
            model = f"openai/{model}"
        return ChatOpenAI(
            model=model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.2,
            timeout=60,
        )

    # default: openai
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY tanımlı değil. .env dosyasını doldurun.")
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key,
        temperature=0.2,
        timeout=60,
    )
