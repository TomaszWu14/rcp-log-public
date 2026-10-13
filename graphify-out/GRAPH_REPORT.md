# Graph Report - rcp-log-public  (2026-10-13)

## Corpus Check
- 12 files · ~34,598 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 184 nodes · 431 edges · 12 communities (10 shown, 2 thin omitted)
- Extraction: 100% EXTRACTED · 0% INFERRED · 0% AMBIGUOUS · INFERRED: 2 edges (avg confidence: 0.8)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4a4c52de`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- app.py
- Wymagania
- load_workers
- 01-problem-i-zakres.md
- _w
- 06. Dziennik decyzji projektowych
- 05. Wymagania
- RCP Log
- 02. Proces biznesowy
- 07. Ograniczenia, znane problemy i dalsze kroki
- screenshots/README.md
- run.py

## God Nodes (most connected - your core abstractions)
1. `is_admin()` - 33 edges
2. `Wymagania` - 24 edges
3. `load_workers()` - 18 edges
4. `api_rejestruj()` - 15 edges
5. `_r()` - 14 edges
6. `_w()` - 14 edges
7. `load_config()` - 12 edges
8. `init_files()` - 11 edges
9. `bg_check()` - 10 edges
10. `api_scan()` - 10 edges

## Surprising Connections (you probably didn't know these)
- `load_app()` --calls--> `Path`  [INFERRED]
  tests/test_wymagania.py →   _Bridges community 2 → community 1_
- `adm_del_worker()` --calls--> `_r()`  [EXTRACTED]
  app.py → app.py  _Bridges community 2 → community 4_
- `load_admins()` --calls--> `_r()`  [EXTRACTED]
  app.py → app.py  _Bridges community 2 → community 0_
- `save_grafik()` --calls--> `_w()`  [EXTRACTED]
  app.py → app.py  _Bridges community 4 → community 0_

## Import Cycles
- None detected.

## Communities (12 total, 2 thin omitted)

### Community 0 - "app.py"
Cohesion: 0.13
Nodes (44): adm_add_admin(), adm_add_pod(), adm_add_strefa(), adm_add_worker(), adm_alerty(), adm_del_admin(), adm_del_pod(), adm_del_strefa() (+36 more)

### Community 1 - "Wymagania"
Cohesion: 0.11
Nodes (4): load_app(), Testy akceptacyjne — nazwa testu = ID wymagania z docs/05-wymagania.md.…, Gdy ktoś to naprawi, test przestanie przechodzić — wtedy usuń P13 z docs., Wymagania

### Community 2 - "load_workers"
Cohesion: 0.21
Nodes (26): adm_dashboard(), adm_grafik_porownanie(), adm_move(), adm_start(), api_rejestruj(), api_scan(), api_status(), append_alert() (+18 more)

### Community 3 - "01-problem-i-zakres.md"
Cohesion: 0.12
Nodes (17): 01. Problem i zakres, Cel, Interesariusze, Poza zakresem, Problem, W zakresie, 03. User flow — mapa ekranów i przejść, Ekrany (+9 more)

### Community 4 - "_w"
Cohesion: 0.24
Nodes (13): adm_del_worker(), adm_korekta_decyzja(), api_korekta(), ensure_alerts(), init_files(), load_korekty(), save_admins(), save_config() (+5 more)

### Community 5 - "06. Dziennik decyzji projektowych"
Cohesion: 0.20
Nodes (10): 06. Dziennik decyzji projektowych, D1. Pliki JSON i CSV zamiast bazy danych, D2. Jeden skan = przejście, a nie para wejście/wyjście, D3. Sesja zamykana o 23:59:59 dnia rozpoczęcia, D4. Przerwa jako strefa, D5. Nadwyżka przerwy do ręcznego rozliczenia, D6. Korekta jako zgłoszenie z decyzją człowieka, D7. Ostrzeżenie zamiast blokady przy szybkiej zmianie strefy (+2 more)

### Community 6 - "05. Wymagania"
Cohesion: 0.22
Nodes (9): 05. Wymagania, Eksport, kopie i bezpieczeństwo, Grafik, Korekty, Panel administratora, Przerwy, Rejestracja (skaner), Sesje i ewidencja (+1 more)

### Community 7 - "RCP Log"
Cohesion: 0.22
Nodes (9): Dokumentacja analityczna, Jak uruchomić, Kontekst projektu, Licencja, Problem → rozwiązanie, RCP Log, Stack i dlaczego taki, Struktura repozytorium (+1 more)

### Community 8 - "02. Proces biznesowy"
Cohesion: 0.25
Nodes (8): 02. Proces biznesowy, Aktorzy, Proces administratora, Proces PO — rejestracja w RCP Log, Proces PRZED — ewidencja w Excelu, Punkty decyzyjne, Wejścia i wyjścia, Zadania systemu w tle (co 60 sekund)

### Community 9 - "07. Ograniczenia, znane problemy i dalsze kroki"
Cohesion: 0.29
Nodes (7): 07. Ograniczenia, znane problemy i dalsze kroki, Co dalej, Miejsca bez obsługi błędów i walidacji, Poza zakresem, Znane problemy — bezpieczeństwo, Znane problemy — interfejs, Znane problemy — proces i dane

## Knowledge Gaps
- **52 isolated node(s):** `Problem → rozwiązanie`, `Dokumentacja analityczna`, `Jak uruchomić`, `Struktura repozytorium`, `Stack i dlaczego taki` (+47 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `06. Dziennik decyzji projektowych` connect `06. Dziennik decyzji projektowych` to `01-problem-i-zakres.md`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `RCP Log` connect `RCP Log` to `01-problem-i-zakres.md`?**
  _High betweenness centrality (0.030) - this node is a cross-community bridge._
- **What connects `Problem → rozwiązanie`, `Dokumentacja analityczna`, `Jak uruchomić` to the rest of the system?**
  _52 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `app.py` be split into smaller, more focused modules?**
  _Cohesion score 0.12525252525252525 - nodes in this community are weakly interconnected._
- **Should `Wymagania` be split into smaller, more focused modules?**
  _Cohesion score 0.10846560846560846 - nodes in this community are weakly interconnected._
- **Should `01-problem-i-zakres.md` be split into smaller, more focused modules?**
  _Cohesion score 0.12 - nodes in this community are weakly interconnected._