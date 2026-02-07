from typing import BinaryIO
import json
import datetime as dt
from app.models import Event, EventSources
from app.parsers.utils import csv_dict_reader, check_mandatory_columns

OUTLOOK_ERROR = "Import of outlook file failed"

MANDATORY_COLUMNS = {"Betreff","Beginnt am","Endet am","Beginnt um","Endet um","Kategorien"}

def parse_calendar_events(file:BinaryIO, min_date:dt.date, max_date:dt.date) -> list[Event]:

    # read csv
    rows = csv_dict_reader(file, sep=",")

    # remove empty rows
    rows = [row for row in rows if any(row.values())]

    # raise exception if mandatory columns are not included
    columns_recieved = rows[0].keys()
    check_mandatory_columns(MANDATORY_COLUMNS, columns_recieved, OUTLOOK_ERROR)

    # remove duplicated events: rare occurance due to synchronization issues
    # https://login.microsoftonline.com/common/reprocess?ctx=rQQIARAAfZO7a9x2AMdPPuf8IE1MKKVLS4ZASx3d_ST99HJxQda9dJZ09p3uIUMrJJ10lu6kn6zH6U5ToUugHUJb6GPsUshkQqElU5YuhkLmkLSZPZTSyWPtf6DLF77w_U7fz3d7g60yVVAFH5XJKth7YHLEhAemjZsmS-PQdjncIqCN05zlUpCjSc514nvbO39an736tvSB9Aj_-PUXP9x--AR7_zRNo2SvVjPDJHfipBp4dowS5KZVGwW13zDsBYZdYdiTtYShOAbQPMfxPEGwgOZgVa1PSSU4hnqgpyeaQnZFAJS6QMgjCaqklOpBA6r1-Vz1e3OdVHLdt0l1pC-V-jTtjgaFvgJALfRc1uaeqimpoumrbkuiFU1YKsV89nwNe7l2tytk6Sl5Iyj2CudybT1EofPv2paL4sCIUJL-WP653I2cUJqIKAwdO63epJ0w9Wwz9VB4FKPIiVPPSfaRn1JztcX2KHwkk4JiQPwwKobtIV0QNm4sF4cd3vSCTttIicFyzjR6OSXGcMXBbuYRWdCfRP0DizElQ9WH6AgfhQPPHoqJR58oc-fUXDJ2YXbigwOzzhUNwWhmrYXQPTg7pDrNjt7Q-Zmc-wIarHpBYyyBkFvJIYjZGXVdjM8Kf8YBfMqkvicySQzzhTwxpuSpO2GSoglWp8daKjJxn6Lw2ejEPEHGMCZsLVwM8dio9wSiaOFp3c3OFgKLdyJVRr02v9Jb49EAOgD1QjDLO02C5IM-TcrhwpISenHiTadRLIxbma1Bn7X8BRq63hFzBERzjHjDjcdNq0e0KbaZGaPmYSh2RUrMHcbMnfnAFlh9cKbiPMpafa9paVKDz7oTVvGm8UwcjXPNlfxpXB_LfGr7xdNy5RqsAIXPyg9Y1uEgpBmc4u0bbKGJ8wx0cJJhIW-xcMKR9kX5zvV2oTe5H8XI9ebOi3Xscv2dzY2dyrul-6UP3wblvc3N7Z3Sjbtax366dc3557_8IX_93afqN5-8fvPl-Veli1s1NNv1CrTws0wWJsIuDDsUAh3f4psoE7R8aa4m0cAa2BrK94k94nEFe1ypXFS2pLqhNjTIkv9UsEcbpWdb7_3vY17e3tq-xjMy72Hk87dKV3f--v3V-a_fP_27fXn3Yf9IL3ZTtZbZaYvv96k29BAPABq7wDuGGQo9rVvjuJVwnOyf72Bvdkr_AQ2&sessionid=77e84456-39c5-4c4a-964e-26749b74d82c&sso_nonce=AwABEgEAAAADAOz_BQD0_zTbT8eBRp00TwraZXqoBnOqUiC9Oqosch0xZ1QPiIfqeOe3pTEu_NtsAPDaSlAK0gdPTtOf0Ds9k4NIgGz5j8AgAA&client-request-id=dc5e62de-0094-4927-882d-3bdd83990c2c&mscrid=dc5e62de-0094-4927-882d-3bdd83990c2c)
    # Deduplication approach: https://www.geeksforgeeks.org/python/python-removing-duplicate-dicts-in-list/
    rows = list({json.dumps(row, sort_keys=True) for row in rows})
    rows = [json.loads(row) for row in rows]
    
    # parse rows
    for row in rows:
        
        # derive start timestamp
        start = row["Beginnt am"] + "." + row["Beginnt um"]
        row["start"] = dt.datetime.strptime(start, "%d.%m.%Y.%H:%M:%S")

        # derive end timestamp
        end = row["Endet am"] + "." + row["Endet um"]
        row["end"] = dt.datetime.strptime(end, "%d.%m.%Y.%H:%M:%S")

        # parse categories
        categories = row["Kategorien"]
        if categories == "" or categories is None:
            categories = "outlook_default"
        row["categories"] = json.dumps(categories.split(";"))

        # add column marking the data source
        row["source"] = EventSources.OUTLOOK.value
    
        # add placeholder column for additional metadata
        # This can be extended in future versions to hold arbitrary json data
        row["additional_metadata"] = None

    # sort by start timestamp
    rows.sort(key=lambda r: r["start"])

    # keep only events starting in specified date range
    _in_date_range = lambda x: min_date <= x.date() <= max_date
    rows = [row for row in rows if _in_date_range(row["start"])]

    # turn each row into pydantic model
    rows = [Event.model_validate(row) for row in rows]

    print(rows)

    return rows