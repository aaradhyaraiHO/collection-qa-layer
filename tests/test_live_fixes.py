"""Covers the fixes from the live Sonnet 5.5 pilot. No network calls."""

import sys
import types

import pytest

from collection_qa.checks import relative_ranking_issues, z_scores
from collection_qa.embeddings import DEFAULT_ST_MODEL
from collection_qa.llm import DEFAULT_MAX_RETRIES, DEFAULT_MAX_TOKENS, DEFAULT_TIMEOUT_SECONDS, LLMClient
from collection_qa.prompts import SYSTEM_PROMPT


def test_prompt_requires_short_english():
    assert "English only" in SYSTEM_PROMPT
    assert "80 words" in SYSTEM_PROMPT
    assert "2 to 4 sentences" in SYSTEM_PROMPT


def test_defaults_match_the_live_pilot_fixes():
    client = LLMClient(model="claude-sonnet-5-5", mock=True)
    assert client.max_tokens == DEFAULT_MAX_TOKENS >= 640
    assert client.timeout == DEFAULT_TIMEOUT_SECONDS == 90.0
    assert client.max_retries == DEFAULT_MAX_RETRIES == 5
    assert "multilingual" in DEFAULT_ST_MODEL


def test_live_client_does_not_send_temperature(monkeypatch: pytest.MonkeyPatch):
    captured: dict = {}

    class _Usage:
        input_tokens = 12
        output_tokens = 4

    class _Block:
        type = "text"
        text = "I would likely book this for the trip."

    class _Message:
        content = [_Block()]
        usage = _Usage()

    class _Messages:
        def create(self, **kwargs):
            captured["create"] = kwargs
            return _Message()

    class _Anthropic:
        def __init__(self, **kwargs):
            captured["client"] = kwargs
            self.messages = _Messages()

    fake = types.ModuleType("anthropic")
    fake.Anthropic = _Anthropic
    monkeypatch.setitem(sys.modules, "anthropic", fake)
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key-not-used")

    client = LLMClient(
        model="claude-sonnet-5-5",
        mock=False,
        temperature=0.5,
        max_tokens=640,
        timeout=90.0,
        max_retries=5,
    )
    result = client._anthropic("How likely are you to book this?")
    assert result.generator == "anthropic"
    assert "temperature" not in captured["create"]
    assert captured["create"]["max_tokens"] == 640
    assert captured["create"]["model"] == "claude-sonnet-5-5"
    assert captured["client"]["timeout"] == 90.0
    assert captured["client"]["max_retries"] == 5
    assert captured["client"]["api_key"] == "test-key-not-used"


def test_z_scores_are_centered_and_signed():
    scores = z_scores({"low": 1.0, "mid": 2.0, "high": 3.0})
    assert scores["mid"] == pytest.approx(0.0)
    assert scores["low"] < 0 < scores["high"]
    assert scores["low"] == pytest.approx(-scores["high"])
    assert z_scores({"only": 3.2}) == {"only": 0.0}
    assert z_scores({"a": 3.2, "b": 3.2}) == {"a": 0.0, "b": 0.0}


def test_compressed_band_warns_and_a_low_outlier_is_relative():
    tight = {"a": 3.20, "b": 3.30, "c": 3.40, "d": 3.35}
    issues = relative_ranking_issues(tight, {key: key for key in tight})
    assert any(issue.code == "score_compression" and issue.severity == "warn" for issue in issues)
    spread_out = {"cruise": 3.4, "day": 3.45, "premium": 3.42, "fly": 2.2}
    ranked = relative_ranking_issues(spread_out, {"fly": "Fly cruise"})
    lows = [issue for issue in ranked if issue.code == "relative_rank"]
    assert len(lows) == 1
    assert lows[0].evidence["key"] == "fly"
    assert lows[0].severity == "fail"
    assert "Fly cruise" in lows[0].message
    assert not any(issue.code == "score_compression" for issue in ranked)
