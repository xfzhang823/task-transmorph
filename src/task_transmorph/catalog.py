"""Public display metadata for the built-in providers and model choices."""


def get_provider_model_catalog() -> tuple[dict[str, object], ...]:
    """Return the curated provider/model choices for display surfaces.

    The empty model value in a ``model_options`` pair means "use the
    provider's configured default". Catalog membership is display metadata;
    it does not guarantee that a provider account currently offers a model.
    """
    from task_transmorph.providers.deepseek import (
        DEFAULT_DEEPSEEK_MODEL,
        DeepSeekDecompositionProvider,
        DeepSeekProviderConfig,
    )
    from task_transmorph.providers.gemini import (
        DEFAULT_GEMINI_MODEL,
        GeminiDecompositionProvider,
        GeminiProviderConfig,
    )
    from task_transmorph.providers.openai import (
        DEFAULT_OPENAI_MODEL,
        DEFAULT_TRANSFORMATION_EVALUATOR_MODEL,
        OpenAIDecompositionProvider,
        OpenAIProviderConfig,
    )

    specs = (
        (
            OpenAIDecompositionProvider,
            OpenAIProviderConfig,
            "OpenAI",
            (
                ("Provider default", ""),
                ("gpt-6-luna", "gpt-6-luna"),
                ("gpt-6.1-sol", "gpt-6.1-sol"),
                ("gpt-6-astra", "gpt-6-astra"),
                ("gpt-5.5", "gpt-5.5"),
                ("gpt-4o-mini", "gpt-4o-mini"),
            ),
            DEFAULT_OPENAI_MODEL,
            DEFAULT_TRANSFORMATION_EVALUATOR_MODEL,
        ),
        (
            GeminiDecompositionProvider,
            GeminiProviderConfig,
            "Gemini",
            (
                ("Provider default", ""),
                ("gemini-3.5-flash-lite", "gemini-3.5-flash-lite"),
                ("gemini-3.8-flash", "gemini-3.8-flash"),
                ("gemini-4-argon", "gemini-4-argon"),
            ),
            DEFAULT_GEMINI_MODEL,
            None,
        ),
        (
            DeepSeekDecompositionProvider,
            DeepSeekProviderConfig,
            "DeepSeek",
            (
                ("Provider default (V4.1 Flash)", ""),
                ("DeepSeek V4.1 Flash (current)", "deepseek-flash"),
                ("DeepSeek V4 Pro (legacy comparison)", "deepseek-v4-pro"),
            ),
            DEFAULT_DEEPSEEK_MODEL,
            None,
        ),
    )
    catalog = []
    for (
        provider_type,
        config_type,
        label,
        model_options,
        default_model,
        evaluator_default,
    ) in specs:
        if config_type().model != default_model:
            raise RuntimeError(
                f"catalog default does not match {provider_type.provider_id} config"
            )
        catalog.append(
            {
                "provider_id": provider_type.provider_id,
                "label": label,
                "model_options": model_options,
                "default_model": default_model,
                "transformation_evaluator_default": evaluator_default,
            }
        )
    return tuple(catalog)


__all__ = ["get_provider_model_catalog"]
