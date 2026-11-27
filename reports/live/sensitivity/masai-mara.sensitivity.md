# Persona-mix sensitivity: masai-mara

This scorecard has no panel_scores, so the mix cannot be reweighted without new model calls.

The committed live files store aggregated pmfs, segment means, a handful of quotes, the design weights, and the seed. They do not store each persona's attributes together with that persona's purchase-intent mean.

Regenerate from the live sqlite cache. The cache key is the hash of model, mock flag, the client temperature field (0.5, even though Sonnet 5.5 is not sent a temperature), max_tokens, the system prompt, the user prompt, and the completion index. The live run used max_tokens 320 and the system prompt from before the English-only wording change. A re-run with today's prompt or with the 640 token cap will miss the cache and call Claude again.

Use the same seed (7), 30 personas, model claude-sonnet-5-5, and embedder sentence-transformers/all-MiniLM-L6-v2 if the new means should match these files. The regenerated scorecard will contain panel_scores. Then run:

collection-qa sensitivity <spec> --from-run <regenerated.json> --out reports/live/sensitivity

