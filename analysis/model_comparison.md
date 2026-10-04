# Model comparison: Gemini versus Mistral

## Verdict

**Gemini performed better in the initial native pilot; neither model is an established overall winner.** Gemini's first completed submission scored 100/100, while Mistral's first submission scored 0/100 because it exhausted its execution budget before saving a standalone implementation. Mistral's separate subsequent submission also scored 100/100.

The successful artifacts therefore **tie on tested numerical correctness**. They show different observed operational advantages: Gemini used one fewer execution for its successful solution; Mistral's successful run had lower elapsed time and completed the concurrent paired attempt that Gemini could not finish because of service/quota failures. Those facts describe these runs, not stable model-level superiority.

## Evidence and scope

This comparison uses the five official native-client attempts in the [published ledger](../results/damodaran_fcff2st/pilot-2026-10-04/attempts.json), the [accepted-execution trace](../results/damodaran_fcff2st/pilot-2026-10-04/execution_trace.json), and the [three frozen-submission grades](../results/damodaran_fcff2st/pilot-2026-10-04/grades/). Elapsed seconds below are calculated directly from metadata start/finish timestamps; they include preflight and client overhead.

| Native attempt | Score | Held-out cases ≥95 | Accepted executions | Elapsed seconds | Outcome |
|---|---:|---:|---:|---:|---|
| `gemini-cli-pilot-01` | 100 | 13/13 | 9 | 168.943 | Successful standalone submission |
| `mistral-cli-pilot-01` | 0 | 0/13 | 12 | 222.721 | Budget exhausted; inspection script frozen |
| `mistral-cli-paired-02` | 100 | 13/13 | 10 | 125.015 | Successful standalone submission |
| `gemini-cli-paired-02` | — | — | 6 | 184.231 | Service/request-limit failure before freezing |
| `gemini-cli-recovery-03` | — | — | 0 | 9.227 | Daily quota exhausted before candidate generation |

“—” means no frozen submission was graded. It is not zero. Both 100-point artifacts received full credit on the public case and every held-out case, not merely enough credit to clear the ≥95 threshold.

The complete campaign also includes three quota-blocked direct Mistral API attempts and one incomplete Mistral browser attempt. They remain in the nine-attempt ledger but are not pooled into a native-client model comparison. The browser model identity was unverified. No OpenAI submission exists.

## Which system did better, and on what measure?

| Measure | Observed advantage | What the evidence supports |
|---|---|---|
| Initial native-pilot task completion | **Gemini** | Its first pilot produced a valid 100-point program; Mistral's first pilot left a 0-point workbook-dependent script |
| Correctness of successful frozen artifacts | **Tie on this suite** | Each produced one 100-point artifact with all 13 held-out scenarios fully correct; no tested numerical difference distinguishes them |
| Accepted executions in the successful runs | **Gemini: 9 versus 10** | One fewer accepted Python call in these two runs; not proof of lower token usage, monetary cost, or expected effort |
| Elapsed time of successful runs | **Mistral: 125.015s versus 168.943s** | About 43.928 seconds lower observed duration; different run times, client settings, overhead and provider retries prevent a pure inference-speed claim |
| Completion during the concurrent pair | **Mistral** | Mistral froze a 100-point program; Gemini was interrupted after six successful executions. This is an operational outcome, not a demonstrated arithmetic loss by Gemini |
| Reliability across future tasks or repeated runs | **Undetermined** | One task, few uneven attempts, and dependent recovery history do not support a population reliability estimate |
| Monetary/token efficiency | **Undetermined** | No measured per-attempt monetary costs or comparable Vibe usage; accepted calls are not a substitute for either |

### Why the first Mistral attempt failed

