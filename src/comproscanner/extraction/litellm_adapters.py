"""Optional LiteLLM adapters used only by an explicitly executed run."""

from __future__ import annotations

import json
import os
import re
import base64
import mimetypes
from dataclasses import dataclass, field
from pathlib import Path
from comproscanner._paths import resolve_recorded_path
from typing import Any

from comproscanner.presets._shared import AgentPrompts, default_fact_fields
from comproscanner.evidence import Evidence
from comproscanner.extraction.evidence_flow import EvidenceDecision


@dataclass(frozen=True)
class ModelSettings:
    model: str
    timeout_seconds: int = 180
    api_base: str | None = None
    api_key_env: str | None = None

    parameters: dict = field(default_factory=dict)

    def api_key(self) -> str | None:
        if not self.api_key_env:
            return None
        value = os.getenv(self.api_key_env)
        if not value:
            raise RuntimeError(
                f"Required API key environment variable is missing: {self.api_key_env}"
            )
        return value


def _response_text(response) -> str:
    return response.choices[0].message.content.strip()


def _json_object(text: str) -> dict[str, Any]:
    stripped = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip())
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        start, end = stripped.find("{"), stripped.rfind("}")
        if start < 0 or end <= start:
            raise ValueError("Model response did not contain a JSON object")
        value = json.loads(stripped[start : end + 1])
    if not isinstance(value, dict):
        raise ValueError("Model response must be a JSON object")
    return value


class _LiteLLMClient:
    def __init__(self, settings: ModelSettings):
        self.settings = settings

    def complete(self, messages: list[dict[str, Any]]) -> str:
        from litellm import completion

        kwargs = {
            "model": self.settings.model,
            "messages": messages,
            "timeout": self.settings.timeout_seconds,
            "temperature": 0,
        }
        kwargs.update(self.settings.parameters)
        if self.settings.api_base:
            kwargs["api_base"] = self.settings.api_base
        api_key = self.settings.api_key()
        if api_key:
            kwargs["api_key"] = api_key
        return _response_text(completion(**kwargs))


class LiteLLMEvidenceIdentifier:
    """Apply the frozen property identifier policy to one Evidence at a time."""

    def __init__(
        self,
        settings: ModelSettings,
        scientific_query: str,
        prompts: AgentPrompts | None = None,
    ):
        self.client = _LiteLLMClient(settings)
        self.scientific_query = scientific_query
        self.prompts = prompts or AgentPrompts()

    def identify(self, evidence: Evidence) -> EvidenceDecision:
        prompt = self.prompts.identifier_template.format(
            scientific_query=self.scientific_query, content=evidence.content
        )
        raw = self.client.complete(
            [
                {
                    "role": "system",
                    "content": self.prompts.identifier_system,
                },
                {"role": "user", "content": prompt},
            ]
        )
        answer = str(_json_object(raw).get("answer", "no")).strip().casefold()
        if answer not in {"yes", "no"}:
            raise ValueError(f"Identifier returned an invalid answer: {answer}")
        return EvidenceDecision(evidence.evidence_id, answer == "yes", raw)


class LiteLLMEvidenceExtractor:
    """Extract zero or more facts from one accepted original Evidence."""

    def __init__(
        self,
        settings: ModelSettings,
        scientific_instructions: str,
        prompts: AgentPrompts | None = None,
        fact_fields: dict | None = None,
    ):
        self.client = _LiteLLMClient(settings)
        self.scientific_instructions = scientific_instructions
        self.prompts = prompts or AgentPrompts()
        self.fact_fields = (
            fact_fields if fact_fields is not None else default_fact_fields()
        )

    def extract(
        self, evidence: Evidence, *, visual_observation: str | None = None
    ) -> dict[str, Any]:
        visual_block = (
            f"\nVLM OBSERVATION (derived from the linked figure pixels):\n{visual_observation}\n"
            if visual_observation
            else ""
        )
        prompt = self.prompts.extractor_template.format(
            scientific_instructions=self.scientific_instructions,
            fact_shape=json.dumps(
                {"facts": [self.fact_fields]}, ensure_ascii=False, separators=(",", ":")
            ),
            source_type=evidence.source_type.value,
            content=evidence.content,
            visual_block=visual_block,
        )
        raw = self.client.complete(
            [
                {
                    "role": "system",
                    "content": self.prompts.extractor_system,
                },
                {"role": "user", "content": prompt},
            ]
        )
        parsed = _json_object(raw)
        if not isinstance(parsed.get("facts", []), list):
            raise ValueError("Extractor response field 'facts' must be a list")
        parsed["raw_response"] = raw
        return parsed


class LiteLLMFigureInterpreter:
    """Use a configured vision model to describe visible scientific content."""

    def __init__(self, settings: ModelSettings, prompts: AgentPrompts | None = None):
        self.client = _LiteLLMClient(settings)
        self.prompts = prompts or AgentPrompts()

    def interpret(self, evidence: Evidence) -> str:
        image_path = resolve_recorded_path(
            str(evidence.metadata.get("image_path", ""))
        ).resolve()
        if not image_path.is_file():
            raise FileNotFoundError(f"Figure image does not exist: {image_path}")
        mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
        encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
        prompt = self.prompts.vision_template.format(content=evidence.content)
        return self.client.complete(
            [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:{mime};base64,{encoded}"},
                        },
                    ],
                }
            ]
        )
