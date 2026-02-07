from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse 
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse 
from datetime import date
import random
from calendar import monthrange
from app.config import parse_config, get_static_resource_root
from app.routers.agg_time_by_cost_unit import agg_time_by_cost_unit
import app.database.db as db
from app.models import EZeitDay, Event, EventSources as EVS
from uuid import UUID
from decimal import Decimal, ROUND_FLOOR

CONFIG = parse_config()

router = APIRouter()

static_resource_root = get_static_resource_root()
router.mount("/static", StaticFiles(directory=(static_resource_root / "static")), name="static")
router.mount("/javascript", StaticFiles(directory=(static_resource_root / "javascript")), name="javascript")
templates = Jinja2Templates(directory = (static_resource_root / "templates"))


@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("home.html", context={"request": request})


@router.get("/not_implemented", response_class=HTMLResponse)
def not_implemented(request: Request):
    return templates.TemplateResponse("not_implemented.html", context={"request": request})


@router.get("/import_files", response_class=HTMLResponse)
def import_files(request: Request):
    return templates.TemplateResponse("import_files.html", context={"request": request})


@router.get("/sap", response_class=HTMLResponse)
def sap(request: Request):
    return templates.TemplateResponse("sap_form.html", context={"request": request})


@router.get("/import_files/preview/{cache_id}", response_class=HTMLResponse)
def import_file_preview(request:Request, cache_id:UUID, min_date:date, max_date:date):

    # retrieve data 
    ezeit_table = db.get_data_from_cache(EZeitDay, cache_id)
    if len(ezeit_table) == 0:
        return HTMLResponse(f"No ezeit data found for cache_id {cache_id}.", status_code=404)

    outlook_table = db.get_data_from_cache(Event, cache_id, source=EVS.OUTLOOK)
    if len(outlook_table) == 0:
        return HTMLResponse(f"No outlook data found for cache_id {cache_id}.", status_code=404)

    kapow_table = db.get_data_from_cache(Event, cache_id, source=EVS.KAPOW) # optional, table may be empty

    # create table views to insert into html templates

    table_views = [
        {"rows": ezeit_table, "source": "ezeit", "label": "EZeit"},
        {"rows": outlook_table, "source": EVS.OUTLOOK, "label": "Outlook"},
        {"rows": kapow_table, "source": EVS.KAPOW, "label": "Kapow"}
    ]
    
    for view in table_views:

        # reference rows for abbreviation
        rows = view["rows"]

        # remove id column as it is not needed for presentation
        for row in rows: row.pop('id') 

        # add row count
        view["row_count"] = len(rows)

        # Get sample rows for a shortened table view on top of collapsed tables containing all rows
        if len(rows) <= 3:
            samples = rows
        else:
            samples = random.sample(rows, 3)
        view["samples"] = samples

 
    return templates.TemplateResponse(
        "import_preview.html",
        context={
            "request": request,
            "table_views": table_views,
            "min_date": min_date,
            "max_date": max_date,
            "cache_id": cache_id
        }
    )


@router.get("/import_files/confirmed", response_class=HTMLResponse)
def import_file_confirmed(request:Request, cache_id:UUID, min_date:date, max_date:date):

    ezeit_rows = db.store_data(EZeitDay, cache_id, min_date, max_date)
    event_rows = db.store_data(Event, cache_id, min_date, max_date)

    ezeit_msg = f"Number of imported dates from EZeit: {ezeit_rows}"
    event_msg = f"Number of imported events from all event sources: {event_rows}"
    
    context = {
        "request": request, "cache_id": cache_id, 
        "min_date": min_date, "max_date": max_date,
        "ezeit_msg": ezeit_msg, "event_msg": event_msg
    }

    return templates.TemplateResponse("import_feedback.html", context=context)


@router.get("/import_files/rejected", response_class=HTMLResponse)
def import_file_rejected(request:Request, cache_id:UUID, min_date:date, max_date:date):
    
    db.delete_cache(EZeitDay, cache_id)
    db.delete_cache(Event, cache_id)

    msg = f"Cache with id {cache_id} was deleted."
    
    context = {
        "request": request, "cache_id": cache_id, 
        "min_date": min_date, "max_date": max_date,
        "ezeit_msg": msg, "event_msg": msg
    }

    return templates.TemplateResponse("import_feedback.html", context=context)


