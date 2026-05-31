"""
Parsers: raw Jolpica API dicts → clean pandas DataFrames.
Each function is pure (no network calls).
"""

import re
import pandas as pd


def _parse_time(t: str | None) -> float | None:
    """'1:23.456' or '23.456' → total seconds as float."""
    if not t or t in ("N/A", ""):
        return None
    t = t.strip()
    if ":" in t:
        parts = t.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    try:
        return float(t)
    except ValueError:
        return None


def parse_race_results(raw: list[dict], race_name: str = "", season: int = 0, round_num: int = 0) -> pd.DataFrame:
    """
    Raw Results list from get_race_results() → DataFrame.

    Columns: position, driver_id, driver_name, team, grid, laps,
             status, points, time_sec, fastest_lap_rank, fastest_lap_time
    """
    rows = []
    for r in raw:
        driver = r["Driver"]
        constructor = r["Constructor"]
        fl = r.get("FastestLap", {})
        rows.append({
            "season":             season,
            "round":              round_num,
            "race_name":          race_name,
            "position":           int(r.get("position", 0)),
            "driver_id":          driver["driverId"],
            "driver_name":        f"{driver['givenName']} {driver['familyName']}",
            "team":               constructor["name"],
            "nationality":        driver.get("nationality", ""),
            "grid":               int(r.get("grid", 0)),
            "laps":               int(r.get("laps", 0)),
            "status":             r.get("status", ""),
            "points":             float(r.get("points", 0)),
            "time_sec":           _parse_time(r.get("Time", {}).get("time")),
            "fastest_lap_rank":   int(fl.get("rank", 0)) if fl else None,
            "fastest_lap_time":   fl.get("Time", {}).get("time") if fl else None,
            "fastest_lap_speed":  float(fl.get("AverageSpeed", {}).get("speed", 0)) if fl else None,
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["finished"] = df["status"] == "Finished"
        df["dnf"] = ~df["finished"] & (df["position"] > 0)
    return df


def parse_qualifying(raw: list[dict], race_name: str = "", season: int = 0, round_num: int = 0) -> pd.DataFrame:
    """
    Raw QualifyingResults list → DataFrame.

    Columns: position, driver_id, driver_name, team, q1_sec, q2_sec, q3_sec
    """
    rows = []
    for r in raw:
        driver = r["Driver"]
        constructor = r["Constructor"]
        rows.append({
            "season":      season,
            "round":       round_num,
            "race_name":   race_name,
            "position":    int(r.get("position", 0)),
            "driver_id":   driver["driverId"],
            "driver_name": f"{driver['givenName']} {driver['familyName']}",
            "team":        constructor["name"],
            "q1_sec":      _parse_time(r.get("Q1")),
            "q2_sec":      _parse_time(r.get("Q2")),
            "q3_sec":      _parse_time(r.get("Q3")),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        # Best qualifying time = lowest non-null Q session
        df["best_time_sec"] = df[["q1_sec", "q2_sec", "q3_sec"]].min(axis=1)
    return df


def parse_driver_standings(raw: list[dict], season: int = 0, round_num: int = 0) -> pd.DataFrame:
    """Driver championship standings → DataFrame."""
    rows = []
    for r in raw:
        driver = r["Driver"]
        constructors = r.get("Constructors", [{}])
        rows.append({
            "season":      season,
            "round":       round_num,
            "position":    int(r.get("position", 0)),
            "driver_id":   driver["driverId"],
            "driver_name": f"{driver['givenName']} {driver['familyName']}",
            "team":        constructors[0].get("name", "") if constructors else "",
            "points":      float(r.get("points", 0)),
            "wins":        int(r.get("wins", 0)),
        })
    df = pd.DataFrame(rows)
    if not df.empty and len(df) > 1:
        df["gap_to_leader"] = df["points"].max() - df["points"]
    return df


def parse_constructor_standings(raw: list[dict], season: int = 0, round_num: int = 0) -> pd.DataFrame:
    """Constructor championship standings → DataFrame."""
    rows = []
    for r in raw:
        constructor = r["Constructor"]
        rows.append({
            "season":           season,
            "round":            round_num,
            "position":         int(r.get("position", 0)),
            "constructor_id":   constructor["constructorId"],
            "team":             constructor["name"],
            "nationality":      constructor.get("nationality", ""),
            "points":           float(r.get("points", 0)),
            "wins":             int(r.get("wins", 0)),
        })
    df = pd.DataFrame(rows)
    if not df.empty and len(df) > 1:
        df["gap_to_leader"] = df["points"].max() - df["points"]
    return df


def parse_lap_times(raw_laps: list[dict], driver_id: str | None = None) -> pd.DataFrame:
    """
    Lap-by-lap data → tidy DataFrame with one row per driver per lap.
    """
    rows = []
    for lap_block in raw_laps:
        lap_num = int(lap_block["number"])
        for timing in lap_block["Timings"]:
            drv = timing["driverId"]
            if driver_id and drv != driver_id:
                continue
            rows.append({
                "lap":        lap_num,
                "driver_id":  drv,
                "position":   int(timing.get("position", 0)),
                "time_sec":   _parse_time(timing.get("time")),
            })
    return pd.DataFrame(rows)


def parse_pit_stops(raw: list[dict]) -> pd.DataFrame:
    """Pit stop log → DataFrame."""
    rows = []
    for stop in raw:
        rows.append({
            "driver_id":   stop["driverId"],
            "lap":         int(stop["lap"]),
            "stop_number": int(stop["stop"]),
            "time":        stop.get("time", ""),
            "duration_sec": _parse_time(stop.get("duration")),
        })
    return pd.DataFrame(rows)


def parse_driver_season(raw_races: list[dict]) -> pd.DataFrame:
    """All results for a driver across a season → summary DataFrame."""
    rows = []
    for race in raw_races:
        result = race["Results"][0] if race.get("Results") else {}
        constructor = result.get("Constructor", {})
        rows.append({
            "round":      int(race["round"]),
            "race_name":  race["raceName"],
            "circuit":    race["Circuit"]["circuitName"],
            "position":   int(result.get("position", 0)),
            "grid":       int(result.get("grid", 0)),
            "points":     float(result.get("points", 0)),
            "laps":       int(result.get("laps", 0)),
            "status":     result.get("status", ""),
            "team":       constructor.get("name", ""),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["cumulative_points"] = df["points"].cumsum()
        df["finished"] = df["status"] == "Finished"
    return df
