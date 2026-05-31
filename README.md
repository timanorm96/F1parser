# 🏎 F1 Parser

> Collect, analyze, and export Formula 1 data — race results, championship standings, driver stats — with one command.

Built on the [Jolpica F1 API](https://jolpica-f1.netlify.app/) (the actively maintained successor to Ergast). No API key required. No Selenium. Pure `requests` + `pandas`.

---

## Features

- **Session data** — race results, qualifying, pit stops, lap times, fastest laps
- **Championship tables** — driver and constructor standings with gap-to-leader
- **Driver analytics** — head-to-head comparison, points progression, qual vs race delta
- **File cache** — responses cached as JSON; historical data never re-fetched
- **One-button export** — styled Excel workbook (openpyxl) or PDF report (ReportLab)

---

## Project structure

```
f1_parser/
├── collectors/
│   └── jolpica.py      # HTTP layer — requests, cache, retry
├── parsers/
│   └── results.py      # Raw API dicts → clean DataFrames
├── analytics/
│   └── stats.py        # pandas pipelines (comparison, trends, summaries)
├── exporters/
│   ├── excel.py        # Multi-sheet styled workbook
│   └── pdf.py          # Paginated PDF report
├── main.py             # CLI entry point
└── .cache/             # Auto-created JSON cache
```

---

## Installation

```bash
git clone https://github.com/your-username/f1-parser.git
cd f1-parser
pip install requests pandas openpyxl reportlab
```

Python 3.11+ recommended.

---

## Usage

### CLI

```bash
# Single race report — Round 5, 2024
python main.py race --season 2024 --round 5

# Full season report
python main.py season --season 2024

# Head-to-head driver comparison
python main.py compare --season 2024 --driver1 verstappen --driver2 norris

# Choose export format: excel | pdf | both (default)
python main.py race --season 2024 --round 1 --fmt pdf
```

### Interactive mode

```bash
python main.py
```

Prompts you to pick a report type, season, and format — no flags needed.

### As a library

```python
from collectors.jolpica import get_race_results, get_driver_standings
from parsers.results import parse_race_results, parse_driver_standings
from exporters.excel import export_excel

raw = get_race_results(2024, 5)
race_df = parse_race_results(raw, race_name="Chinese GP", season=2024, round_num=5)

standings_raw = get_driver_standings(2024)
standings_df = parse_driver_standings(standings_raw, season=2024)

export_excel(
    "report.xlsx",
    race_results=race_df,
    driver_standings=standings_df,
    season=2024,
    race_name="Chinese GP",
)
```

---

## Excel output

Each export produces a multi-sheet workbook:

| Sheet | Contents |
|---|---|
| Race Results | Finishing order, points, status — podium rows highlighted gold/silver/bronze |
| Qualifying | Q1/Q2/Q3 times in seconds |
| Driver Standings | Points, wins, gap to leader + data bar conditional formatting |
| Constructor Standings | Team points and wins |
| Season Summary | Aggregated stats per driver (wins, podiums, poles, DNFs, avg finish) |
| Driver Comparison | Head-to-head metric table |
| Points Progression | Pivoted cumulative points by round + embedded line chart |

---

## PDF output

Single paginated document with:
- Summary stat cards (winner, team, fastest lap)
- Race results and qualifying tables
- Driver and constructor standings
- Head-to-head comparison section
- Auto-pagination with header/footer on every page

---

## How the hidden API trick works

Some F1 sites (formula1.com, motorsport.com) load data via undocumented internal endpoints. To find them:

1. Open the site in Chrome and go to a race result page
2. Press `F12` → **Network** tab → filter by **Fetch/XHR**
3. Look for requests to `api.formula1.com/...` — click one and copy the URL + headers
4. Replicate with `requests.Session()`:

```python
import requests

session = requests.Session()
session.headers.update({
    "apikey": "YOUR_COPIED_KEY",
    "User-Agent": "Mozilla/5.0 ...",
})

resp = session.get("https://api.formula1.com/v1/editorial-race-result?...")
data = resp.json()
```

No Selenium, no JS rendering, no browser automation — just direct JSON calls.

---

## Driver IDs reference

Jolpica uses lowercase slugs for driver IDs:

| Driver | ID |
|---|---|
| Max Verstappen | `verstappen` |
| Lewis Hamilton | `hamilton` |
| Charles Leclerc | `leclerc` |
| Lando Norris | `norris` |
| Carlos Sainz | `sainz` |
| George Russell | `russell` |
| Fernando Alonso | `alonso` |
| Oscar Piastri | `piastri` |

Full list: `https://api.jolpi.ca/ergast/f1/drivers/`

---

## Caching

Responses are stored as JSON files in `.cache/` (keyed by URL + params hash). Default TTL is **72 hours** for historical data. To force a fresh fetch, delete `.cache/` or pass `ttl_hours=0` to `_get()`.

---

## Dependencies

| Package | Purpose |
|---|---|
| `requests` | HTTP calls to Jolpica API |
| `pandas` | Data parsing and analytics pipelines |
| `openpyxl` | Excel export with styling and charts |
| `reportlab` | PDF generation |

---

## Data source

All data comes from the **[Jolpica F1 API](https://jolpica-f1.netlify.app/)** — a free, open, no-auth REST API covering every Formula 1 season from 1950 to present. It is the recommended successor to the now-retired Ergast API and uses the same JSON structure.

---

## License

MIT
