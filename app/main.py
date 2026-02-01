from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import uvicorn
import sys
sys.path.append(Path(__file__).parents[1].as_posix())

from app.config import parse_config, get_static_resource_root
from app.routers import agg_time_by_cost_unit, frontend, import_files, rest
from app.database import db

# -----------------------------------------------------
# Initiation
# -----------------------------------------------------

# global config
CONFIG = parse_config()
DATABASE = Path(CONFIG.database_path) / CONFIG.database_name

# initiate database
if DATABASE.is_file():
    print(f"Database {DATABASE} already exists. Moving on...")
else:
    print(f"Creating new database file: {DATABASE}...")
    db.initiate_db()
    print("Database created.")

# clean database cache
MAX_AGE_IN_MINUTES = 20
print(f"Cleaning cache tables: Deleting rows cached {MAX_AGE_IN_MINUTES} minutes ago or older")
db.clean_cache_by_age(MAX_AGE_IN_MINUTES)

# instantiate api entrypoint, static resources and routers
app = FastAPI()

static_resource_root = get_static_resource_root()
app.mount("/static", StaticFiles(directory=(static_resource_root / "static")), name="static")
app.mount("/javascript", StaticFiles(directory=(static_resource_root / "javascript")), name="javascript")

app.include_router(agg_time_by_cost_unit.router)
app.include_router(import_files.router)
app.include_router(rest.router)
app.include_router(frontend.router)

# -----------------------------------------------------
# Run app
# -----------------------------------------------------

if __name__ == "__main__":
    
    cwd = Path(__file__).parent
    html_templates = cwd / "templates"
    static_files = cwd / "static"

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[
            html_templates.as_posix(), 
            static_files.as_posix(),
            cwd.as_posix()
        ]
    )
