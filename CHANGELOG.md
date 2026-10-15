# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/), wersjonowanie [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

### Security
- US-003: limit prób logowania (5 / 10 min z adresu → 429 na 15 min); token CSRF na formularzach logowania,
  zmiany hasła i imporcie grafiku; ciasteczko sesji `SameSite=Lax`, `HttpOnly`, `Secure` przy `RCP_PROXY=1`;
  pola CSV zaczynające się od `= + - @` lub tabulatora dostają apostrof (B6, B8).
- US-002: `/api/status` (obecność z nazwiskami) wymaga sesji administratora; bez niej 401 z pustym ciałem (B4).
- US-001: poza trybem demo `RCP_SECRET_KEY` jest wymagany (≥ 32 znaki) — brak kończy start błędem; usunięty klucz
  domyślny z kodu (B1). Hasło startowe `admin` z `RCP_ADMIN_PASSWORD` albo losowe wypisane raz w konsoli;
  pierwsze logowanie wymusza zmianę na `/admin/haslo` (B2, B3). `admins.json` trzyma skrót i znacznik zmiany
  (stary format czytany w locie).

### Fixed
- US-005: jedno miejsce zamykania pobytu (`zamknij_pobyt`) — nadwyżka przerwy powstaje także przy zamknięciu przez
  administratora i auto-zamknięciu (T1); wpis automatyczny ma numer i format czasu (T14); jeden próg długiego dyżuru 10 h
  (T2); przesunięcie, ręczny start i przypisanie nadwyżki sprawdzają słownik stref i uprawnienia (T9); usunięty martwy
  filtr `PRZEKROCZENIE_ZMIANY` (T15). Kontrola w tle wydzielona do `kontrola_pobytow()`.
- Odwołania `app.py:linia` w dokumentacji naprawione po podwójnym przeliczeniu w US-003; skrypt blokuje drugi przebieg.

### Added
- `tools/remap_line_refs.py` — przelicza odwołania `app.py:linia` w dokumentacji po zmianie kodu.
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
