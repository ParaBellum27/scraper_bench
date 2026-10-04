# Agent harness

The harness gives every provider the same benchmark environment.

## Model-side environment

The model receives:
- the task prompt;
- one editable `solution.py` file;
- execution feedback from one logical tool: `run_solution`.

The model does **not** receive the hidden grader, reference implementation, hidden scenarios, or hidden-test results.

## Execution-side environment

During development/tool calls, `solution.py` is executed in an isolated workspace with the public workbook/input artifacts available. The model cannot inspect those artifacts directly; it must write Python to inspect them.

At final evaluation, the workbook is removed. The frozen `solution.py` receives only JSON inputs and must return JSON outputs.

## Fairness controls

Default limits:
- 20 model turns;
- 12 `run_solution` calls;
- 10 seconds per execution call;
- no internet inside the code-execution sandbox.

Use the same limits, task prompt, and public feedback for every model.

## Secrets

Set API keys locally; never commit them:

```bash
export OPENAI_API_KEY="..."
export MISTRAL_API_KEY="..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."   # optional fourth model
```

Model IDs are centralized in `harness/config.py` so provider-facing names can be updated without changing benchmark logic.
