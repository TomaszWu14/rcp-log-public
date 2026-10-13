# 05. Wymagania

Wymagania odtworzone z działającej aplikacji. Każde ma kryterium akceptacji, które da się sprawdzić
ręcznie na ekranie albo zapytaniem do API, oraz wskazanie miejsca realizacji.
Domyślne progi pochodzą z `app.py:52-58` i można je zmienić w zakładce Config.

Kryteria oznaczone w kolumnie ID symbolem 🧪 sprawdza test automatyczny — patrz [Testy akceptacyjne](#testy-akceptacyjne).

Funkcje, których aplikacja nie ma, są w [01-problem-i-zakres](01-problem-i-zakres.md#poza-zakresem)
i [07-ograniczenia](07-ograniczenia.md), nie tutaj.

## Rejestracja (skaner)

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| REJ-01 🧪 | Pracownik identyfikuje się kodem QR. | Skan lub wpisanie `hu_kowalski_jan` (małymi literami, ze spacjami na brzegach) otwiera ekran pracownika Kowalski Jan. | `app.py:433-481`, `index.html:413-432` |
| REJ-02 🧪 | Nieznany kod jest odrzucany i odnotowany. | Skan `HU_NIEMA` pokazuje „Nieznany kod QR. Skontaktuj się z liderem.”, ekran zostaje na starcie, w `alerty.csv` pojawia się wiersz typu `NIEZNANY_KOD`. | `app.py:440-442` |
| REJ-03 🧪 | Pracownik widzi i może wybrać tylko przypisane mu strefy. | Pracownik z uprawnieniami PICKING i PRZERWA widzi dokładnie dwa kafelki. Wysłanie do API strefy spoza listy zwraca 403 „Brak uprawnień do strefy X”. | `app.py:451-458, 501-503` |
| REJ-04 | Strefa może mieć podstrefy; wybór podstrefy jest opcjonalny. | Kliknięcie strefy z podstrefami otwiera listę podstref z opcją „Bez podstrefy”; strefa bez podstref przechodzi od razu do potwierdzenia. | `index.html:485-516` |
| REJ-05 | Każdy wybór wymaga potwierdzenia. | Po wyborze strefy pojawia się „Potwierdź przejście do strefy…”; „Wróć” nie zapisuje niczego. | `index.html:521-568` |
| REJ-06 🧪 | Zbyt szybka zmiana strefy wymaga dodatkowego potwierdzenia. | Zmiana strefy po mniej niż 5 min od wejścia pokazuje „Byłeś w X tylko mm:ss. Na pewno zmieniasz strefę?”; dopiero „Tak, zmień strefę” zapisuje zmianę. | `app.py:509-520`, `index.html:556-573` |
| REJ-07 🧪 | Pracownik kończy zmianę jednym przyciskiem. | „Koniec zmiany” → potwierdzenie → ekran „Zmiana zakończona” z łącznym czasem dnia; pracownik znika z podglądu Live. | `app.py:571-583` |
| REJ-08 | Pracownik widzi swój bieżący stan. | Ekran pracownika pokazuje bieżącą strefę i podstrefę, czas w strefie (aktualizowany co sekundę) i „Dziś” — sumę **zamkniętych** pobytów z dzisiejszego pliku ewidencji; bieżący pobyt nie jest w niej wliczony. | `app.py:460-481`, `index.html:392-400, 434-462` |

## Sesje i ewidencja

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| SES-01 🧪 | Pracownik ma najwyżej jedną otwartą sesję. | Po wejściu do PICKING, a potem do PRZYJECIA, podgląd Live pokazuje pracownika raz, w PRZYJECIA. | `app.py:522-577` |
| SES-02 🧪 | Zamknięcie sesji tworzy wpis ewidencji. | Po zmianie strefy w `ewidencja_<dzień>.csv` i `ewidencja_<miesiąc>.csv` pojawia się wiersz z poprzednią strefą, godziną wejścia, godziną wyjścia równą chwili skanu i czasem w minutach. | `app.py:529-547, 217-222` |
| SES-03 🧪 | Ewidencja otwiera się poprawnie w Excelu. | Plik CSV ma separator `;` i kodowanie UTF-8 z BOM; polskie znaki w nazwiskach wyświetlają się poprawnie po dwukliku. | `app.py:212-222` |
| SES-04 | Sesja nie przechodzi na kolejny dzień. | Sesja otwarta wczoraj jest w ciągu minuty po północy zamknięta na 23:59:59 dnia wejścia, z flagą `AUTO_ZAMKNIETO` i alertem. | `app.py:396-418` |
| SES-05 | System ostrzega o zbyt długim pobycie w jednej strefie. | Sesja trwająca ponad 10 h generuje jeden alert `DLUGI_DYZUR`; w Live wiersz ma oznaczenie „DŁUGI DYŻUR”. | `app.py:388-394, 598-613` |

## Przerwy

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| PRZ-01 | Administrator dowiaduje się o przekroczonej przerwie, gdy ona trwa. | Po 30 min w strefie PRZERWA w ciągu minuty pojawia się alert `DLUGA_PRZERWA`, a w otwartym panelu w ciągu 20 s baner i sygnał dźwiękowy. Baner pojawia się raz na sesję; w `alerty.csv` przekroczona przerwa daje dwa wiersze: w trakcie i przy zamknięciu z nadwyżką (`app.py:566`). | `app.py:379-386, 618-624`, `admin.html:469-490` |
| PRZ-02 🧪 | Przekroczona przerwa jest oznaczona w ewidencji. | Wpis przerwy dłuższej niż 30 min ma flagę `DLUGA_PRZERWA`. | `app.py:292-297` |
| PRZ-03 🧪 | Nadwyżka przerwy trafia do rozliczenia. | Zakończenie przerwy 42 min przez pracownika tworzy w zakładce Przerwy pozycję z nadwyżką 12 min i statusem „oczekuje”; pracownik widzi na ekranie potwierdzenia ramkę z czasem przerwy i nadwyżką. | `app.py:549-569`, `index.html:588-593` |
| PRZ-04 | Administrator przypisuje nadwyżkę do strefy. | „Przypisz strefę” → wybór strefy → „Zapisz” zmienia status na strefę przypisaną; licznik przy zakładce Przerwy maleje. | `app.py:778-790`, `admin.html:754-774` |

## Korekty

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| KOR-01 | Pracownik zgłasza korektę opisem tekstowym. | „Zgłoś korektę wpisu” → opis → kod pracownika → zgłoszenie pojawia się w zakładce Korekty ze statusem „oczekuje”. Pusty opis jest odrzucany komunikatem „Opisz problem”. | `app.py:627-645`, `index.html:599-618` |
| KOR-02 🧪 | Zgłosić korektę może tylko znany pracownik. | Zgłoszenie z kodem spoza słownika jest odrzucane przez serwer (403) i nie trafia do listy. | `app.py:631-633` |
| KOR-03 | Administrator zatwierdza lub odrzuca korektę. | ✓ zmienia status na „zatwierdzona”, ✕ na „odrzucona”; przyciski znikają. | `app.py:798-809`, `admin.html:824-849` |

## Panel administratora

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| ADM-01 🧪 | Panel jest dostępny tylko po zalogowaniu. | Wejście na `/admin` bez sesji przekierowuje do logowania; API panelu bez sesji zwraca 401; złe hasło pokazuje „Nieprawidłowy login lub hasło”. | `app.py:650-672`, `is_admin()` w każdym endpointcie `/admin/api/*` |
| ADM-02 | Dashboard pokazuje stan dnia. | Dla wybranej daty widać: aktywne sesje, osoby na przerwie, przekroczone przerwy, liczbę wpisów; per strefa — liczbę osób teraz i łączny czas dnia. | `app.py:705-764` |
| ADM-03 | Podgląd Live pokazuje, kto jest gdzie i od kiedy. | Tabela odświeża się co 20 s; wiersze z alertem są na górze. | `app.py:591-616`, `admin.html:555-608` |
| ADM-04 | Administrator może przesunąć pracownika lub zakończyć mu zmianę. | „Przesuń” do innej strefy zamyka bieżącą sesję wpisem z `korekta_info = ADMIN:<login>` i otwiera nową. | `app.py:812-852` |
| ADM-05 | Administrator może uruchomić sesję bez skanu. | „Dodaj ręcznie” tworzy sesję widoczną w Live; ewentualna wcześniejsza sesja jest zamknięta wpisem z `ADMIN:<login>:start_override`. | `app.py:854-888` |
| ADM-06 | Historia wpisów z filtrami. | Filtr dat, pracownika i strefy zwraca najnowsze wpisy, maksymalnie 500. | `app.py:681-702` |
| ADM-07 🧪 | Administrator zarządza słownikami. | Dodanie pracownika z kodem bez prefiksu `HU_` zwraca błąd „Kod musi zaczynać się od HU_”; nowa strefa jest widoczna na skanerze przy kolejnym skanie pracownika, któremu nadano do niej uprawnienie. | `app.py:890-964` |
| ADM-08 | Uprawnienia można nadawać hurtowo. | W Macierzy uprawnień zaznaczenie kolumny i „Zapisz wszystkie uprawnienia” zmienia uprawnienia widocznych pracowników; zapis obejmuje wszystkich pracowników z macierzy. | `admin.html:1175-1316` |
| ADM-09 🧪 | Administrator zarządza kontami administratorów. | Można dodać konto; nie można usunąć konta, na którym jest się zalogowanym. | `app.py:966-987` |
| ADM-10 | Progi są konfigurowalne. | Zmiana progu przerwy na 20 min w Config sprawia, że kolejna przerwa 25 min dostaje flagę `DLUGA_PRZERWA`. | `app.py:989-1000`, `admin.html:983-1002` |

## Grafik

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| GRF-01 | Szablon grafiku do pobrania. | „Pobierz szablon” zwraca plik `.xlsx` z kolumną „Pracownik”, dniami bieżącego miesiąca i legendą R / P / N / W. | `app.py:1022-1070` |
| GRF-02 🧪 | Import grafiku z Excela. | Import wypełnionego szablonu pokazuje liczbę wpisów i pracowników; wiersze z nieznanym nazwiskiem są wylistowane jako błędy. Kody R, P, N i zakresy `05-13` lub `05:00-13:00` są rozpoznawane. | `app.py:97-196, 1073-1089` |
| GRF-03 | Ręczna edycja grafiku. | Kliknięcie komórki i wpisanie `P` zmienia dzień na 13:00–21:00. | `app.py:1110-1124`, `admin.html:1147-1155` |
| GRF-04 🧪 | Porównanie planu z obecnością. | Dla zaplanowanego dnia: pierwszy **zamknięty** wpis ewidencji zaczęty do 15 min po początku zmiany = „na czas”, później = „spóźnienie” z liczbą minut, brak wpisu w dniu minionym lub bieżącym = „nieobecność”; nad tabelą widać podsumowanie. | `app.py:1127-1187` |

## Eksport, kopie i bezpieczeństwo

| ID | Wymaganie | Kryterium akceptacji | Gdzie zrealizowane |
|---|---|---|---|
| EKS-01 | Eksport ewidencji i alertów. | Przyciski „CSV dziś”, „CSV mies.” i „Alerty” pobierają odpowiednie pliki. | `app.py:1003-1016` |
| SYS-01 | Codzienna kopia zapasowa. | Jeśli serwer działa między 02:00 a 02:59, w katalogu z ustawień pojawia się jedna na dobę kopia wszystkich plików CSV i JSON z prefiksem daty i godziny. | `app.py:330-354` |
| SYS-02 🧪 | Hasła administratorów nie są przechowywane jawnie. | `admins.json` zawiera hash werkzeug, nie hasło. | `app.py:276-277, 978` |
| SYS-03 🧪 | Aplikacja startuje bez ręcznego przygotowania danych. | Pierwsze uruchomienie w pustym katalogu tworzy `data/` ze strefami, trzema przykładowymi pracownikami i kontem `admin`. | `app.py:300-327` |

## Testy akceptacyjne

Plik [`tests/test_wymagania.py`](../tests/test_wymagania.py), uruchomienie jedną komendą:

```
python -m unittest discover tests
```

Nazwa testu zaczyna się od ID wymagania. Testy pokrywają 18 z 38 wymagań — te, które da się sprawdzić
przez API bez przeglądarki i bez czekania na zegar (alerty w tle, kopia o 02:00 i interfejs zostały
do sprawdzenia ręcznie według kryteriów z tabel).

| Test | Wymaganie |
|---|---|
| `test_REJ_01_…` | REJ-01 |
| `test_REJ_02_…` | REJ-02 |
| `test_REJ_03_…` | REJ-03 |
| `test_REJ_06_…` | REJ-06 |
| `test_REJ_07_…` | REJ-07 |
| `test_SES_01_…` | SES-01 |
| `test_SES_02_…` | SES-02 |
| `test_SES_03_…` | SES-03 |
| `test_KOR_02_…` | KOR-02 |
| `test_ADM_01_…` | ADM-01 |
| `test_ADM_07_…` | ADM-07 |
| `test_ADM_09_…` | ADM-09 |
| `test_GRF_02_…` | GRF-02 |
| `test_GRF_04_…` | GRF-04 |
| `test_SYS_02_…` | SYS-02 |
| `test_SYS_03_…` | SYS-03 |
| `test_PRZ_02_PRZ_03_…` | PRZ-02, PRZ-03 |
| `test_P13_…` | znany problem P13 z [07-ograniczenia](07-ograniczenia.md) — test pilnuje, żeby opis zgadzał się z działaniem |
