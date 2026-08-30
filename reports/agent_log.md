# AI Agent Decision Log

## Decision 1 — Contract enforcement
- Hypothesis: CSV parsing can hide type drift, and deterministic schema failures should stop bad commerce data before dbt.
- Prompt / request to agent: Implement the lab phases while retaining `student_api.py`.
- Agent proposal: Validate parseable integer/number/datetime/string types, required columns, freshness, and attach severity-aware actions.
- Evidence/test: `test_type_and_freshness_drift` passes; duplicate scenario reports one critical contract failure.
- Accept / reject / revise: Accept.
- Why: It detects missing/type/duplicate/stale failures without changing the stable API.

## Decision 2 — GX validation and quarantine
- Hypothesis: Individual expectations do not provide a reusable operational validation flow.
- Agent proposal: Build an Expectation Suite, ValidationDefinition and Checkpoint; quarantine a failed critical batch locally.
- Evidence/test: Healthy `gx/validate_orders.py` passes; duplicate scenario fails and writes `reports/quarantine_orders.csv`.
- Accept / reject / revise: Accept for this local lab.
- Why: It demonstrates an executable action without an external notification/storage dependency.

## Decision 3 — SCD revenue protection
- Hypothesis: Two active customer versions multiply joined order rows and inflate CEO revenue.
- Agent proposal: Deduplicate active customer keys at the join boundary, add a singular active-version test and a minimal dbt unit test.
- Evidence/test: `dbt build` passes 19/19 resources including `duplicate_active_customer_does_not_inflate_revenue`.
- Accept / reject / revise: Accept.
- Why: The data test detects the upstream invariant violation while the unit test proves transformation behavior.

## Decision 4 — Robust anomaly baseline
- Hypothesis: Mean/std Z-score is unstable with outliers, zero variance and weekday seasonality.
- Agent proposal: Keep Z-score for explicit use; use same-segment median/MAD in `auto`, handle zero MAD, and allow known-event suppression.
- Evidence/test: A legitimate Saturday segment is not anomalous; the 150/600 volume-drop scenario is anomalous with score 7.55.
- Accept / reject / revise: Revised baseline caller to use full history because the reset fixture always contains 600 rows regardless of runtime weekday.
- Why: This prevents a false positive on the documented healthy fixture while preserving context-aware API behavior.

## Decision 5 — Distribution and RAG drift
- Hypothesis: Mean ratio misses shape drift, and embedding norm collapse/expansion can degrade retrieval without changing document count.
- Agent proposal: Combine an empirical two-sample KS signal with mean ratio and implement a robust median/MAD embedding-norm detector.
- Evidence/test: Same-mean/different-shape and large embedding-norm shift tests both pass.
- Accept / reject / revise: Accept.
- Why: Both signals are local, deterministic and require no model download.

## Decision 6 — Lineage and SLO alerting
- Hypothesis: Direct-only column lineage underestimates blast radius; a short burn spike should not wake on-call.
- Agent proposal: BFS for transitive column lineage and paired-window burn thresholds requiring both windows to be elevated before paging.
- Evidence/test: Three-hop column traversal passes; burns `(20, 2)` do not page while `(20, 15)` page critical.
- Accept / reject / revise: Accept.
- Why: Results are actionable and cover both missed-impact and alert-fatigue risks.

## Phase 0 system understanding
- Critical datasets: `orders` (business revenue) and `kb_documents` (Support Agent policy correctness).
- Consumers: `fct_daily_revenue` and CEO dashboard for orders; active KB, RAG index and Support Agent for documents.
- Trust signals: contract failures, freshness delay, row-count/distribution anomalies, dbt failures, retrieval drift and SLO burn rate.

`not_null` and `unique` are data tests because they inspect records produced from real data. A dbt unit test supplies controlled input rows and checks exact transformation output, isolating SQL logic such as join cardinality.

Z-score can fail when standard deviation is zero, outliers distort mean/std, traffic is seasonal, or a trend makes the historic mean obsolete. The `auto` policy therefore uses robust and segmented history when supplied.
