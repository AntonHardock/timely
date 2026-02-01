import csv
from typing import BinaryIO


def csv_dict_reader(file:BinaryIO, encoding:str="utf-8-sig", sep:str=";") -> list[dict]:
    """Reads binary csv as list of dictionaries. Uses first row as header.
    Strips all keys and values from whitespaces."""

    decoded = (line.decode(encoding) for line in file)    
    reader = csv.DictReader(decoded, delimiter=sep)
    rows = [{k.strip():v.strip() for k,v in row.items()} for row in reader]
    return rows


def add_exception_context(exc:Exception, context:str):
    """Adds context to message of last handled exception.
    Raises the exception afterwards, see: https://stackoverflow.com/a/18001776.
    Only needed for Python < 3.11, since a new method exists
    to achieve this: https://stackoverflow.com/a/75549200
    """
    args = exc.args
    if not args:
        arg0 = context
    else:
        arg0 = f"{args[0]}\n{context}"
    exc.args = (arg0,) + args[1:]
    raise


def check_mandatory_columns(
    mandatory_columns:set[str], 
    columns_recieved:set[str], 
    error_msg_prefix:str) -> None:
    
    mandatory_columns = set(mandatory_columns)
    if not mandatory_columns.issubset(columns_recieved):
        msg = f"""{error_msg_prefix}.
            Following columns are mandatory: {list(mandatory_columns)}.
            Got columns: {list(columns_recieved)}"""
        raise ValueError(msg)
    else:
        return None

