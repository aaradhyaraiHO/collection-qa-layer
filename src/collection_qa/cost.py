"""Token cost estimates for the Anthropic Messages API.

Prices are USD per million tokens, read from Anthropic's model overview on
2026-11-26. Haiku's published price is a floor ('from'). Unknown model ids use
Sonnet 5.5 rates and set `price_known` false so the printout can say so.
"""

from __future__ import annotations

from dataclasses import dataclass

# (input USD / MTok, output USD / MTok)
MODEL_PRICES: dict[str, tuple[float, float]] = {
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-sonnet-5": (3.0, 15.0),
    "claude-haiku-5-5": (0.10, 0.50),
    "claude-opus-5-5": (4.0, 20.0),
    "claude-fable-5-2": (8.0, 40.0),
}

DEFAULT_MODEL = "claude-sonnet-5-5"

# Rough prompt sizes used only for the pre-run estimate.
EST_INPUT_TOKENS_PER_CALL = 900
EST_OUTPUT_TOKENS_PER_CALL = 140


@dataclass(frozen=True)
class CostEstimate:
    model: str
    calls: int
    input_tokens: int
    output_tokens: int
    input_usd_per_mtok: float
    output_usd_per_mtok: float
    usd: float
    price_known: bool
    actual_usage: bool

    def lines(self) -> list[str]:
        kind = "actual API usage" if self.actual_usage else "pre-run estimate"
        known = "published price" if self.price_known else "UNKNOWN MODEL, using Sonnet 5.5 rates"
        return [
            f"Cost ({kind}, {known})",
            f"  model: {self.model}",
            f"  calls: {self.calls}",
            f"  input tokens: {self.input_tokens}",
            f"  output tokens: {self.output_tokens}",
            f"  rates: ${self.input_usd_per_mtok}/MTok in, ${self.output_usd_per_mtok}/MTok out",
            f"  estimated USD: ${self.usd:.4f}",
        ]


def prices_for(model: str) -> tuple[float, float, bool]:
    if model in MODEL_PRICES:
        inp, out = MODEL_PRICES[model]
        return inp, out, True
    inp, out = MODEL_PRICES[DEFAULT_MODEL]
    return inp, out, False


def estimate_cost(
    *,
    model: str,
    calls: int,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    actual_usage: bool = False,
) -> CostEstimate:
    inp_rate, out_rate, known = prices_for(model)
    in_tok = EST_INPUT_TOKENS_PER_CALL * calls if input_tokens is None else input_tokens
    out_tok = EST_OUTPUT_TOKENS_PER_CALL * calls if output_tokens is None else output_tokens
    usd = (in_tok / 1_000_000) * inp_rate + (out_tok / 1_000_000) * out_rate
    return CostEstimate(
        model=model,
        calls=calls,
        input_tokens=in_tok,
        output_tokens=out_tok,
        input_usd_per_mtok=inp_rate,
        output_usd_per_mtok=out_rate,
        usd=usd,
        price_known=known,
        actual_usage=actual_usage,
    )


def planned_calls(
    *,
    n_personas: int,
    n_products: int,
    n_surfaces: int,
    gates: set[str],
    completions: int,
) -> int:
    per_persona = 0
    if "A" in gates:
        per_persona += n_products
    if "B" in gates:
        per_persona += n_surfaces
    return n_personas * per_persona * completions
