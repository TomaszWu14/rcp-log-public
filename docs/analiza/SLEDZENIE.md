# Macierz śledzenia

Wymaganie → historyjka → test → PR. Mapa WF-n → test dla stanu wyjściowego jest w kolumnie „Test"
tabel wymagań w [01-procesy](../01-procesy/); tu śledzimy pracę od audytu wzwyż.

| Wymaganie / dług / ryzyko | Historyjka | Test | PR | Status |
|---|---|---|---|---|
| NFR-009 | US-004 | CI: ruff, unittest, bandit, pip-audit, gitleaks, trivy | #14 | zrobione |
| NFR-008, B1–B3, R1, R2 | US-001 | `test_SYS_04_start_bez_klucza_sesji_konczy_sie_bledem`, `test_SYS_05_haslo_startowe_wymusza_zmiane`, `test_SYS_06_bez_zmiennej_haslo_startowe_losowe_i_wypisane_raz` | #20 | zrobione |
| NFR-007, B4, R3 | US-002 | `test_ADM_01_status_bez_sesji_401` | #21 | zrobione |
| B6, B8, R5, R6, R8 | US-003 | `test_ADM_11_limit_prob_logowania`, `test_ADM_12_csrf_formularzy_i_importu`, `test_ADM_13_ciasteczko_sesji_samesite_httponly`, `test_REJ_09_kod_z_formula_nie_trafia_do_csv_jako_formula` | #22 | zrobione |
| T1, T2, T9, T14, T15 | US-005 | `test_PRZ_03_zamkniecie_przerwy_przez_administratora_tworzy_nadwyzke`, `test_PRZ_04_nadwyzka_tylko_do_strefy_ze_slownika`, `test_ADM_04_przesuniecie_sprawdza_uprawnienia_i_slownik`, `test_ADM_05_reczny_start_zamyka_poprzedni_pobyt_wpisem`, `test_SES_04_auto_zamkniecie_o_23_59_59_dnia_wejscia`, `test_SES_05_jeden_prog_dlugiego_dyzuru_10h` | #23 | zrobione |
| T12, NFR-003 | US-006 | `test_KOR_04_rownoczesne_id` | — | backlog |
| A3, R10 | US-007 | n/d (dokument `RODO.md`) | #24 | zrobione (do potwierdzenia z IOD) |
| T11, R10, Z29 | US-009 | `test_SYS_07_retencja_plikow`, `test_SYS_08_retencja_kopii` (do napisania) | — | backlog |
| B5, R4 | US-008 | — | — | decyzja PO |