@router.get("/sap/monthly_report", response_class=HTMLResponse)
def sap_report(
    request: Request, month:int, year:int, 
    decimal_hours:bool | None = None, decimal_comma:bool | None = None):
    
    """        
    Aggregates time spent by cost_units for given month and year.
    Segments data into calendar weeks to construct corresponding tables
    in the html template returned.
    The data structure expected by the template:
        [
            {
                "title": "Tabelle KW 1",
                "dates": ["2025-06-01", "2025-06-02", "2025-06-03"],
                "rows": [
                    {"name": "a", "highlighted": false, "values": [7.5, 2.0, 0.0]},
                    {"name": "b", "highlighted": true, "values": [0.0, 8.0, 1.25]},
                    ...
                ]
            },
            ...
        ]
    """

    # find first and last date of specified month
    result = monthrange(year, month)
    n_days_in_month = result[1]
    from_date, to_date = date(year, month, 1), date(year, month, n_days_in_month)

    # get data
    data = agg_time_by_cost_unit(from_date, to_date)

    # flag if data is empty to adjust html output
    empty_data = True if len(data) == 0 else False


    # calculate decimal hours, always rounding off to 2 decimal places
    if decimal_hours == True:
        for row in data:
            for k, v in row.items():
                if isinstance(v, int):
                    number = Decimal(v / 60)
                    number = number.quantize(Decimal('0.01'), rounding=ROUND_FLOOR)
                    if decimal_comma == True:
                        number = str(number).replace(".", ",")
                    row[k] = number

    # add calendar week for each date
    for d in data:
        d["calendar_week"] = date.fromisoformat(d["date"]).isocalendar().week

    # extract unique calendar weeks 
    calendar_weeks = sorted(list(set(d["calendar_week"] for d in data)))

    # extract cost_units from configuration to adjust order and labels of rows
    cost_units = CONFIG.model_dump()["cost_units"]

    # segregate default and user defined cost units for table layout costomization
    cost_units_default = ["default_cost_unit", "overhead"]
    cost_units_user_defined = [k for k in cost_units.keys() if k not in cost_units_default]

    # define rows to be highlighted
    highlighted_rows = set()
    highlighted_rows.add("default_cost_unit_inkl_non_event_minutes")
    highlighted_rows.update(cost_units_user_defined)
     
    # set row order
    row_keys = \
        ["day_category", "default_cost_unit_inkl_non_event_minutes"] + \
        cost_units_user_defined + \
        cost_units_default + \
        ["booked_minutes", "event_minutes", "non_event_minutes"]

    # set row labels
    row_labels = {k: v["label"] for k,v in cost_units.items()}
    default_cost_unit_label = cost_units["default_cost_unit"]["label"]
    row_labels.update({
        "default_cost_unit_inkl_non_event_minutes": \
            default_cost_unit_label + \
            " (incl. non-event minutes)",
        "default_cost_unit": \
            default_cost_unit_label + \
            " (only event minutes)"             
    })

    # asseble one table view per calendar week
    tables = list()

    for calendar_week in calendar_weeks:
            
        week_data = [d for d in data if d["calendar_week"] == calendar_week]
        
        dates = [d["date"] for d in week_data]
        
        rows = list()
        for row_key in row_keys:
            row = dict()
            row["label"] = row_labels.get(row_key, row_key) # row_key is default if no label was set
            if decimal_hours == True: row["label"] = row["label"].replace("minutes", "hours")
            row["highlighted"] = True if row_key in highlighted_rows else False
            row["values"] = [d[row_key] for d in week_data]
            rows.append(row)
            
        table = {
            "title": f"Calendar Week {calendar_week}",
            "dates": dates,
            "colspan": len(dates) + 1,
            "rows" : rows
        }

        tables.append(table)

    # edge case december: might contain calendar week 1, which should be presented after calendar week 52
    if (1 in calendar_weeks and 52 in calendar_weeks):
        first_table = tables.pop(0)
        first_table["title"] += " (following year)" 
        tables.append(first_table)
            
    return templates.TemplateResponse(
        "sap_monthly_report.html", 
        context={"request": request, "tables": tables, 
                 "empty_data": empty_data, "from_date":from_date, "to_date":to_date}
    )