# Separate Pierre LBO holdout

**Frozen passing Gemini source: 22/22 fully correct. No API calls, source edits or model feedback.** This is separate from its original 45/45 hidden result, not an enlarged or rewritten benchmark score.

Before candidate evaluation, all 22 expected cases qualified against actual LibreOffice 26.8.0.3 recalculations across all 55 scored fields, at the unchanged benchmark tolerances (relative/absolute 1e-7). Both implementations also passed predeclared branch, failure-prefix, null-return, date and independent arithmetic witnesses.

| Family | Cases | Coverage |
|---|---:|---|
| Liquidity neighborhoods | 6 | Shortages 0.2×/5× the relative guard at currency scales 0.0001×, 1×, 10000× |
| Preferred hurdle | 9 | Below/equal/above proceeds, ordinary payout and management-IRR nullness at those scales |
| Mandatory term maturity | 2 | Funded refinancing and period-3 failure retaining earlier financing rows |
| Revolver no-redraw | 2 | Failure at maturity; funded repayment then later failure despite unused commitment |
| Fiscal dates | 2 | Sequential leap-date clamping; one-day stub with full working capital |
| Dated returns | 1 | Leap-day close and actual-day annualization |

The new arithmetic setup has EBITDA512, entry equity896 and preferred448. None of these inputs duplicate the original public/45 hidden inputs or nine earlier hand diagnostics. Cases were designed without reading the candidate source or holdout outcomes, and saved before evaluation. Their canonical recorded file hash is in the report.

Frozen submission SHA-256: `6966f0c0788aeccbdd55cc9d5c5a21022d1a9669092ea0b0fb25e02b4fb3cd36`. Before/after and frozen-copy hashes agree. Weighted diagnostic: 100/100.

## Evidence

- [Exact predeclared inputs and witnesses](cases.json).
- [Full qualification and isolated candidate grades](report.json).
- [Exact frozen submission](frozen_submission.py).
- `sources/`: exact financial, qualification and grading source snapshots.
- `holdout_*.xlsx`: source workbooks; `calculated/`: independently recalculated derivatives. Both hashes are recorded per case.
- [Experiment protocol](../protocol.json): preregistered separation and controlled-comparison order.

## Reproduction

From the repository root, choose a new output directory:

```bash
PY="$HOME/.local/share/scraper-bench/runtime/bin/python"
SOFFICE="$HOME/.local/share/scraper-bench/tools/LibreOffice-26.8.0.app/Contents/MacOS/soffice"
"$PY" -m reference.pierre_lbo.holdout \
  --output-dir /new/holdout-evidence --soffice "$SOFFICE" \
  --submission /absolute/path/to/frozen/solution.py
```

Omit `--submission` to qualify only. Any expected-suite qualification failure skips candidate execution. The original workbook, public task, oracle and official scoreboard were not changed. These cases expand observed coverage; they do not exhaust the public domain or establish native Excel agreement.
