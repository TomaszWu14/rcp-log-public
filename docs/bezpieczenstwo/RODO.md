# RODO i retencja danych — wersja 0.1

Materiał roboczy [BA]+[SEC] pod wdrożenie produkcyjne (Z16). **To nie jest porada prawna** — podstawy, okresy
i obowiązki informacyjne wymagają potwierdzenia z inspektorem ochrony danych (IOD) organizacji przed
uruchomieniem z danymi pracowników. Wybory przyjęte domyślnie: Z28, Z29 w [ZALOZENIA](../analiza/ZALOZENIA.md).
Klasyfikacja danych: [KLASYFIKACJA_DANYCH](KLASYFIKACJA_DANYCH.md). Instancja demo przetwarza wyłącznie dane
fikcyjne i ten dokument jej nie dotyczy.

## Role

| Rola | Kto | Uwagi |
|---|---|---|
| Administrator danych | pracodawca (organizacja prowadząca magazyn) | aplikacja jest narzędziem wewnętrznym; brak podmiotu przetwarzającego, jeśli serwer jest własny (Z16: Coolify organizacji) |
| Osoby, których dane dotyczą | pracownicy magazynu | ~60 osób na zmianie (Z23) |
| Użytkownik z dostępem do danych | administrator aplikacji | jedna rola (Z11); konto imienne, hasło własne (US-001) |

## Cel i podstawa przetwarzania (Z28)

| Cel | Dane | Podstawa | Uwagi |
|---|---|---|---|
| Ewidencja czasu pracy w strefach, rozliczenie przerw | pobyty, wpisy ewidencji, nadwyżki, korekty | art. 6 ust. 1 lit. c RODO — obowiązek prowadzenia ewidencji czasu pracy (art. 149 Kodeksu pracy) w zakresie, w jakim ewidencja z aplikacji zasila ewidencję oficjalną; w pozostałym zakresie art. 6 ust. 1 lit. f — organizacja pracy i planowanie obsady stref | **do potwierdzenia z IOD**: czy pliki CSV są elementem oficjalnej ewidencji czasu pracy, czy narzędziem pomocniczym — od tego zależy okres retencji |
| Nadzór nad obsadą i alerty | trwające pobyty, alerty | art. 6 ust. 1 lit. f | rejestracja miejsca i czasu pracy jest formą **monitoringu** innego niż wizyjny (art. 22³ Kodeksu pracy): cel, zakres i sposób trzeba ustalić w układzie zbiorowym, regulaminie pracy albo obwieszczeniu i poinformować pracowników **nie później niż 2 tygodnie** przed uruchomieniem |
| Porównanie grafiku z obecnością | grafik, pierwszy skan dnia | art. 6 ust. 1 lit. f | jak wyżej |
| Dostęp do panelu | login, skrót hasła administratora | art. 6 ust. 1 lit. f | dane dostępowe, nie pracownicze |

Ocena skutków (DPIA): systematyczne monitorowanie pracowników jest na liście operacji wymagających DPIA
(komunikat Prezesa UODO) — **decyzja IOD**, czy skala ~60 osób i zakres (strefa + czas, bez lokalizacji
ciągłej) ją wymaga. Rekomendacja SEC: zrobić uproszczoną DPIA na podstawie [THREAT_MODEL](THREAT_MODEL.md).

## Minimalizacja

- Skaner nie zbiera nic poza kodem pracownika i wybraną strefą; brak lokalizacji ciągłej, brak obrazu.
- Opis korekty to wolny tekst — instrukcja dla pracowników: opisuj własny wpis, nie innych osób; administrator
  usuwa z opisu dane osób trzecich przed decyzją.
- Kod pracownika `HU_NAZWISKO_IMIE` jest jawny na karcie — zmiana na token (US-008) zmniejszy ekspozycję nazwiska.
- Nazwiska w pliku alertów i w logu serwera (hasło startowe, R11) — log traktować jak `admins.json`.

## Retencja (Z29)

