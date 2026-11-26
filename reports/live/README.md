# Live pilot scorecards

Claude Sonnet 5.5 (`claude-sonnet-5-5`), 30 personas, seed **7**, run on 2026-11-26. 780 calls, about US$3.15. Embeddings were English-only `all-MiniLM-L6-v2`. Reply cap was 320 tokens.

These files are the run as it finished. They are not MOCK. They also predate the follow-up fixes, so they do not contain z-scores:

- The API temperature argument was already removed on the machine that ran this, which is why the run completed.
- About 15% of replies were cut off at 320 tokens.
- 25 replies are in German or French. The English-only embedder scored them anyway.
- Product means sit in about 3.17–3.46, so the absolute pass lines mostly warn.

The code defaults are now a 640-token cap, an English-only prompt, a multilingual embedder, a 90-second timeout with 5 retries, and relative z-scores. Re-run to pick those up. Until a conversion backtest exists, rank products inside a collection instead of applying the 3.6 / 3.4 / 3.3 cuts.
