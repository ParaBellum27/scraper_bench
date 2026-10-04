# Pilot evidence pack — Damodaran FCFF, 2026-10-04

Start with the [benchmark summary](../../../BENCHMARK_SUMMARY.md), then the [model comparison](../../../analysis/model_comparison.md), [complete technical report](../../../analysis/pilot_report.md), or [benchmark-design research](../../../analysis/benchmark_design.md).

## Contents and accounting

| Artifact | Purpose |
|---|---|
| [attempts.json](attempts.json), [attempts.csv](attempts.csv) | All nine persisted finance attempts; exact timestamps, settings, outcomes and null scores for ungraded attempts |
| [submissions/](submissions/) | Three byte-identical frozen model submissions, including the failed inspection script |
| [grades/](grades/) | Historical per-case grades; private host paths redacted from diagnostics, numerical evidence unchanged |
| [execution_trace.json](execution_trace.json) | 46 accepted finance executions: source hashes, exit codes and UTF-8-encoded output byte counts; no raw reasoning or output transcripts |
| [terminal_prompt.txt](terminal_prompt.txt), [comparison.json](comparison.json) | Exact common terminal prompt; matching-input scope, original public hashes, limits, paired overlap and recovery-workbook exception |
| [diagnostics.json](diagnostics.json) | Separate provider probes, native lifecycle smoke and OpenAI package preparation; not finance scores |
| [oracle_check.json](oracle_check.json) | 36 base-case cached-workbook/reference/stored-output comparisons across 28 fields |
| [worked_example.json](worked_example.json) | Actual unchanged candidate inputs/outputs and grades for the base and changed-horizon cases |
| [controls/](controls/) | Reference and constant-public-answer control grades; not model attempts |
| [verification.json](verification.json) | Offline replay comparison and actual seven-test/type-check output |
| [runtime_versions.json](runtime_versions.json) | Observed Python/platform/package versions for publication verification |
| [artifact_manifest.json](artifact_manifest.json) | SHA-256 of published payloads and relevant current source files; not a historical per-run build attestation |

There are **nine finance attempts, three graded submissions, six ungraded infrastructure interruptions, and 46 accepted finance executions**. The three historical reports contain 42 grading-case outcomes. Replays, controls, the worked example and the separate native lifecycle smoke do not add candidate-generation attempts. An execution count is not a model-request count.

## Offline reproduction

Requirements: macOS with `/usr/bin/sandbox-exec`, Python 3.13, and the repository dependencies. The runner intentionally fails closed on unsupported systems. Use an existing supported runtime or provision one as documented in [harness setup](../../../harness/README.md). The observed verification environment is recorded separately; it is not a claim that every historical generation used an identical dependency lock.

From the repository root:

```bash
PYTHON="$HOME/.local/share/scraper-bench/runtime/bin/python"
RESULTS="results/damodaran_fcff2st/pilot-2026-10-04"

"$PYTHON" -m evaluator.run_grader "$RESULTS/submissions/gemini-cli-pilot-01.py" \
  --seed 20261003 --timeout 5 --summary-only
"$PYTHON" -m evaluator.run_grader "$RESULTS/submissions/mistral-cli-pilot-01.py" \
  --seed 20261003 --timeout 5 --summary-only
"$PYTHON" -m evaluator.run_grader "$RESULTS/submissions/mistral-cli-paired-02.py" \
  --seed 20261003 --timeout 5 --summary-only

"$PYTHON" -m unittest discover -s tests -v
```

Expected historical summaries, in that order:

| Submission | Overall | Public | Held-out mean | Held-out cases ≥95 |
|---|---:|---:|---:|---:|
| Gemini pilot | 100 | 100 | 100 | 13/13 |
| Mistral pilot | 0 | 0 | 0 | 0/13 |
| Mistral paired | 100 | 100 | 100 | 13/13 |

Omit `--summary-only` for full per-case results. The grader's process exit status indicates whether it produced a report, not candidate correctness. No workbook or model credentials are needed to replay these grades. The failed candidate intentionally remains unchanged and fails because the grading workspace has no workbook.

The publication also ran `ty check --python "$PYTHON" --output-format concise harness tests` with the installed standalone type checker; its actual output is retained in `verification.json`.

### Reproduce the grader controls

The positive control is the complete published reference module followed by a JSON stdin/stdout entry point. The negative control consumes stdin but always emits the stored public outputs. The following creates temporary files only and makes no provider requests:

```bash
"$PYTHON" - <<'PY'
import json
from pathlib import Path
import subprocess
import sys
import tempfile

reference = Path('reference/damodaran_fcff2st/reference.py').read_text()
expected = json.loads(Path('reference/damodaran_fcff2st/expected_outputs.json').read_text())
sources = {
    'reference': reference + "\nif __name__ == '__main__':\n    import json, sys\n    print(json.dumps(value_company(json.load(sys.stdin))))\n",
    'base_case_constant': 'import json, sys\njson.load(sys.stdin)\nprint(json.dumps(' + repr(expected) + '))\n',
}
with tempfile.TemporaryDirectory(prefix='fcff-controls-', dir='/private/tmp') as directory:
    for name, source in sources.items():
        path = Path(directory) / f'{name}.py'
        path.write_text(source)
        print(name, flush=True)
        subprocess.run([sys.executable, '-m', 'evaluator.run_grader', str(path),
                        '--seed', '20261003', '--timeout', '5', '--summary-only'], check=True)
PY
```

Observed control scores: reference **100**; constant-public-answer **44.43076923076923**, despite public score 100. The constant answer passes the interest-expense invariance case and earns partial credit on fields that remain unchanged. This is a specific hardcoding check, not adversarial robustness certification.

## Provenance and safe-publication policy

- Final candidate bytes are unchanged and hashes match their original private metadata. Historical grade values are preserved; host/private temporary paths in diagnostic text are normalized.
- Frozen source formatting is also preserved. Git's whitespace check flags trailing whitespace in the archived Mistral paired submission; it is intentionally not reformatted because byte-identical evidence takes precedence over styling generated artifacts.
- Metadata is allowlisted. Raw model/browser transcripts, reasoning, credentials, auth caches, account identifiers and full native sessions remain private. The accepted-execution ledger is derived from saved tool records, not reconstructed model narration.
- A raw-metadata hash identifies a locally retained source artifact; it does not make that private artifact independently inspectable. The overlap value comes from the historical native-event analysis, whose raw transcript is not republished.
- All raw `runs/` are Git-ignored. This curated directory is separate from raw collection.
- The workbook/ZIP is omitted because redistribution permission is not documented. Original workbook SHA-256: `0f329a49478cfa8072286b26edd2d365c1016a77de31e82d06365caca0fb3789`. A new comparable generation run needs that exact separately obtained workbook, not an arbitrary current download or the changed recovery file.
- Case definitions and expected outputs are disclosed for reproduction. They must be treated as public regression material, not a fresh secret holdout.
- Artifact hashes establish file integrity, not provider model identity, financial certification, or complete historical build provenance. Stochastic regeneration is a different claim from deterministic score replay.