Od US-009 aplikacja usuwa dane po okresach z konfiguracji (`retencja_*_dni`, przebieg raz na dobę po kopii zapasowej, wpis `retencja` w audycie). Wcześniej niczego nie usuwała ([05](../05-decyzje-i-ograniczenia.md#znane-ograniczenia-rozwiązania), T11).
Okresy poniżej to propozycja do potwierdzenia; mechanizm usuwania to historyjka **US-009**.

| Dane | Plik | Okres | Liczony od | Uzasadnienie |
|---|---|---|---|---|
| Wpisy ewidencji (dzienne i miesięczne) | `ewidencja_*.csv` | **wariant A**: jak dokumentacja pracownicza — 10 lat od końca roku kalendarzowego, w którym ustał stosunek pracy (art. 94 pkt 9b KP); **wariant B** (narzędzie pomocnicze): 12 miesięcy od końca miesiąca | data wpisu / ustanie zatrudnienia | zależy od statusu ewidencji (Z28) |
| Trwające pobyty | `aktywne_sesje.json` | do zamknięcia (najpóźniej 23:59:59 dnia wejścia, D3) | — | stan bieżący |
| Alerty | `alerty.csv` | 90 dni | data alertu | potrzebne do wyjaśnienia bieżących odchyleń, nie do historii |
| Nadwyżki przerw | `nadwyzki_przerw.json` | 12 miesięcy po przypisaniu (rozliczenie miesięczne, Z5) | status „przypisana" | po rozliczeniu bez celu |
| Korekty | `korekty.json` | 12 miesięcy po decyzji | status zatwierdzona/odrzucona | ślad decyzji o zmianie ewidencji |
| Grafik | `grafik.json` | 12 miesięcy od końca miesiąca | miesiąc grafiku | porównanie z obecnością |
| Słownik pracowników | `pracownicy.json` | do ustania zatrudnienia + usunięcie wpisu (dziś ręcznie, T3) | — | kod przestaje działać przy skanie |
| Kopie zapasowe | `backup/` | **30 dni** (Z7, potwierdzone) | data kopii | mechanizm do zbudowania (T11) |
| Logi serwera / kontenera | Coolify | 30 dni | — | zawierają hasło startowe (R11) i adresy IP |
| Dziennik audytu panelu | `audyt.csv` | 12 miesięcy | data wpisu | kto co zmienił (login administratora, kod pracownika, adres przy logowaniu); rozliczalność operacji na danych osobowych (US-012) |
| Konta administratorów | `admins.json` | do usunięcia konta | — | dane dostępowe |

Zasada dla US-009: usuwanie pliku po okresie, nie anonimizacja wierszy (pliki są dzienne/miesięczne, więc granica
jest naturalna); wpisy w plikach miesięcznych usuwane razem z plikiem po upływie okresu dla najnowszego wpisu.

## Prawa osób

| Prawo | Jak realizowane dziś | Luka |
|---|---|---|
| Dostęp (art. 15) | Historia z filtrem po pracowniku → eksport CSV; grafik i nadwyżki w zakładkach | brak eksportu „wszystko o osobie" jednym przyciskiem — ręcznie z 4 plików |
| Sprostowanie (art. 16) | zgłoszenie korekty przez pracownika (P4), decyzja administratora | poprawka nanoszona ręcznie w plikach (D6) |
| Usunięcie (art. 17) | po okresie retencji (US-009); w trakcie zatrudnienia ograniczone obowiązkiem ewidencji | brak mechanizmu |
| Sprzeciw (art. 21) wobec lit. f | rozpatruje pracodawca; aplikacja nie ma trybu „bez nadzoru" | — |
| Informacja (art. 13) | — | **do przygotowania**: klauzula dla pracowników + obwieszczenie o monitoringu (art. 22³ KP) |

## Środki bezpieczeństwa (stan)

Zrobione: klucz sesji wymagany, hasło startowe jednorazowe (US-001); podgląd obecności tylko po zalogowaniu
(US-002); limit prób, CSRF, `SameSite`/`HttpOnly`/`Secure`, ochrona CSV (US-003); obraz bez roota, TLS na proxy.
Dziennik audytu operacji administratora: `audyt.csv` (US-012). Retencja: US-009. Brakuje: szyfrowanie dysku z danymi
(decyzja infrastrukturalna), ograniczenie dostępu do serwera i logów do administratora.

## Rejestr czynności przetwarzania (wpis)

| Pole | Wartość |
|---|---|
| Nazwa czynności | Rejestracja czasu pracy w strefach magazynu (RCP Log) |
| Cele | ewidencja czasu pracy w strefach, rozliczenie przerw, nadzór nad obsadą, porównanie z grafikiem |
| Kategorie osób | pracownicy magazynu |
| Kategorie danych | identyfikacyjne (imię, nazwisko, kod), czas i miejsce pracy, przerwy, grafik, treść zgłoszeń korekt |
| Odbiorcy | administrator aplikacji; kierownik magazynu (eksport CSV); brak przekazywania poza organizację |
| Przekazanie do państw trzecich | nie |
| Okresy usuwania | tabela „Retencja" |
| Środki techniczne i organizacyjne | sekcja „Środki bezpieczeństwa"; regulamin / obwieszczenie o monitoringu |

## Checklista przed wdrożeniem (RODO)

1. Potwierdzić z IOD status ewidencji (wariant A/B retencji) i podstawę prawną (Z28).
2. Obwieszczenie o monitoringu (art. 22³ KP) i klauzula informacyjna — 2 tygodnie przed startem.
3. Decyzja o DPIA.
4. US-009 wdrożone: retencja plików i kopii (Z7, Z29).
5. Dostęp do serwera, logów i kopii ograniczony do administratora; log serwera z retencją 30 dni.
6. Wpis w rejestrze czynności przetwarzania.
