import sqlite3
from contextlib import contextmanager
from app.config import parse_config
from pathlib import Path

CONFIG = parse_config()
DATABASE = Path(CONFIG.database_path) / CONFIG.database_name

# ---------------------------------------------------------------------------------------
# Custom Context Managers: https://stackoverflow.com/questions/67436362/decorator-for-sqlite3
#   - default context manager not working as expected with sqlite, connections are not closed: 
#       https://blog.rtwilson.com/a-python-sqlite3-context-manager-gotcha/
#   - Why is the cursor yielded in below context managers?
#       This is required by with statements: https://docs.python.org/3/library/contextlib.html
# ---------------------------------------------------------------------------------------

@contextmanager
def read_manager():  
    conn = sqlite3.connect(DATABASE)
    conn.set_trace_callback(print)
    try:
        cur = conn.cursor()
        yield cur 
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@contextmanager
def read_manager_row_factory(): 
    conn = sqlite3.connect(DATABASE)
    conn.set_trace_callback(print)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        yield cur 
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


@contextmanager
def write_manager(): 
    conn = sqlite3.connect(DATABASE)
    conn.set_trace_callback(print)
    try:
        cur = conn.cursor()
        yield cur
    except Exception as e:
        conn.rollback()
        raise e
    else:
        conn.commit()
    finally:
        conn.close()

# ---------------------------------------------------------------------------------------
# READ ONLY OPERATIONS
# ---------------------------------------------------------------------------------------

def create_db() -> None:
    """Initiates database by opening a connection without further operations.
    By opening a database connection through a context manager,
    the sqlite3 module creates a new database file if it does not exist"""
    with read_manager() as _:
        return
    

def fetch(sql:str) -> tuple:
    with read_manager() as cur: 
        record = cur.execute(sql).fetchone()
    return record


def fetch_as_dict(sql:str) -> dict:
    with read_manager_row_factory() as cur:
        record = cur.execute(sql).fetchone()
    return dict(record)


def fetch_all(sql:str) -> list[tuple]:
    with read_manager() as cur: 
        records = cur.execute(sql).fetchall()
    return records


def fetch_all_as_dicts(sql:str, params:dict) -> list[dict]:
    with read_manager_row_factory() as cur:
        records = cur.execute(sql, params).fetchall()
    return [dict(r) for r in records]

# ---------------------------------------------------------------------------------------
# WRITE OPERATIONS
# ---------------------------------------------------------------------------------------

def execute(sql:str) -> None:
    with write_manager() as cur:
        cur.execute(sql)


def execute_script(sql_script:str) -> None:
    with write_manager() as cur:
        cur.executescript(sql_script)


def insert(table_name:str, record:tuple) -> None:
    with write_manager() as cur:
        placeholders = ", ".join(["?"] * len(record))
        sql = f"INSERT INTO {table_name} VALUES({placeholders})"
        cur.execute(sql, record)


def insert_many(table_name:str, records:list[tuple]) -> None:
    """Assumes equal length for each tuple in data"""
    with write_manager() as cur:
        placeholders = ", ".join(["?"] * len(records[0]))
        sql = f"INSERT INTO {table_name} VALUES({placeholders})"
        cur.executemany(sql, records)
