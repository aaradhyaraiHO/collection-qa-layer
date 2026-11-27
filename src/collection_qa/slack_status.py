"""Optional Slack context for where an MMP sits.

The client is pluggable. The default uses a user token from SLACK_TOKEN and
Slack's search.messages method. No token means Slack is skipped, not failed.
"""

from __future__ import annotations

import json
import os
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Protocol

# Most advanced stage last. The first match from the end wins.
STAGE_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("assortment", ("assortment", "proposed assortment")),
    ("content_lock", ("content lock", "content locked")),
    ("src", ("src", "supply readiness")),
    ("bob", ("bob", "job card")),
    ("boqa", ("boqa", "bo qa", "bizops qa")),
    ("bizqa", ("bizqa", "biz qa")),
    ("campaign", ("campaign ticket", "campaigns launched", "campaign launch")),
)


@dataclass
class SlackHit:
    text: str
    permalink: str | None = None
    channel: str | None = None


@dataclass
class SlackSummary:
    queried: bool
    stage: str | None
    summary: str
    hits: list[SlackHit] = field(default_factory=list)
    error: str | None = None


class SlackClient(Protocol):
    def search(self, query: str) -> list[SlackHit]:
        """Return public hits the token can see. Empty when Slack is skipped."""


class SkippingSlack:
    def search(self, query: str) -> list[SlackHit]:
        return []


class EnvSlackClient:
    """Slack Web API search. Token stays in the environment, never in a spec."""

    def __init__(self, token: str | None = None, opener=None):
        self.token = token if token is not None else os.environ.get("SLACK_TOKEN", "")
        self.opener = opener or urllib.request.urlopen

    def search(self, query: str) -> list[SlackHit]:
        if not self.token:
            return []
        url = "https://slack.com/api/search.messages?" + urllib.parse.urlencode(
            {"query": query, "count": 20}
        )
        request = urllib.request.Request(url, headers={"Authorization": f"Bearer {self.token}"})
        with self.opener(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if not payload.get("ok", True) and payload.get("error"):
            raise RuntimeError(str(payload["error"]))
        matches = payload.get("messages", {}).get("matches", [])
        hits = []
        for match in matches:
            if not isinstance(match, dict):
                continue
            hits.append(
                SlackHit(
                    text=str(match.get("text") or ""),
                    permalink=match.get("permalink"),
                    channel=(match.get("channel") or {}).get("name")
                    if isinstance(match.get("channel"), dict)
                    else None,
                )
            )
        return hits


def infer_stage(hits: list[SlackHit]) -> str | None:
    blob = " ".join(hit.text for hit in hits).lower()
    found = None
    for stage, needles in STAGE_RULES:
        if any(needle in blob for needle in needles):
            found = stage
    return found


def summarize_slack(client: SlackClient, *, ce_id: str | None, name: str) -> SlackSummary:
    if isinstance(client, SkippingSlack) or (
        isinstance(client, EnvSlackClient) and not client.token
    ):
        return SlackSummary(
            queried=False,
            stage=None,
            summary="Slack was not queried. Set SLACK_TOKEN to add MMP stage context.",
        )
    label = ce_id or name
    query = (
        f'"{label}" (MMP OR SRC OR BOQA OR BizQA OR BOB OR assortment '
        f'OR "content lock" OR "campaign ticket")'
    )
    try:
        hits = client.search(query)
    except Exception as exc:
        return SlackSummary(queried=True, stage=None, summary="Slack search failed.", error=str(exc))
    stage = infer_stage(hits)
    if not hits:
        return SlackSummary(queried=True, stage=None, summary="No MMP or go-live thread matched.")
    excerpt = hits[0].text.replace("\n", " ")[:180]
    summary = f"{len(hits)} Slack hit(s). Latest stage keyword: {stage or 'unspecified'}. {excerpt}"
    return SlackSummary(queried=True, stage=stage, summary=summary, hits=hits)


def combine_status(*, page_live: bool, collection_found: bool, slack: SlackSummary) -> tuple[str, str | None]:
    """Return (LIVE | IN_PIPELINE | NOT_FOUND, stage)."""
    if page_live:
        return "LIVE", slack.stage
    if slack.stage or slack.hits:
        return "IN_PIPELINE", slack.stage or "mentioned"
    if collection_found:
        return "IN_PIPELINE", "no_bookable_cards"
    return "NOT_FOUND", None
