# Hindsight Integration

Sentinel uses Hindsight as its memory and consolidated-knowledge layer. The wrapper in `backend/memory_client.py` intentionally uses the HTTP API directly so request contracts remain visible and testable.

## Authentication and bank isolation

Cloud requests send `Authorization: Bearer <HINDSIGHT_API_KEY>`. Each team should receive a separate `HINDSIGHT_BANK_ID`; reads from a missing or mistyped bank return `404` rather than silently acting like empty memory.

## Retain

`POST /v1/default/banks/{bank_id}/memories`

```json
{
  "items": [
    {
      "content": "INCIDENT INC-1047 ...",
      "context": "SRE production incident postmortem...",
      "timestamp": "2026-09-10T02:14:00+00:00",
      "document_id": "INC-1047"
    }
  ],
  "tags": [
    "service:checkout-service",
    "root-cause:redis-pool-exhaustion",
    "status:resolved"
  ]
}
```

Stable `document_id` values make repeated seeding an upsert rather than duplicate ingestion.

## Recall

`POST /v1/default/banks/{bank_id}/memories/recall`

```json
{
  "query": "checkout-service SEV-2 at 02:11 UTC; Redis pool wait rising; payments v2.5 deployed",
  "tags": ["service:checkout-service"],
  "tags_match": "all_strict",
  "types": ["experience", "world", "observation"],
  "max_tokens": 4096
}
```

The current API field is `types`, not `fact_types`. Each result provides an extracted fact, tags, document ID, timestamps, and stage scores. Sentinel exposes the final/reranker score as a relative recall score; it must not be interpreted as a calibrated probability.

Hindsight may return several extracted facts for one retained incident. Sentinel maps citations to `document_id` when available and deduplicates occurrence counts by that ID.

## Mental model

Mental models are explicit saved reflect responses. Seeding creates one with ID `checkout-redis-pattern`:

`POST /v1/default/banks/{bank_id}/mental-models`

```json
{
  "id": "checkout-redis-pattern",
  "name": "Checkout Redis exhaustion pattern",
  "source_query": "What recurring checkout Redis incidents, triggers, mitigations, and unresolved fixes exist?",
  "tags": ["service:checkout-service", "root-cause:redis-pool-exhaustion"],
  "trigger": {"refresh_after_consolidation": true}
}
```

Analysis fetches it with:

`GET /v1/default/banks/{bank_id}/mental-models/checkout-redis-pattern`

The model is not sent to analysis unless recall produced at least two memories. This prevents a persisted summary from making a freshly reset demo appear informed before evidence has been recalled.

## AI analyzer boundary

The default Groq path uses `openai/gpt-oss-120b` with JSON-object mode. The prompt includes the alert, recalled memories, mental model, and the `SentinelResponse` JSON schema. Pydantic performs actual schema validation and the client retries once on contract failure. When `GEMINI_API_KEY` is configured, `gemini-3.6-flash` is a provider-level failover after a Groq HTTP or contract failure; it is subject to the same citation allow-list.

After parsing, Sentinel verifies every `cited_memory_id` and every hypothesis evidence ID belongs to the current recall set. A response with an invented incident ID is rejected.

## Reset semantics

`DELETE /v1/default/banks/{bank_id}/memories` clears retained memories. A configured mental-model object can remain in the bank, so the orchestrator's evidence threshold is part of reset integrity. For fully isolated stage rehearsals, use a fresh bank ID as well.

## Source references

- Hindsight Swagger/OpenAPI: <https://api.hindsight.vectorize.io/docs>
- Hindsight recall concepts: <https://hindsight.vectorize.io/developer/api/recall>
- Hindsight retain concepts: <https://hindsight.vectorize.io/developer/api/retain>
- Groq structured output: <https://console.groq.com/docs/structured-outputs>
