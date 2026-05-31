"""
Analytics: pandas pipelines for cross-race and driver comparison stats.
All functions accept DataFrames produced by parsers/results.py
"""

import pandas as pd
import numpy as np


def season_driver_summary(race_results: list[pd.DataFrame]) -> pd.DataFrame:
    """
    Combine race results from multiple rounds into a season summary per driver.

    Input:  list of DataFrames from parse_race_results()
    Output: one row per driver with aggregated stats
    """
    if not race_results:
        return pd.DataFrame()

    df = pd.concat(race_results, ignore_index=True)

    grp = df.groupby(["driver_id", "driver_name", "team"])

    summary = grp.agg(
        races=("round", "count"),
        points=("points", "sum"),
        wins=("position", lambda x: (x == 1).sum()),
        podiums=("position", lambda x: (x <= 3).sum()),
        poles=("grid", lambda x: (x == 1).sum()),
        dnfs=("dnf", "sum"),
        avg_finish=("position", "mean"),
        avg_grid=("grid", "mean"),
        best_finish=("position", "min"),
        fastest_laps=("fastest_lap_rank", lambda x: (x == 1).sum()),
    ).reset_index()

    summary["points_per_race"] = (summary["points"] / summary["races"]).round(2)
    summary["positions_gained_avg"] = (summary["avg_grid"] - summary["avg_finish"]).round(2)
    summary = summary.sort_values("points", ascending=False).reset_index(drop=True)
    summary.index += 1  # 1-based ranking

    return summary


def driver_comparison(df_a: pd.DataFrame, name_a: str,
                      df_b: pd.DataFrame, name_b: str) -> pd.DataFrame:
    """
    Head-to-head stat comparison for two drivers across a season.

    Input:  DataFrames from parse_driver_season()
    Output: comparison table (metric | driver_a | driver_b)
    """
    def stats(df):
        return {
            "Races":            len(df),
            "Points":           df["points"].sum(),
            "Wins":             (df["position"] == 1).sum(),
            "Podiums":          (df["position"] <= 3).sum(),
            "Poles":            (df["grid"] == 1).sum(),
            "DNFs":             (~df["finished"]).sum(),
            "Avg finish pos":   round(df["position"].mean(), 2),
            "Avg grid pos":     round(df["grid"].mean(), 2),
            "Best finish":      df["position"].min(),
        }

    sa, sb = stats(df_a), stats(df_b)
    rows = []
    for metric in sa:
        va, vb = sa[metric], sb[metric]
        # Determine winner (lower is better for positions)
        lower_is_better = "pos" in metric.lower() or metric in ("DNFs",)
        if lower_is_better:
            winner = name_a if va < vb else (name_b if vb < va else "—")
        else:
            winner = name_a if va > vb else (name_b if vb > va else "—")
        rows.append({"Metric": metric, name_a: va, name_b: vb, "Better": winner})

    return pd.DataFrame(rows)


def points_progression(race_results: list[pd.DataFrame], driver_ids: list[str]) -> pd.DataFrame:
    """
    Points progression across rounds for selected drivers.

    Returns: DataFrame with columns [round, race_name, driver_id, cumulative_points]
    """
    if not race_results:
        return pd.DataFrame()

    df = pd.concat(race_results, ignore_index=True)
    df = df[df["driver_id"].isin(driver_ids)].copy()
    df = df.sort_values(["driver_id", "round"])
    df["cumulative_points"] = df.groupby("driver_id")["points"].cumsum()
    return df[["round", "race_name", "driver_id", "driver_name", "points", "cumulative_points"]]


def qualifying_vs_race(qual_df: pd.DataFrame, race_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compare qualifying position vs race finish for each driver.

    Returns: DataFrame with positions_gained column (positive = improved)
    """
    merged = pd.merge(
        qual_df[["driver_id", "driver_name", "position", "best_time_sec"]].rename(
            columns={"position": "qual_pos", "best_time_sec": "qual_time_sec"}
        ),
        race_df[["driver_id", "position", "points", "status"]].rename(
            columns={"position": "race_pos"}
        ),
        on="driver_id",
        how="inner"
    )
    merged["positions_gained"] = merged["qual_pos"] - merged["race_pos"]
    return merged.sort_values("race_pos").reset_index(drop=True)


def lap_time_stats(lap_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per-driver lap time statistics from parse_lap_times().
    """
    if lap_df.empty:
        return pd.DataFrame()

    stats = lap_df.groupby("driver_id")["time_sec"].agg(
        laps="count",
        fastest=("min"),
        average=("mean"),
        std_dev=("std"),
        median=("median"),
    ).reset_index()
    stats["average"] = stats["average"].round(3)
    stats["std_dev"] = stats["std_dev"].round(3)
    stats["fastest"] = stats["fastest"].round(3)
    stats = stats.sort_values("fastest").reset_index(drop=True)
    return stats


def pit_stop_analysis(pit_df: pd.DataFrame) -> pd.DataFrame:
    """
    Pit stop strategy summary per driver.
    """
    if pit_df.empty:
        return pd.DataFrame()

    summary = pit_df.groupby("driver_id").agg(
        total_stops=("stop_number", "max"),
        total_pit_time=("duration_sec", "sum"),
        avg_stop_duration=("duration_sec", "mean"),
        fastest_stop=("duration_sec", "min"),
    ).reset_index()
    summary["total_pit_time"] = summary["total_pit_time"].round(3)
    summary["avg_stop_duration"] = summary["avg_stop_duration"].round(3)
    return summary.sort_values("total_pit_time").reset_index(drop=True)
