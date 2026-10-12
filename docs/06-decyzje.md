# 06. Dziennik decyzji projektowych

Decyzje odczytane z kodu. Dla każdej opisano kontekst, alternatywy możliwe w tej sytuacji,
uzasadnienie wyboru i skutki widoczne w działaniu aplikacji.

| # | Decyzja | Obszar |
|---|---|---|
| [D1](#d1-pliki-json-i-csv-zamiast-bazy-danych) | Pliki JSON i CSV zamiast bazy danych | dane |
| [D2](#d2-jeden-skan--przejście-a-nie-para-wejściewyjście) | Jeden skan = przejście, a nie para wejście/wyjście | model procesu |
| [D3](#d3-sesja-zamykana-o-235959-dnia-rozpoczęcia) | Sesja zamykana o 23:59:59 dnia rozpoczęcia | model procesu |
| [D4](#d4-przerwa-jako-strefa) | Przerwa jako strefa | model danych |
| [D5](#d5-nadwyżka-przerwy-do-ręcznego-rozliczenia) | Nadwyżka przerwy do ręcznego rozliczenia | proces |
| [D6](#d6-korekta-jako-zgłoszenie-z-decyzją-człowieka) | Korekta jako zgłoszenie z decyzją człowieka | proces |
| [D7](#d7-ostrzeżenie-zamiast-blokady-przy-szybkiej-zmianie-strefy) | Ostrzeżenie zamiast blokady przy szybkiej zmianie strefy | UX |
| [D8](#d8-uprawnienia-na-poziomie-strefy) | Uprawnienia na poziomie strefy | model danych |
| [D9](#d9-skaner-bez-logowania-panel-z-logowaniem) | Skaner bez logowania, panel z logowaniem | dostęp |

---

## D1. Pliki JSON i CSV zamiast bazy danych

**Kontekst.** Prototyp dla jednego magazynu. Wcześniej ewidencja była w Excelu. Dane: kilkanaście stref,
słownik pracowników, wpisy czasu.

**Alternatywy.** SQLite; serwer bazy (PostgreSQL); pliki JSON/CSV.

**Dlaczego ta.** <DO UZUPEŁNIENIA — podpowiedź: brak instalacji bazy; CSV otwiera się w Excelu, czyli w narzędziu, którego używano wcześniej (kod zapisuje CSV z BOM i separatorem `;` właśnie pod Excel, `app.py:214`); kopia zapasowa = kopiowanie plików.>

**Skutki.**
- ➕ Uruchomienie bez żadnej infrastruktury; ewidencja od razu czytelna w Excelu.
- ➖ Brak kluczy obcych — spójność trzyma kod, i nie wszędzie (patrz [04-model-danych](04-model-danych.md), N1–N12).
- ➖ Odczyt historii wymaga przejścia po plikach dziennych; zapis wpisu zawsze do dwóch plików.
- ➖ Uszkodzony plik JSON jest czytany jak pusty bez alarmu (`app.py:63-67`).

## D2. Jeden skan = przejście, a nie para wejście/wyjście

**Kontekst.** Pracownik w ciągu zmiany wielokrotnie zmienia strefę. Każda dodatkowa czynność przy
skanerze to czas i ryzyko pominięcia.

**Alternatywy.** Osobne skany „wejście” i „wyjście” dla każdej strefy; jeden skan zamykający
bieżący pobyt i otwierający następny.

**Dlaczego ta.** <DO UZUPEŁNIENIA — podpowiedź: jedna czynność zamiast dwóch; nie da się „zapomnieć wyjścia”.>

**Skutki.**
- ➕ Pracownik ma najwyżej jedną otwartą sesję (`app.py:526, 576`) — wpisy jednego pracownika nigdy na siebie nie nachodzą i nie ma wyjścia bez wejścia.
- ➕ Godzina wyjścia ze strefy jest równa godzinie wejścia do następnej — ciągła oś czasu dnia.
- ➖ Brak skanu „Koniec zmiany” oznacza, że ostatnia sesja trwa dalej — rozwiązuje to dopiero D3.
- ➖ Ponowny skan tej samej strefy rozbija jeden pobyt na dwa wpisy.

## D3. Sesja zamykana o 23:59:59 dnia rozpoczęcia

**Kontekst.** Skutek D2: sesja bez „Końca zmiany” nie ma naturalnego końca.

**Alternatywy.** Zamknięcie po stałym czasie od wejścia; zamknięcie o północy; zostawienie sesji
otwartej do decyzji administratora; zamknięcie na końcu zmiany z grafiku.

**Dlaczego ta.** <DO UZUPEŁNIENIA — czy zmiany nocne w ogóle występowały w strefach? Grafik zna zmianę N 21:00–05:00 (`app.py:94`).>

**Skutki.**
- ➕ Każdy wpis należy do jednego dnia kalendarzowego; ewidencja dzienna jest kompletna.
- ➕ Wpis dostaje flagę `AUTO_ZAMKNIETO` i alert — administrator wie, co sprawdzić.
- ➖ Czas zapomnianej sesji do północy jest liczony jako praca w strefie.
- ➖ Zmiana nocna przez północ traci czas po północy do kolejnego skanu.

## D4. Przerwa jako strefa

**Kontekst.** Przerwę trzeba mierzyć i kontrolować tak samo jak czas w strefach.

**Alternatywy.** Osobny typ zdarzenia „przerwa start / koniec”; przerwa jako zwykła strefa
o zarezerwowanej nazwie `PRZERWA`.

**Dlaczego ta.** <DO UZUPEŁNIENIA — podpowiedź: ten sam mechanizm skanu, ta sama ewidencja, zero dodatkowych ekranów.>

**Skutki.**
- ➕ Przerwa jest kafelkiem jak każda strefa; ewidencja przerw nie wymaga osobnej struktury.
- ➖ Logika przerw zależy od nazwy strefy (`app.py:295, 380`); zmiana nazwy wyłączyłaby kontrolę przerw.
- ➖ Pracownik bez uprawnienia do strefy PRZERWA nie zarejestruje przerwy.

## D5. Nadwyżka przerwy do ręcznego rozliczenia

**Kontekst.** Przerwa dłuższa niż próg (domyślnie 30 min) wymaga decyzji, co zrobić z nadwyżką.

**Alternatywy.** Automatyczne odjęcie nadwyżki od czasu pracy; tylko flaga w ewidencji;
osobna lista nadwyżek rozliczana przez administratora.

**Dlaczego ta.** <DO UZUPEŁNIENIA — co dalej działo się z nadwyżką przypisaną do strefy?>

**Skutki.**
- ➕ Każda nadwyżka ma status „oczekuje” / „przypisana” — widać, co jeszcze nie jest rozliczone.
- ➖ Przypisanie nie zmienia ewidencji; znaczenie przypisania jest poza systemem.
- ➖ Nadwyżka powstaje tylko, gdy przerwę zamknie pracownik — nie przy zamknięciu przez administratora ani automatycznym (`app.py:549` vs `843, 412`).

## D6. Korekta jako zgłoszenie z decyzją człowieka

**Kontekst.** Pracownik może się pomylić przy skanie. Ewidencja czasu pracy nie powinna zmieniać się
bez kontroli.

**Alternatywy.** Edycja wpisu przez pracownika; edycja wpisu przez administratora w panelu;
zgłoszenie tekstowe z decyzją administratora.

**Dlaczego ta.** <DO UZUPEŁNIENIA — kto i gdzie poprawiał dane po zatwierdzeniu?>

**Skutki.**
- ➕ Pracownik nie może sam zmienić ewidencji; każda korekta ma ślad i decyzję.
- ➖ Zatwierdzenie zmienia tylko status — sama poprawka danych odbywa się poza aplikacją.
- ➖ Zgłoszenie nie wskazuje konkretnego wpisu, tylko opisuje problem tekstem.

## D7. Ostrzeżenie zamiast blokady przy szybkiej zmianie strefy

**Kontekst.** Dwa skany w krótkim odstępie to najczęściej pomyłka — ale nie zawsze.

**Alternatywy.** Blokada zmiany przez X minut; brak kontroli; ostrzeżenie z możliwością potwierdzenia.

**Dlaczego ta.** <DO UZUPEŁNIENIA — podpowiedź: blokada zatrzymałaby pracownika, który faktycznie zmienia strefę po 2 minutach.>

**Skutki.**
- ➕ Pomyłkowe kliknięcie zostaje zatrzymane, prawdziwa zmiana przechodzi po jednym dodatkowym kliknięciu.
- ➕ Próg jest konfigurowalny (domyślnie 5 min).

## D8. Uprawnienia na poziomie strefy

**Kontekst.** Nie każdy pracownik pracuje w każdej strefie.

**Alternatywy.** Brak uprawnień; uprawnienia per strefa; uprawnienia per podstrefa.

**Dlaczego ta.** <DO UZUPEŁNIENIA — macierz w panelu ma kolumny podstref (`admin.html:1204`), backend ich nie egzekwuje: porzucony pomysł czy plan?>

**Skutki.**
- ➕ Pracownik widzi tylko swoje strefy — mniej kafelków, mniej pomyłek.
- ➖ Wszystkie podstrefy dozwolonej strefy są dostępne dla każdego, kto ma strefę.

## D9. Skaner bez logowania, panel z logowaniem

**Kontekst.** Stanowisko skanowania jest wspólne dla wszystkich pracowników zmiany.

**Alternatywy.** Logowanie każdego pracownika; skaner otwarty, kod QR jako identyfikator.

**Dlaczego ta.** <DO UZUPEŁNIENIA — podpowiedź: szybkość przy wspólnym stanowisku.>

**Skutki.**
- ➕ Rejestracja to jeden skan, bez hasła.
- ➖ Kod QR ma przewidywalną treść (`HU_NAZWISKO_IMIE`) — kto zna nazwisko, może zarejestrować kogoś innego.
- ➖ Podgląd obecności `/api/status` też jest dostępny bez logowania (`app.py:591`).
