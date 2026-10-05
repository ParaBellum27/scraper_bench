# Gemini-only LBO attempt — 8192-token condition

User selected Gemini alone after it was the only provider to pass the live access probe. This fresh attempt raised the response cap from 4096 to **8192**, preserving the task/grader/public hashes, provider-default temperature/thinking, 20 turns, 12 execution calls, 10-second executions and 900-second wall limit.

Persistent trial slots were extended explicitly rather than deleting the first claim. Cumulative spending used the original private ledger/provider policy fingerprint. **102 behavioral tests**, configured-runtime type checking and all three loopback execution smokes passed before dispatch. Financial qualification sources remained unchanged.

## Observed outcome

- Direct model: `gemini-3.8-flash`; access probe succeeded.
- Real provider requests: **13** (one probe, eleven successful candidate responses, one final truncated response).
- Tool executions: **11**, exit codes `0,0,0,0,0,0,1,1,0,0,0`. Candidate execution errors remained public feedback and the model corrected them.
- No explicit `submit=True` selection. **No frozen solution or financial score.** Inspection/debugging source was not substituted for submission.
- Last provider response: `MAX_TOKENS`, **4243 visible + 781 thinking = 5024 output tokens**, despite requested cap 8192. Exact limiting mechanism remains unknown; it is not proven simply to be exhausting all 8192 tokens.
- Conservative usage-price accounting for this attempt: **$0.34476150**; cumulative Gemini **$0.47506425**, with **$1.52493575** remaining under the $2 cap and no uncertain hold. Full input price is used even for reported cached input; this is not a verified invoice.

Evidence: [pre-execution-manifest.json](pre-execution-manifest.json), [outcome.json](outcome.json), [actual trajectory](trial/trajectory.json), [provider response](trial/provider-error.json), and exact host snapshots under `trial/`. Original 4096-token evidence is retained separately.

The subsequent final corrective condition uses the documented **65536-token** ceiling and is recorded separately in `../gemini-only-65536-2026-10-05/`. Neither attempt is silently merged into a matched cross-provider benchmark.
