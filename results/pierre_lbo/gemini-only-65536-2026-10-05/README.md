# Pierre LBO — Gemini-only benchmark result

**Result: 0/45 hidden scenarios fully correct; public base failed; weighted diagnostic 0/100.** The direct API worked and Gemini explicitly submitted a program. That exact unmodified program failed at runtime on every scored case.

## Condition and provenance

- Requested/returned model: **`gemini-3.8-flash`**, native direct `generateContent` API, current confirmed-project `.env` key.
- Financial task: **Pierre LBO v0.2**, unchanged public files, reference, 55 scored fields and 45 hidden scenarios; seed `20261004`, numerical tolerances relative/absolute `1e-7`.
- Generation: provider-default temperature/thinking, overrides omitted. Effective settings/backend revision beyond returned model ID were not exposed and are not guessed.
- Limits: **20 turns, 12 execution calls, 10 seconds per execution, 900 seconds wall, 65536 response tokens**, plus 512-token access probe; grading 5 seconds per case.
- This is the third and final truncation-corrective attempt, not a matched cross-provider comparison. Earlier 4096/8192 attempts and spend remain preserved. Persistent claim files were extended, never deleted; all calls used the original cumulative ledger.
- [pre-execution-manifest.json](pre-execution-manifest.json) and `source/` freeze exact code/policy before dispatch. Public hashes match the financial qualification. No hidden feedback or human source repair was sent to generation.

## Observed run

Access probe succeeded. The model then used **12 turns and all 12 executions**; first eleven executions exited 0, and call twelve explicitly submitted source but exited 1. The source was protected before execution, as required by the public contract. Runner stop reason was `max_run_calls`; it froze call twelve without human correction.

Submission SHA-256:

```text
d7c008b17c07b10e8885f9d2bab20aaea011849f391f8963164e5b3f0325edbe
```

The final program's `run_model` creates its result dictionary using undefined `preferred_accrued` at line 297; the implementation's local variable is `pref_accrued`. Observed error:

```text
NameError: name 'preferred_accrued' is not defined. Did you mean: 'pref_accrued'?
```

Independent grading of the exact frozen file returned this error for the public base and **all 45 hidden scenarios**. `all_hidden_cases_correct=false`, `all_cases_correct=false`. The execution failure prevents an inference about whether the underlying financial calculations are otherwise correct. Inspection/debugging code, truncated responses and a hypothetical manually repaired program were not scored as submissions.

## Three recorded attempts

| Response cap | Candidate result | Hidden fully correct | Conservative attempt cost |
|---:|---|---:|---:|
| 4096 | `MAX_TOKENS`, no submission | Ungraded | $0.13030275 |
| 8192 | `MAX_TOKENS`, no submission | Ungraded | $0.34476150 |
| 65536 | Explicit submission; runtime error | **0/45** | $0.26899275 |

Final attempt: **13 real API requests** including its probe. Cumulative Gemini: **33 requests**, conservative accounting **$0.744057**, no uncertain hold. The original **$2 hard guard** remained in force, leaving $1.255943 internally available. The user subsequently allowed up to **$4 if needed**; no extra spend or guard increase was necessary. The estimate charges cached input at full standard input rate and is not an independently verified billing invoice.

No more candidate attempts were started after the third. Candidate execution authorization was closed. Groq/Mistral were not retried: their earlier 403/429 access failures remain separate, ungraded records.

## Evidence and replay

- [outcome.json](outcome.json): primary result, accounting, limits and evidence hashes.
- [grade.json](grade.json): all 46 actual isolated grading results.
- [trial/solution.py](trial/solution.py): exact explicit submission, unmodified.
- [trial/trajectory.json](trial/trajectory.json): actual provider responses, tool arguments and public feedback.
- [trial/metadata.json](trial/metadata.json), execution snapshots/log/state and [ledger-snapshot.json](ledger-snapshot.json).
- [Prior 8192 condition](../gemini-only-8192-2026-10-05/README.md), [initial preparation/access attempts](../preparation-2026-10-05/README.md).

Offline replay from repository root (no API calls):

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m evaluator.run_grader \
  results/pierre_lbo/gemini-only-65536-2026-10-05/trial/solution.py \
  --benchmark pierre_lbo --seed 20261004
```

One graded attempt is not a population-level model ranking. It is evidence that this frozen model-plus-harness condition produced a runtime-broken final submission.
