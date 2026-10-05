# Pierre LBO — relaxed-budget Gemini result

**Pass: 45/45 hidden scenarios fully correct; public base passed; all-cases-correct true; weighted diagnostic 100/100.** Independent grading used the exact, unmodified explicit submission.

## Frozen condition

- Direct native API, requested/returned **`gemini-3.8-flash`**, confirmed-project current local key.
- Fresh conversation; unchanged Pierre LBO **v0.2** public prompt/workbook/input, reference, 55 fields, 45 hidden scenarios, seed `20261004`, relative/absolute tolerance `1e-7`.
- **32 model turns, 24 Python executions, 10 seconds/execution, 1800 seconds overall, 65536 response tokens**, 512-token access probe; isolated grading 5 seconds/case.
- Provider-default temperature/thinking, overrides omitted. Unexposed effective settings/backend revision are not guessed.
- Generic workflow addition: submit a working candidate early, test the exact source on public input, reserve at least three calls for correction and explicit resubmission. No previous variable-name bug, reference code, hidden scenario or grading feedback was supplied.
- One user-authorized fourth attempt, separately labelled relaxed-budget condition. It is not the original 12-execution condition or a matched cross-provider comparison.

[pre-execution-manifest.json](pre-execution-manifest.json), `source/` and [cap-increase-receipt.json](cap-increase-receipt.json) freeze the source/policy and prove that the explicit **$2→$4** cumulative cap increase preserved every previous request, $0.744057 accounted usage, quota history and all other providers' records. No ledger or trial claim was reset.

## Actual run and result

- Access probe succeeded; **19 real API requests** total for this run.
- **18 model turns**, **17 executions**, final stop `stop`, approximately **171.73 seconds** before grading.
- One public execution error on call 12: an inspection script omitted `import json`. Subsequent calls succeeded; generation received only its own public feedback.
- Explicit final submission on **call 17**, execution exit 0, **seven execution calls still available**. The model then finished normally.
- Public base and **all 45 hidden cases fully correct**. `all_hidden_cases_correct=true`, `all_cases_correct=true`; weighted diagnostic **100/100**.

Submission SHA-256:

```text
6966f0c0788aeccbdd55cc9d5c5a21022d1a9669092ea0b0fb25e02b4fb3cd36
```

No human code correction, inspection-source substitution, or hidden feedback occurred. The grader verified unchanged submission bytes across all cases. The original author workbook and financial qualification sources were not modified.

## Spending and scope

This attempt added **$0.79745925** in conservative token-price accounting. Cumulative Gemini accounting, including all four attempts and their probes: **$1.54151625**, leaving **$2.45848375** under the enforced **$4** cap; no uncertain hold. The estimate charges reported cached input at full standard input price and is not an independently verified invoice.

The earlier standard execution-budget submission scored 0/45 because of an undefined output variable. This fresh relaxed-budget run passes the frozen suite. That demonstrates successful completion under this new condition, not that the extra calls alone caused the difference: execution limits, workflow instruction and stochastic generation differed. One pass on 45 fixed scenarios does not establish universal correctness or a population-level model ranking.

Candidate authorization was closed after the run. No fifth attempt, Groq retry or Mistral retry was made.

## Evidence and offline replay

- [outcome.json](outcome.json): primary result, limits, actual debugging history and accounting.
- [grade.json](grade.json): all 46 isolated grading results.
- [trial/solution.py](trial/solution.py): exact final submission.
- [trial/trajectory.json](trial/trajectory.json): complete actual conversation, tool arguments and public results.
- [trial/metadata.json](trial/metadata.json), protected source snapshots, execution state/log and [ledger-snapshot.json](ledger-snapshot.json).
- [artifact_manifest.json](artifact_manifest.json): evidence hashes; [offline-smoke.json](offline-smoke.json): pre-dispatch local lifecycle proof. **104 tests and configured-runtime type checking passed** before dispatch.
- [Prior standard-budget result](../gemini-only-65536-2026-10-05/README.md) remains unchanged.

Offline replay from repository root, no provider calls:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m evaluator.run_grader \
  results/pierre_lbo/gemini-relaxed-2026-10-05/trial/solution.py \
  --benchmark pierre_lbo --seed 20261004
```
