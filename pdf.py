"""
PDF exporter using ReportLab.
Generates a clean analytical report with tables, summary cards, and auto-pagination.
"""

from pathlib import Path
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, HRFlowable, KeepTogether
)
from reportlab.platypus.flowables import HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

# ── Brand colours ─────────────────────────────────────────────────────────────
F1_RED    = colors.HexColor("#C8102E")
F1_DARK   = colors.HexColor("#1A1A2E")
F1_SILVER = colors.HexColor("#C0C0C0")
F1_GOLD   = colors.HexColor("#FFD700")
F1_BRONZE = colors.HexColor("#CD7F32")
LIGHT_GRAY= colors.HexColor("#F8F9FA")
MID_GRAY  = colors.HexColor("#6C757D")
BORDER    = colors.HexColor("#DEE2E6")
WHITE     = colors.white

PAGE_W, PAGE_H = A4
MARGIN = 1.8 * cm


def _styles():
    base = getSampleStyleSheet()
    custom = {
        "Title": ParagraphStyle("Title", fontSize=22, textColor=F1_DARK,
                                 fontName="Helvetica-Bold", spaceAfter=4,
                                 alignment=TA_LEFT),
        "Subtitle": ParagraphStyle("Subtitle", fontSize=12, textColor=MID_GRAY,
                                    fontName="Helvetica", spaceAfter=16),
        "SectionH": ParagraphStyle("SectionH", fontSize=13, textColor=F1_DARK,
                                    fontName="Helvetica-Bold", spaceBefore=14, spaceAfter=6),
        "Normal": ParagraphStyle("Normal", fontSize=9, fontName="Helvetica",
                                  textColor=F1_DARK, spaceAfter=4),
        "Cell": ParagraphStyle("Cell", fontSize=8, fontName="Helvetica",
                                textColor=F1_DARK),
        "CellBold": ParagraphStyle("CellBold", fontSize=8, fontName="Helvetica-Bold",
                                    textColor=F1_DARK),
        "Footer": ParagraphStyle("Footer", fontSize=7, textColor=MID_GRAY,
                                  fontName="Helvetica", alignment=TA_CENTER),
    }
    return {**{k: base[k] for k in base.byName}, **custom}


S = _styles()


def _header_footer(canvas, doc):
    canvas.saveState()
    # Top red bar
    canvas.setFillColor(F1_RED)
    canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, fill=1, stroke=0)
    canvas.setFillColor(WHITE)
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawString(MARGIN, PAGE_H - 5.5 * mm, "F1 Analytics Report")
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 5.5 * mm, f"Page {doc.page}")
    # Bottom line
    canvas.setStrokeColor(BORDER)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 1.2 * cm, PAGE_W - MARGIN, 1.2 * cm)
    canvas.setFillColor(MID_GRAY)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(PAGE_W / 2, 0.7 * cm, "Data sourced from Jolpica/Ergast F1 API")
    canvas.restoreState()


