#!/usr/bin/env python3
"""
F1 Parser — main entry point.

Usage examples:

  # Full season report (current season)
  python main.py season --season 2024

  # Single race report (round 5 of 2024)
  python main.py race --season 2024 --round 5

  # Driver comparison
  python main.py compare --season 2024 --driver1 verstappen --driver2 leclerc

  # Interactive mode (guided)
  python main.py
"""

import sys
from pathlib import Path

# Make sure local imports work regardless of cwd
sys.path.insert(0, str(Path(__file__).parent))

import argparse
import pandas as pd

from collectors.jolpica import (
    get_season_races, get_race_results, get_qualifying_results,
    get_driver_standings, get_constructor_standings,
    get_driver_season_results, get_lap_times, get_pit_stops,
)
from parsers.results import (
    parse_race_results, parse_qualifying,
    parse_driver_standings, parse_constructor_standings,
    parse_driver_season, parse_lap_times, parse_pit_stops,
)
from analytics.stats import (
    season_driver_summary, driver_comparison,
    points_progression, qualifying_vs_race,
    lap_time_stats, pit_stop_analysis,
)
from exporters.excel import export_excel
from exporters.pdf import export_pdf

OUTPUT_DIR = Path(__file__).parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# Report builders
# ─────────────────────────────────────────────────────────────────────────────

def build_race_report(season: int | str, round_num: int, fmt: str = "both") -> dict[str, Path]:
    """Collect, parse, and export a single-race report."""
    print(f"\n🏎  Fetching race {round_num} of {season}...")

    races = get_season_races(season)
    race_meta = next((r for r in races if r["round"] == str(round_num)), {})
    race_name = race_meta.get("raceName", f"Round {round_num}")
    print(f"   Race: {race_name}")

    print("   → Race results...")
    raw_results = get_race_results(season, round_num)
    race_df = parse_race_results(raw_results, race_name, int(season), round_num)

    print("   → Qualifying...")
    raw_qual = get_qualifying_results(season, round_num)
    qual_df = parse_qualifying(raw_qual, race_name, int(season), round_num)

    print("   → Driver standings...")
    ds_df = parse_driver_standings(get_driver_standings(season, round_num), int(season), round_num)

    print("   → Constructor standings...")
    cs_df = parse_constructor_standings(get_constructor_standings(season, round_num), int(season), round_num)

    print("   → Pit stops...")
    raw_pits = get_pit_stops(season, round_num)
    pit_df = parse_pit_stops(raw_pits)

    print("   → Qual vs race comparison...")
    qvr_df = qualifying_vs_race(qual_df, race_df) if not qual_df.empty and not race_df.empty else None

    outputs = {}
    safe_name = race_name.replace(" ", "_").replace("/", "-")

    if fmt in ("excel", "both"):
        path = OUTPUT_DIR / f"f1_{season}_r{round_num:02d}_{safe_name}.xlsx"
        print(f"\n📊 Exporting Excel → {path.name}")
        export_excel(
            path,
            race_results=race_df,
            qualifying=qual_df,
            driver_standings=ds_df,
            constructor_standings=cs_df,
            driver_comparison=qvr_df,
            season=int(season),
            race_name=race_name,
        )
        outputs["excel"] = path
        print("   ✓ Done")

    if fmt in ("pdf", "both"):
        path = OUTPUT_DIR / f"f1_{season}_r{round_num:02d}_{safe_name}.pdf"
        print(f"📄 Exporting PDF   → {path.name}")
        export_pdf(
            path,
            race_results=race_df,
            qualifying=qual_df,
            driver_standings=ds_df,
            constructor_standings=cs_df,
            season=int(season),
            race_name=race_name,
            round_num=round_num,
        )
        outputs["pdf"] = path
        print("   ✓ Done")

    return outputs


def build_season_report(season: int | str, fmt: str = "both") -> dict[str, Path]:
    """Collect all races in a season and produce aggregate analytics."""
    print(f"\n🏆 Fetching full season {season}...")

    races = get_season_races(season)
    n = len(races)
    print(f"   {n} rounds found")

    all_race_dfs = []
    for i, race in enumerate(races, 1):
        rn = int(race["round"])
        name = race["raceName"]
        print(f"   [{i}/{n}] {name}...", end=" ", flush=True)
        try:
            raw = get_race_results(season, rn)
            df = parse_race_results(raw, name, int(season), rn)
            if not df.empty:
                all_race_dfs.append(df)
            print("✓")
        except Exception as e:
            print(f"✗ ({e})")

    print("\n   → Final standings...")
    ds_df = parse_driver_standings(get_driver_standings(season), int(season))
    cs_df = parse_constructor_standings(get_constructor_standings(season), int(season))

    print("   → Season summary...")
    summary_df = season_driver_summary(all_race_dfs) if all_race_dfs else pd.DataFrame()

    print("   → Points progression...")
    if ds_df is not None and not ds_df.empty:
        top_drivers = ds_df["driver_id"].head(5).tolist()
        prog_df = points_progression(all_race_dfs, top_drivers)
    else:
        prog_df = pd.DataFrame()

    outputs = {}
    if fmt in ("excel", "both"):
        path = OUTPUT_DIR / f"f1_{season}_season.xlsx"
        print(f"\n📊 Exporting Excel → {path.name}")
        export_excel(
            path,
            driver_standings=ds_df,
            constructor_standings=cs_df,
            season_summary=summary_df,
            points_progression=prog_df,
            season=int(season),
        )
        outputs["excel"] = path
        print("   ✓ Done")

    if fmt in ("pdf", "both"):
        path = OUTPUT_DIR / f"f1_{season}_season.pdf"
        print(f"📄 Exporting PDF   → {path.name}")
        export_pdf(
            path,
            driver_standings=ds_df,
            constructor_standings=cs_df,
            season_summary=summary_df,
            season=int(season),
            race_name=f"{season} Full Season",
        )
        outputs["pdf"] = path
        print("   ✓ Done")

    return outputs


