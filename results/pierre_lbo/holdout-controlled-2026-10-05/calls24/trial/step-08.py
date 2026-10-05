# Let's inspect the exact formula in Forecast:
# C5: =EDATE(B5,12)
# C6: =EDATE(B6,12)
# C7: =EDATE(B7,12)
# etc.
# In Python datetime / dateutils:
# What does EDATE(d, 12) do?
# If we add 1 year (12 months):
# year = d.year + 1, month = d.month.
# If d.day > days_in_month(year, month): clamp day to days_in_month(year, month).
# Wait, does Excel EDATE clamp when the input date was the end of month?
# For example, if input is 2023-02-28 (month end), does EDATE(2023-02-28, 12) return 2024-02-28 or 2024-02-29?
# In Excel: EDATE does NOT clamp if day <= days_in_target_month!
# EDATE(2023-02-28, 12) in Excel returns 2024-02-28!
# Excel's EDATE function:
# "If day is greater than the number of days in the calculated month, EDATE returns the last day of the month."
# Otherwise, it returns that day!
# EOMONTH returns the last day of the month. EDATE returns the same day of the month, or clamps if the day does not exist in that month (e.g. 31st in a 30-day month, or 29th/30th/31st in February).
print("Checking EDATE description in task.md:")
