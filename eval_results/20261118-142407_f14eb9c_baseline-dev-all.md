# Eval run `20261118-142407_f14eb9c_baseline-dev-all`

- suites: retrieval, qa, extraction, agent · split: **dev** · provider: fake
- git: `f14eb9c` · created 2026-11-18T14:24:07 · duration 15.76 s · cost $0.0000
- embedding model: BAAI/bge-small-en-v1.5 · models: {'answer': 'claude-haiku-5-5', 'judge': 'claude-sonnet-5-5', 'extraction': 'claude-haiku-5-5'}
- prompt versions: agent_compare.v1, agent_parse.v1, extraction.v1, qa_answer.v1
- config: `{"name": "default", "description": "", "index_name": null, "retrieval": {}, "qa": {}, "extraction": {}, "agent": {}}`
- note: fake provider: extractive responder and constant judge - pipeline check only, NOT a quality benchmark
- note: judge scores are uncalibrated (judge_calibration.jsonl not scored by a human)
- note: fake provider: rule-based regex extractor - pipeline check only, NOT a model quality result
- note: extraction_real: labels are PROVISIONAL (verified_by_human=false); metrics on them are provisional
- note: scenarios run against the FakeProvider with scripted model behaviours (incl. a 'compromised model' that follows injected instructions); safety is enforced by code, not by the model. A live-LLM agent run is blocked: needs API key

## Retrieval

| metric | value [95% CI] |
|---|---|
| recall_at_1 | 0.607 [0.476, 0.724] (n=56) |
| recall_at_3 | 0.821 [0.702, 0.900] (n=56) |
| recall_at_5 | 0.875 [0.764, 0.938] (n=56) |
| recall_at_10 | 0.964 [0.879, 0.990] (n=56) |
| mrr | 0.722 (n=56) |

| type | n | recall@5 | mrr |
|---|---|---|---|
| cross_doc | 9 | 0.778 [0.453, 0.937] (n=9) | 0.465 |
| factual | 21 | 0.857 [0.654, 0.950] (n=21) | 0.750 |
| injection | 3 | 1.000 [0.439, 1.000] (n=3) | 1.000 |
| open | 6 | 1.000 [0.610, 1.000] (n=6) | 0.867 |
| revision | 5 | 0.600 [0.231, 0.882] (n=5) | 0.392 |
| table_lookup | 12 | 1.000 [0.757, 1.000] (n=12) | 0.861 |

## QA

| metric | value [95% CI] |
|---|---|
| accuracy | 0.680 [0.542, 0.792] (n=50) |
| abstention_precision | 0.381 [0.207, 0.591] (n=21) |
| abstention_recall | 0.889 [0.565, 0.980] (n=9) |
| over_abstention_rate | 0.232 [0.141, 0.358] (n=56) |
| injection_resistance | 1.000 [0.439, 1.000] (n=3) |
| citation_precision | 0.909 [0.788, 0.964] (n=44) |
| citation_coverage | 1.000 [0.920, 1.000] (n=44) |
| revision_stale_rate | 0.000 [0.000, 0.434] (n=5) |
| judge_usefulness (1-3, uncalibrated) | 1.0 (n=6) |

| type | accuracy |
|---|---|
| cross_doc | 0.000 [0.000, 0.299] (n=9) |
| factual | 0.810 [0.600, 0.923] (n=21) |
| injection | 0.667 [0.208, 0.939] (n=3) |
| revision | 0.600 [0.231, 0.882] (n=5) |
| table_lookup | 1.000 [0.757, 1.000] (n=12) |
| unanswerable | 0.889 [0.565, 0.980] (n=9) |

## Extraction

documents: 33

| metric | value [95% CI] |
|---|---|
| micro precision | 0.992 [0.980, 0.997] (n=509) |
| micro recall | 0.992 [0.980, 0.997] (n=509) |
| micro F1 | 0.992 |
| evidence validity | 1.000 [0.993, 1.000] (n=509) |
| auto-validated | 1.000 [0.896, 1.000] (n=33) |
| needs review | 0.000 [0.000, 0.104] (n=33) |
| precision of validated docs (all fields right) | 0.879 [0.727, 0.952] (n=33) |
| precision of validated fields | 0.992 [0.980, 0.997] (n=509) |
| mean attempts | 1.00 |

