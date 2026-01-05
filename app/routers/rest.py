from fastapi import APIRouter
import app.models as mo
from app.models import EventSources as IMS, DayCategories as EZC
import app.database.sqlite_operations as sql_ops
from typing import Literal

router = APIRouter(prefix="/api")

EZEIT_TABLE = mo.EZeitDay.table_name
EVENT_TABLE = mo.Event.table_name


@router.get(f"/{EZEIT_TABLE}")
def get_ezeit(limit:int=10, offset:int=0, on_work:bool=False,
    random:bool=False, ids_only:bool=False) -> mo.EZeitDayList:
    
    columns = "id" if ids_only else "*"
    sql = f"SELECT {columns} FROM {EZEIT_TABLE}"
    
    conditions = list()
    if on_work:
        conditions.append(f"day_category = '{EZC.ON_WORK.value}'")
    if conditions:
        conditions = " AND ".join(conditions)
        sql += " WHERE " + conditions

    order_by = "RANDOM()" if random else "date"
    sql += f" ORDER BY {order_by} LIMIT {limit} OFFSET {offset};"

    print(sql)

    data = sql_ops.fetch_all_as_dicts(sql)
    response = {
        "data": data
    }
    return response



@router.get(f"/{EVENT_TABLE}")
def get_workevents(limit:int=10, offset:int=0, source:Literal[IMS.KAPOW, IMS.OUTLOOK] | None = None,
    random:bool=False, ids_only:bool=False) -> mo.EventList:
    
    columns = "id" if ids_only else "*"
    sql = f"SELECT {columns} FROM {EVENT_TABLE}"
    
    conditions = list()
    if source:
        conditions.append(f"source = '{source}'")
    if conditions:
        conditions = " AND ".join(conditions)
        sql += " WHERE " + conditions

    order_by = "RANDOM()" if random else "start"
    sql += f" ORDER BY {order_by} LIMIT {limit} OFFSET {offset};"

    print(sql)

    params = dict()
    data = sql_ops.fetch_all_as_dicts(sql, params)
    response = {
        "data": data
    }
    return response