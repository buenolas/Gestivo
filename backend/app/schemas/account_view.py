import enum


class DueDateFilter(str, enum.Enum):
    overdue = "overdue"
    today = "today"
    next_7_days = "next_7_days"
    next_30_days = "next_30_days"
