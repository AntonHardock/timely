from lxml import etree
from typing import BinaryIO
from app.models import Event, EventSources
import json
from datetime import date

PARSER = etree.XMLParser(encoding="utf-8")

KAPOW_ERROR = "Import of kapow file failed"

def parse_kapow_sessions(file:BinaryIO, min_date:date, max_date:date) -> list[Event]:
    
    # parse xml root
    xml_tree = etree.parse(file, PARSER)
    xml = xml_tree.getroot()

    # parse kapow sessions as events in specified date range
    _in_date_range = lambda x: x >= min_date and x <= max_date

    events = list()
    for project in xml.iterfind(f"./project"):
        project_name = project.attrib["name"]
        sessions = (dict(p.attrib, **{"categories": project_name}) for p in project)
        sessions = [s for s in sessions if _in_date_range(date.fromisoformat(s["date"]))]
        events.extend(sessions)

    # transform event dictionaries into target pydantic models 
    _transform_event = lambda e: {
        "start": e["date"] + "T" + e["start"],
        "end": e["date"] + "T" + e["stop"],
        "categories": json.dumps([e["categories"]]),
        "source": EventSources.KAPOW.value,
        "additional_metadata": json.dumps({
            "kapow_billed": int(e["billed"]),
            "kapow_note": e["note"]
        })
    }
    
    events = (_transform_event(e) for e in events)

    events = [Event.model_validate(e) for e in events]

    return events






