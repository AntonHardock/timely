from pydantic import BaseModel, Field, Json
from typing import ClassVar, Literal
from datetime import date, datetime
from enum import Enum
from uuid import UUID, uuid4

# -------------------------------------------------------------------------------
# primary data structures
# -------------------------------------------------------------------------------

class CoreDataModel(BaseModel):
    """A core data model represents a datastructure that the application 
    revolves around. Aside from validating input data,
    they are used to derive corresponding database tables."""
    table_name: ClassVar[str]
    primary_key: ClassVar[str]
    primary_date: ClassVar[str]


class DayCategories(str, Enum):
    ON_WORK = "on_work"
    OFF_WORK = "off_work"
    OVERTIME_LEAVE = "overtime_leave"
    VACATION = "vacation"
    SICK_LEAVE = "sick_leave"

class EZeitDay(CoreDataModel):
    table_name = "ezeit_days"
    primary_key = "id"
    primary_date = "date"
    id: UUID = Field(default_factory=lambda: uuid4().hex)
    date: date
    booked_minutes: int
    day_category: Literal[
        DayCategories.ON_WORK,
        DayCategories.OFF_WORK,
        DayCategories.OVERTIME_LEAVE,
        DayCategories.VACATION,
        DayCategories.SICK_LEAVE
    ]


class EventSources(str, Enum):
    KAPOW = "kapow"
    OUTLOOK = "outlook"

class Event(CoreDataModel):
    table_name: ClassVar[str] = "events"
    primary_key: ClassVar[str] = "id"
    primary_date: ClassVar[str] = "start"
    id: UUID = Field(default_factory=lambda: uuid4().hex)
    start: datetime
    end: datetime
    categories: Json[list[str]]
    source: Literal[EventSources.KAPOW, EventSources.OUTLOOK]
    additional_metadata: Json | None

# -------------------------------------------------------------------------------
# secondary data structures
# -------------------------------------------------------------------------------

class EZeitDayCache(EZeitDay):
    """Extension used to cache data in a separate database table"""
    cache_id: UUID
    cache_timestamp: datetime
    table_name = EZeitDay.table_name + "_cache"
    primary_date = "cache_timestamp"

class EventCache(Event):
    """Extension used to cache data in a separate database table"""
    cache_id: UUID
    cache_timestamp: datetime
    table_name = Event.table_name + "_cache"
    primary_date = "cache_timestamp"


class EZeitDayList(BaseModel):
    """Explicit and extendable list type for REST API"""
    data: list[EZeitDay]

class EventList(BaseModel):
    """Explicit and extendable list type for REST API"""
    data: list[Event]
