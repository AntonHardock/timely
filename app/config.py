from pathlib import Path
import sys
from app.config_model import MainConfig

PROJECT_ROOT = Path(__file__).parents[1]


def parse_config() -> MainConfig:
    
    config_path = PROJECT_ROOT / "configs/config.json"

    with open(config_path, "r") as f:
        config = f.read()

    config = MainConfig.model_validate_json(config)

    return config


def get_root_path() -> Path:
    """returns the root path of the project and modifies it when run as pyinstaller bundle
        see https://pyinstaller.org/en/stable/runtime-information.html#using-file 
    """

    root_path = PROJECT_ROOT

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        root_path = Path(sys._MEIPASS)

    return root_path