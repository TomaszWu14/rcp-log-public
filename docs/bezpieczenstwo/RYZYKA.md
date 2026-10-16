# Rejestr ryzyk

Wpływ i prawdopodobieństwo: 1–3. Decyzja: **naprawić** / **zaakceptować** (z podpisem PO i datą przeglądu) / **przenieść**.
Opis ryzyk: [AUDYT](../AUDYT.md#sec-najważniejsze-ryzyka-top-10); odpowiedniki B1–B9 w [05](../05-decyzje-i-ograniczenia.md#bezpieczeństwo).
Dotyczy planowanej instancji produkcyjnej (Z16); demo przetwarza dane fikcyjne.

| ID | Ryzyko | Wpływ | Prawd. | Decyzja | Właściciel | Historyjka | Przegląd |
|---|---|---|---|---|---|---|---|
| R1 | domyślny klucz sesji w kodzie użyty, gdy brak `RCP_SECRET_KEY` (B1) | 3 | 2 | **naprawione** 2026-10-15 (PR #20) | SEC | US-001 | zamknięte |
| R2 | domyślne hasło admina bez wymuszenia zmiany (B2, B3) | 3 | 3 | **naprawione** 2026-10-15 (PR #20) | SEC | US-001 | zamknięte |
| R11 | hasło startowe bez `RCP_ADMIN_PASSWORD` trafia raz do logu serwera — kto czyta log, może zalogować się przed administratorem | 2 | 1 | zaakceptować: hasło jednorazowe, log = ten sam krąg zaufania co `admins.json`; produkcyjnie podawać `RCP_ADMIN_PASSWORD` | SEC | US-001 | 2026-11-15 |
| R3 | obecność z nazwiskami bez logowania (B4) | 3 | 2 | **naprawione** 2026-10-15 (US-002) | SEC | US-002 | zamknięte |
| R4 | przewidywalne, nieunieważnialne kody QR; duplikat z tym samym kodem (B5, Z3) | 2 | 2 | **decyzja PO** | PO | US-008 | 2026-11-15 |
| R5 | brak limitu prób logowania (B6) | 2 | 2 | **naprawione** 2026-10-15 (US-003) | SEC | US-003 | zamknięte |
| R6 | CSRF formularzy, cookie bez SameSite/Secure (B6) | 2 | 1 | **naprawione** 2026-10-15 (US-003); JSON API bez tokenu — chroni `SameSite=Lax` i wymóg `Content-Type: application/json` (Z27) | SEC | US-003 | 2026-11-15 |
| R7 | config bez walidacji, dowolny `backup_path` (B7) | 2 | 1 | **naprawione** 2026-10-15 (US-011) | DEV | US-011 | zamknięte |
| R8 | CSV injection przez nieznany kod (B8) | 2 | 1 | **naprawione** 2026-10-15 (US-003) | DEV | US-003 | zamknięte |
| R9 | brak limitu żądania, nagłówków; nasłuch na `0.0.0.0`; demo bez limitu żądań | 2 | 1 | **naprawione** 2026-10-15 (US-011): limit 2 MB, nagłówki, HSTS za proxy; `0.0.0.0` i demo — wyjątki poniżej | DEV | US-011 | zamknięte |
| R10 | brak retencji (poza kopiami, Z7) i ~~audytu operacji~~ | 2 | 1 | audyt: **naprawione** 2026-10-16 (US-012, `audyt.csv`); retencja opisana w [RODO.md](RODO.md), mechanizm — US-009 | BA+SEC | US-009 | 2026-11-15 |
| R12 | limit prób logowania w pamięci jednego procesu, per adres (szczegóły w wyjątkach) | 1 | 2 | zaakceptować (Z27) | SEC | US-003 | 2026-11-15 |
| R13 | CSP z `'unsafe-inline'` dla skryptów i stylów — szablony mają cały JS i CSS inline (brak builda frontendu, D1); XSS w szablonie nie jest blokowany przez CSP | 2 | 1 | zaakceptować do czasu wydzielenia JS do plików statycznych | SEC | US-011 | 2026-11-15 |

## Wyjątki (ryzyka świadomie zaakceptowane)

| ID | Uzasadnienie | Zaakceptował | Data | Przegląd |
|---|---|---|---|---|
| R9 (część: demo bez limitu żądań) | instancja demo zawiera tylko dane fikcyjne odtwarzane co 30 min; skutkiem nadużycia jest co najwyżej niedostępność demo | PO (Z17) | 2026-10-15 | 2026-11-15 |
| R11 | hasło startowe w logu jest jednorazowe i wymusza zmianę; alternatywa (`RCP_ADMIN_PASSWORD`) dostępna | PO (Z26) | 2026-10-15 | 2026-11-15 |
| R12 | limit prób logowania liczony w pamięci jednego procesu i per adres: za proxy bez `RCP_PROXY=1` wszyscy mają jeden adres (wspólna blokada), bez proxy nagłówek `X-Forwarded-For` jest ignorowany; restart kasuje blokady | PO (Z27) | 2026-10-15 | 2026-11-15 |
| R13 | `'unsafe-inline'` w CSP: reszta polityki (`default-src 'self'`, `frame-ancestors 'none'`, `form-action 'self'`) działa; dane z zewnątrz są escapowane w szablonach (US-003, audyt) | SEC | 2026-10-15 | 2026-11-15 |

Weto SEC (R1–R3) zdjęte 2026-10-15. Demo publiczne nadal tylko z danymi fikcyjnymi; instancja produkcyjna po
spełnieniu listy „przed wdrożeniem" z [05](../05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym).
