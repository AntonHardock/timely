
from fastapi import APIRouter, HTTPException, status
import json
from datetime import date

from app.models import EventSources, Event
import app.database.sqlite_operations as sql_ops
from app.config import parse_config, get_root_path

router = APIRouter(prefix="/api")

# unpack important constants from config
CONFIG = parse_config()

# get root for resources
root_path = get_root_path()

@router.get(f"/agg_time_by_cost_unit") 
def agg_time_by_cost_unit(from_date:date, to_date:date) -> list[dict]:

    # check for invalid date entry
    if from_date > to_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Parameter 'from_date' has to predate parameter 'to_date'")

    # check for ambigous mappings of events to cost_units
    ambigous_mappings = _get_ambigous_event_mappings()
    if len(ambigous_mappings) > 0:
        msg = "Found work events with redundant or ambigous mappings to cost units." \
            + " Please correct the entries in question and reimport the data." \
            + " Affected events are listed below"
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": msg,
                "affected_events": ambigous_mappings
            }
        )

    # read corresponding sql template
    template_filepath = root_path / "app/routers/agg_time_by_cost_unit.sql"
    with open(template_filepath,  "r", encoding="utf-8") as f:
        sql_template = f.read()

    # insert dynamic sql statements based on cost units in configuration
    sql_pivot_statements = list()
    sql_sum_columns = list()

    for cost_unit in CONFIG.cost_units.keys():
        
        sql_pivot_statements.append(f"MAX(CASE WHEN cost_unit = '{cost_unit}' THEN event_time_in_cost_unit ELSE 0 END) AS '{cost_unit}'")
        
        sql_sum_columns.append(f"e.{cost_unit}")

    sql_pivot_statements = ", ".join(sql_pivot_statements)        
    sql_sum_columns = " + ".join(sql_sum_columns)

    sql_template = sql_template.format(
        sql_pivot_statements = sql_pivot_statements,
        sql_sum_columns = sql_sum_columns
    )

    print(sql_template)

    # map query parameters to names in sql template
    # table names have to be part of the sql template, 
    # see https://stackoverflow.com/questions/78516750/parametrize-table-name-in-sql-query
    params = {
        "cost_units": json.dumps(CONFIG.model_dump()["cost_units"]),
        "from_date": from_date.isoformat(),
        "to_date": to_date.isoformat()
    }
    
    result = sql_ops.fetch_all_as_dicts(sql_template, params)
    
    faulty_bookings = [r for r in result if r["event_minutes_exceed_booked_minutes"] == 1]
    if len(faulty_bookings) != 0:
        detail = {"error": "Event time exceeds booked time on followin dates", "data":  faulty_bookings}
        raise HTTPException(status_code=422, detail=detail)

    return result


def _get_ambigous_event_mappings() -> list[tuple]:
    """For each event source, find events with categories assigned to multiple cost_units.
    Events of any given source, e.g. outlook, can be stored with multiple categories assigned.
    This allows for flexibility as to how users can work with categories in respective programs.
    However, each event has to be assigned to one and only one cost_unit.
    Otherwise, the time spent on that event woult be booked redundantly"""
    
    results = list()

    for source in EventSources:
        source = source.value    
        mapped_categories = CONFIG.mapped_categories_of_event_source(source)
        mapped_categories = ",".join(f"'{c}'" for c in mapped_categories) 
        sql = f"""
            SELECT 
                e.id, e.source, 
                COUNT(array.value) AS n_mapped_categories,
                GROUP_CONCAT(array.value, ' | ') AS invalid_category_combination
            FROM {Event.table_name} e, json_each(e.categories) array
            WHERE e.source = '{source}'
            AND array.value IN ({mapped_categories})
            GROUP BY e.id
            HAVING n_mapped_categories > 1
            ;"""
        params = dict()
        result = sql_ops.fetch_all_as_dicts(sql, params)
        results.extend(result)

    return results