# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/), wersjonowanie [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

### Added
- Proces zespołu BA / DEV / SEC: `CONTRIBUTING.md`, `SECURITY.md`, szablony issue i PR, CODEOWNERS.
- CI (GitHub Actions): ruff, testy, bandit, pip-audit, gitleaks, build obrazu + trivy; Dependabot; pre-commit.
- Dokumenty: `docs/AUDYT.md`, `docs/analiza/` (wizja z miernikami, NFR v0.1, backlog US-001…008, śledzenie,
  założenia Z17–Z25), `docs/bezpieczenstwo/` (klasyfikacja danych, threat model STRIDE, rejestr ryzyk R1–R10),
  `docs/architektura/` (C4 kontenery, ADR 0012), `docs/testy/`, `docs/operacje/`.

### Changed
- Zależności przypięte do dokładnych wersji (`requirements.txt`); narzędzia deweloperskie w `requirements-dev.txt`.
- `demo_data.py`: usunięty nieużywany import i zmienna (lint).

## [0.2.0] — 2026-10-14

- Tryb demo (`RCP_DEMO=1`) z fikcyjnymi danymi, Dockerfile i compose, publiczna instancja na Coolify (PR #10, #12).
- Dokumentacja przedwdrożeniowa `docs/00–05`: procesy P1–P7, BR-1–58, WF-1–37, ustalenia Z1–Z16 (PR #13);
  logo i film (PR #11).

## [0.1.0] — 2026-10-13

Prototyp z pierwszą dokumentacją analityczną (dziś `docs/archiwum/`) i 18 testami akceptacyjnymi (PR #9).
