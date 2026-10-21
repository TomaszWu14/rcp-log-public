<img src="docs/media/logo.svg" alt="RCP Log logo" width="96" align="right">

# RCP Log

🇵🇱 [Wersja polska](README.md) (full documentation, in Polish)

Warehouse zone time tracking with a single QR scan. It is built for shift workers and for the administrator
who used to track this time by hand in Excel.

![demo](docs/screenshots/demo.gif)

📹 **Video (1:46, no sound, Polish captions):** [docs/media/rcp-log-prezentacja.mp4](docs/media/rcp-log-prezentacja.mp4)

**Live demo, no login:** [rcp.log.twapp.pl](https://rcp.log.twapp.pl). It runs on fictional data and resets every 30 minutes.
The UI is in Polish.

## Problem → solution

A shift has about 60 people working across about 15 zones: picking, receiving, shipping, breaks. The shift
leader typed time spent in each zone into Excel by hand. Nobody knew in real time who was where, and an
overrun break only showed up at payroll.

RCP Log replaces the spreadsheet with a scan. Each scan closes the previous stay and opens a new one.
The administrator sees zone staffing live. A break over the threshold raises an alert and goes on a list to settle.

| Worker scanner | Admin panel: Live | Schedule vs attendance |
|---|---|---|
| ![Scanner](docs/screenshots/skaner-pracownik.png) | ![Live](docs/screenshots/panel-live.png) | ![Schedule](docs/screenshots/panel-grafik.png) |

## Features

- **Scanner screen.** A worker scans their QR badge, picks a zone (and sub-zone) from the zones they are
  allowed in, and confirms. A quick-change warning catches accidental double scans.
- **Live staffing and alerts.** A background check flags overrun breaks, very long stays and unknown codes.
  The admin can move people between zones manually.
- **Break overruns and corrections.** Minutes over the break threshold are assigned to a zone. Workers
  submit corrections to a specific log entry, and the admin approves or rejects them.
- **Schedule.** The app generates an `.xlsx` template, imports the filled schedule and compares it with
  the first scan of the day (on time / late / absent).
- **Audit and retention.** An audit log records admin operations. Retention periods and daily backups are configurable.
- **Export.** CSV with `;` and BOM, so it opens directly in Excel.

## Engineering and process

The repo is run like a three-person team (business analyst, developer, security), with a Product Owner accepting scope and risk:

- analysis docs reconstructed from code: processes P1–P7 as BPMN in Mermaid, business rules, requirements
  with Given/When/Then criteria, data model, user flow, decision log ([`docs/`](docs/00-przeglad.md)),
- threat model (STRIDE), risk register and GDPR notes ([`docs/bezpieczenstwo/`](docs/bezpieczenstwo/THREAT_MODEL.md)),
- C4 architecture, API reference with access roles, ADRs ([`docs/architektura/`](docs/architektura/ARCHITEKTURA.md)),
- 47 acceptance tests named after requirement IDs, with a traceability matrix: requirement → story → test → PR.

CI (GitHub Actions) runs on every PR and blocks the merge if any of these finds a problem: ruff, tests, bandit, Semgrep `p/owasp-top-ten`,
pip-audit, gitleaks and Trivy (repository and Docker image). Actions are pinned to SHAs, and Dependabot
proposes updates weekly. The app sends CSP, `X-Frame-Options`, `Referrer-Policy`, `Permissions-Policy`,
COOP and HSTS headers. Login is rate-limited, forms are CSRF-protected, and the first admin login forces a password change.

## Quick start

Requires Python 3.11 or newer.

```bash
git clone https://github.com/TomaszWu14/rcp-log-public.git
cd rcp-log-public
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
RCP_DEMO=1 .venv/bin/python run.py          # demo mode: fictional data, admin panel without login
```

| URL | What it is |
|---|---|
| http://localhost:5050/ | scanner. Type `HU_KOWALSKI_JAN` and press Enter |
| http://localhost:5050/admin | admin panel |

Outside demo mode, set `RCP_SECRET_KEY` (at least 32 characters). Without it the app refuses to start.
The initial `admin` password comes from `RCP_ADMIN_PASSWORD`, or is generated and printed once to the console.

Docker:

```bash
docker build -t rcp-log .
docker run --rm -p 5050:5050 -e RCP_DEMO=1 rcp-log
```

Tests:

```bash
python -m unittest discover tests
```

## Stack and why

| Element | Why |
|---|---|
| **Python + Flask** | all logic and the API fit in one file (`app.py`). For a prototype, what counts is how fast an idea can be tested against the real process |
| **Waitress** | a production WSGI server that also runs on Windows (`run.py`) |
| **JSON and CSV files instead of a database** | no infrastructure, and the log opens directly in Excel, which was already in use. Trade-offs are in [D1](docs/05-decyzje-i-ograniczenia.md#d1-pliki-json-i-csv-zamiast-bazy-danych) |
| **openpyxl** | the shift schedule arrives as Excel |
| **Plain HTML, CSS and JS** | the scanner runs in any browser at the station, with no frontend build step |

## Scope and limitations

Out of scope: payroll, HR system integration, night shifts across midnight and offline scanning.
This is a prototype. The main security findings are fixed. The remaining open items are listed in
[docs/05](docs/05-decyzje-i-ograniczenia.md#bezpieczeństwo).

## Background

I noticed the problem in my own warehouse job, where zone time was calculated in Excel from the shift leader's
manual entries. On my own initiative I built this prototype to replace that process, and I owned everything
from process analysis and requirements (gathered from the warehouse manager, the shift leader and my own
observation) to screen and data design, implementation and acceptance tests. It took about a month from idea
to working prototype. It has not yet been tested with users on a live shift; that is the next step.

The repository contains no real data and no company name. All data is fictional.

## License

[MIT](LICENSE)