def build_comparison_report(season: int | str, driver1_id: str, driver2_id: str,
                             fmt: str = "both") -> dict[str, Path]:
    """Head-to-head driver comparison for a full season."""
    print(f"\n⚔️  Comparing {driver1_id} vs {driver2_id} — {season}...")

    print(f"   → {driver1_id} results...")
    df1 = parse_driver_season(get_driver_season_results(season, driver1_id))
    print(f"   → {driver2_id} results...")
    df2 = parse_driver_season(get_driver_season_results(season, driver2_id))

    comp_df = driver_comparison(df1, driver1_id, df2, driver2_id)

    outputs = {}
    if fmt in ("excel", "both"):
        path = OUTPUT_DIR / f"f1_{season}_{driver1_id}_vs_{driver2_id}.xlsx"
        print(f"\n📊 Exporting Excel → {path.name}")
        export_excel(path, driver_comparison=comp_df, season=int(season))
        outputs["excel"] = path
        print("   ✓ Done")

    if fmt in ("pdf", "both"):
        path = OUTPUT_DIR / f"f1_{season}_{driver1_id}_vs_{driver2_id}.pdf"
        print(f"📄 Exporting PDF   → {path.name}")
        export_pdf(path, driver_comparison=comp_df, season=int(season),
                   race_name=f"{driver1_id} vs {driver2_id}")
        outputs["pdf"] = path
        print("   ✓ Done")

    return outputs


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def interactive():
    print("\n╔══════════════════════════════╗")
    print("║   F1 Analytics Parser 1.0    ║")
    print("╚══════════════════════════════╝\n")
    print("What would you like to do?")
    print("  1. Single race report")
    print("  2. Full season report")
    print("  3. Driver head-to-head comparison")
    print()
    choice = input("Choice [1/2/3]: ").strip()

    fmt_input = input("Export format [excel/pdf/both] (default: both): ").strip() or "both"

    if choice == "1":
        season = input("Season [e.g. 2024]: ").strip() or "2024"
        round_num = int(input("Round number: ").strip())
        build_race_report(season, round_num, fmt_input)
    elif choice == "2":
        season = input("Season [e.g. 2024]: ").strip() or "2024"
        build_season_report(season, fmt_input)
    elif choice == "3":
        season = input("Season [e.g. 2024]: ").strip() or "2024"
        d1 = input("Driver 1 ID (e.g. verstappen): ").strip()
        d2 = input("Driver 2 ID (e.g. leclerc): ").strip()
        build_comparison_report(season, d1, d2, fmt_input)
    else:
        print("Unknown choice.")
        sys.exit(1)

    print(f"\n✅ All outputs saved to: {OUTPUT_DIR.resolve()}")


def cli():
    parser = argparse.ArgumentParser(description="F1 Data Parser & Analytics")
    sub = parser.add_subparsers(dest="cmd")

    r = sub.add_parser("race", help="Single race report")
    r.add_argument("--season", default="current")
    r.add_argument("--round", type=int, required=True, dest="round_num")
    r.add_argument("--fmt", default="both", choices=["excel", "pdf", "both"])

    s = sub.add_parser("season", help="Full season report")
    s.add_argument("--season", default="current")
    s.add_argument("--fmt", default="both", choices=["excel", "pdf", "both"])

    c = sub.add_parser("compare", help="Driver comparison")
    c.add_argument("--season", default="current")
    c.add_argument("--driver1", required=True)
    c.add_argument("--driver2", required=True)
    c.add_argument("--fmt", default="both", choices=["excel", "pdf", "both"])

    args = parser.parse_args()

    if args.cmd == "race":
        outputs = build_race_report(args.season, args.round_num, args.fmt)
    elif args.cmd == "season":
        outputs = build_season_report(args.season, args.fmt)
    elif args.cmd == "compare":
        outputs = build_comparison_report(args.season, args.driver1, args.driver2, args.fmt)
    else:
        interactive()
        return

    print(f"\n✅ Output files:")
    for k, v in outputs.items():
        print(f"   {k}: {v.resolve()}")


if __name__ == "__main__":
    cli()