def _make_table(df: pd.DataFrame, col_widths: list[float] | None = None,
                highlight_positions: bool = False) -> Table:
    """Convert DataFrame to a styled ReportLab Table."""
    headers = [Paragraph(str(c).replace("_", " ").title(), S["CellBold"]) for c in df.columns]
    body = []
    for _, row in df.iterrows():
        body.append([Paragraph(str(v) if v is not None else "—", S["Cell"]) for v in row])

    data = [headers] + body

    usable_w = PAGE_W - 2 * MARGIN
    if col_widths is None:
        col_widths = [usable_w / len(df.columns)] * len(df.columns)

    tbl = Table(data, colWidths=col_widths, repeatRows=1)

    style = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), F1_DARK),
        ("TEXTCOLOR",  (0, 0), (-1, 0), WHITE),
        ("FONTNAME",   (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",   (0, 0), (-1, 0), 8),
        ("ALIGN",      (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("TOPPADDING",    (0, 0), (-1, 0), 6),
        # Grid
        ("GRID",       (0, 0), (-1, -1), 0.4, BORDER),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        ("ALIGN",      (0, 1), (-1, -1), "CENTER"),
        ("FONTSIZE",   (0, 1), (-1, -1), 8),
        ("TOPPADDING",    (0, 1), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 4),
    ]

    if highlight_positions and "position" in df.columns:
        pos_col = list(df.columns).index("position")
        for row_idx, pos in enumerate(df["position"], 1):
            if pos == 1:
                colour = F1_GOLD
            elif pos == 2:
                colour = F1_SILVER
            elif pos == 3:
                colour = F1_BRONZE
            else:
                continue
            style.append(("BACKGROUND", (0, row_idx), (-1, row_idx), colour))

    tbl.setStyle(TableStyle(style))
    return tbl


def _stat_cards(stats: dict[str, str]) -> Table:
    """Render a row of stat cards (label + value)."""
    pairs = list(stats.items())
    # 4 per row max
    rows = [pairs[i:i+4] for i in range(0, len(pairs), 4)]
    all_tables = []
    usable_w = PAGE_W - 2 * MARGIN
    for row in rows:
        cell_w = usable_w / 4
        data = [
            [Paragraph(str(v), ParagraphStyle("CV", fontSize=16, fontName="Helvetica-Bold",
                                               textColor=F1_RED, alignment=TA_CENTER)) for _, v in row],
            [Paragraph(str(k), ParagraphStyle("CL", fontSize=8, fontName="Helvetica",
                                               textColor=MID_GRAY, alignment=TA_CENTER)) for k, _ in row],
        ]
        # Pad to 4 cols
        while len(data[0]) < 4:
            data[0].append(Paragraph("", S["Cell"]))
            data[1].append(Paragraph("", S["Cell"]))

        tbl = Table(data, colWidths=[cell_w] * 4)
        tbl.setStyle(TableStyle([
            ("BOX",        (0, 0), (-1, -1), 0.5, BORDER),
            ("INNERGRID",  (0, 0), (-1, -1), 0.5, BORDER),
            ("BACKGROUND", (0, 0), (-1, -1), LIGHT_GRAY),
            ("TOPPADDING",    (0, 0), (-1, -1), 8),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ]))
        all_tables.append(tbl)
    return all_tables


def export_pdf(
    output_path: str | Path,
    race_results: pd.DataFrame | None = None,
    qualifying: pd.DataFrame | None = None,
    driver_standings: pd.DataFrame | None = None,
    constructor_standings: pd.DataFrame | None = None,
    season_summary: pd.DataFrame | None = None,
    driver_comparison: pd.DataFrame | None = None,
    season: int = 0,
    race_name: str = "",
    round_num: int = 0,
) -> Path:
    output_path = Path(output_path)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN + 1.2 * cm,
        bottomMargin=MARGIN + 0.6 * cm,
    )

    story = []

    # ── Cover header ─────────────────────────────────────────────────────────
    story.append(Paragraph(f"Formula 1 — {season} Season", S["Title"]))
    subtitle = race_name or "Season Analytics"
    if round_num:
        subtitle = f"Round {round_num}: {subtitle}"
    story.append(Paragraph(subtitle, S["Subtitle"]))
    story.append(HRFlowable(width="100%", thickness=2, color=F1_RED, spaceAfter=12))

    # ── Quick stats cards (from race results) ─────────────────────────────────
    if race_results is not None and not race_results.empty:
        winner = race_results[race_results["position"] == 1]
        if not winner.empty:
            w = winner.iloc[0]
            cards = {
                "Winner":    w.get("driver_name", "—"),
                "Team":      w.get("team", "—"),
                "Laps":      str(int(w.get("laps", 0))),
                "Fastest Lap": race_results[race_results.get("fastest_lap_rank", pd.Series()) == 1]["driver_name"].values[0]
                               if "fastest_lap_rank" in race_results.columns and (race_results["fastest_lap_rank"] == 1).any()
                               else "—",
            }
            for tbl in _stat_cards(cards):
                story.append(tbl)
            story.append(Spacer(1, 0.4 * cm))

    # ── Race Results table ────────────────────────────────────────────────────
    if race_results is not None and not race_results.empty:
        story.append(Paragraph("Race Results", S["SectionH"]))
        cols = [c for c in ["position", "driver_name", "team", "grid",
                             "laps", "points", "status"] if c in race_results.columns]
        df = race_results[cols].head(20)
        widths = [1.2*cm, 4.5*cm, 4.0*cm, 1.5*cm, 1.3*cm, 1.5*cm, 3.0*cm]
        widths = widths[:len(cols)]
        story.append(_make_table(df, widths, highlight_positions=True))
        story.append(Spacer(1, 0.4 * cm))

    # ── Qualifying ────────────────────────────────────────────────────────────
    if qualifying is not None and not qualifying.empty:
        story.append(Paragraph("Qualifying", S["SectionH"]))
        cols = [c for c in ["position", "driver_name", "team",
                             "q1_sec", "q2_sec", "q3_sec"] if c in qualifying.columns]
        df = qualifying[cols].head(20)
        story.append(_make_table(df, highlight_positions=True))
        story.append(Spacer(1, 0.4 * cm))

    # ── Driver Standings ──────────────────────────────────────────────────────
    if driver_standings is not None and not driver_standings.empty:
        story.append(PageBreak())
        story.append(Paragraph("Driver Championship Standings", S["SectionH"]))
        cols = [c for c in ["position", "driver_name", "team", "points",
                             "wins", "gap_to_leader"] if c in driver_standings.columns]
        df = driver_standings[cols]
        widths = [1.5*cm, 4.5*cm, 4.0*cm, 2.0*cm, 1.5*cm, 3.0*cm]
        widths = widths[:len(cols)]
        story.append(_make_table(df, widths, highlight_positions=True))
        story.append(Spacer(1, 0.4 * cm))

    # ── Constructor Standings ─────────────────────────────────────────────────
    if constructor_standings is not None and not constructor_standings.empty:
        story.append(Paragraph("Constructor Championship Standings", S["SectionH"]))
        cols = [c for c in ["position", "team", "points", "wins",
                             "gap_to_leader"] if c in constructor_standings.columns]
        story.append(_make_table(constructor_standings[cols], highlight_positions=True))
        story.append(Spacer(1, 0.4 * cm))

    # ── Season Summary ────────────────────────────────────────────────────────
    if season_summary is not None and not season_summary.empty:
        story.append(PageBreak())
        story.append(Paragraph("Season Driver Summary", S["SectionH"]))
        keep_cols = [c for c in ["driver_name", "team", "races", "points", "wins",
                                  "podiums", "poles", "dnfs", "avg_finish",
                                  "points_per_race"] if c in season_summary.columns]
        story.append(_make_table(season_summary[keep_cols]))
        story.append(Spacer(1, 0.4 * cm))

    # ── Driver Comparison ─────────────────────────────────────────────────────
    if driver_comparison is not None and not driver_comparison.empty:
        story.append(Paragraph("Head-to-Head Comparison", S["SectionH"]))
        story.append(_make_table(driver_comparison))

    doc.build(story, onFirstPage=_header_footer, onLaterPages=_header_footer)
    return output_path
