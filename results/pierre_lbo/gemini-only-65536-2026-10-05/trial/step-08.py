# Let's check EDATE behavior in Excel if we can create a sheet or use Python
import datetime
import calendar

# Let's check if there are any specific guidelines in task.md:
# "Advance fiscal ends sequentially with Excel's EDATE(previous,12) month-end clamping; do not substitute 31 December."

def edate(dt: datetime.date, months: int) -> datetime.date:
    y = dt.year + (dt.month + months - 1) // 12
    m = (dt.month + months - 1) % 12 + 1
    max_d = calendar.monthrange(y, m)[1]
    d = min(dt.day, max_d)
    return datetime.date(y, m, d)

# Test with 2021-12-01
dt = datetime.date(2021, 12, 1)
for i in range(8):
    dt = edate(dt, 12)
    print(f"Period {i+1}: {dt}")
