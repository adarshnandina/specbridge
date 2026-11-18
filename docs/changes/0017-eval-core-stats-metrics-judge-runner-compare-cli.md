# 2.6 Eval core: stats, metrics, judge, runner, compare, CLI
## Summary
Wilson CIs and noise flags; answer matching (numeric with units/decimal commas, sets with aliases, contains, exact), retrieval recall@k/MRR by type, QA accuracy/abstention P&R/injection resistance/citation precision+coverage/stale-revision rate; LLM judge (uncalibrated); runner with cost estimate and abort, result json+md with dataset hashes, config, models, prompt versions; compare; 'specbridge eval run|compare|set-baseline|validate-datasets'
## Why
Part of milestone task 2.6 in SPECBRIDGE_SPEC.md Section 13.
## Changes (files/modules)
specbridge/eval/{stats,metrics,judge,runner,compare,suites_extra}.py specbridge/cli.py specbridge/prompts/judge_usefulness.v1.md tests/unit/test_eval_*.py tests/integration/test_eval_run.py
## How it was tested (commands + results)
unit: test_eval_metrics 17, test_eval_runner_units 5; integration test_eval_run 5 (retrieval deterministic, modes differ, fake QA pipeline, missing index, paid provider without key blocked)
## Eval impact (baseline run id → new run id, deltas) or "n/a"
n/a
## Risks / follow-ups
none known
## Self-review checklist
- [x] tests added/updated   - [x] types pass   - [x] lint passes
- [x] no secrets            - [x] logs added for new code paths
- [x] docs updated          - [x] error handling covers failure modes
