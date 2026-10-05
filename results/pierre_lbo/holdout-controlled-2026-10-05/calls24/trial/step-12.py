# Let's check task.md wording:
# "Advance fiscal ends sequentially with Excel's EDATE(previous,12) month-end clamping; do not substitute 31 December."
# Notice the phrase:
# "Excel's EDATE(previous,12) month-end clamping"
# In Excel:
# EDATE(start_date, months)
# "If start_date is not a valid date, EDATE returns the #VALUE! error value.
# If months is not an integer, it is truncated.
# If the resulting day is invalid for the resulting month (for example, February 30),
# EDATE adjusts the day to the last day of the month."
print("Standard Excel EDATE: clamps day to max days of target month.")
