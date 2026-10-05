# Pierre LBO: frozen-source holdout and matched execution comparison

**The frozen passing source passed all 22 fresh qualified holdout cases. Both fresh matched Gemini conditions passed the public base, all 45 original hidden cases and all 22 separate holdout cases.** No candidate was manually repaired and no hidden or holdout feedback entered generation.

## Frozen-source holdout

The [22-case holdout](holdout/README.md) was constructed without inspecting candidate source or outcomes. Its complete inputs and independent witnesses were saved before evaluation. All expected cases qualified against actual LibreOffice 26.8.0.3 recalculations across all 55 scored fields, at unchanged relative/absolute 1e-7 tolerances. Both implementations also passed predeclared arithmetic, branch, failure-prefix, date and null-return witnesses.

Coverage: scaled liquidity neighborhoods, below/equal/above preferred hurdles, funded/failed mandatory maturities, revolver no-redraw and retained prefixes, sequential leap-date clamping, one-day fiscal stub with full working capital, and dated returns. Inputs do not duplicate the original public/hidden cases or earlier hand diagnostics.

Only after every expected case qualified was the original passing Gemini program copied and evaluated in isolated grading workspaces. It passed **22/22**, weighted diagnostic 100. SHA-256 before/after/frozen copy: `6966f0c0788aeccbdd55cc9d5c5a21022d1a9669092ea0b0fb25e02b4fb3cd36`. No API calls or edits. Its earlier **45/45** result and evidence remain untouched; the holdout is not appended to the official scoreboard.

## Preregistered matched pair

The [protocol](protocol.json) was recorded before holdout evaluation and provider dispatch. Host-side `random.Random(2026100501).shuffle` selected **calls24, then calls12**. This randomizes order, not provider sampling. One fresh conversation per condition; no previous submission, grading feedback or bug hints were supplied.

Only `max_run_calls` differed: **24 vs 12**. Shared controls:

- Native `gemini-3.8-flash`; requested/returned model IDs agree.
- 32 model turns, 1,800 seconds overall, 10 seconds per execution, 65,536 response tokens.
- Same generic submit-early/reserve-three-calls instruction, task v0.2, public files, tool/submission protocol and sandbox.
- Provider-default temperature/thinking, overrides omitted; effective values/backend revision unexposed.
- Same grader, seed 20261004, relative/absolute 1e-7 tolerances and 5-second case timeout.
- Same persistent cumulative $4 ledger and quota/deadline/retry controls, retaining all four prior attempts. Access probes also count.

[Effective configurations and complete hashes](conditions.json) are frozen. The private release separately authorized only the next condition, and bound its entire effective configuration hash. Labels were host provenance, not extra model instructions.

## Observed results

| Condition (actual order) | Original hidden fully correct | Public base | Separate holdout | Executions / allowance | Turns | Elapsed | Conservative trial cost |
|---|---:|---|---:|---:|---:|---:|---:|
| 24 executions, first | 45/45 | Pass | 22/22 | 19/24 | 20 | 148.65s | $0.77267925 |
| 12 executions, second | 45/45 | Pass | 22/22 | 12/12 | 12 | 83.21s | $0.34812975 |

Both `all_cases_correct` flags are true; weighted partial-credit diagnostics are 100/100. Both final explicit submissions executed successfully and were independently graded at their exact frozen hashes.

- **calls24:** explicit submission at call19; normal stop after turn20; five executions unused. Four non-submission inspection errors: missing `openpyxl`, missing `solution_test`, denied subprocess/fork, missing `solution`. The subprocess denial demonstrates the sandbox remained active, not a financial score failure.
- **calls12:** explicit submission at call12; stop reason `max_run_calls`; zero correction margin. One non-submission inspection error at call11 (`res` undefined). The generic workflow is advisory: this run still waited until its final execution to submit.

The first source was preserved and the second condition dispatched before the first original hidden grade was computed. Later independent grading results stayed outside candidate generation. No sources were modified after explicit submission.

Exact submissions:

- [calls24 source](calls24/trial/solution.py): `1802931df82cd891eb3e866bdd0a659923c6253dff8fd4adf3aa4312a7855991`.
- [calls12 source](calls12/trial/solution.py): `0b64686446e6981bb208451ff5d842c5d273527a64c98b3e9922958ebddd7dd6`.

## Spending and closure

[Exact accounting](accounting.json):

- Earlier Gemini total: **$1.54151625**.
- New matched pair, including both access probes: **$1.12080900** across 34 requests.
- Cumulative Gemini total: **$2.66232525 / $4**; remaining **$1.33767475**.
- Uncertain Gemini holds: **$0**. All six historical/new trial claims remain preserved; no reset, repricing or cap increase.
- [Paid access and candidate dispatch closed](release-closed.json); no seventh attempt or further request authorized.

Amounts are conservative usage-based token-price accounting, not independently verified invoices. Groq/Mistral were not retried; their prior HTTP403/429 observations and unrelated ledger records remain preserved.

## Interpretation

**12 executions sufficed in this matched run; no accuracy advantage for the 24-execution condition was observed.** The larger condition retained five correction calls; the smaller succeeded on its last call. This leaves a practical fragility difference, not measured reliability.

One randomized pair cannot establish equal success probabilities, a general budget effect or the cause of the earlier 0/45-versus45/45 difference: that earlier comparison changed turns, workflow and wall time as well as executions. The 45 original scenarios and 22 deterministic, partly related stress cases are inputs, not independent model replicates. Three frozen programs passing this holdout expand observed coverage but do not establish universal correctness. Native Excel and extreme/uncovered public-domain combinations remain unqualified.

## Evidence and verification

- [Structured outcome](outcome.json), [preregistered protocol](protocol.json), [policy](policy.json), [conditions](conditions.json), [accounting](accounting.json), [persistent ledger snapshot](ledger-snapshot.json).
- [Holdout full qualification and original-source grades](holdout/report.json), [exact cases](holdout/cases.json), all source/recalculated XLSX files and source snapshots under `holdout/`.
- [calls24 original grade](calls24/original-grade.json), [holdout grade](calls24/holdout-grade.json), [metadata](calls24/trial/metadata.json).
- [calls12 original grade](calls12/original-grade.json), [holdout grade](calls12/holdout-grade.json), [metadata](calls12/trial/metadata.json).
- Each `trial/`: raw trajectory, execution log/state, access response, public base, every exact executed step and frozen source.
- [47-file runnable source manifest](source-manifest.json) and `sources/`, frozen before provider dispatch. Documentation delivery copies are separate.
- [Closed dispatch smoke](closed-gate-smoke.json): the real CLI rejected execution before any provider request while qualification was pending.
- [111 behavioral regressions passed](tests.txt); [configured-runtime type check passed](typecheck.txt).

Original grading can be repeated offline from the repository root:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m evaluator.run_grader \
  results/pierre_lbo/holdout-controlled-2026-10-05/calls12/trial/solution.py \
  --benchmark pierre_lbo --seed 20261004
```

To independently recalculate/evaluate the separate holdout again, use the [holdout reproduction command](holdout/README.md#reproduction) with a new directory and either frozen source. Model trials are not automatically repeatable: private release gates are closed and pricing/account authorizations expire.
