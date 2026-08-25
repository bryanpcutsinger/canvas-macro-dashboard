"""Minimal FRED API client. Standard library only — no pip installs needed.

The API key is read from the FRED_API_KEY environment variable and never
written to logs or output files.
"""

import json
import os
import time
import urllib.parse
import urllib.request

BASE = "https://api.stlouisfed.org/fred"

RETRIES = 3
TIMEOUT_SECONDS = 20


class FredError(RuntimeError):
    """Raised when a FRED request fails after all retries."""


def _api_key():
    key = os.getenv("FRED_API_KEY")
    if not key:
        raise FredError("FRED_API_KEY environment variable is not set")
    return key


def _request(endpoint, params):
    query = {"api_key": _api_key(), "file_type": "json", **params}
    url = f"{BASE}/{endpoint}?" + urllib.parse.urlencode(query)
    last_err = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT_SECONDS) as resp:
                return json.load(resp)
        except Exception as err:  # network, HTTP, or JSON failure — retry all
            last_err = err
            time.sleep(2 ** (attempt + 1))  # 2s, 4s, 8s backoff
    raise FredError(f"{endpoint} failed after {RETRIES} attempts: {last_err}")


def redacted_url(endpoint, params):
    """The request URL with the API key removed, for provenance logs."""
    query = {"api_key": "REDACTED", "file_type": "json", **params}
    return f"{BASE}/{endpoint}?" + urllib.parse.urlencode(query)


def series_meta(series_id):
    """Metadata (title, units, frequency, seasonal adjustment) for one series."""
    data = _request("series", {"series_id": series_id})
    return data["seriess"][0]


def observations(series_id, start, **extra):
    """Sorted (date, value) pairs; missing values (".") are dropped."""
    params = {"series_id": series_id, "observation_start": start, **extra}
    data = _request("series/observations", params)
    obs = []
    for o in data["observations"]:
        if o["value"] == ".":
            continue
        obs.append((o["date"], float(o["value"])))
    obs.sort(key=lambda pair: pair[0])
    if not obs:
        raise FredError(f"{series_id}: no usable observations returned")
    return obs
