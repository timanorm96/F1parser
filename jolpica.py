"""
Collector for Jolpica F1 API (Ergast-compatible successor).
Base URL: https://api.jolpi.ca/ergast/f1/
Docs:     https://jolpica-f1.netlify.app/

Uses file-based JSON cache so repeated runs never hit the network.
"""

import json
import time
import hashlib
from pathlib import Path
from typing import Any

import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
CACHE_DIR = Path(__file__).parent.parent / ".cache"
CACHE_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "F1-Parser/1.0 (personal analytics project)",
    "Accept": "application/json",
})


def _cache_path(url: str, params: dict) -> Path:
    key = url + json.dumps(params, sort_keys=True)
    digest = hashlib.md5(key.encode()).hexdigest()
    return CACHE_DIR / f"{digest}.json"


def _get(endpoint: str, params: dict | None = None, ttl_hours: int = 72) -> dict:
    """GET with file cache. Historical data cached 72h by default."""
    params = params or {}
    params["format"] = "json"
    url = f"{BASE_URL}/{endpoint}.json"

    cache_file = _cache_path(url, params)
    if cache_file.exists():
        age_hours = (time.time() - cache_file.stat().st_mtime) / 3600
        if age_hours < ttl_hours:
            return json.loads(cache_file.read_text())

    for attempt in range(3):
        try:
            resp = SESSION.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            cache_file.write_text(json.dumps(data))
            return data
        except requests.RequestException as e:
            if attempt == 2:
                raise
            print(f"  Retry {attempt + 1}/3 for {endpoint}: {e}")
            time.sleep(2 ** attempt)


def get_season_races(season: int | str = "current") -> list[dict]:
    """Return list of all rounds in a season."""
    data = _get(f"{season}/races")
    return data["MRData"]["RaceTable"]["Races"]


def get_race_results(season: int | str, round_num: int | str) -> list[dict]:
    """Finishing results for one race."""
    data = _get(f"{season}/{round_num}/results")
    races = data["MRData"]["RaceTable"]["Races"]
    return races[0]["Results"] if races else []


def get_qualifying_results(season: int | str, round_num: int | str) -> list[dict]:
    """Qualifying results for one race."""
    data = _get(f"{season}/{round_num}/qualifying")
    races = data["MRData"]["RaceTable"]["Races"]
    return races[0]["QualifyingResults"] if races else []


def get_driver_standings(season: int | str, round_num: int | str | None = None) -> list[dict]:
    """Driver championship standings after a given round (or end of season)."""
    endpoint = f"{season}/driverStandings" if round_num is None else f"{season}/{round_num}/driverStandings"
    data = _get(endpoint)
    lists = data["MRData"]["StandingsTable"]["StandingsLists"]
    return lists[0]["DriverStandings"] if lists else []


def get_constructor_standings(season: int | str, round_num: int | str | None = None) -> list[dict]:
    """Constructor championship standings."""
    endpoint = f"{season}/constructorStandings" if round_num is None else f"{season}/{round_num}/constructorStandings"
    data = _get(endpoint)
    lists = data["MRData"]["StandingsTable"]["StandingsLists"]
    return lists[0]["ConstructorStandings"] if lists else []


def get_driver_season_results(season: int | str, driver_id: str) -> list[dict]:
    """All race results for a specific driver in a season."""
    data = _get(f"{season}/drivers/{driver_id}/results")
    return data["MRData"]["RaceTable"]["Races"]


def get_lap_times(season: int | str, round_num: int | str, driver_id: str | None = None) -> list[dict]:
    """Lap times for a race. Optionally filter by driver."""
    endpoint = f"{season}/{round_num}/laps"
    if driver_id:
        endpoint = f"{season}/{round_num}/drivers/{driver_id}/laps"
    data = _get(endpoint, params={"limit": 2000})
    races = data["MRData"]["RaceTable"]["Races"]
    return races[0]["Laps"] if races else []


def get_pit_stops(season: int | str, round_num: int | str) -> list[dict]:
    """Pit stop data for a race."""
    data = _get(f"{season}/{round_num}/pitstops", params={"limit": 200})
    races = data["MRData"]["RaceTable"]["Races"]
    return races[0]["PitStops"] if races else []


def get_fastest_laps(season: int | str, round_num: int | str) -> list[dict]:
    """Fastest lap per driver in a race."""
    data = _get(f"{season}/{round_num}/fastest/1/results")
    races = data["MRData"]["RaceTable"]["Races"]
    return races[0]["Results"] if races else []