| field | precision | recall | F1 |
|---|---|---|---|
| part_number | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| manufacturer | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| product_name | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| category | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| supply_voltage_min_v | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| supply_voltage_max_v | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| rated_current_a | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| power_w | 0.885 (n=26) | 0.885 (n=26) | 0.885 |
| operating_temp_min_c | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| operating_temp_max_c | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| ip_rating | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| weight_g | 1.000 (n=26) | 1.000 (n=26) | 1.000 |
| datasheet_revision | 1.000 (n=33) | 1.000 (n=33) | 1.000 |
| certifications | 0.970 (n=33) | 0.970 (n=33) | 0.970 |
| interfaces | 1.000 (n=28) | 1.000 (n=28) | 1.000 |
| dimensions_mm | 1.000 (n=33) | 1.000 (n=33) | 1.000 |

## Extraction (PROVISIONAL labels)

documents: 6

| metric | value [95% CI] |
|---|---|
| micro precision | 0.308 [0.165, 0.500] (n=26) |
| micro recall | 0.119 [0.062, 0.218] (n=67) |
| micro F1 | 0.172 |
| evidence validity | 0.808 [0.621, 0.915] (n=26) |
| auto-validated | 0.000 [0.000, 0.390] (n=6) |
| needs review | 1.000 [0.610, 1.000] (n=6) |
| precision of validated docs (all fields right) | n/a |
| precision of validated fields | n/a |
| mean attempts | 2.00 |

| field | precision | recall | F1 |
|---|---|---|---|
| part_number | n/a (n=0) | 0.000 (n=6) | 0.000 |
| manufacturer | n/a (n=0) | 0.000 (n=6) | 0.000 |
| product_name | n/a (n=0) | 0.000 (n=6) | 0.000 |
| category | n/a (n=0) | 0.000 (n=6) | 0.000 |
| supply_voltage_min_v | 0.500 (n=2) | 0.200 (n=5) | 0.286 |
| supply_voltage_max_v | 0.500 (n=2) | 0.200 (n=5) | 0.286 |
| rated_current_a | 0.333 (n=3) | 0.500 (n=2) | 0.400 |
| power_w | 0.333 (n=3) | 0.500 (n=2) | 0.400 |
| operating_temp_min_c | 0.500 (n=2) | 0.200 (n=5) | 0.286 |
| operating_temp_max_c | 0.500 (n=2) | 0.200 (n=5) | 0.286 |
| ip_rating | 0.167 (n=6) | 0.200 (n=5) | 0.182 |
| weight_g | n/a (n=0) | 0.000 (n=4) | 0.000 |
| datasheet_revision | n/a (n=0) | n/a (n=0) | 0.000 |
| certifications | 0.000 (n=2) | 0.000 (n=2) | 0.000 |
| interfaces | 0.000 (n=3) | 0.000 (n=4) | 0.000 |
| dimensions_mm | 1.000 (n=1) | 0.250 (n=4) | 0.400 |

## Agent scenarios

- scenarios passed: 1.000 [0.796, 1.000] (n=15)
- safety scenarios passed (S05, S06, S07, S10, S11, S12): 1.000 [0.610, 1.000] (n=6) - **ALL PASS**

## Ops

```json
{
 "retrieval": {
  "retrieval_latency_ms": {
   "n": 56,
   "p50": 19.0,
   "p95": 23.0,
   "mean": 19.071428571428573
  }
 },
 "qa": {
  "retrieval_latency_ms": {
   "n": 65,
   "p50": 18.0,
   "p95": 22.0,
   "mean": 18.076923076923077
  },
  "llm_latency_ms": {
   "n": 65,
   "p50": 1.0,
   "p95": 1.0,
   "mean": 1.0
  },
  "total_latency_ms": {
   "n": 65,
   "p50": 19.0,
   "p95": 22.0,
   "mean": 18.907692307692308
  },
  "input_tokens": 72261,
  "output_tokens": 2218,
  "cache_hits": 0,
  "llm_calls": 65,
  "cost_usd": 0.0,
  "cost_per_100_queries": 0.0
 },
 "extraction": {
  "latency_ms": {
   "n": 33,
   "p50": 1.0,
   "p95": 1.0,
   "mean": 1.0
  },
  "cost_usd": 0.0,
  "cost_per_document": 0.0,
  "llm_calls": 45,
  "input_tokens": 32185,
  "output_tokens": 15181
 },
 "agent": {
  "scenario_duration_ms": {
   "n": 15,
   "p50": 135.0,
   "p95": 183.60000000000002,
   "mean": 116.2
  }
 }
}
```
