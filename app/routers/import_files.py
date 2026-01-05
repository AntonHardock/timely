
from fastapi import APIRouter, HTTPException, UploadFile, Form, File
from fastapi.responses import RedirectResponse
from typing import Annotated
from datetime import date, datetime
from calendar import monthrange
from uuid import uuid4

from app.parsers.ezeit_parser import parse_working_hours, EZEIT_ERROR
from app.parsers.outlook_parser import parse_calendar_events, OUTLOOK_ERROR
from app.parsers.kapow_parser import parse_kapow_sessions, KAPOW_ERROR
from app.models import EZeitDay, Event
from app.parsers.exceptions import ColumnsError, DateRangeError, TimeFormatError
from lxml import etree
from app.database import db
from pydantic import ValidationError

router = APIRouter(prefix="/api/import_files")

@router.post("/parse")
def parse(
    month: Annotated[int, Form()],
    year: Annotated[int, Form()],
    ezeit: Annotated[UploadFile, File()],
    outlook: Annotated[UploadFile, File()],
    kapow: Annotated[UploadFile | None, File()] = None):

    """Recieves files together with other types of data, requiring the use of fastapi's
    Form() and File() factories wrapped in an 'Annotated' Object"""

    # derive date boundaries for import given year and month inputs
    _, n_days_in_month = monthrange(year, month)
    min_date = date(year, month, 1)
    max_date = date(year, month, n_days_in_month)

    # initiate cache for storing input files before validation
    cache_id = uuid4()
    timestamp = datetime.now()

    # import required ezeit file
    if ezeit.file.read() == b"":
        raise HTTPException(status_code=422, detail=f"{EZEIT_ERROR}. File is required and must not be empty.")
    else:
        ezeit.file.seek(0)
        try:
            ezeit_data = parse_working_hours(ezeit.file, month=month, year=year)
        except (ColumnsError, DateRangeError, TimeFormatError, ValidationError) as exc:
            detail = exc.errors() if isinstance(exc, ValidationError) else str(exc)
            raise HTTPException(status_code=422, detail=detail)
        db.cache_data(EZeitDay, ezeit_data, cache_id, timestamp)

    # import required outlook file
    if outlook.file.read() == b"":
        raise HTTPException(status_code=422, detail=f"{OUTLOOK_ERROR}. File is required and must not be empty.")
    else:
        outlook.file.seek(0)
        try:
            outlook_data = parse_calendar_events(outlook.file, min_date, max_date)
        except (ColumnsError, ValidationError) as exc:
            detail = exc.errors() if isinstance(exc, ValidationError) else str(exc)
            raise HTTPException(status_code=422, detail=detail)
        db.cache_data(Event, outlook_data, cache_id, timestamp)

    # import optional kapow file
    kapow_data = None # assume no kapow data was uploaded
    kapow_filename = kapow.filename # empty string in case of no file
    kapow_filename = None if kapow_filename == "" else kapow_filename # empt string to None for explicitness

    if kapow_filename is None:
        pass
    elif kapow_filename is not None and kapow.file.read() == b"":
        raise HTTPException(status_code=422, detail=f"{KAPOW_ERROR}. File is optional but cannot be empty when provided.")
    else:
        kapow.file.seek(0)
        try:
            kapow_data = parse_kapow_sessions(kapow.file, min_date, max_date)
        except (ValidationError, etree.XMLSyntaxError) as exc:
            detail = None
            if isinstance(exc, ValidationError):
                detail = exc.errors()
            else:
                detail = f"{KAPOW_ERROR}. A parsing error occured: " + str(exc)
            raise HTTPException(status_code=422, detail=detail)
        db.cache_data(Event, kapow_data, cache_id, timestamp)

    redirect_url = f"/import_files/preview/{cache_id}?min_date={min_date}&max_date={max_date}"

    return RedirectResponse(url=redirect_url, status_code=303)
