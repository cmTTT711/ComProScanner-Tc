"""Shared preset defaults. Property definitions may override every policy here.

The default text is the validated per-Evidence prompt, including whitespace.
Credentials are environment variable *names*, never values.
"""

from dataclasses import dataclass


def default_models():
    return {
        "identifier": {
            "model": "openai/qwen-flash",
            "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
            "api_key_env": "DASHSCOPE_API_KEY",
        },
        "extractor": {
            "model": "deepseek/deepseek-v4-flash",
            "base_url": None,
            "api_key_env": None,
        },
        "vision": {"model": None, "base_url": None, "api_key_env": None},
    }


def default_fact_fields():
    return {
        "material_reported": "...",
        "property": "...",
        "value": 0,
        "unit": "...",
        "qualifier": None,
        "conditions": {},
    }


@dataclass(frozen=True)
class AgentPrompts:
    identifier_system: str = (
        "You identify material-property evidence in scientific articles."
    )
    identifier_template: str = (
        "{scientific_query}\n\nEvaluate only the following original article evidence. Return exactly "
        '{{"answer":"yes"}} or {{"answer":"no"}}.\n\nEVIDENCE:\n{content}'
    )
    extractor_system: str = (
        "You extract traceable material-property facts from scientific evidence."
    )
    extractor_template: str = """{scientific_instructions}

Extract every supported material-property fact from only the original evidence below.
Do not use external knowledge. Preserve approximate/above/below/range meaning.
Return JSON only in this shape:
{fact_shape}
Return {{"facts":[]}} when no fact is explicitly supported.

EVIDENCE TYPE: {source_type}
ORIGINAL EVIDENCE:
{content}
{visual_block}
"""
    vision_template: str = (
        "Read this scientific figure. Report only content visibly supported by "
        "the pixels: labels, legend, axes, material names, values and qualifiers. "
        "Do not infer missing values.\n\nCAPTION AND NEARBY ORIGINAL TEXT:\n{content}"
    )


def default_rag_settings():
    return {
        "embedding_model": "huggingface:thellert/physbert_cased",
        "rag_max_tokens": 512,
        "rag_top_k": 3,
    }
