"""Rough USD cost for Anthropic Messages API calls.

Prices are the public base rates from the Claude models overview fetched
2026-11-26: https://platform.claude.com/docs/en/about-claude/models
They do not include prompt-cache writes, long-context surcharges, or thinking
tokens. The character-to-token ratio is a planning estimate.
"""

from __future__ import annotations

from dataclasses import dataclass

# USD per million tokens.
MODEL_PRICES: dict[str, dict[str, float]] = {
    "claude-sonnet-5-5": {"input": 2.0, "output": 10.0},
    "claude-sonnet-5": {"input": 2.0, "output": 10.0},
    "claude-haiku-5-5": {"input": 0.10, "output": 0.50},
    "claude-opus-5-5": {"input": 4.0, "output": 20.0},
    "claude-sonnet-4-6": {"input": 3.0, "output": 15.0},
    "claude-sonnet-4-5": {"input": 3.0, "output": 15.0},
}

PRICE_SOURCE = "https://platform.claude.com/docs/en/about-claude/models"
PRICE_AS_OF = "2026-11-26"
CHARS_PER_TOKEN = 4.0
ASSUMED_OUTPUT_TOKENS = 180


@dataclass
class CostEstimate:
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    usd: float
    priced: bool
    note: str

    def as_dict(self) -> dict:
        prices = MODEL_PRICES.get(self.model)
        return {
            "model": self.model,
            "calls": self.calls,
            "estimated_input_tokens": self.input_tokens,
            "estimated_output_tokens": self.output_tokens,
            "estimated_usd": round(self.usd, 4),
            "prices_per_mtok": prices,
            "prices_as_of": PRICE_AS_OF,
            "prices_source": PRICE_SOURCE,
            "priced": self.priced,
            "note": self.note,
        }


def estimate_cost(model: str, prompts: list[str], *, completions: int = 1) -> CostEstimate:
    calls = len(prompts) * max(completions, 1)
    characters = sum(len(prompt) for prompt in prompts) * max(completions, 1)
    input_tokens = int(round(characters / CHARS_PER_TOKEN))
    output_tokens = calls * ASSUMED_OUTPUT_TOKENS
    prices = MODEL_PRICES.get(model)
    if prices is None:
        return CostEstimate(
            model=model,
            calls=calls,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            usd=0.0,
            priced=False,
            note=(
                f"No stored price for {model}. Token counts are a 4-characters-per-token "
                "estimate and exclude thinking tokens."
            ),
        )
    usd = (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
    return CostEstimate(
        model=model,
        calls=calls,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        usd=usd,
        priced=True,
        note=(
            "Rough estimate at 4 characters per token and "
            f"{ASSUMED_OUTPUT_TOKENS} output tokens per call. Excludes Claude thinking tokens."
        ),
    )


def actual_cost(model: str, input_tokens: int, output_tokens: int) -> float | None:
    prices = MODEL_PRICES.get(model)
    if prices is None:
        return None
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000
