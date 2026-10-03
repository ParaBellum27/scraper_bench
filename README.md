# Finance Coding Benchmark

A benchmark for evaluating whether coding-capable language models can translate real financial-modeling logic into correct, executable, and robust Python programs.

## Current scope

The first benchmark task reproduces Aswath Damodaran's two-stage FCFF valuation spreadsheet (`fcff2st.xls`) in Python.

The benchmark is designed to test more than whether a model can match one final valuation. A strong submission should:

1. implement the valuation logic correctly;
2. produce the expected intermediate and final outputs;
3. remain correct when valuation assumptions are changed in hidden tests;
4. avoid hard-coding spreadsheet outputs;
5. fail cleanly on invalid inputs;
6. be understandable enough to inspect for systematic model failures.

## Benchmark structure

```text
.
├── README.md
├── tasks/
│   └── damodaran_fcff2st/
│       ├── task.md
│       ├── metadata.json
│       ├── inputs/
│       └── public_tests/
├── evaluator/
│   ├── grader.py
│   └── schemas.py
├── reference/
│   └── damodaran_fcff2st/
│       ├── reference.py
│       └── expected_outputs.json
├── runs/
│   ├── luna/
│   ├── mistral_medium_3_5/
│   └── gemini_3_8_flash/
└── analysis/
    └── failure_taxonomy.md
```

## Task 001: Damodaran FCFF two-stage valuation

The model will be given the source workbook and a task specification. It must write executable Python that reproduces the spreadsheet's valuation methodology.

The evaluator will score the submission on both base-case correctness and hidden scenario generalization. Hidden tests will change selected assumptions so that solutions that merely hard-code known spreadsheet outputs fail.

### Planned outputs

The exact output schema will be finalized after the workbook has been inspected, but is expected to include inputs, intermediate valuation quantities, terminal-value calculations, enterprise/equity value, and implied value per share where applicable.

## Models

Initial benchmark set:

- Luna
- Mistral Medium 3.5
- Gemini 3.8 Flash

Model-provider wiring will be added only after the benchmark task and evaluator are validated locally.

## Evaluation philosophy

The project is intended to produce useful coding-evaluation data, not just a leaderboard number. In addition to aggregate scores, model trajectories and generated code should be reviewed to identify recurring failure modes such as:

- formula translation errors;
- misuse of valuation assumptions;
- incorrect terminal-value logic;
- unit or percentage mistakes;
- hard-coded outputs;
- brittle handling of hidden scenarios;
- structurally correct code with financially incorrect reasoning.

## Development status

- [x] Repository architecture defined
- [x] Initial task specification scaffolded
- [ ] Add `fcff2st.xls`
- [ ] Inspect workbook formulas and dependencies
- [ ] Build verified Python reference implementation
- [ ] Freeze output schema
- [ ] Implement public and hidden tests
- [ ] Validate evaluator locally
- [ ] Add model runner interfaces
- [ ] Run initial model set
- [ ] Analyze trajectories and publish failure taxonomy
