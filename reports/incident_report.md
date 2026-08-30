# Incident Report — Stale Support Knowledge Base Game Day

## Severity
P2 — customer-facing Support Agent can return obsolete policy, while checkout/order processing remains available.

## Summary
The KB ingestion batch remained structurally valid and its text-length distribution stayed normal, but all publication timestamps were approximately three hours behind the expected schedule. The 60-minute KB freshness SLO was violated. The affected branch was held from promotion so the last known-good RAG index could continue serving until a fresh publish completed.

## Detection
- Signal: `kb_contract.yaml` freshness check on `published_at` failed; text-length anomaly stayed false.
- First observed time: the first baseline validation after the injected stale-KB batch on 2026-08-30 UTC.

## Root Cause
The upstream KB publishing step delivered otherwise valid documents with stale `published_at` values. Evidence points to delayed publication rather than truncation or orders-pipeline corruption.

## Evidence
1. Baseline reported `KB contract failed checks: 1` after the stale-KB scenario and zero KB contract failures before it.
2. `KB length anomaly: False`, so document bodies did not collapse or truncate.
3. Orders contract had zero critical failures and row count remained 600, isolating the incident to the KB lineage branch.
4. Transitive lineage maps `kb_documents -> kb_active_docs -> rag_index -> support_agent`.

## Blast Radius

```text
kb_documents.published_at/content
-> kb_active_docs
-> rag_index.embedding
-> support_agent.answer
```

CEO revenue output is not downstream of the KB branch and is not impacted.

## Mitigation
- Block promotion of the stale KB batch and retain the last known-good active index.
- Re-run the publisher from the authoritative policy source.
- Warn Support/on-call that policy answers may be stale until verification succeeds.

## Recovery
Run `make reset` (simulation of a successful republish), rebuild the active index, then execute contract, retrieval-drift and smoke-answer checks before switching traffic.

## Verification
- [x] Contract healthy after reset
- [x] dbt tests healthy (19/19)
- [x] anomaly returned to expected range
- [x] SLO math and multi-window policy verified
- [x] downstream blast radius verified via transitive lineage

## Prevention / Action Items
| Action | Owner | Deadline | Why |
|---|---|---|---|
| Enforce KB freshness before index promotion | Support AI | Next sprint | Prevent stale policy from reaching retrieval |
| Alert on sustained multi-window freshness burn | Reliability | Next sprint | Page on actionable sustained failures, not spikes |
| Keep last known-good index and atomic alias swap | Search Platform | Next sprint | Make rollback immediate |
| Monitor embedding norms and retrieval quality | Support AI | Next sprint | Detect semantic/index drift beyond timestamps |
| Add Support Agent policy-answer smoke tests | Support QA | Next sprint | Verify user-visible recovery |
