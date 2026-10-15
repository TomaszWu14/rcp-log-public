# Backlog historyjek

Wymagania funkcjonalne WF-1–37 (historyjki z Given/When/Then) są w [01-procesy](../01-procesy/).
Tu jest backlog **zmian**: priorytet MoSCoW, odwołanie do długu T-n / ryzyka B-n / R-n i kryteria.
Kolejność z listy „przed wdrożeniem" ([05](../05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym), Z21).
Do realizacji dopiero po Definition of Ready ([CONTRIBUTING](../../CONTRIBUTING.md)).

## Must

### US-001 Klucz sesji i hasło startowe spoza kodu (B1–B3, R1, R2)
**Jako** administrator **chcę**, żeby poza trybem demo klucz sesji i hasło startowe pochodziły ze środowiska,
**aby** nikt z publicznego repo nie mógł podrobić mojej sesji ani zalogować się domyślnym hasłem.
```gherkin
Given RCP_DEMO nie jest ustawione i brak RCP_SECRET_KEY
When  uruchamiam aplikację
Then  start kończy się błędem z czytelnym komunikatem

Given pierwsze uruchomienie z RCP_ADMIN_PASSWORD=<losowe>
When  loguję się tym hasłem
Then  panel wymusza zmianę hasła przed dalszą pracą
```
SEC: brak hasła w README i w konsoli (`run.py`); `.gitleaks.toml` traci allowlistę; `gitleaks` zielony.

### US-002 Podgląd obecności tylko dla zalogowanych (B4, R3)
**Jako** pracownik **chcę**, żeby lista, kto jest gdzie, nie była publiczna, **aby** moje dane o miejscu
pracy nie wyciekły poza panel.
```gherkin
Given brak sesji administratora
When  GET /api/status
Then  401 i puste ciało
```

### US-003 Ochrona logowania i formularzy (B6, B8, R5, R6, R8)
**Jako** administrator **chcę** limitu prób logowania, bezpiecznych ciasteczek i ochrony CSV, **aby** hasła
nie dało się zgadnąć, formularzy użyć z obcej strony, a pliku alertów otworzyć bez ryzyka formuły.
```gherkin
Given 5 nieudanych prób z tego samego adresu w 10 min
When  szósta próba
Then  429 przez 15 min

Given import grafiku wysłany z obcej strony bez tokenu CSRF
When  POST /admin/api/grafik/import
Then  403

Given skan kodu "=1+1"
When  wiersz trafia do alerty.csv
Then  pole zaczyna się od apostrofu, nie od "="
```

### US-004 CI i przypięte zależności (DEV-6, DEV-7)
Zrealizowane w PR ze szkieletem procesu — [SLEDZENIE](SLEDZENIE.md).

## Should

### US-005 Jedno miejsce zamykania pobytu (DEV-1 → T1, T9, T2)
**Jako** administrator **chcę**, żeby zamknięcie przerwy przez mnie lub automat liczyło nadwyżkę tak samo
jak zamknięcie przez pracownika, **aby** rozliczenie było kompletne.
```gherkin
Given pracownik na przerwie 42 min
When  administrator przesuwa go do PICKING
Then  w zakładce Przerwy jest nadwyżka 12 min ze statusem „oczekuje"

Given pracownik bez uprawnienia do BUS
When  administrator przesuwa go do BUS
Then  403 „Brak uprawnień do strefy BUS"
```
Przy okazji: jeden próg długiego dyżuru 10 h (T2, Z13), spłata ignorowanych reguł ruff z `pyproject.toml`.

### US-006 Atomowy zapis i identyfikatory bez kolizji (DEV-2, T12)
```gherkin
Given dwa równoczesne zgłoszenia korekty
When  oba zapisane
Then  lista ma dwa wpisy o różnych id
```

### US-007 RODO i retencja (A3, R10, Z7)
`bezpieczenstwo/RODO.md`: podstawa przetwarzania, informacja dla pracowników, retencja ewidencji, alertów,
nadwyżek i korekt (kopie: 30 dni, Z7), prawa osób. Wymóg przed instancją produkcyjną (Z16).

## Could

### US-008 Tokeny na kartach zamiast przewidywalnych kodów (B5, R4)
Zmienia proces wydawania kart (Z3) — decyzja PO przy pierwszym przeglądzie rejestru ryzyk.

## Won't (w tej iteracji)

Zmiana nocna (Z8), praca offline, naliczanie wynagrodzeń — [05](../05-decyzje-i-ograniczenia.md#znane-ograniczenia-rozwiązania).
