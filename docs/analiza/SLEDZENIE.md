# Macierz śledzenia

Wymaganie → historyjka → test → PR. Mapa WF-n → test dla stanu wyjściowego jest w kolumnie „Test"
tabel wymagań w [01-procesy](../01-procesy/); tu śledzimy pracę od audytu wzwyż.

| Wymaganie / dług / ryzyko | Historyjka | Test | PR | Status |
|---|---|---|---|---|
| NFR-009 | US-004 | CI: ruff, unittest, bandit, pip-audit, gitleaks, trivy | #14 | zrobione |
| NFR-008, B1–B3, R1, R2 | US-001 | `test_SYS_04_start_bez_klucza`, `test_SYS_05_wymuszona_zmiana_hasla` | — | backlog |
| NFR-007, B4, R3 | US-002 | `test_ADM_01_status_bez_sesji_401` | — | backlog |
| B6, B8, R5, R6, R8 | US-003 | `test_ADM_11_limit_prob`, `test_ADM_12_csrf_import`, `test_REJ_09_csv_injection` | — | backlog |
| T1, T9, T2, NFR-002 | US-005 | `test_PRZ_03_zamkniecie_przez_admina`, `test_ADM_04_brak_uprawnien`, WF-18 | — | backlog |
| T12, NFR-003 | US-006 | `test_KOR_04_rownoczesne_id` | — | backlog |
| A3, R10 | US-007 | n/d (dokument) | — | backlog |
| B5, R4 | US-008 | — | — | decyzja PO |