The [frozen source](../results/damodaran_fcff2st/pilot-2026-10-04/submissions/mistral-cli-pilot-01.py) opens `fcff2st.xlsx` and inspects workbook cells instead of implementing the standalone JSON valuation contract. All 12 accepted execution calls exited successfully, but the thirteenth requested execution was refused before it could replace that file. The [historical grade](../results/damodaran_fcff2st/pilot-2026-10-04/grades/mistral-cli-pilot-01.json) records execution failures in the deliberately workbook-free grading environment.

That is a real task failure: inspection consumed the available budget without delivering the required program. It does **not** establish that the rejected final source had incorrect valuation formulas; that source was not the submission and was not graded. The later 100-point result demonstrates a successful separate attempt, not a proven learning effect.

### Why Gemini's later failures are different

The paired Gemini attempt encountered provider 503/high-demand and request-limit errors after six successful candidate executions. The recovery immediately hit the daily quota before any candidate execution. Neither produced a frozen submission, so neither has a numerical score. Treating them as zero would conflate service availability with observed numerical correctness; omitting them would conceal operational limitations.

## Denominators and misleading averages

| Native condition | Attempts | Graded submissions | Fully credited submissions | Ungraded infrastructure outcomes |
|---|---:|---:|---:|---:|
| Gemini CLI | 3 | 1 | 1 | 2 |
| Mistral Vibe | 2 | 2 | 1 | 0 |

These are descriptive counts, not estimated success probabilities. In particular, Gemini's recovery was conditional on a preceding service failure and shared quota conditions; it is not an independent clean replication.

A mean computed **only over graded submissions** would be Gemini 100 versus Mistral 50. That arithmetic is correct but is not a fair overall leaderboard: it compares one completed Gemini artifact against two Mistral artifacts and excludes Gemini's two infrastructure failures. Assigning arbitrary zero scores to the missing submissions does not repair that estimand. Report the numerical scores and completion accounting separately.

## What prevents a stronger ranking?

1. **One independent task.** The 13 scenarios are correlated checks of one program and workbook, not 13 independent model samples. Generalization to other financial tasks is unmeasured.
2. **Different systems and generation settings.** Vibe 2.25.8 used display alias `mistral-medium-3.5`, configured API alias `mistral-vibe-cli-latest`, account authentication, temperature 1 and high thinking. Gemini CLI 0.29.5 selected `gemini-3.8-flash`, API-key authentication and CLI defaults. This compares model-plus-agent configurations, not isolated model effects; immutable backend revisions are not established.
3. **Matched limits are not matched compute.** Four pilot/paired runs had identical prompt/input hashes and 20-turn/12-execution/10-second-execution/900-second-wall limits. Provider retries, token budgets, context handling and native turn semantics differ.
4. **The concurrent pair was incomplete.** Native execution intervals overlapped by 118.927 seconds, but only Mistral completed. The two successful artifacts were not produced in a completed simultaneous pair.
5. **Recovery provenance differs.** The workbook changed before Gemini recovery03; it made zero candidate executions. The recovery is excluded from the four-run identical-input claim and contributes no numerical score.
6. **Success-conditioned timing is selective.** Comparing only the two successful runs ignores failed-attempt effort. Gemini's successful pilot also had transient 503 retries. Neither elapsed-time observations nor incomplete native token counters establish cost superiority.
7. **Harness provenance and statistical precision are limited.** The pipeline was hardened during the pilot; exact immutable per-run harness builds and a preregistered balanced sampling/retry design were not retained. No confidence interval or pass@k claim is warranted.

## Practical conclusion

For these observed runs, **Gemini showed the stronger initial submission outcome and slightly lower successful-run execution count; Mistral showed a lower successful-run elapsed time and completed the interrupted concurrent comparison. Both demonstrated a fully correct tested artifact.** Choosing one as generally better would go beyond the evidence.

A stronger comparison needs a frozen common scaffold or clearly separated native-agent track, independently reviewed additional tasks, fresh-state repetitions with balanced run order, a predefined retry policy, and comparable usage/cost measurements. Those are planned checks, not completed results. See the [benchmark-design assessment](benchmark_design.md) for the methodological rationale.
