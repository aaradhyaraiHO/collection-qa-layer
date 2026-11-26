# Live persona-mix sensitivity

Both collections stop here. `reports/live/masai-mara.json` and `reports/live/milford-sound-cruises.json` do not contain `panel_scores`, so the mix cannot be reweighted without inventing persona-level ratings.

Each `*.sensitivity.md` in this folder is that gap, not a robustness verdict. There is no ROBUST or WEIGHT-SENSITIVE call on the live rankings until the scorecards are regenerated from the sqlite cache.

What the cache re-run has to match, or it will miss and call Claude again:

- seed 7, 30 personas, model `claude-sonnet-5-5`
- `max_tokens` 320
- client temperature field 0.5 (it is part of the cache key; it was not sent to the API)
- the original system prompt, stored on each JSON file as `original_system_prompt`
- embedder `sentence-transformers/all-MiniLM-L6-v2` if the new means should match these live files

The regenerated scorecard includes `panel_scores`. Then:

```bash
collection-qa sensitivity specs/masai-mara.yaml \
  --from-run <regenerated.json> --out reports/live/sensitivity
```

A segment mean still will not depend on the mix. Only the blended page number and the overall ranking will.
