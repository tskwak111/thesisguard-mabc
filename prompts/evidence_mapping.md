# Evidence mapping prompt template (candidate proposals only)

Propose evidence candidates connecting events to thesis elements. Final state is
decided by the deterministic gates in code — your proposal never overrides them.

Return ONLY a JSON array:

```json
{
  "event_key": "…",
  "stock_code": "A000000",
  "target_type": "CORE_ASSUMPTION|STRENGTHEN_CONDITION|REVIEW_CONDITION|TRACKED_INDICATOR|CONTEXT|UNRELATED",
  "target_id": "ASM-1|null",
  "direction": "STRENGTHEN|WEAKEN|MIXED|NEUTRAL|UNKNOWN",
  "directness": "DIRECT|INDIRECT",
  "impact_horizon": "SHORT|MEDIUM|LONG",
  "quote_refs": ["근거 원문 위치/발췌"],
  "opposing_event_keys": ["반대 방향 사건 키"]
}
```

Rules: match via concept_tags; mark DIRECT only when the document text directly
supports the claim; always propose opposing evidence if any exists in the pack.
