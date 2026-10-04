# Failure Taxonomy

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

Populate after the first model runs.
