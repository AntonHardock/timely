from pydantic import BaseModel
from pydantic.fields import FieldInfo
from types import UnionType
import app.database.sqlite_operations as sql_ops

PYDANTIC_TO_SQLITE_MAP = {
    "int": "INTEGER",
    "float": "REAL",
    "str": "TEXT",
    "bool": "INTEGER", # sqlite has no boolean type but supports boolean operators working on 0 and 1!
    "list": "TEXT", # sqlite has no json type but supports operators for json arrays and objects
    "list[str]": "TEXT",
    "pydantic.types.Json": "TEXT",
    "dict": "TEXT",
    "date": "TEXT",
    "datetime": "TEXT",
    "Literal": "TEXT",
    "UUID": "TEXT" 
}

def create_table_from_pydantic(table_name:str, model:BaseModel, primary_key:str, drop_if_exists:bool=False) -> None:
    """Create sqlite table from pydantic model. Columns are declared in order of model fields"""
    
    fields = [_parse_field(f, i, primary_key) for f, i in model.model_fields.items()]
    fields = ", ".join(fields)
    sql_create_table = f"CREATE TABLE {table_name} (\n{fields}\n);"
    
    if drop_if_exists:
        sql_drop_if_exists = f"DROP TABLE IF EXISTS {table_name};"
        sql_script = sql_drop_if_exists + sql_create_table
        sql_ops.execute_script(sql_script)
    else:
        sql_ops.execute(sql_create_table)


def _parse_field(field: str, info: FieldInfo, primary_key:str) -> str:
    """Translates a pydantic field info to a sqlite column constraint"""    
    
    annotation = info.annotation
    nullable = False
    field_type = None

    if hasattr(annotation, "__name__"):
        field_type = annotation.__name__
    elif isinstance(annotation, UnionType):
        field_type = str(annotation)
        union_types = field_type.split(" | ") #split union type definitions
        if "None" in union_types: 
            nullable = True # if None type is present, interpret declared type as nullable
            union_types = [t for t in union_types if t != "None"] # remove None from list of valid types
        field_type = union_types[0] # pick first listed type for sqlite mapping
    else:
        msg = """Pydantic annotation object derived from FieldInfo neither has a __name__ atribute 
            nor is it of type UnionType - This is not handled by this function so far"""
        raise ValueError(msg)
    
    storage_class = PYDANTIC_TO_SQLITE_MAP[field_type]
    
    result = f"{field} {storage_class}"
    if not nullable: 
        result += " NOT NULL" # in sqlite, even primary keys can be null, which I assume is not desired for typical use cases
    if field == primary_key:
        result += " PRIMARY KEY"
    return result