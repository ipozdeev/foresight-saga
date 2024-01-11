import pandas as pd
import numpy as np
from pathlib import Path
import requests
from joblib import Memory
import os

DATAPATH = Path(os.environ.get("DATAPATH", "data"))
FRED_API_KEY = os.environ.get("FRED_API_KEY")

memory = Memory(location=DATAPATH / "joblib")


def get_policy_rate_announcements():
    """"""
    files = [
        _f for _f in os.listdir(DATAPATH / "raw")
        if _f.startswith("policy-meetings") and _f.endswith(".csv")
    ]

    res = {}

    for _f in files:
        bank = _f.split("-")[-1][:-4]  # boc, snb etc.
        r = pd.read_csv(DATAPATH / "raw" / _f)
        r.index = r.get("date_announcement", r.get("date_meeting"))\
            .map(pd.to_datetime)
        if bank in ("rba", "rbnz"):
            r.index = 1
        res[bank] = r["rate_change"]

    return pd.concat(res, axis=1)


@memory.cache
def get_usd_exchange_rates():
    """"""
    series = {
        "eur": "DEXUSEU",
        "gbp": "DEXUSUK",
        "cad": "DEXCAUS",
        "aud": "DEXUSAL",
        "sek": "DEXSDUS",
        "nok": "DEXNOUS",
        "nzd": "DEXUSNZ",
        "chf": "DEXSZUS"
    }
    root = "https://api.stlouisfed.org"
    endpoint = "fred/series/observations"

    res = {}

    for _k, _v in series.items():
        pars = f"series_id={_v}" + "&" + f"api_key={FRED_API_KEY}"

        url = f"{root}/{endpoint}?{pars}"

        response = requests.get(url)

        _s = pd.read_xml(response.content)[["date", "value"]]\
            .set_index("date")["value"].replace(".", np.nan)\
            .astype(float)

        res[_k] = _s

    res = pd.concat(res, axis=1).rename(index=pd.to_datetime).sort_index()

    return res
