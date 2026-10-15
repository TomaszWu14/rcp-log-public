# 05. Decyzje projektowe, ograniczenia i dług techniczny

## Dziennik decyzji projektowych

Decyzje odczytane z kodu. Dla każdej: kontekst, rozważane opcje, uzasadnienie wyboru i konsekwencje
widoczne w działaniu aplikacji.

| # | Decyzja | Obszar |
|---|---|---|
| [D1](#d1-pliki-json-i-csv-zamiast-bazy-danych) | Pliki JSON i CSV zamiast bazy danych | dane |
| [D2](#d2-jeden-skan--przejście-a-nie-para-wejściewyjście) | Jeden skan = przejście, a nie para wejście/wyjście | model procesu |
| [D3](#d3-pobyt-zamykany-o-235959-dnia-rozpoczęcia) | Pobyt zamykany o 23:59:59 dnia rozpoczęcia | model procesu |
| [D4](#d4-przerwa-jako-strefa) | Przerwa jako strefa | model danych |
| [D5](#d5-nadwyżka-przerwy-do-ręcznego-rozliczenia) | Nadwyżka przerwy do ręcznego rozliczenia | proces |
| [D6](#d6-korekta-jako-zgłoszenie-z-decyzją-człowieka) | Korekta jako zgłoszenie z decyzją człowieka | proces |
| [D7](#d7-ostrzeżenie-zamiast-blokady-przy-szybkiej-zmianie-strefy) | Ostrzeżenie zamiast blokady przy szybkiej zmianie strefy | doświadczenie użytkownika |
| [D8](#d8-uprawnienia-na-poziomie-strefy) | Uprawnienia na poziomie strefy | model danych |
| [D9](#d9-skaner-bez-logowania-panel-z-logowaniem) | Skaner bez logowania, panel z logowaniem | dostęp |
| [D10](#d10-zadania-cykliczne-jako-wątki-wewnątrz-serwera) | Zadania cykliczne jako wątki wewnątrz serwera | architektura |
| [D11](#d11-tryb-demo-w-tym-samym-kodzie) | Tryb demo w tym samym kodzie | wdrożenie |

### D1. Pliki JSON i CSV zamiast bazy danych

- **Kontekst.** Prototyp dla jednego magazynu; wcześniej ewidencja była w Excelu. Dane: kilkanaście stref,
  słownik pracowników, wpisy czasu.
- **Opcje.** SQLite; serwer bazy danych; pliki JSON i CSV.
- **Wybór i uzasadnienie.** Pliki. Ewidencja ma trafiać do Excela, którego odbiorcy używali wcześniej,
  dlatego CSV jest zapisywany ze średnikiem i UTF-8 BOM (`app.py:250`) i otwiera się dwuklikiem. Prototyp
  nie wymaga instalowania ani utrzymywania bazy.
- **Konsekwencje.** ➕ Start bez infrastruktury; ewidencja od razu czytelna w Excelu. ➖ Brak kluczy obcych:
  spójność trzyma kod, i nie wszędzie ([02. Model danych](02-dane/model-danych.md#spójność-danych)).
  ➖ Każdy wpis zapisywany do dwóch plików; historia czytana z wielu plików dziennych. ➖ Uszkodzony plik JSON
  czytany jak pusty z wpisem ERROR w logu (`app.py:91-98`, US-010).

### D2. Jeden skan = przejście, a nie para wejście/wyjście

- **Kontekst.** Pracownik zmienia strefę wiele razy na zmianę; każda czynność przy skanerze to czas i ryzyko
  pominięcia.
- **Opcje.** Osobne skany „wejście” i „wyjście”; jeden skan zamykający bieżący pobyt i otwierający następny.
- **Wybór i uzasadnienie.** Jeden skan. Para skanów podwajałaby liczbę podejść do stanowiska.
- **Konsekwencje.** ➕ Najwyżej jeden trwający pobyt na pracownika (BR-7); wpisy nie nachodzą na siebie,
  nie ma wyjścia bez wejścia. ➕ Ciągła oś czasu dnia: wyjście z jednej strefy to wejście do następnej.
  ➖ Brak skanu „Koniec zmiany” zostawia pobyt otwarty, co rozwiązuje dopiero D3. ➖ Ponowny skan tej samej
  strefy rozbija pobyt na dwa wpisy (BR-12).

### D3. Pobyt zamykany o 23:59:59 dnia rozpoczęcia

- **Kontekst.** Skutek D2: pobyt bez „Końca zmiany” nie ma naturalnego końca.
- **Opcje.** Zamknięcie po stałym czasie od wejścia; o północy; decyzja administratora; koniec zmiany
  z grafiku.
- **Wybór i uzasadnienie.** Zamknięcie o 23:59:59 dnia wejścia. W strefach objętych rejestracją nie ma
  zmian nocnych (potwierdzone, [Z8](00-przeglad.md#ustalenia-potwierdzone)), więc pobyt przez północ
  oznacza zapomniany koniec zmiany, nie pracę; każdy wpis zostaje w jednym dniu kalendarzowym.
- **Konsekwencje.** ➕ Kompletna ewidencja dzienna. ➕ Wpis z flagą `AUTO_ZAMKNIETO` i alert (BR-17).
  ➖ Czas zapomnianego pobytu do północy liczony jako praca. ➖ Wprowadzenie zmian nocnych wymaga zmiany
  reguły; kod zmiany N w grafiku nie jest używany przez rejestrację.

### D4. Przerwa jako strefa

- **Kontekst.** Przerwę trzeba mierzyć i kontrolować jak czas w strefach.
- **Opcje.** Osobny typ zdarzenia „przerwa start / koniec”; przerwa jako strefa o zarezerwowanej nazwie.
- **Wybór i uzasadnienie.** Strefa `PRZERWA`. Ten sam mechanizm skanu; pracownik nie uczy się osobnej
  czynności.
- **Konsekwencje.** ➕ Przerwa jest kafelkiem jak każda strefa; brak osobnej struktury danych. ➖ Logika
  zależy od nazwy strefy (BR-13); zmiana nazwy wyłącza kontrolę przerw. ➖ Pracownik bez uprawnienia do
  `PRZERWA` nie zarejestruje przerwy.

### D5. Nadwyżka przerwy do ręcznego rozliczenia

- **Kontekst.** Przerwa dłuższa niż próg wymaga decyzji, co zrobić z nadwyżką.
- **Opcje.** Automatyczne odjęcie od czasu pracy; sama flaga w ewidencji; osobna lista rozliczana przez
  administratora.
- **Wybór i uzasadnienie.** Osobna lista ze statusem. Nadwyżka jest kosztem czasu, a przypisanie wskazuje
  strefę, która ten koszt ponosi w rozliczeniu miesięcznym prowadzonym poza aplikacją (potwierdzone, [Z5](00-przeglad.md#ustalenia-potwierdzone)).
- **Konsekwencje.** ➕ Widać, co nie jest rozliczone (status „oczekuje”). ➖ Przypisanie nie zmienia
  ewidencji (BR-27). ➖ Nadwyżka powstaje tylko przy zamknięciu przerwy przez pracownika (BR-24).

### D6. Korekta jako zgłoszenie z decyzją człowieka

- **Kontekst.** Pracownik może się pomylić przy skanie; ewidencja czasu pracy nie powinna zmieniać się
  bez kontroli.
- **Opcje.** Edycja wpisu przez pracownika; edycja przez administratora w panelu; zgłoszenie tekstowe
  z decyzją administratora.
- **Wybór i uzasadnienie.** Zgłoszenie z decyzją. Każda korekta przechodzi przez ocenę człowieka i zostawia
  ślad.
- **Konsekwencje.** ➕ Pracownik nie zmienia ewidencji sam. ➖ Zatwierdzenie zmienia tylko status; poprawkę
  nanosi człowiek w dwóch plikach (BR-32), pominięcie jednego rozspójnia ewidencję. ➖ Zgłoszenie nie
  wskazuje wpisu (BR-33).

### D7. Ostrzeżenie zamiast blokady przy szybkiej zmianie strefy

- **Kontekst.** Dwa skany w krótkim odstępie to najczęściej pomyłka, ale nie zawsze.
- **Opcje.** Blokada zmiany przez X minut; brak kontroli; ostrzeżenie z możliwością potwierdzenia.
- **Wybór i uzasadnienie.** Ostrzeżenie. Blokada zatrzymałaby pracę i wymagała interwencji administratora
  przy prawdziwej szybkiej zmianie.
- **Konsekwencje.** ➕ Pomyłkowe kliknięcie zatrzymane, prawdziwa zmiana po jednym dodatkowym kliknięciu
  (BR-6). ➕ Próg konfigurowalny. ➖ Sprawdzenie czasu odbywa się poza blokadą stanu, więc przy dwóch
  równoczesnych skanach jednego kodu ostrzeżenie może się nie pojawić (`app.py:626-637`).

### D8. Uprawnienia na poziomie strefy

- **Kontekst.** Nie każdy pracownik pracuje w każdej strefie.
- **Opcje.** Brak uprawnień; uprawnienia per strefa; per podstrefa.
- **Wybór i uzasadnienie.** Per strefa. Uprawnienia per podstrefa okazały się zbędne; pozostałości tego
  pomysłu usunięto z kodu (README: refaktoryzacje w historii zmian).
- **Konsekwencje.** ➕ Pracownik widzi tylko swoje strefy (BR-3). ➖ Wszystkie podstrefy dozwolonej strefy
  są dostępne dla każdego, kto ma strefę (BR-5).

### D9. Skaner bez logowania, panel z logowaniem

- **Kontekst.** Jedno wspólne stanowisko skanowania na zmianie: komputer z czytnikiem USB działającym jak klawiatura (potwierdzone, [Z2](00-przeglad.md#ustalenia-potwierdzone)).
- **Opcje.** Logowanie każdego pracownika; skaner otwarty, kod QR jako identyfikator.
- **Wybór i uzasadnienie.** Skaner otwarty. Logowanie hasłem przy każdej zmianie strefy byłoby
  niepraktyczne na wspólnym urządzeniu.
- **Konsekwencje.** ➕ Rejestracja to jeden skan. ➖ Kod QR ma przewidywalną treść (`HU_NAZWISKO_IMIE`):
  kto zna nazwisko, może zarejestrować kogoś innego. ➖ ~~Podgląd obecności dostępny bez logowania~~ —
  od US-002 wymaga sesji administratora (`app.py:669-671`).

### D10. Zadania cykliczne jako wątki wewnątrz serwera

- **Kontekst.** Kontrola przerw i dyżurów, zamykanie pobytów i kopia zapasowa muszą działać bez udziału
  człowieka.
- **Opcje.** Zewnętrzny harmonogram systemu operacyjnego; osobny proces; wątki uruchamiane przy starcie
  serwera.
- **Wybór i uzasadnienie.** Wątki w procesie serwera (`app.py:480, 542, 1347`). Jedno polecenie uruchamia
  wszystko; brak dodatkowej konfiguracji na stanowisku.
- **Konsekwencje.** ➕ Zero konfiguracji. ➖ Zadania żyją tylko, gdy serwer działa: kopia o 02:00 nie
  powstanie przy wyłączonym serwerze (BR-56), a nieoczekiwany błąd kończy wątek kontroli po cichu
  (`app.py:541`). ➖ Nowe alerty trzymane w pamięci giną przy restarcie (BR-19). ➖ Przy kilku procesach
  serwera (skalowanie) każdy uruchomiłby własne zadania.

### D11. Tryb demo w tym samym kodzie

- **Kontekst.** Publiczna prezentacja prototypu bez ujawniania danych i bez osobnej wersji aplikacji.
- **Opcje.** Osobna gałąź lub kopia kodu z danymi; nagranie wideo; tryb demo sterowany zmienną
  środowiskową.
- **Wybór i uzasadnienie.** Zmienna `RCP_DEMO` (`app.py:28`): osobny katalog danych, generator fikcyjnych
  danych, automatyczne logowanie, blokada zmian słowników, cykliczne odtwarzanie danych.
- **Konsekwencje.** ➕ Jedna baza kodu; demo zawsze zgodne z aktualną wersją. ➕ Reset nie dotyka katalogu
  produkcyjnego (`app.py:46`). ➖ Lista blokad jest utrzymywana ręcznie: nowy adres zmieniający dane trzeba
  do niej dopisać (`app.py:1290-1295`). ➖ W demo działają przesunięcia, korekty i nadwyżki, więc gość
  może „zepsuć” scenę demo do następnego resetu.

## Znane ograniczenia rozwiązania

| Ograniczenie | Konsekwencja | Źródło |
|---|---|---|
| Brak naliczania wynagrodzeń i integracji kadrowo-płacowej | dane przekazywane przez eksport CSV | `app.py:1092-1105` |
| Korekta nie zmienia ewidencji | poprawka ręczna w dwóch plikach | BR-32 |
| Brak zmian nocnych przez północ | pobyt zamykany o 23:59:59 | BR-17, D3 |
| Uprawnienia tylko per strefa | podstrefy dostępne dla każdego z uprawnieniem do strefy | BR-5, D8 |
| Skaner wymaga połączenia z serwerem | skan bez połączenia przepada z komunikatem | `index.html:459, 595` |
| Jedna rola w panelu | pełny panel ma tylko administrator; lider zmiany nie ma dostępu, co właściciel projektu uznał za wystarczające ([Z11](00-przeglad.md#ustalenia-potwierdzone)) | `app.py:317` |
| Eksport tylko dnia dzisiejszego i bieżącego miesiąca | dane z przeszłości przez Historię (maks. 500 wierszy) albo z serwera | BR-54, BR-55 |
| Alerty bez potwierdzania | kolumna „potwierdzone” zawsze „NIE”; brak listy alertów w panelu (tylko eksport); potwierdzone jako wystarczające (Z12) | `app.py:295`, [04. Integracje](04-integracje.md#adresy-aplikacji-interfejs-http) |
| Brak retencji danych osobowych | wpisy, alerty, nadwyżki, korekty i kopie przechowywane bezterminowo | brak mechanizmu w kodzie |
| Brak edycji nazwisk i nazw stref | zmiana przez usunięcie i ponowne dodanie; stare nazwy zostają w historii | BR-48, BR-50 |
| Czas lokalny serwera bez strefy w zapisach | zmiana czasu letni/zimowy zaburza pobyty trwające w noc zmiany czasu; zaakceptowane: serwer w Europe/Warsaw, czas lokalny wystarcza (Z10) | `datetime.now()` w całym `app.py` |

## Dług techniczny

### Proces i dane

| # | Problem | Gdzie opisane | Źródło |
|---|---|---|---|
| T1 | ~~Nadwyżka tylko przy zamknięciu przerwy przez pracownika~~ — naprawione (US-005): jedna funkcja `zamknij_pobyt()` dla skanera, administratora i auto-zamknięcia | BR-24, [P3](01-procesy/P3-nadwyzki-przerw.md) | `app.py:371-410` |
| T2 | ~~Dwa domyślne progi długiego dyżuru~~ — naprawione (US-005): jedna stała `ALERT_DYZUR_H = 10` dla alertu i Live (Z13) | Z13, [P2](01-procesy/P2-nadzor-i-alerty.md) | `app.py:59, 491, 677` |
| T3 | Usunięcie pracownika kasuje trwający pobyt bez wpisu; zostawia grafik, nadwyżki, korekty | BR-49 | `app.py:1036-1044` |
| T4 | Ponowny skan tej samej strefy rozbija pobyt | BR-12 | `app.py:639-655` |
| T5 | Porównanie z grafikiem liczy tylko zamknięte wpisy; dzień, który się nie zaczął, ma status „nieobecność” | [P5](01-procesy/P5-grafik-i-obecnosc.md) wyjątki | `app.py:1231-1262` |
| T6 | Import grafiku: dopasowanie po fragmencie nazwiska, literówka w kodzie zmiany = dzień wolny, numer dnia w nagłówku = bieżący miesiąc, wiersz legendy w szablonie zgłaszany jako błąd | BR-36, BR-37, BR-38, [P5](01-procesy/P5-grafik-i-obecnosc.md) wyjątki | `app.py:156, 158-169, 216-221, 1144` |
| T7 | Nowe alerty w pamięci serwera: giną przy restarcie, pobiera je pierwsza karta panelu, nowszy alert tego samego pracownika nadpisuje starszy | BR-19, [P2](01-procesy/P2-nadzor-i-alerty.md) wyjątki | `app.py:483, 508, 516, 530, 701-702` |
| T8 | Dodanie pracownika, strefy lub konta o istniejącej nazwie nadpisuje rekord | BR-48, BR-51 | `app.py:991, 1033, 1020` |
| T9 | ~~Przesunięcie i ręczny start nie sprawdzały uprawnień ani słownika stref; nazwa strefy przy nadwyżce była wolnym tekstem~~ — naprawione (US-005): `sprawdz_strefe()` (400 / 403), nadwyżka tylko do strefy ze słownika | BR-20, BR-21, BR-26 | `app.py:412-419, 893, 938-939, 966-967` |
| T10 | Przekroczona przerwa daje dwa wiersze `DLUGA_PRZERWA` w pliku alertów: w trakcie i przy zamknięciu | BR-9, BR-15 | `app.py:507, 408` |
| T11 | Kopia tylko w godzinie 02 przy działającym serwerze; brak retencji; ~~błąd tylko w konsoli~~ — od US-010 błąd w logu z pełnym śladem, kopia jako funkcja `kopia_zapasowa()` z testem | BR-56, BR-57 | `app.py:461-478` |
| T12 | ~~Równoczesne decyzje dwóch administratorów: wygrywał ostatni zapis~~ — naprawione (US-006): decyzja pod blokadą; druga decyzja o rozliczonej pozycji dostaje 409 z komunikatem, nieistniejący numer 404 | [P3](01-procesy/P3-nadwyzki-przerw.md), [P4](01-procesy/P4-korekty-ewidencji.md) wyjątki | `app.py:894-901, 914-921` |
| T13 | Dane dashboardu zawierają niewyświetlane sumy per strefa i per pracownik | [04. Integracje](04-integracje.md) | `app.py:826-835, 867-868` |
| T14 | Numery wpisów liczone z liczby linii pliku; ~~wpisy automatyczne bez numeru, formatu czasu i pola korekty~~ — od US-005 wpis automatyczny ma te same pola co każdy inny | [02. Model danych](02-dane/model-danych.md#spójność-danych) | `app.py:265-270, 371-391` |
| T15 | ~~Alert `PRZEKROCZENIE_ZMIANY` filtrowany na ekranie~~ — usunięty (US-005, Z14) | Z14 | — |

### Bezpieczeństwo

Prototyp nie przeszedł przeglądu bezpieczeństwa. Przed jakimkolwiek wdrożeniem:

| # | Problem | Źródło |
|---|---|---|
| B1 | ~~Klucz sesji z wartością domyślną w kodzie~~ — naprawione (US-001): poza trybem demo brak `RCP_SECRET_KEY` kończy start błędem | `app.py:30-40` |
| B2 | ~~Konto `admin/admin123` bez wymuszenia zmiany, dane logowania w konsoli~~ — naprawione (US-001): hasło startowe z `RCP_ADMIN_PASSWORD` albo losowe wypisane raz; zmiana wymuszona przy pierwszym logowaniu | `app.py:353-360, 756-780` |
| B3 | ~~Migracja starych skrótów haseł ustawiała stałe hasło~~ — naprawione (US-001): konto dostaje nowe hasło startowe jak wyżej | `app.py:435-445` |
| B4 | ~~Podgląd obecności dostępny bez logowania~~ — naprawione (US-002): `/api/status` bez sesji administratora odpowiada 401 z pustym ciałem | `app.py:669-671` |
| B5 | Przewidywalna treść kodu QR; brak unieważniania kodu zgubionej karty, a zgubiona karta dostaje duplikat z tym samym kodem (Z3) | `app.py:1032`, D9 |
| B6 | ~~Brak limitu prób logowania i ochrony CSRF~~ — naprawione (US-003): 5 nieudanych prób z adresu w 10 min blokuje logowanie na 15 min (429); token CSRF na formularzach logowania, zmiany hasła i importu grafiku; ciasteczko `SameSite=Lax`, `HttpOnly`, `Secure` przy `RCP_PROXY=1` | `app.py:43-45, 320-350, 731-750` |
| B7 | Konfiguracja zapisuje dowolne klucze; ścieżka kopii może wskazać dowolny katalog serwera | `app.py:1084-1089` |
| B8 | ~~Treść nieznanego kodu trafiała do pliku alertów bez oczyszczenia~~ — naprawione (US-003): pola CSV zaczynające się od `= + - @` lub tabulatora dostają apostrof | `app.py:253-255, 259, 294-295` |
| B9 | Dodanie administratora o istniejącym loginie po cichu zmienia hasło tego konta | `app.py:1067` |

### Interfejs

Ślepe ścieżki U1–U10 opisuje [03. User flow](03-user-flow/user-flow.md#ślepe-ścieżki-i-akcje-bez-informacji-zwrotnej).
Najważniejsza: ekran pracownika nie wraca sam do ekranu startu (U1).

### Obsługa błędów i walidacja

| Miejsce | Co się dzieje | Źródło |
|---|---|---|
| odczyt JSON | uszkodzony plik: wpis ERROR w logu i wartość domyślna (US-010); brak pliku nie jest błędem | `app.py:91-98` |
| zapis JSON | ~~bez obsługi błędu i nieatomowy~~ — od US-006 zapis przez plik tymczasowy i `os.replace`: przerwany zapis zostawia poprzednią wersję; błąd nadal nie jest logowany | `app.py:100-109` |
| wiele miejsc | ~~błędy pomijane bez śladu (`except: pass`)~~ — US-010: wyjątki zawężone do oczekiwanych typów, odczyty logują ERROR/WARNING, parsowanie dat grafiku w `_data_z_naglowka()` | `app.py:158-169, 270, 278-279, 313, 361-364, 1243-1244, 1274` |
| wątek kontroli | ~~inny wyjątek kończył wątek po cichu~~ — US-010: każdy wyjątek przebiegu trafia do logu z pełnym śladem, wątek działa dalej (`_przebieg`) | `app.py:452-459, 537-540` |
| daty z plików | uszkodzony zapis pobytu daje błąd serwera | `app.py:502, 630, 646, 680, 942, 970` |
| data dashboardu | zły format w adresie daje błąd serwera | `app.py:821-822` |
| plik grafiku | nieprawidłowy plik daje błąd serwera; pole wyboru dopuszcza `.xls`, którego biblioteka nie czyta | `app.py:177`, `admin.html:388` |
| treść żądań | treść niebędąca obiektem JSON daje błąd serwera | `app.py:553, 603, 716` |
| opis korekty, lista uprawnień, konfiguracja, wpis grafiku | bez walidacji po stronie serwera | `app.py:720, 1049-1052, 1087-1088, 1203-1212` |
| nieistniejący numer nadwyżki lub korekty | od US-006 odpowiedź 404 „Nie znaleziono …” | `app.py:894-901, 914-921` |
| ekran | nie sprawdza odpowiedzi serwera w kilku akcjach; brak obsługi wygaśnięcia sesji i błędów sieci w panelu | `index.html:640-645`, `admin.html:863-867, 972-975, 1165-1173, 529-532` |

## Co trzeba zrobić przed wdrożeniem produkcyjnym

Kolejność według wpływu na wiarygodność ewidencji i bezpieczeństwo danych osobowych.

1. **Powrót ekranu pracownika do startu po bezczynności** (U1) — chroni przed rejestracją w cudzym imieniu;
   ~~ochrona podglądu obecności (B4)~~ — zrobione (US-002).
2. ~~Wymóg ustawienia klucza sesji poza trybem demo i wymuszenie zmiany hasła startowego (B1–B3)~~ — zrobione (US-001);
   ~~limit prób logowania i ochrona CSRF (B6)~~ — zrobione (US-003).
3. ~~Spójne zamykanie przerw (T1); jeden próg długiego dyżuru (T2); usunięcie `PRZEKROCZENIE_ZMIANY` (T15)~~ — zrobione (US-005). ~~Jeden próg długiego
   dyżuru 10 h (T2, Z13); usunięcie pozostałości `PRZEKROCZENIE_ZMIANY` (T15, Z14).
4. **Korekta powiązana z konkretnym wpisem**, która po zatwierdzeniu zmienia ewidencję w obu plikach
   (D6, BR-32, BR-33).
5. **Polityka retencji danych osobowych** — opisana w [RODO.md](bezpieczenstwo/RODO.md) (US-007: podstawy,
   okresy dla ewidencji, alertów, nadwyżek, korekt; kopie 30 dni, [Z7](00-przeglad.md#ustalenia-potwierdzone));
   do potwierdzenia z IOD, mechanizm usuwania w US-009; oraz decyzja o anonimizacji danych
   przykładowych ([Do anonimizacji](00-przeglad.md#do-anonimizacji)).
6. **Kopia zapasowa niezależna od godziny pracy serwera**, na tym samym serwerze, z retencją 30 dni
   i powiadomieniem o błędzie (T11, D10, Z7).
7. **Walidacja na serwerze**: ~~strefa ze słownika przy przesunięciach i nadwyżkach (T9)~~ — zrobione (US-005); zostaje podstrefa, unikalne
   nazwy (T8), zakresy konfiguracji (B7), pliki grafiku (T6).
8. ~~Blokada równoczesnej edycji nadwyżki i korekty przez dwóch administratorów (T12)~~ — zrobione (US-006).
9. **Unieważnianie kodu QR zgubionej karty** (B5): dziś administrator drukuje duplikat z tym samym kodem
   ([Z3](00-przeglad.md#ustalenia-potwierdzone)).
10. **Ustalenie obowiązujących wartości progów** z kierownikiem magazynu: dzisiejsze 30 min, 5 min, 10 h
    i 15 min to wartości robocze z prototypu ([Z4](00-przeglad.md#ustalenia-potwierdzone)).
11. **Osobna instancja produkcyjna** na tym samym serwerze Coolify bez trybu demo, z woluminami na dane
    i kopie ([Z16](00-przeglad.md#ustalenia-potwierdzone)).
12. **Testy z użytkownikami na zmianie**: prototyp nie był jeszcze sprawdzony w pracy (README).
