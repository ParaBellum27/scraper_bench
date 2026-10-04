# Failure Taxonomy

For the complete nine-attempt history and offline-reproduced outcomes, see the [pilot report](pilot_report.md), [benchmark summary](../BENCHMARK_SUMMARY.md), [model comparison](model_comparison.md), and [sanitized evidence pack](../results/damodaran_fcff2st/pilot-2026-10-04/README.md). Local raw-archive paths below are provenance references, not published transcripts.

This document will track recurring model failure modes observed across benchmark runs.

## Categories

### Execution failures
- syntax/import errors
- missing dependencies
- invalid file handling
- timeout or non-termination

### Spreadsheet translation failures
- incorrect formula translation
- incorrect dependency ordering
- wrong use of inputs or assumptions
- unit / percentage mistakes

### Valuation logic failures
- incorrect FCFF construction
- incorrect discount-rate logic
- incorrect high-growth / stable-growth transition
- incorrect terminal-value logic
- incorrect enterprise-to-equity bridge
- incorrect per-share calculation

### Generalization failures
- hard-coded base-case values
- hidden-input sensitivity errors
- brittle assumptions about input ranges
- invalid behavior on edge cases

### Reasoning / trajectory failures
- correct answer for incorrect reason
- ignored task constraints
- unsupported assumptions
- unnecessary complexity masking incorrect logic

## Run notes

### Initial terminal pilots

Both pilots used the same public artifacts, a 20-turn limit, 12 Python executions, a 10-second execution timeout, and grading seed `20261003`. Generation settings and native client behavior differ; these are single model-plus-agent observations, not a model ranking.

| Condition | Score | Hidden cases passing 95% | Executions |
| --- | ---: | ---: | ---: |
| Gemini CLI 0.29.5, selected `gemini-3.8-flash`, API key | 100/100 | 13/13 | 9 |
| Vibe 2.25.8, advertised Medium 3.5 alias → `mistral-vibe-cli-latest`, account login | 0/100 | 0/13 | 12; a 13th request was refused |

Mistral's accepted executions all exited successfully. It exhausted its execution budget before saving its final valuation implementation; the last accepted file was a workbook-inspection script. That file still called `openpyxl.load_workbook('fcff2st.xlsx')`, so it failed in the deliberately workbook-free grader. Classification: **budget/submission management**, **ignored standalone-output contract**, and **file dependency at grading**. This result does not establish that its proposed valuation formulas were wrong. The rejected thirteenth source was not substituted for the frozen submission, and no human fixes or hidden feedback were supplied.

Gemini's frozen submission passed the public case and all 13 hidden cases. This is one successful trial, not an estimate of repeat-run reliability.

Local, Git-ignored evidence: `runs/private/gemini-cli-pilot-01/` and `runs/private/mistral-cli-pilot-01/`, including native events, exact executed sources, frozen-file hashes, and independent `grade.json` reports. Vibe's public trajectory records its configured alias, not a resolved backend revision. The initial Gemini pilot retains selected-model evidence in stdout but predates native-session preservation.

Infrastructure failures preceding these pilots are separate from model scores: Studio-key Medium quota refusal, rate-limited CLI authentication polling, and slow package reads in the Desktop virtualenv. Account-backed Vibe authentication and a separate Python runtime enabled the completed trials.

### Concurrent verification pair and recovery

The fresh native clients overlapped for **118.927 seconds**, verified from their event timestamps. The two initial pilots and both paired attempts had identical public-artifact hashes, prompt bytes, and turn/execution/time limits.

| Attempt | Outcome | Hidden cases | Accepted executions |
| --- | --- | ---: | ---: |
| `mistral-cli-paired-02` | 100/100 | 13/13 | 10 |
| `gemini-cli-paired-02` | Infrastructure failure; no score | Not graded | 6 |
| `gemini-cli-recovery-03` | Daily API quota exhausted; no score | Not graded | 0 |

The paired Gemini attempt encountered provider 503/high-demand responses and free-tier request-limit errors. Its six candidate executions succeeded, but the CLI failed before freezing a submission. A single recovery attempt after more than the provider's supplied cooldown failed immediately with HTTP 429, daily request limit 20, and a retry interval pointing to approximately `2026-10-05T00:00:00Z`. These are infrastructure outcomes, not zero-scoring model submissions. No further requests should use that exhausted API allowance before reset.

Mistral's second attempt succeeded under unchanged limits; its first zero remains recorded. Neither the later success nor Gemini's earlier success should replace failed attempts in reporting.

The Desktop workbook's bytes changed before recovery03; that attempt made no candidate calls. The original public ZIP was validated against the prior manifest and restored separately to `runs/private/frozen-public-inputs/` for future comparable runs, without altering the changed Desktop workbook. Full local comparison and provenance: `runs/private/terminal-pilot-summary.json`.

The existing Google-account credential also authenticated, but Gemini CLI rejected its retired consumer entitlement before generation. Antigravity's documented successor was investigated without installation, keyring migration, model substitution, or billing changes. The user selected preservation of the existing Gemini API condition and deferral until quota reset.
