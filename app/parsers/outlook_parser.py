import pandas as pd
from app.models import Event, EventSources
from typing import BinaryIO
import json
from datetime import date
from app.parsers.exceptions import ColumnsError

OUTLOOK_ERROR = "Import of outlook file failed"

def parse_calendar_events(file:BinaryIO, min_date:date, max_date:date) -> list[Event]:

    # read and adjust column names
    df = pd.read_csv(file, sep=",")

    # ensure that expected columns are included
    mandatory_columns = ["Betreff","Beginnt am","Endet am","Beginnt um","Endet um","Kategorien"]
    if not set(mandatory_columns).issubset(set(df.columns)):
        msg = f"{OUTLOOK_ERROR}. Following columns are mandatory: {mandatory_columns}. Got columns: {list(df.columns)}"
        raise ColumnsError(msg)
    
    # remove duplicated events: rare occurance due to synchronization issues
    # https://login.microsoftonline.com/common/reprocess?ctx=rQQIARAAfZO7a9x2AMdPPuf8IE1MKKVLS4ZASx3d_ST99HJxQda9dJZ09p3uIUMrJJ10lu6kn6zH6U5ToUugHUJb6GPsUshkQqElU5YuhkLmkLSZPZTSyWPtf6DLF77w_U7fz3d7g60yVVAFH5XJKth7YHLEhAemjZsmS-PQdjncIqCN05zlUpCjSc514nvbO39an736tvSB9Aj_-PUXP9x--AR7_zRNo2SvVjPDJHfipBp4dowS5KZVGwW13zDsBYZdYdiTtYShOAbQPMfxPEGwgOZgVa1PSSU4hnqgpyeaQnZFAJS6QMgjCaqklOpBA6r1-Vz1e3OdVHLdt0l1pC-V-jTtjgaFvgJALfRc1uaeqimpoumrbkuiFU1YKsV89nwNe7l2tytk6Sl5Iyj2CudybT1EofPv2paL4sCIUJL-WP653I2cUJqIKAwdO63epJ0w9Wwz9VB4FKPIiVPPSfaRn1JztcX2KHwkk4JiQPwwKobtIV0QNm4sF4cd3vSCTttIicFyzjR6OSXGcMXBbuYRWdCfRP0DizElQ9WH6AgfhQPPHoqJR58oc-fUXDJ2YXbigwOzzhUNwWhmrYXQPTg7pDrNjt7Q-Zmc-wIarHpBYyyBkFvJIYjZGXVdjM8Kf8YBfMqkvicySQzzhTwxpuSpO2GSoglWp8daKjJxn6Lw2ejEPEHGMCZsLVwM8dio9wSiaOFp3c3OFgKLdyJVRr02v9Jb49EAOgD1QjDLO02C5IM-TcrhwpISenHiTadRLIxbma1Bn7X8BRq63hFzBERzjHjDjcdNq0e0KbaZGaPmYSh2RUrMHcbMnfnAFlh9cKbiPMpafa9paVKDz7oTVvGm8UwcjXPNlfxpXB_LfGr7xdNy5RqsAIXPyg9Y1uEgpBmc4u0bbKGJ8wx0cJJhIW-xcMKR9kX5zvV2oTe5H8XI9ebOi3Xscv2dzY2dyrul-6UP3wblvc3N7Z3Sjbtax366dc3557_8IX_93afqN5-8fvPl-Veli1s1NNv1CrTws0wWJsIuDDsUAh3f4psoE7R8aa4m0cAa2BrK94k94nEFe1ypXFS2pLqhNjTIkv9UsEcbpWdb7_3vY17e3tq-xjMy72Hk87dKV3f--v3V-a_fP_27fXn3Yf9IL3ZTtZbZaYvv96k29BAPABq7wDuGGQo9rVvjuJVwnOyf72Bvdkr_AQ2&sessionid=77e84456-39c5-4c4a-964e-26749b74d82c&sso_nonce=AwABEgEAAAADAOz_BQD0_zTbT8eBRp00TwraZXqoBnOqUiC9Oqosch0xZ1QPiIfqeOe3pTEu_NtsAPDaSlAK0gdPTtOf0Ds9k4NIgGz5j8AgAA&client-request-id=dc5e62de-0094-4927-882d-3bdd83990c2c&mscrid=dc5e62de-0094-4927-882d-3bdd83990c2c)
    df = df.drop_duplicates()

    # derive full datetime entries for beginning and end of each event
    df["Beginn"] = df["Beginnt am"] + "." + df["Beginnt um"]
    df["Beginn"] = pd.to_datetime(df["Beginn"], format="%d.%m.%Y.%H:%M:%S")

    df["Ende"] = df["Endet am"] + "." + df["Endet um"]
    df["Ende"] = pd.to_datetime(df["Ende"], format="%d.%m.%Y.%H:%M:%S")

    # fill uncategorized events with default category
    df["Kategorien"] = df["Kategorien"].fillna("outlook_default")

    # parse events into expected form
    df["Kategorien"] = df["Kategorien"].apply(lambda x: json.dumps(x.split(";")))

    # rename and keep only required columns
    required_columns = {
        "Beginn": "start",
        "Ende": "end",
        "Kategorien": "categories"
    }
    df = df.rename(columns=required_columns, errors="raise")
    df = df[required_columns.values()]

    # add column marking the data source
    df["source"] = EventSources.OUTLOOK.value
    
    # add placeholder column for additional metadata
    # This can be extended in future versions to hold arbitrary json data
    df["additional_metadata"] = None

    # sort chronologically
    df = df.sort_values(by="start")

    # filter by specified date range
    cond = (
        (df["start"].dt.date >= min_date) &
        (df["start"].dt.date <= max_date)
    )
    df = df[cond]

    # convert dataframe into a list of pydantic objects
    data = df.to_dict(orient="records")
    data = [Event.model_validate(record) for record in data]

    return data