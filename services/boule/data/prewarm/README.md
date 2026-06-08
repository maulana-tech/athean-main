# Boule LLM response cache — prewarm bundle

Each `.json` file in this directory is a SHA-256-keyed snapshot of one
LLM round-1 / round-4 response, captured during a live deliberation
against the synthetic BTC-$115k signal that ships in
`scripts/try_council_gemini.py`.

## Why this exists

The Boule council fires ~30 calls per deliberation. On the default
fallback chain (Claude → Gemini 3.5 Flash → Gemini 2.5 Flash-Lite),
that costs $0.10–0.80 per run depending on which stage answers and
free-tier quotas being what they are, a judge replaying the script
back-to-back without quota will hit a wall.

When `scripts/try_council_gemini.py` boots it copies anything in this
directory into the local `.cache/boule-llm/` so identical prompts hit
cached responses with zero network cost. The cache key is
`sha256(provider, model, system_prompt, messages, max_tokens)` so a
prewarmed entry only serves an *identical* re-run — tweak the signal
and you're back to live LLM calls.

## Updating the bundle

```bash
rm -rf .cache/boule-llm/
uv run --project services/boule python scripts/try_council_gemini.py
cp .cache/boule-llm/*.json services/boule/data/prewarm/
```

The output is deterministic when `BOULE_LLM_DETERMINISTIC=1` is set
(temperature 0, top_p 1, seed 42 on Gemini).

## What's NOT cached

* Anthropic responses — only Gemini cache entries are checked in here.
  Add the Anthropic key + run the same script to add Anthropic prewarm
  entries if you want the head of the chain to also serve cached.
* The Areopagus EV / Kelly path — those are deterministic functions of
  the thesis and don't need caching.
* The Redis trace stream — events stream live regardless of cache hits.
