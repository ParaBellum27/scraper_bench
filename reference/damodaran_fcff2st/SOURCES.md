# Methodological sources for Task 001

Task 001 is anchored to Aswath Damodaran's own two-stage FCFF materials.

## Primary numerical oracle

- Supplied workbook: `fcff2st.xlsx` (converted from Damodaran's `fcff2st.xls`).
- Damodaran spreadsheet index: https://pages.stern.nyu.edu/~adamodar/New_Home_Page/eqspread.htm
  - Describes `fcff2st.xls` as a two-stage FCFF discount model suited to firms with shifting leverage and moderate growth.

## Methodology cross-checks

- Fundamental determinants of growth:
  https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/growth.htm
  - Operating-income growth = reinvestment rate × return on capital under stable ROC.

- Terminal value and excess returns:
  https://pages.stern.nyu.edu/~adamodar/New_Home_Page/valquestions/termvalueexreturns.htm
  - Stable reinvestment rate = stable growth / stable return on capital.

- Project / valuation questions:
  https://pages.stern.nyu.edu/~adamodar/New_Home_Page/project/prques.htm
  - Stable growth should be sustainable; stable-period reinvestment is tied to growth and return on capital.

## Benchmark policy

The spreadsheet is the base-case numerical oracle. The Python reference implementation independently reproduces its active formulas. Hidden-case expected values are generated from that verified implementation rather than by re-running Excel during grading.
