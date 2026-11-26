"""Anthropic Messages client with a sqlite cache and a mock path.

The API key is read by the official SDK from ANTHROPIC_API_KEY. This module
never accepts a key argument and never logs one.
"""

from __future__ import annotations

import hashlib
import sqlite3
import threading
from dataclasses import dataclass
from pathlib import Path

from collection_qa.prompts import SYSTEM_PROMPT


@dataclass
class Completion:
    text: str
    input_tokens: int
    output_tokens: int
    cached: bool


class LLMCache:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        with self._connect() as conn:
            conn.execute(
                """
                create table if not exists llm_cache (
                    key text primary key,
                    response text not null,
                    input_tokens integer not null,
                    output_tokens integer not null
                )
                """
            )

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        return conn

    def get(self, key: str) -> tuple[str, int, int] | None:
        with self._lock, self._connect() as conn:
            row = conn.execute(
                "select response, input_tokens, output_tokens from llm_cache where key = ?",
                (key,),
            ).fetchone()
        if row is None:
            return None
        return row["response"], int(row["input_tokens"]), int(row["output_tokens"])

    def put(self, key: str, text: str, input_tokens: int, output_tokens: int) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                insert into llm_cache (key, response, input_tokens, output_tokens)
                values (?, ?, ?, ?)
                on conflict(key) do update set
                    response = excluded.response,
                    input_tokens = excluded.input_tokens,
                    output_tokens = excluded.output_tokens
                """,
                (key, text, input_tokens, output_tokens),
            )


def cache_key(model: str, temperature: float | None, system: str, user: str) -> str:
    payload = f"{model}\n{temperature}\n{system}\n{user}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _text_from_response(response) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        block_type = getattr(block, "type", None)
        text = getattr(block, "text", None)
        if text and block_type in (None, "text"):
            parts.append(text)
    return "\n".join(parts).strip()


class AnthropicCompleter:
    def __init__(self, model: str, *, temperature: float | None = 0.5, cache: LLMCache | None = None, client=None):
        self.model = model
        self.temperature = temperature
        self.cache = cache
        self._client = client
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_hits = 0
        self.api_calls = 0

    def _client_or_create(self):
        if self._client is not None:
            return self._client
        import anthropic

        self._client = anthropic.Anthropic()
        return self._client

    def complete(self, user: str, *, system: str = SYSTEM_PROMPT, max_tokens: int = 400) -> Completion:
        key = cache_key(self.model, self.temperature, system, user)
        if self.cache is not None:
            hit = self.cache.get(key)
            if hit is not None:
                text, input_tokens, output_tokens = hit
                self.cache_hits += 1
                self.input_tokens += input_tokens
                self.output_tokens += output_tokens
                return Completion(text, input_tokens, output_tokens, cached=True)

        client = self._client_or_create()
        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        try:
            response = client.messages.create(**kwargs)
        except Exception as exc:  # anthropic.BadRequestError, without importing it eagerly
            message = str(exc).lower()
            if self.temperature is not None and "temperature" in message:
                kwargs.pop("temperature", None)
                response = client.messages.create(**kwargs)
            else:
                raise
        text = _text_from_response(response)
        usage = getattr(response, "usage", None)
        input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        self.api_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        if self.cache is not None:
            self.cache.put(key, text, input_tokens, output_tokens)
        return Completion(text, input_tokens, output_tokens, cached=False)
