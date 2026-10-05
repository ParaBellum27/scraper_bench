# Direct API preparation — 2026-10-05

The financial task remains Pierre LBO **v0.2**. Its public hashes and every qualification source hash are unchanged from the prior audit.

## Implemented and exercised

- Direct Groq/Mistral chat-completions adapters; native Gemini `generateContent` with lossless thought-signature replay and documented output cap.
- Current `.env` keys are authoritative, without exported-key fallback/interpolation. Private confirmations bind the actual current key to the approved account; no key values are published.
- Serial campaign lock, persistent cumulative monetary reservations, whole-trial/network deadlines, rolling quota windows, actual-usage reconciliation and bounded `Retry-After` retries.
- Missing/ambiguous usage retains the full worst-case reservation. Legitimate omitted Gemini zero counts are accepted only when explicit totals agree. No blanket zero usage defaults.
- Only explicit `submit=True` selects protected source; inspection and workspace mutation cannot replace it. Truncated arguments are not executed. Access/quota/provider/deadline/protocol/truncation errors remain separate from candidate execution/financial errors.
- Groq's documented daily-request header now stops retry immediately at zero; the minute-token header is not mistaken for daily exhaustion. The before/after local repro passed after **one corrective attempt**.

Verification: **102 tests passed**, configured-runtime type checking passed, and three loopback HTTP → real adapter → Agent → sandbox → frozen reference → isolated grading smokes matched **all 55 spreadsheet fields**. Loopback fixtures are infrastructure proof, not model runs; their enlarged synthetic quotas do not prove production quota feasibility.

## Frozen evidence

- [artifact_manifest.json](artifact_manifest.json): exact source hashes, executable policy, public hashes and authorization scope, captured before the live request.
- `source/`: exact source/document snapshots at that freeze.
- [offline-smoke.py](offline-smoke.py) and [offline-smoke.json](offline-smoke.json): reproducible local proof, no real provider requests.
- [groq-quota-header-proof.json](groq-quota-header-proof.json): failure-before/fix-after evidence.
- Prior financial [qualification](../audit-2026-10-05/qualification.json) remains valid; no hidden scenario or task feature was added.

## Authorized real condition

The user requested a real API trial after pausing preparation. Selected conservative condition: **one Groq `openai/gpt-oss-120b` trial**, confirmed Free account, $0 paid fallback, immediate small access check. Gemini/Mistral candidate authorization remains disabled. Account facts were confirmed by the user, not independently read from provider billing dashboards.

Frozen generation limits: **20 turns, 12 executions, 10 seconds per execution, 900 seconds overall, 4096 output tokens per candidate request**, 512 tokens for the access probe. Provider-default temperature/reasoning are omitted; effective values are not inferred. Only `run_solution` is exposed; no built-in provider tools or hidden feedback.

Groq quotas: 30 RPM, 8000 combined TPM, 1000 RPD, 200000 TPD. The local estimate includes the entire payload with `o200k_harmony` and a 512-token framing allowance. Waiting can release earlier usage, but cannot make an individual input-plus-output reservation above 8000 fit. The runner stops without trimming history or silently changing its output cap/model. Account-shared rate usage and tokenizer estimation can still cause a provider 429.

The real invocation is:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
"$PY" -m harness.run_benchmark --provider groq --execute
```

It is not a repeatable free reset: private trial claims and accounting persist across processes. Do not delete claims/ledger to rerun. Final grading, when there is a frozen candidate, is separate and receives no provider credentials or workbook.

## Observed real access outcome

The runner made **one real Groq request** at `2026-10-05T05:11:06Z`. Local sandbox/workbook preflight passed. The completion endpoint returned **HTTP 403**, classified `access_failed`; no automatic retry, candidate start, submission, grade or provider/model fallback occurred. There is no model-quality result.

See [live-outcome.json](live-outcome.json), [actual metadata](groq-access-attempt.metadata.json) and [durable ledger](groq-access-attempt.ledger.json). The provider's error body was deliberately not retained; HTTP 403 alone does not establish whether the cause is credential permission, account/model entitlement or an upstream access restriction. The free-only accounting records $0 committed; provider billing was not independently inspected.

No candidate trial claim was consumed because the access gate failed first. Execution is blocked until the exact target's access is restored or the user explicitly chooses another trial condition. Repeating the same rejected request, changing models silently, or assigning a finance score would not resolve this failure.

## Explicitly authorized Mistral attempt

After the Groq rejection, the user explicitly requested Mistral. Exact model, policy and source checks are in [mistral-pre-execution.json](mistral-pre-execution.json). Candidate authorization was changed to **Mistral only**; no Gemini trial was enabled.

The runner made **one real direct Mistral access request** at `2026-10-05T05:14:54Z` to `mistral-medium-latest`. Local sandbox/workbook preflight passed. The endpoint returned **HTTP 429**, classified quota rejection, and the runner did not retry. No candidate started, no trial claim/submission/grade was created, and no CLI/model fallback occurred.

[mistral-live-outcome.json](mistral-live-outcome.json), [actual metadata](mistral-access-attempt.metadata.json) and [ledger snapshot](mistral-access-attempt.ledger.json) preserve the observed result. The ledger retains **$0.397056** as an uncertain worst-case hold, leaving $9.602944 internally available under the confirmed included allowance. This is **not an observed provider charge**; settled usage is zero. The exact quota window/reset and actual billing were not established from retained evidence. Do not repeatedly retry or discard the hold to manufacture availability.

## Explicitly authorized Gemini trial

The user next requested Gemini. Exact policy, source checks and Gemini-only authorization are in [gemini-pre-execution.json](gemini-pre-execution.json). The real `gemini-3.8-flash` access probe **succeeded**, and the model started the public LBO task.

There were **seven real requests**: one access probe, five successful candidate responses with one workbook-inspection execution each (all exit 0), and one final truncated response. The last response returned `MAX_TOKENS` with **3929 thinking + 163 visible = 4092 output tokens** under the requested 4096 cap. No explicit submission had been selected. The runner stopped as `provider_truncation`; inspection files were not frozen or assigned a benchmark score. This is an incomplete generation attempt, not an API access rejection or a financial correctness result.

[gemini-live-outcome.json](gemini-live-outcome.json) records usage, termination and evidence hashes; [gemini-trial/trajectory.json](gemini-trial/trajectory.json) and its accompanying exact host snapshots preserve the actual public-workspace interaction. The returned model identifier was `gemini-3.8-flash`; effective temperature/thinking settings were not exposed and are not inferred.

Conservative usage-based accounting is **$0.13030275**, with no uncertain hold and **$1.86969725** remaining under the cumulative $2 cap. Cached prompt tokens were charged at full input price in this estimate, so it is not a claimed provider invoice. No second candidate trial was started. A higher output cap requires an explicitly authorized new condition/attempt while retaining cumulative spending and the original evidence; do not reset the one-trial claim or grade inspection snapshots.
