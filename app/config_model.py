from pydantic import BaseModel, Field, model_validator
from app.models import EventSources
from typing_extensions import Self

MANDATORY_COST_UNITS = {"default_cost_unit", "overhead"}
MANDATORY_OUTLOOK_CATEGORIES = {"outlook_default"}


class CostUnit(BaseModel):
    label: str
    outlook: list[str]
    kapow: list[str]

    @model_validator(mode="after")
    def check_mandatory_fields(self) -> Self:
        missing = set(e.value for e in EventSources) - set(self.model_fields)
        if len(missing) > 0:
            raise ValueError(f"Class CostUnit is missing the following fields: {missing}")
        return self


class MainConfig(BaseModel):
    database_name: str = Field(pattern=r".*\.sqlite3$")
    database_path: str
    run_in_dev_mode: bool
    cost_units: dict[str, CostUnit]

    @model_validator(mode="after")
    def check_mandatory_cost_units(self) -> Self:
        missing = MANDATORY_COST_UNITS - set(self.cost_units.keys())
        if len(missing) > 0:
            raise ValueError(f"The following mandatory cost units are missing: {missing}")
        return self
    
    @model_validator(mode="after")
    def check_mandatory_categories_in_default_cost_unit(self) -> Self:
        categories = self.cost_units["default_cost_unit"].outlook
        missing = MANDATORY_OUTLOOK_CATEGORIES - set(categories)
        if len(missing) > 0:
            raise ValueError(f'In "default_cost_unit", the following mandatory categores are missing for "outlook": {missing}')
        return self
    
    def mapped_categories_of_event_source(self, event_source: EventSources) -> list:
        all_categories = list()
        for cost_unit in self.cost_units.values():
            cost_unit = cost_unit.model_dump()
            categories = cost_unit.get(event_source)
            all_categories.extend(categories)
        return all_categories
