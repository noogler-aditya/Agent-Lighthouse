"""
Model pricing utilities for auto-instrumentation.
Best-effort: missing models return cost 0.0.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, Optional

import logging

logger = logging.getLogger("agent_lighthouse.pricing")


@dataclass(frozen=True)
class ModelPricing:
    prompt_per_1k: float
    completion_per_1k: float


_DEFAULT_PRICING: Dict[str, ModelPricing] = {
    # OpenAI (sample defaults, override as needed)
    "gpt-4": ModelPricing(prompt_per_1k=0.03, completion_per_1k=0.06),
    "gpt-4-turbo": ModelPricing(prompt_per_1k=0.01, completion_per_1k=0.03),
    "gpt-3.5-turbo": ModelPricing(prompt_per_1k=0.0005, completion_per_1k=0.0015),
    # Anthropic (sample defaults, override as needed)
    "claude-3-opus": ModelPricing(prompt_per_1k=0.015, completion_per_1k=0.075),
    "claude-3-sonnet": ModelPricing(prompt_per_1k=0.003, completion_per_1k=0.015),
    "claude-3-haiku": ModelPricing(prompt_per_1k=0.00025, completion_per_1k=0.00125),
}

_cached_pricing: Optional[Dict[str, ModelPricing]] = None


def _load_override_from_json(text: str) -> Dict[str, ModelPricing]:
    data = json.loads(text)
    out: Dict[str, ModelPricing] = {}
    for model, entry in data.items():
        prompt = float(entry.get("prompt_per_1k", 0.0))
        completion = float(entry.get("completion_per_1k", 0.0))
        out[model] = ModelPricing(prompt_per_1k=prompt, completion_per_1k=completion)
    return out


def _load_pricing() -> Dict[str, ModelPricing]:
    """
    Resolve pricing from override env vars, with fallback to defaults.
    Precedence:
      1) LIGHTHOUSE_PRICING_JSON
      2) LIGHTHOUSE_PRICING_PATH
      3) built-in defaults
    """
    override_json = os.getenv("LIGHTHOUSE_PRICING_JSON")
    if override_json:
        try:
            return _load_override_from_json(override_json)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid LIGHTHOUSE_PRICING_JSON override: %s", exc)

    override_path = os.getenv("LIGHTHOUSE_PRICING_PATH")
    if override_path:
        try:
            with open(override_path, "r", encoding="utf-8") as f:
                return _load_override_from_json(f.read())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Invalid LIGHTHOUSE_PRICING_PATH override: %s", exc)

    return dict(_DEFAULT_PRICING)


def get_pricing_table() -> Dict[str, ModelPricing]:
    global _cached_pricing
    if _cached_pricing is None:
        _cached_pricing = _load_pricing()
    return _cached_pricing


def get_cost_usd(model: Optional[str], prompt_tokens: int, completion_tokens: int) -> float:
    if not model:
        return 0.0
    table = get_pricing_table()
    pricing = table.get(model)
    if not pricing:
        return 0.0
    return (prompt_tokens / 1000) * pricing.prompt_per_1k + (
        completion_tokens / 1000
    ) * pricing.completion_per_1k


def reset_pricing_cache() -> None:
    global _cached_pricing
    _cached_pricing = None
