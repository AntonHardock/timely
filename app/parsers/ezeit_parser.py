from typing import BinaryIO
import datetime as dt
from calendar import monthrange
from app.models import EZeitDay, DayCategories
from app.parsers.utils import csv_dict_reader, check_mandatory_columns, add_exception_context

EZEIT_ERROR = "Import of Ezeit file failed"

MANDATORY_COLUMNS = {"date", "time_worked", "day_category", "comment"}

DAY_CATEGORY_MAP = {
    "07:48": DayCategories.ON_WORK.value,
    "frei": DayCategories.OFF_WORK.value,
    "fza": DayCategories.OVERTIME_LEAVE.value,
    "kr": DayCategories.SICK_LEAVE.value,
    "url": DayCategories.VACATION.value
}


def parse_working_hours(file:BinaryIO, month:int, year:int) -> list[EZeitDay]:

    # read csv
    rows = csv_dict_reader(file)

    # raise exception if mandatory columns are not included
    columns_recieved = rows[0].keys()
    check_mandatory_columns(MANDATORY_COLUMNS, columns_recieved, EZEIT_ERROR)

    # remove empty rows
    rows = [row for row in rows if any(row.values())]

    # parse rows by column
    for row in rows:

        # parse date
        date = row["date"]
        if date == "":
            raise ValueError(f"{EZEIT_ERROR}. Empty fields in 'date' are not allowed.")
        try:
            date = dt.datetime.strptime(date, "%d.%m.%Y").date()
        except ValueError as exc:
            add_exception_context(exc, EZEIT_ERROR)
        row["date"] = date

        # parse time_worked
        time_worked = row["time_worked"]
        if time_worked == "":
            time_worked = "00:00"
        try:
            t = dt.datetime.strptime(time_worked, "%H:%M")
        except ValueError as exc:
            add_exception_context(exc, EZEIT_ERROR)
        row["time_worked"] = t.hour * 60 + t.minute

        # parse day_category
        day_category = row["day_category"]

        if day_category == "":
            raise ValueError(f"{EZEIT_ERROR}. Empty fields in 'day_category' are not allowed.")
        row["day_category"] = DAY_CATEGORY_MAP[day_category.lower()]

        if "Erkrankung im Dienst" in row["comment"]:
            row["day_category"] = DayCategories.SICK_LEAVE.value

    # sort rows by date
    rows.sort(key=lambda r: r["date"])

    # ensure all dates of given month and year are present
    _, n_days_in_month = monthrange(year, month)
    expected_dates = [dt.date(year, month, i) for i in range(1, n_days_in_month + 1)]
    parsed_dates = [row["date"] for row in rows]

    if parsed_dates != expected_dates:
        unexpected_dates = set(parsed_dates) - set(expected_dates)
        unexpected_dates = [d.isoformat() for d in unexpected_dates]
        msg = f"""{EZEIT_ERROR}. All dates of year {year} and month no. {month} have to be included.
            The import seems to deviate in some way: wrong year/month or incomplete data?
            Expected {n_days_in_month} dates, got {len(parsed_dates)}
            In case any valid dates were imported, these are the unexpected ones: {unexpected_dates}"""
        raise ValueError(msg)

    # Rename columns, keep only required ones and turn each row into pydantic model
    _map_columns = lambda row: {
        "date": row["date"],
        "booked_minutes": row["time_worked"],
        "day_category": row["day_category"]
    }

    rows = [_map_columns(row) for row in rows]

    rows = [EZeitDay.model_validate(row) for row in rows]

    return rows