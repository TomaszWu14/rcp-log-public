# Klasyfikacja danych

| Klasa | Dane | Gdzie | Kto ma dostęp dziś | Kto powinien |
|---|---|---|---|---|
| **Dane osobowe** (instancja produkcyjna, Z16) | imię i nazwisko, kod pracownika, czas i miejsce pracy, przerwy, spóźnienia, grafik | `pracownicy.json`, `aktywne_sesje.json`, `ewidencja_*.csv`, `alerty.csv`, `nadwyzki_przerw.json`, `korekty.json`, `grafik.json`, kopie w `backup/` | administrator; **obecność także bez logowania** (`/api/status`, B4) | tylko administrator |
| **Poufne** | hashe haseł administratorów, klucz sesji `RCP_SECRET_KEY` | `admins.json`, env (demo: losowany przez Coolify); wartość domyślna w `app.py:16` | każdy z dostępem do repo zna klucz domyślny (B1) | tylko serwer, z env, bez wartości domyślnej |
| **Wewnętrzne** | słownik stref i podstref, progi, ścieżka kopii | `strefy.json`, `config.json` | administrator; strefy pracownika widoczne na skanerze | bez zmian |
| **Publiczne** | kod, dokumentacja, dane przykładowe przy starcie, **dane fikcyjne instancji demo** (`demo_data.py`, `data_demo/`) | repo, [rcp.log.twapp.pl](https://rcp.log.twapp.pl) | wszyscy — w demo każdy jest administratorem (D11) | bez zmian, dopóki demo nie zawiera danych rzeczywistych |

Uwagi:
- Ewidencja miejsca i czasu pracy może być uznana za **monitoring pracownika** (art. 22³ Kodeksu pracy) —
  wymaga poinformowania pracowników i uzasadnienia celu; `RODO.md` (US-007) przed instancją produkcyjną.
- Nazwy stref domyślnych są przykładowe (Z15); lista do anonimizacji w [00-przeglad](../00-przeglad.md#do-anonimizacji).
- Opis korekty to wolny tekst od pracownika — może zawierać dane o innych osobach.
- Nieznany kod ze skanu trafia do `alerty.csv` bez logowania — pole kontrolowane przez osobę przy skanerze (B8).
