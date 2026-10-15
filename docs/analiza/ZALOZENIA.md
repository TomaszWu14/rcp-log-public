# Założenia do potwierdzenia przez Product Ownera

Ustalenia Z1–Z16 potwierdzone 14.10.2026 są w [00-przeglad](../00-przeglad.md#ustalenia-potwierdzone).
Numeracja jest ciągła. Poniżej założenia przyjęte przez BA 15.10.2026, gdy PO nie odpowiedział —
zaakceptowane hurtowo tego samego dnia; status zmienia się przy pierwszej korekcie.

| # | Założenie | Skutek | Status |
|---|---|---|---|
| Z17 | Wdrożenie produkcyjne jest planowane (Z16), więc RODO, retencja i audyt to wymagania *Must* przed produkcją, a nie opis. Tokeny na kartach (R4, US-008) — *Could*, bo zmieniają proces wydawania kart (Z3). | `RODO.md` wchodzi do backlogu jako US-007 | zaakceptowane 2026-10-15 |
| Z18 | Dokumentacja `00–05` zostaje źródłem prawdy; katalogi `analiza/`, `architektura/`, `bezpieczenstwo/` dopisują brakujące treści (NFR, mierniki, backlog, threat model, rejestr ryzyk) i linkują, nie dublują. | pliki-wskaźniki tam, gdzie treść już jest (`PROCESY`, `MODEL_DANYCH`, `API`, `SLOWNIK`) | zaakceptowane 2026-10-15 |
| Z19 | Praca zespołu od gałęzi `chore/zespol-ba-dev-sec` na `main`; jeden PR ze szkieletem procesu, potem funkcje po kolei. | — | zaakceptowane 2026-10-15 |
| Z20 | Commity: typ po angielsku, opis po polsku (jak dotąd). | [CONTRIBUTING](../../CONTRIBUTING.md) | zaakceptowane 2026-10-15 |
| Z21 | Kolejność backlogu = lista „przed wdrożeniem" z [05](../05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym): najpierw bezpieczeństwo (B1–B4, B6), potem spójność ewidencji (T1, T9), reszta. | US-001…US-003 pierwsze | zaakceptowane 2026-10-15 |
| Z22 | Próg pokrycia testami 80% dla logiki domenowej, mierzony po refaktorze DEV-1 (dziś jeden plik — pomiar bez sensu). | `pytest-cov` dochodzi z US-005 | zaakceptowane 2026-10-15 |
| Z23 | Skala do NFR: ~60 osób na zmianie, ~15 stref, jedno wspólne stanowisko skanera (Z2), 1–2 administratorów jednocześnie. | [WYMAGANIA](WYMAGANIA.md) NFR-001, NFR-002 | zaakceptowane 2026-10-15 |
| Z24 | Narzędzia CI: ruff, bandit, pip-audit, gitleaks, trivy (jest Dockerfile). Semgrep i mypy pominięte — jeden plik bez typów, koszt przewyższa zysk. | [ADR 0012](../architektura/adr/0012-proces-zespolu-i-narzedzia-ci.md) | zaakceptowane 2026-10-15 |
| Z25 | Mierniki sukcesu z [WIZJA](WIZJA.md) są propozycją BA; wartości „dziś" to szacunki, do zmierzenia przy testach na zmianie. | — | zaakceptowane 2026-10-15 |
| Z26 | US-001: hasło startowe konta `admin` z `RCP_ADMIN_PASSWORD`; bez zmiennej losowane i wypisane raz w logu serwera. Zmiana hasła wymuszona tylko po haśle startowym (nie cyklicznie); minimalna długość 12 znaków, bez innych reguł złożoności. | ryzyko R11 zaakceptowane | potwierdzone 2026-10-15 |
| Z27 | US-003: limit prób per adres (5 / 10 min → blokada 15 min), w pamięci procesu; za proxy adres z `X-Forwarded-For` tylko przy `RCP_PROXY=1`; token CSRF tylko dla formularzy HTML i importu multipart — JSON API z panelu chroni `SameSite=Lax` i wymóg `Content-Type: application/json`; `Secure` na ciasteczku z flagi `RCP_PROXY`, nie zawsze (lokalne `http://localhost` musi trzymać sesję). | ryzyko R12 zaakceptowane | potwierdzone 2026-10-15 („domyślnie”) |
| Z28 | US-007: podstawa przetwarzania — art. 6 ust. 1 lit. c RODO (ewidencja czasu pracy, art. 149 KP) w zakresie zasilania ewidencji oficjalnej, poza tym lit. f (organizacja pracy); rejestracja stref traktowana jako monitoring z art. 22³ KP (obwieszczenie + informacja 2 tygodnie przed); decyzja o DPIA po stronie IOD. | [RODO](../bezpieczenstwo/RODO.md) | do potwierdzenia z IOD |
| Z29 | US-007: okresy retencji — ewidencja wariant A (dokumentacja pracownicza, 10 lat) albo B (narzędzie pomocnicze, 12 mies.) zależnie od Z28; alerty 90 dni; nadwyżki i korekty 12 mies. po rozliczeniu/decyzji; grafik 12 mies.; kopie 30 dni (Z7); logi 30 dni. Usuwanie całych plików, nie wierszy. | US-009 | do potwierdzenia z IOD |
