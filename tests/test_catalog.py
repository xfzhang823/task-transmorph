from task_transmorph import get_provider_model_catalog
from task_transmorph.providers import (
    DEFAULT_DEEPSEEK_MODEL,
    DEFAULT_GEMINI_MODEL,
    DEFAULT_OPENAI_MODEL,
    DEFAULT_TRANSFORMATION_EVALUATOR_MODEL,
    DeepSeekProviderConfig,
    GeminiProviderConfig,
    OpenAIProviderConfig,
)


def test_provider_model_catalog_contains_curated_display_options():
    catalog = get_provider_model_catalog()

    assert [item["provider_id"] for item in catalog] == [
        "openai",
        "gemini",
        "deepseek",
    ]
    assert [item["label"] for item in catalog] == [
        "OpenAI",
        "Gemini",
        "DeepSeek",
    ]
    assert catalog[0]["model_options"] == (
        ("Provider default", ""),
        ("gpt-6-luna", "gpt-6-luna"),
        ("gpt-6.1-sol", "gpt-6.1-sol"),
        ("gpt-6-astra", "gpt-6-astra"),
        ("gpt-5.5", "gpt-5.5"),
        ("gpt-4o-mini", "gpt-4o-mini"),
    )
    assert catalog[1]["model_options"][0] == ("Provider default", "")
    assert catalog[2]["model_options"][-1] == (
        "DeepSeek V4 Pro (legacy comparison)",
        "deepseek-v4-pro",
    )


def test_catalog_defaults_match_provider_configuration_defaults():
    by_id = {item["provider_id"]: item for item in get_provider_model_catalog()}

    assert by_id["openai"]["default_model"] == DEFAULT_OPENAI_MODEL
    assert by_id["openai"]["default_model"] == OpenAIProviderConfig().model
    assert (
        by_id["openai"]["transformation_evaluator_default"]
        == DEFAULT_TRANSFORMATION_EVALUATOR_MODEL
    )
    assert by_id["gemini"]["default_model"] == DEFAULT_GEMINI_MODEL
    assert by_id["gemini"]["default_model"] == GeminiProviderConfig().model
    assert by_id["gemini"]["transformation_evaluator_default"] is None
    assert by_id["deepseek"]["default_model"] == DEFAULT_DEEPSEEK_MODEL
    assert by_id["deepseek"]["default_model"] == DeepSeekProviderConfig().model
    assert by_id["deepseek"]["transformation_evaluator_default"] is None


def test_catalog_keeps_main_and_transformation_evaluator_defaults_distinct():
    openai = next(
        item for item in get_provider_model_catalog() if item["provider_id"] == "openai"
    )

    assert openai["default_model"] != openai["transformation_evaluator_default"]
