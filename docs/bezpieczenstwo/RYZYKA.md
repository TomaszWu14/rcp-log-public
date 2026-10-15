# Rejestr ryzyk

Wpływ i prawdopodobieństwo: 1–3. Decyzja: **naprawić** / **zaakceptować** (z podpisem PO i datą przeglądu) / **przenieść**.
Opis ryzyk: [AUDYT](../AUDYT.md#sec-najważniejsze-ryzyka-top-10); odpowiedniki B1–B9 w [05](../05-decyzje-i-ograniczenia.md#bezpieczeństwo).
Dotyczy planowanej instancji produkcyjnej (Z16); demo przetwarza dane fikcyjne.

| ID | Ryzyko | Wpływ | Prawd. | Decyzja | Właściciel | Historyjka | Przegląd |
|---|---|---|---|---|---|---|---|
| R1 | domyślny klucz sesji w kodzie użyty, gdy brak `RCP_SECRET_KEY` (B1) | 3 | 2 | naprawić | SEC | US-001 | — |
| R2 | domyślne hasło admina bez wymuszenia zmiany (B2, B3) | 3 | 3 | naprawić | SEC | US-001 | — |
| R3 | obecność z nazwiskami bez logowania (B4) | 3 | 2 | naprawić | SEC | US-002 | — |
| R4 | przewidywalne, nieunieważnialne kody QR; duplikat z tym samym kodem (B5, Z3) | 2 | 2 | **decyzja PO** | PO | US-008 | 2026-11-15 |
| R5 | brak limitu prób logowania (B6) | 2 | 2 | naprawić | SEC | US-003 | — |
| R6 | CSRF formularzy, cookie bez SameSite/Secure (B6) | 2 | 1 | naprawić | SEC | US-003 | — |
| R7 | config bez walidacji, dowolny `backup_path` (B7) | 2 | 1 | naprawić | DEV | — (krok 7 listy przed wdrożeniem) | — |
| R8 | CSV injection przez nieznany kod (B8) | 2 | 1 | naprawić | DEV | US-003 | — |
| R9 | brak limitu żądania, nagłówków; nasłuch na `0.0.0.0` (bandit B104, zamierzone — kontener za proxy); demo bez limitu żądań | 2 | 1 | naprawić przy wdrożeniu | DEV | — | — |
| R10 | brak retencji (poza kopiami, Z7) i audytu operacji | 2 | 1 | opisać (RODO.md), wdrożyć przed produkcją | BA+SEC | US-007 | — |

## Wyjątki (ryzyka świadomie zaakceptowane)

| ID | Uzasadnienie | Zaakceptował | Data | Przegląd |
|---|---|---|---|---|
| R9 (część: demo bez limitu żądań) | instancja demo zawiera tylko dane fikcyjne odtwarzane co 30 min; skutkiem nadużycia jest co najwyżej niedostępność demo | PO (Z17) | 2026-10-15 | 2026-11-15 |

Do czasu naprawy R1–R3 obowiązuje weto SEC: brak instancji produkcyjnej; demo publiczne tylko z danymi fikcyjnymi.
