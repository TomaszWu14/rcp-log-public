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
**Zrealizowane** (PR #20): `test_SYS_04`, `test_SYS_05`, `test_SYS_06`; założenie Z26 (hasło startowe bez zmiennej losowane i wypisane raz w logu).

### US-002 Podgląd obecności tylko dla zalogowanych (B4, R3)
**Jako** pracownik **chcę**, żeby lista, kto jest gdzie, nie była publiczna, **aby** moje dane o miejscu
pracy nie wyciekły poza panel.
```gherkin
Given brak sesji administratora
When  GET /api/status
Then  401 i puste ciało
```
**Zrealizowane** (PR #21): `test_ADM_01_status_bez_sesji_401`; skaner nie korzystał z tego adresu, więc bez zmian w `index.html`.

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
**Zrealizowane** (PR #22): `test_ADM_11` (limit), `test_ADM_12` (CSRF formularzy i importu), `test_ADM_13` (ciasteczko), `test_REJ_09` (CSV); założenie Z27; ryzyko R12 zaakceptowane.

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
**Zrealizowane** (PR #23): `test_PRZ_03` (nadwyżka przy zamknięciu przez administratora), `test_PRZ_04` (strefa nadwyżki ze słownika), `test_ADM_04` (400/403 przy przesunięciu i starcie), `test_ADM_05` (charakteryzujący: `start_override`), `test_SES_04` (auto-zamknięcie z nadwyżką, T14), `test_SES_05` (jeden próg 10 h); T15 usunięty; ruff bez wyjątków poza `except: pass`.

### US-006 Atomowy zapis i identyfikatory bez kolizji (DEV-2, T12)
```gherkin
Given dwa równoczesne zgłoszenia korekty
When  oba zapisane
Then  lista ma dwa wpisy o różnych id

Given nadwyżka już przypisana przez pierwszego administratora
When  drugi administrator przypisuje ją ponownie
Then  409 „Nadwyżka już rozliczona”, decyzja pierwszego zostaje
```
**Zrealizowane** (PR #25): `test_KOR_04` (20 równoczesnych zgłoszeń, 20 różnych id), `test_KOR_05` i `test_PRZ_05` (409 / 404), `test_SYS_09` (przerwany zapis nie uszkadza pliku); komunikat 409 widoczny w panelu.

### US-007 RODO i retencja (A3, R10, Z7)
`bezpieczenstwo/RODO.md`: podstawa przetwarzania, informacja dla pracowników, retencja ewidencji, alertów,
nadwyżek i korekt (kopie: 30 dni, Z7), prawa osób. Wymóg przed instancją produkcyjną (Z16).
**Zrealizowane** (PR #24) jako [RODO.md](../bezpieczenstwo/RODO.md) v0.1: role, cele i podstawy (Z28), minimalizacja,
tabela retencji (Z29), prawa osób, wpis do rejestru czynności, checklista przed wdrożeniem. Do potwierdzenia z IOD.

### US-009 Mechanizm retencji (T11, R10, Z7, Z29)
**Jako** administrator danych **chcę**, żeby aplikacja sama usuwała dane po okresie z `RODO.md`, **aby** nie trzymać
danych osobowych bez celu.
```gherkin
Given plik ewidencji starszy niż okres retencji z konfiguracji
When  przebieg kontroli w tle
Then  plik jest usunięty, a w alertach jest wpis RETENCJA z nazwą pliku

Given kopia zapasowa starsza niż 30 dni
When  przebieg kopii zapasowej
Then  kopia jest usunięta
```
Okresy jako klucze konfiguracji z wartościami domyślnymi z `RODO.md`; kopia zapasowa niezależna od godziny pracy serwera (T11).

### US-010 Błędy do logu zamiast `except: pass` (DEV-3)
**Jako** administrator **chcę**, żeby każdy błąd w tle i przy odczycie plików zostawiał ślad w logu, a wątki kontroli
i kopii działały dalej, **aby** alerty nie przestawały działać po cichu.
```gherkin
Given przebieg kontroli pobytów rzuca nieprzewidziany wyjątek
When  wątek wykonuje przebieg
Then  w logu jest wpis ERROR ze śladem, a kolejny przebieg po 60 s wykonuje się normalnie

Given uszkodzony plik config.json
When  aplikacja czyta konfigurację
Then  używa wartości domyślnych i loguje ERROR z nazwą pliku
```
**Zrealizowane** (PR #26): logger `rcp` (`logging.basicConfig`), `_przebieg()` dla trzech wątków, `kopia_zapasowa(now)`
i `_data_z_naglowka()` wydzielone i przetestowane; `test_SYS_01`, `test_SYS_10`, `test_SYS_11`; `pyproject.toml` bez wyjątków ruff.

### US-011 Walidacja konfiguracji, limit żądania, nagłówki bezpieczeństwa (B7, R7, R9, T6)
**Jako** administrator **chcę**, żeby serwer odrzucał błędną konfigurację i podejrzane pliki oraz wysyłał nagłówki
bezpieczeństwa, **aby** panel nie dał się wywrócić jednym żądaniem ani osadzić na obcej stronie.
```gherkin
Given próg przerwy 999 albo nieznany klucz
When  POST /admin/api/config
Then  400 z komunikatem, konfiguracja bez zmian

Given plik .xls albo uszkodzony .xlsx, albo plik 3 MB
When  import grafiku
Then  400 z komunikatem albo 413 (limit 2 MB)
```
**Zrealizowane** (PR #27): `sprawdz_konfiguracje()`, `MAX_CONTENT_LENGTH`, `naglowki_bezpieczenstwa()` (CSP, nosniff,
Referrer-Policy, X-Frame-Options, HSTS za proxy); `test_ADM_10`, `test_ADM_14`, `test_GRF_05`; ryzyko R13 (CSP inline) zaakceptowane.

### US-012 Dziennik audytu operacji administratora (R10)
**Jako** administrator danych **chcę** wiedzieć, kto, kiedy i co zmienił w panelu, **aby** operacje na danych pracowników były rozliczalne.
```gherkin
Given administrator dodaje strefę, zmienia konfigurację i przesuwa pracownika
When  czytam /admin/api/audyt
Then  trzy wpisy z loginem, chwilą, akcją i obiektem, najnowszy pierwszy

Given nieudane logowanie
When  czytam dziennik
Then  wpis logowanie_nieudane z loginem i adresem
```
**Zrealizowane** (PR #28): `zapisz_audyt()` w 17 miejscach, `audyt.csv` tylko dopisywany, `/admin/api/audyt`, eksport `audyt`;
`test_ADM_15`. Zakładka w panelu — US-013 (PR #29): „🧾 Audyt” z filtrem i linkiem do pełnego CSV; `test_ADM_16`.

### US-014 Korekta nanoszona na wpis (krok 4 listy, D6 → D12)
**Jako** administrator **chcę** nanieść zatwierdzoną korektę na konkretny wpis w aplikacji, **aby** plik dnia i miesiąca były spójne i miały ślad.
```gherkin
Given korekta pracownika i jego wpis PICKING 08:00–09:00
When  administrator nanosi PRZYJECIA 08:00–10:00
Then  oba pliki mają poprawiony wpis z KOREKTA#<nr>, w audycie stara i nowa wartość; drugi raz → 409
```
**Zrealizowane** (PR #30): `adm_korekta_wpisy`, `adm_korekta_nanies`, `_przepisz_csv` (atomowo); panel Korekty → „✎ Nanieś”; `test_KOR_06`; Z30.

## Could

### US-008 Tokeny na kartach zamiast przewidywalnych kodów (B5, R4)
Zmienia proces wydawania kart (Z3) — decyzja PO przy pierwszym przeglądzie rejestru ryzyk.

## Won't (w tej iteracji)

Zmiana nocna (Z8), praca offline, naliczanie wynagrodzeń — [05](../05-decyzje-i-ograniczenia.md#znane-ograniczenia-rozwiązania).
