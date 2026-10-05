# Let's inspect how Excel EDATE works and test it
# In Excel: EDATE(start_date, months)
# If the resulting day of month is invalid (e.g. Feb 30), it clamps to the last day of that month (Feb 28/29).
# But does EDATE clamp to end of month if start_date is end of month?
# E.g. EDATE(2021-02-28, 12)? In Excel, EDATE(2021-02-28, 12) is 2022-02-28.
# EDATE(2020-02-29, 12) is 2021-02-28 (clamped because 2021 has 28 days in Feb).
# What about EDATE(2021-04-30, 12)? 2022-04-30.
# Let's verify what task.md says:
# "Advance fiscal ends sequentially with Excel's EDATE(previous,12) month-end clamping; do not substitute 31 December."
import calendar, datetime

def edate(dt, months):
    # standard EDATE definition:
    year = dt.year + (dt.month + months - 1) // 12
    month = (dt.month + months - 1) % 12 + 1
    max_days = calendar.monthrange(year, month)[1]
    day = min(dt.day, max_days)
    return datetime.date(year, month, day)

d = datetime.date(2020, 2, 29)
print("EDATE leap:", edate(d, 12), edate(edate(d, 12), 12))
d2 = datetime.date(2021, 12, 1)
print("EDATE 2021-12-01 + 12:", edate(d2, 12))
