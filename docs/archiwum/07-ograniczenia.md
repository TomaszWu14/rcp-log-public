# 07. Ograniczenia, znane problemy i dalsze kroki

RCP Log jest **prototypem**. Ten dokument zbiera świadome ograniczenia zakresu, znane problemy
i pytania, na które analiza nie dała jeszcze odpowiedzi.

## Poza zakresem

| Czego nie ma | Konsekwencja |
|---|---|
| Naliczanie wynagrodzeń, integracja z systemem kadrowo-płacowym | dane przekazywane przez eksport CSV |
| Automatyczna poprawka ewidencji po zatwierdzeniu korekty | poprawka danych odbywa się poza aplikacją |
| Zmiana nocna przechodząca przez północ (brak zmian nocnych w strefach) | sesja zamykana o 23:59:59 ([D3](06-decyzje.md#d3-sesja-zamykana-o-235959-dnia-rozpoczęcia)) |
| Uprawnienia per podstrefa | podstrefy dostępne dla każdego z uprawnieniem do strefy ([D8](06-decyzje.md#d8-uprawnienia-na-poziomie-strefy)) |
| Praca skanera bez połączenia | skan bez połączenia przepada z komunikatem „Błąd połączenia” |
| Role w panelu | jeden poziom dostępu: administrator |
| Eksport dowolnego dnia lub miesiąca | eksport tylko dla dziś i bieżącego miesiąca (`app.py:1006-1012`) |
| Retencja danych osobowych | wpisy, alerty i kopie przechowywane bezterminowo |

## Znane problemy — proces i dane

| # | Problem | Gdzie |
|---|---|---|
| P1 | Nadwyżka przerwy powstaje tylko, gdy przerwę zamknie pracownik; przy zamknięciu przez administratora lub automatycznym jest tylko flaga. | `app.py:549` vs `843, 412` |
| P2 | Dwa różne domyślne progi długiego dyżuru: 10 h dla alertu, 12 h dla podglądu Live (gdy brak wpisu w konfiguracji). | `app.py:366` vs `598` |
| P3 | Usunięcie pracownika kasuje jego otwartą sesję bez zapisu wpisu — czas od ostatniego skanu przepada. | `app.py:953-954` |
| P4 | Ponowny skan tej samej strefy rozbija jeden pobyt na dwa wpisy. | `app.py:528-577` |
| P5 | Porównanie z grafikiem bierze pod uwagę tylko zamknięte wpisy — pracownik wciąż w pierwszej strefie dnia ma status „nieobecność”. | `app.py:1142-1170` |
| P6 | Import grafiku dopasowuje nazwisko po fragmencie — przy kilku podobnych nazwiskach wiersz trafi do pierwszego pasującego pracownika, bez ostrzeżenia. | `app.py:180-185` |
| P7 | Nierozpoznany kod zmiany w grafiku jest traktowany jako dzień wolny — literówka ukrywa nieobecność. | `app.py:115` |
| P8 | Porównanie z grafikiem ignoruje obecność w dniu wolnym i nie ocenia wcześniejszego wyjścia. | `app.py:1164-1167` |
| P9 | Alert w panelu trzymany w pamięci serwera: przy dwóch administratorach baner zobaczy tylko jeden; restart serwera kasuje nieodczytane; drugi alert tego samego pracownika nadpisuje pierwszy. | `app.py:357, 622-623` |
| P10 | Dodanie pracownika lub strefy o istniejącej nazwie nadpisuje rekord. | `app.py:944, 902` |
| P11 | Zmiana nazwy strefy jest możliwa tylko przez usunięcie i ponowne dodanie; stare uprawnienia i wpisy zostają ze starą nazwą. | `app.py:905-909` |
| P12 | Czas lokalny serwera bez strefy czasowej — zmiana czasu letni/zimowy zaburza sesje nocne. | `datetime.now()` w całym `app.py` |
| P13 | Import pobranego szablonu grafiku zawsze zgłasza błąd „Wiersz 2: nie znaleziono pracownika 'LEGENDA →'” — szablon wstawia wiersz legendy, a import czyta go jak pracownika. Pozostałe wiersze importują się poprawnie. Pilnuje tego test `test_P13_…`. | `app.py:1055, 172-188` |
| P14 | Dzień zaplanowany, który jeszcze się nie zaczął, ma dziś status „nieobecność” — np. o 08:00 przy zmianie od 13:00. | `app.py:1170` |
| P15 | Nagłówek grafiku z samym numerem dnia trafia do bieżącego miesiąca — grafik na kolejny miesiąc zaimportowany wcześniej nadpisze bieżący. | `app.py:159-163` |
| P16 | Usunięcie pracownika zostawia jego grafik, nadwyżki i korekty ([04](04-model-danych.md) N12). | `app.py:950-954` |
| P17 | Przesunięcie i ręczny start sesji przez administratora nie sprawdzają uprawnień pracownika ani istnienia strefy — serwer przyjmie dowolną nazwę. | `app.py:812-888` |
| P18 | Przekroczona przerwa daje w `alerty.csv` dwa wiersze `DLUGA_PRZERWA`: w trakcie i przy zamknięciu. | `app.py:383, 566` |
| P19 | Kopia zapasowa powstaje tylko, gdy serwer działa między 02:00 a 02:59; stare kopie nie są usuwane. | `app.py:332-352` |
| P20 | Dwóch administratorów może jednocześnie rozliczać tę samą nadwyżkę lub korektę — wygrywa ostatni zapis, bez ostrzeżenia. Docelowo drugi administrator ma zostać zablokowany, dopóki pierwszy edytuje pozycję. | `app.py:783-789, 802-808` |
| P21 | API dashboardu liczy czas per strefa i per pracownik, których interfejs nie wyświetla — pozostałość po usuniętych wykresach. | `app.py:712-724, 757-758` |

## Znane problemy — interfejs

Ślepe ścieżki i akcje bez informacji zwrotnej opisuje [03-user-flow](03-user-flow.md#ślepe-ścieżki-i-akcje-bez-informacji-zwrotnej) (U1–U9).
Najważniejsza: ekran pracownika nie wraca sam do ekranu startowego (U1).

## Znane problemy — bezpieczeństwo

Prototyp nie przeszedł przeglądu bezpieczeństwa. Przed jakimkolwiek wdrożeniem:

| # | Problem | Gdzie |
|---|---|---|
| B1 | Klucz sesji ma wartość domyślną w kodzie, używaną, gdy nie ustawiono zmiennej `RCP_SECRET_KEY`. | `app.py:16` |
| B2 | Konto startowe `admin / admin123` bez wymuszenia zmiany hasła; dane logowania wypisywane w konsoli. | `app.py:314`, `run.py:4, 17` |
| B3 | Migracja starych hashy ustawia hasło `admin123`. | `app.py:319-322` |
| B4 | Podgląd obecności `/api/status` dostępny bez logowania. | `app.py:591` |
| B5 | Przewidywalna treść kodów QR pozwala zarejestrować inną osobę. Przy zgubieniu karty drukowany jest duplikat z tym samym kodem, a kodu nie da się unieważnić — zgubiona karta działa dalej. | `app.py:943` |
| B6 | Brak limitu prób logowania i ochrony CSRF. | `app.py:650-662` |
| B7 | API konfiguracji zapisuje dowolne klucze, a ścieżka kopii zapasowej może wskazywać dowolny katalog serwera. | `app.py:995-1000` |
| B8 | Skan bez logowania zapisuje treść nieznanego kodu do `alerty.csv`. Kod zaczynający się od `=` zostaje formułą po otwarciu pliku w Excelu (CSV injection). | `app.py:441, 248-252` |
| B9 | Dodanie administratora o istniejącym loginie po cichu zmienia hasło tego konta. | `app.py:978` |

## Miejsca bez obsługi błędów i walidacji

| Miejsce | Co się dzieje |
|---|---|
| `app.py:63-67` | uszkodzony plik JSON czytany jak pusty, bez alarmu |
| `app.py:69-71` | zapis JSON bez obsługi błędu i nie atomowy — przerwany zapis uszkadza plik |
| `app.py:148-164, 229, 236, 259, 274, 288-289, 717, 724, 1154, 1184` | `except: pass` — błędy pomijane bez śladu |
| `app.py:359-422` | wątek alertów łapie tylko `OSError`, `KeyError`, `ValueError`; inny wyjątek kończy wątek po cichu — alerty i auto-zamknięcie przestają działać |
| `app.py:351-352` | błąd kopii zapasowej tylko w konsoli serwera |
| `app.py:601, 377, 513, 530, 831, 871` | odczyt dat z plików bez obsługi błędu — uszkodzony wpis sesji daje błąd 500 |
| `app.py:708-709` | data z adresu bez walidacji — zły format daje błąd 500 |
| `app.py:123` | nieprawidłowy plik Excel daje błąd 500; pole wyboru akceptuje `.xls` (`admin.html:388`), którego biblioteka nie czyta |
| `app.py:435, 485, 629` | treść żądania, która nie jest obiektem JSON, daje błąd 500 |
| `app.py:640` | opis korekty bez walidacji po stronie serwera |
| `app.py:784-790, 803-809` | nieistniejące `id` nadwyżki lub korekty zwraca sukces |
| `app.py:960-963` | lista uprawnień bez walidacji typu |
| `app.py:998-999` | konfiguracja bez walidacji zakresów |
| `app.py:1114-1123` | wpis grafiku bez walidacji pracownika i daty |
| `index.html:640-645`; `admin.html:864, 884, 931, 955, 1151` | interfejs nie sprawdza odpowiedzi serwera |
| `admin.html:529-532, 555-557` i pozostałe funkcje `load*` | brak obsługi 401 i błędów sieci |

## Co dalej

Kolejność wynika z wpływu na wiarygodność ewidencji:

1. Powrót ekranu pracownika do startu po bezczynności (U1) i ochrona `/api/status` (B4) — chronią przed rejestracją w cudzym imieniu i wyciekiem obecności.
2. Spójne zamykanie przerw: nadwyżka niezależnie od tego, kto zamknął przerwę (P1).
3. Korekta powiązana z konkretnym wpisem i zmieniająca go po zatwierdzeniu (D6).
4. Wymóg ustawienia `RCP_SECRET_KEY` poza trybem demo i wymuszenie zmiany hasła startowego (B1–B3).
5. Polityka retencji danych osobowych w ewidencji, alertach i kopiach zapasowych — wymagana przed wdrożeniem.
6. Blokada równoczesnej edycji nadwyżki i korekty przez dwóch administratorów (P20).
7. Unieważnianie kodu QR zgubionej karty — dziś duplikat ma ten sam kod (B5).
8. Testy z użytkownikami — prototyp nie był jeszcze sprawdzony na zmianie.
