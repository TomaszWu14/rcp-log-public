# Runbook

Środowisko, zmienne i tryb demo: [04-integracje — Środowisko uruchomieniowe](../04-integracje.md#środowisko-uruchomieniowe).
Instancja produkcyjna jeszcze nie istnieje (weto SEC do czasu R1–R3; plan: Z16).

## Uruchomienie

- Lokalnie: `python run.py` → Waitress na `0.0.0.0:$PORT` (5050). Przy starcie powstaje `data/` z danymi przykładowymi.
- Docker: `docker compose up --build` (`RCP_DEMO=1` w compose). Produkcyjnie: `RCP_DEMO=0`, `RCP_SECRET_KEY`
  ustawiony, odkomentowane woluminy `rcp-data`, `rcp-backup`.
- Coolify: zasób z tego repo, Build Pack Docker Compose; domena i `SERVICE_PASSWORD_64_RCPLOG` z panelu.
  Redeploy = nowy kontener; bez woluminów dane giną (w demo to zamierzone).

Zatrzymanie: Ctrl+C / stop kontenera. Trwające pobyty zostają w `aktywne_sesje.json` i są wczytane po restarcie.

## Kopia zapasowa

Automatyczna o 02:00, tylko gdy serwer działa (T11), do `config.json → backup_path` (domyślnie `backup/`);
w demo wyłączona. Ręcznie: skopiuj cały `data/`. Retencja 30 dni (Z7) — do zbudowania; dziś nic nie usuwa kopii.

## Odtworzenie

1. Zatrzymaj serwer / kontener.
2. Skopiuj pliki z kopii do `data/` (wolumin `rcp-data`), usuwając prefiks `YYYYMMDD_HHMM_`.
3. Uruchom. Sprawdź `/admin` → Live.

## Incydenty

| Objaw | Przyczyna | Co zrobić |
|---|---|---|
| Alerty przestały przychodzić | wątek `bg_check` zginął na nieobsłużonym wyjątku (DEV-3) | restart; zgłoś bug z `alerty.csv` |
| Błąd 500 przy wejściu na Live | uszkodzony wpis daty w `aktywne_sesje.json` | przywróć plik z kopii lub usuń wadliwy wpis |
| „Plik jest pusty" przy imporcie grafiku | `.xls` zamiast `.xlsx` albo pusty arkusz | zapisz jako `.xlsx` |
| Demo pokazuje dziwne dane | gość edytował grafik / przesunął pracowników | poczekaj na reset (`RCP_DEMO_RESET_MIN`) lub Redeploy |
| Podejrzenie wycieku hasła admina | — | usuń konto w zakładce Admini z innego konta; po US-001 — rotacja `RCP_SECRET_KEY` |
