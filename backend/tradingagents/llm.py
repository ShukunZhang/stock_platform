"""LLM factory for DeepSeek via OpenAI-compatible API."""

from __future__ import annotations

from langchain_openai import ChatOpenAI

from tradingagents.config import settings


def get_llm(temperature: float | None = None) -> ChatOpenAI:
    if not settings.deepseek_api_key:
        raise RuntimeError(
            "DEEPSEEK_API_KEY is not set. Add it to .env before running analysis."
        )

    return ChatOpenAI(
        model=settings.deepseek_model,
        api_key=settings.deepseek_api_key,
        base_url=settings.deepseek_base_url,
        temperature=settings.temperature if temperature is None else temperature,
    )
