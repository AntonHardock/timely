import json
from datetime import date, datetime, timedelta
from uuid import UUID

import app.database.sqlite_operations as sql_ops
from app.models import CoreDataModel, EZeitDay, EZeitDayCache, Event, EventCache
from app.database.pydantic_to_sqlite import create_table_from_pydantic

CORE_DATA_MODELS = [
    EZeitDay, EZeitDayCache, 
    Event, EventCache
]

CORE_DATA_CACHES = [EZeitDayCache, EventCache]

def initiate_db(models:list[CoreDataModel] = CORE_DATA_MODELS) -> None:
    
    sql_ops.create_db()
 
    for model in models:
        table_name = model.table_name
        primary_key = model.primary_key
        create_table_from_pydantic(table_name, model, primary_key)


def _insert_parsed_data(table_name:str, data:list[CoreDataModel]) -> None:

    # dump pydantic models to json so that types like datetime or UUID become strings
    # round_trip=True preserves nested JSON
    # see https://github.com/pydantic/pydantic/discussions/7204
    # and https://docs.pydantic.dev/latest/concepts/serialization/#modelmodel_dump
    data = (x.model_dump_json(round_trip=True) for x in data)

    # load json to get a dict of basic python types again, as needed for 
    data = (json.loads(x) for x in data) 

    # convert to a list of tuples for insert_many operation
    data = [tuple(x.values()) for x in data]

    sql_ops.insert_many(table_name, data)


def _match_cache_model(data_model_class:CoreDataModel) -> CoreDataModel:
    """Based on input data model class, returns the corresponding class used for caching data"""

    # caveats with matching classes using the match syntax:
    # https://stackoverflow.com/questions/71441761/how-to-use-match-case-with-a-class-type
    # https://stackoverflow.com/a/70124597

    match data_model_class.__qualname__:
        case EZeitDay.__qualname__:
            return EZeitDayCache
        case Event.__qualname__:
            return EventCache
        case _:
            raise ValueError("Data model could not be matched successfully. Check the input.")


def cache_data(model:CoreDataModel, data:list[CoreDataModel], cache_id:UUID, timestamp:datetime) -> None:

    cache_model = _match_cache_model(model)
    table_name = cache_model.table_name
    cache_fields = {"cache_id": cache_id, "cache_timestamp": timestamp}
    
    data = (model.model_dump(round_trip=True) | cache_fields for model in data)
    data = [cache_model.model_validate(model) for model in data]
    _insert_parsed_data(table_name, data)


def get_data_from_cache(model:CoreDataModel, cache_id:UUID, source:str | None = None) -> list[dict]:
    
    columns = ", ".join(model.model_fields.keys())

    cache_model = _match_cache_model(model)
    table = cache_model.table_name

    sql = f"SELECT {columns} FROM {table} WHERE cache_id = '{cache_id}'"
    if source is None:
        sql += ";"
    else:
        sql += f" AND source = '{source}';"
    
    params = dict()
    records = sql_ops.fetch_all_as_dicts(sql, params)

    return records


def store_data(model:CoreDataModel, cache_id:UUID, min_date:date, max_date:date) -> int:

    """Stores data into a table derived from the CoreDataModel.
    Retrieves the data to store from a corresponding cache table as mapped to the CoreDataModel.
    Caching is implemented in a way that it could serve multiple users.
    With sqlite, however, this would only work when data imports are processed sequentially,
    as parallel writes are not supported. The data storage currently only serves one user, since no user management
    is implemented yet. 
    
    In addition to the cache_id, min_date and max_date are nesseccary for idempotent storage. 
    The data in given date range is deleted completely before writing from cache.
    """

    cache_model = _match_cache_model(model)
    
    # derive relevant table names and filter statements for sql
    table = model.table_name
    columns = ", ".join(model.model_fields.keys())
    cache_table = cache_model.table_name
    cache_filter = f"cache_id = '{cache_id}'"
    # CAUTION: DATE() ensures last date is inclusive for datetimes of that date: https://stackoverflow.com/questions/29971762/sqlite-database-select-the-data-between-two-dates
    date_filter = f"DATE({model.primary_date}) BETWEEN '{min_date.isoformat()}' AND '{max_date.isoformat()}'"

    # check if cached data exists and proceed acccordingly
    sql = f"SELECT COUNT(*) FROM {cache_table} WHERE {cache_filter}" 
    result = sql_ops.fetch(sql)
    n_rows = result[0]

    # delete and overwrite data in given date range ONLY if cached data still exists
    if n_rows > 0:
      
        sql_delete_data = f"DELETE FROM {table} WHERE {date_filter};"

        sql_insert_data = f"""INSERT INTO {table}({columns})
            SELECT {columns} FROM {cache_table} WHERE {cache_filter};"""

        sql_delete_cache = f"DELETE FROM {cache_table} WHERE {cache_filter};"

        sql_script = sql_delete_data + sql_insert_data + sql_delete_cache

        sql_ops.execute_script(sql_script)
  
    return n_rows


def delete_cache(model:CoreDataModel, cache_id:UUID) -> None:

    cache_model = _match_cache_model(model)
   
    # derive relevant table names and filter statements for sql
    cache_table = cache_model.table_name
    cache_filter = f"cache_id = '{cache_id}'"

    sql = f"DELETE FROM {cache_table} WHERE {cache_filter};"
    sql_ops.execute(sql)


def clean_cache_by_age(max_age_in_minutes:int, cache_models:list[CoreDataModel] = CORE_DATA_CACHES) -> None:

    cutoff_datetime = datetime.now() - timedelta(minutes=max_age_in_minutes)

    for model in cache_models:
        table_name = model.table_name
        primary_date = model.primary_date

        sql = f"""DELETE FROM {table_name} 
            WHERE {primary_date} < '{cutoff_datetime.isoformat()}'"""
        sql_ops.execute(sql)