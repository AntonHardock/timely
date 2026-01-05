import pandas as pd
from app.models import EZeitDay, DayCategories
from typing import BinaryIO
import datetime as dt
from calendar import monthrange
from app.parsers.exceptions import ColumnsError, DateRangeError, TimeFormatError

EZEIT_ERROR = "Import of Ezeit file failed"

def parse_working_hours(file:BinaryIO, month:int, year:int) -> list[EZeitDay]:

    # read data
    df = pd.read_csv(file, header=0, delimiter=";")

    # ensure expected columns are included
    mandatory_columns = ["Datum", "Arbeitszeit", "Dienst", "Dienstbemerkung"]
    if not set(mandatory_columns).issubset(set(df.columns)):
        msg = f"{EZEIT_ERROR}. Following columns are mandatory: {mandatory_columns}. Got columns: {list(df.columns)}"
        raise ColumnsError(msg)

    # remove na's
    df = df.dropna(axis=0, how="all")
    df = df[pd.notnull(df["Datum"])]

    # prepare abbreviated date information for further validations into a regular date string
    time_format = "%d.%m.%Y"   
    try:
        df["Datum"] = pd.to_datetime(df["Datum"], format=time_format)
    except ValueError as exc:
        msg_pattern = f'doesn\'t match format "{time_format}"'
        if msg_pattern in str(exc):
            raise TimeFormatError(f"{EZEIT_ERROR}. Malformatted dates! Expected format: DD.MM.YYYY")
        else:
            raise exc

    df["Datum"] = df["Datum"].dt.date # remove time information from datetime

    # sort chronologically (should be the regular case)
    df = df.sort_values(by="Datum")

    # ensure all dates of given month and year are present in inported data
    _, n_days_in_month = monthrange(year, month)
    expected_dates = [dt.date(year, month, i) for i in range(1, n_days_in_month + 1)]
    parsed_dates = df["Datum"].to_list()

    if parsed_dates != expected_dates:
        unexpected_dates = set(parsed_dates) - set(expected_dates)
        unexpected_dates = [d.isoformat() for d in unexpected_dates]
        msg = f"""{EZEIT_ERROR}. All dates of year {year} and month no. {month} have to be included.
            The import seems to deviate in some way: wrong year/month or incomplete data?
            Expected {n_days_in_month} dates, got {len(parsed_dates)}
            In case any valid dates were imported, these are the unexpected ones: {unexpected_dates}"""
        raise DateRangeError(msg)

    # convert worktime into integer minutes
    df["Arbeitszeit"] = df["Arbeitszeit"].str.strip()
    df["Arbeitszeit"] = pd.to_datetime(df["Arbeitszeit"], format='%H:%M')
    df["Arbeitszeit"] = df["Arbeitszeit"].fillna(dt.datetime(1900, 1, 1)) #adds placeholder timestamp with time 00:00:00
    df["Arbeitszeit"] = (df["Arbeitszeit"].dt.hour * 60) + df["Arbeitszeit"].dt.minute
    
    # recode entries in "Dienst" to the categories used in target pydantic model
    df["Dienst"] = df["Dienst"].astype(str)
    df["Dienst"] = df["Dienst"].str.lower()
    work_category_map = {
        "07:48": DayCategories.ON_WORK.value,
        "frei": DayCategories.OFF_WORK.value,
        "fza": DayCategories.OVERTIME_LEAVE.value,
        "kr": DayCategories.SICK_LEAVE.value,
        "url": DayCategories.VACATION.value
    }
    df["Dienst"] = df["Dienst"].replace(work_category_map, regex=False)
    
    # deal with rare event "Erkrankung im Dienst"
    # for simplicity, this is treated equally to being sick the entire day
    df["Dienstbemerkung"] = df["Dienstbemerkung"].astype(str)
    sick_during_work = df["Dienstbemerkung"].str.contains("Erkrankung im Dienst", regex=False, na=False)
    df.loc[sick_during_work, "Dienst"] = DayCategories.SICK_LEAVE.value
    
    # rename and keep only required columns for target pydantic model
    required_columns = {
        "Datum": "date",
        "Arbeitszeit": "booked_minutes",
        "Dienst": "day_category"
    }
    df = df.rename(columns=required_columns, errors="raise")
    df = df[required_columns.values()]
    
    # convert dataframe into a list of pydantic objects
    data = df.to_dict(orient="records")
    data = [EZeitDay.model_validate(record) for record in data]

    return data