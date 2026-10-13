# RCP Log

Rejestracja czasu pracy w strefach magazynu jednym skanem kodu QR — dla pracowników zmiany
i administratora, który do tej pory liczył ten czas ręcznie w Excelu.

![demo](docs/screenshots/demo.gif)

📹 Prezentacja wideo (2 min) — w przygotowaniu.

**Demo bez logowania:** <DO UZUPEŁNIENIA: adres instancji na Render> — dane fikcyjne, odtwarzane co 30 min. Lokalnie: [tryb demo](#tryb-demo).

## Problem → rozwiązanie

Na zmianie pracuje około 60 osób w około 15 strefach: kompletacja, przyjęcia, wysyłka, przerwa.
Czas w strefach lider wpisuje ręcznie do Excela, więc nikt nie wie na bieżąco, kto jest gdzie,
a przekroczoną przerwę widać dopiero przy rozliczeniu.
RCP Log zastępuje arkusz jednym skanem: każdy skan zamyka poprzedni pobyt i otwiera nowy,
administrator widzi obsadę na żywo, a przerwa ponad próg wywołuje alert i trafia na listę do rozliczenia.

## Dokumentacja analityczna

| Dokument | Zawartość |
|---|---|
| [01. Problem i zakres](docs/01-problem-i-zakres.md) | problem, interesariusze, co jest w zakresie, a co poza nim i dlaczego |
| [02. Proces](docs/02-proces.md) | proces przed i po wdrożeniu, aktorzy, punkty decyzyjne — diagramy Mermaid |
| [03. User flow](docs/03-user-flow.md) | mapa 12 ekranów i okien oraz 11 zakładek panelu, przejścia, ścieżki alternatywne i ślepe |
| [04. Model danych](docs/04-model-danych.md) | ERD, opis encji, słowniki wartości, reguły integralności i znane niespójności |
| [05. Wymagania](docs/05-wymagania.md) | 38 wymagań z kryteriami akceptacji, wskazaniem miejsca w kodzie i mapą testów automatycznych |
| [06. Decyzje](docs/06-decyzje.md) | dziennik 9 decyzji projektowych: kontekst, alternatywy, uzasadnienie, skutki |
| [07. Ograniczenia](docs/07-ograniczenia.md) | czego aplikacja nie robi, znane problemy, miejsca bez walidacji, dalsze kroki |

## Jak uruchomić

Wymagany Python 3.11 lub nowszy.

Windows (PowerShell lub cmd):

```powershell
git clone https://github.com/TomaszWu14/rcp-log-public.git
cd rcp-log-public
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python run.py
```

Linux / macOS:

```bash
git clone https://github.com/TomaszWu14/rcp-log-public.git
cd rcp-log-public
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run.py
```

Po starcie:

| Adres | Co to jest |
|---|---|
| http://localhost:5050/ | skaner — wpisz `HU_KOWALSKI_JAN` i naciśnij Enter |
| http://localhost:5050/admin | panel administratora — login `admin`, hasło `admin123` |

Przy pierwszym uruchomieniu aplikacja sama tworzy katalog `data/` ze strefami, trzema przykładowymi
pracownikami (`HU_KOWALSKI_JAN`, `HU_NOWAK_ANNA`, `HU_WISNIEWSKI_PIOTR`) i kontem administratora.
Katalog `data/` nie jest wersjonowany.

### Tryb demo

Zmienna `RCP_DEMO=1` uruchamia aplikację do pokazu:

- panel administratora otwiera się bez logowania,
- [`demo_data.py`](demo_data.py) generuje 12 fikcyjnych pracowników, ewidencję z 10 dni roboczych, trwającą zmianę
  z przekroczoną przerwą, nadwyżki przerw, korekty do zatwierdzenia i grafik ze spóźnieniem i nieobecnością,
- dane leżą w osobnym katalogu `data_demo/` i są odtwarzane co `RCP_DEMO_RESET_MIN` minut (domyślnie 30),
- dodawanie i usuwanie stref, pracowników i adminów, zmiana konfiguracji i import grafiku są zablokowane.

```bash
RCP_DEMO=1 .venv/bin/python run.py          # Linux / macOS
```

```powershell
$env:RCP_DEMO = "1"; .venv\Scripts\python run.py   # Windows (PowerShell)
```

Publiczną instancję opisuje [`render.yaml`](render.yaml): w [Render](https://render.com) wybierz
**New → Blueprint** i wskaż to repozytorium. Darmowy plan usypia usługę bez ruchu — pierwsze wejście
budzi ją w około minutę.

| Zmienna | Znaczenie |
|---|---|
| `RCP_DEMO` | `1` włącza tryb demo |
| `RCP_DEMO_RESET_MIN` | co ile minut odtworzyć dane demo (domyślnie 30) |
| `RCP_SECRET_KEY` | klucz podpisu sesji; bez niej używana jest wartość z kodu |
| `PORT` | port serwera (domyślnie 5050) |

Testy akceptacyjne (18 testów nazwanych ID wymagań, bez dodatkowych zależności):

```bash
python -m unittest discover tests
```

## Struktura repozytorium

```
app.py              cała logika i API (Flask) — świadomie jeden plik, patrz D1
run.py              start produkcyjny (Waitress)
demo_data.py        generator fikcyjnych danych dla trybu demo
render.yaml         konfiguracja publicznego demo na Render
templates/          skaner (index.html), panel (admin.html), logowanie
tests/              testy akceptacyjne wymagań z docs/05
docs/               dokumentacja analityczna 01–07 i zrzuty ekranu
data/               tworzony przy starcie: JSON i CSV z danymi (poza repozytorium)
data_demo/          dane trybu demo, odtwarzane automatycznie (poza repozytorium)
```

## Stack i dlaczego taki

| Element | Dlaczego |
|---|---|
| **Python 3.11 + Flask** | cała logika i API mieszczą się w jednym pliku (`app.py`) — przy prototypie liczy się czas od pomysłu do sprawdzenia procesu |
| **Waitress** | produkcyjny serwer WSGI, który działa także na Windowsie (`run.py`) |
| **Pliki JSON i CSV zamiast bazy** | zero infrastruktury; ewidencja zapisywana jest jako CSV z separatorem `;` i BOM, więc otwiera się wprost w Excelu, którego używano wcześniej — szczegóły i koszty tej decyzji w [D1](docs/06-decyzje.md#d1-pliki-json-i-csv-zamiast-bazy-danych) |
| **openpyxl** | grafik zmian przychodzi w Excelu — aplikacja generuje szablon `.xlsx` i importuje wypełniony plik |
| **HTML, CSS i JavaScript bez frameworka** | skaner działa w dowolnej przeglądarce na stanowisku, bez kroku budowania frontendu |

## Zakres i ograniczenia

W zakresie: rejestracja wejść do stref i przerw, uprawnienia do stref, alerty przerw i długich dyżurów,
korekty, podgląd na żywo, grafik i porównanie z obecnością, eksport CSV, kopia zapasowa.

Poza zakresem: naliczanie wynagrodzeń i integracja z systemem kadrowym, automatyczna poprawka ewidencji
po zatwierdzeniu korekty, zmiana nocna przez północ, praca skanera offline.

To prototyp, który nie przeszedł przeglądu bezpieczeństwa (m.in. klucz sesji w kodzie, domyślne hasło
administratora). Pełna lista: [07. Ograniczenia](docs/07-ograniczenia.md).

## Kontekst projektu

Projekt powstał z problemu, który zauważyłem w swojej pracy w magazynie: czas w strefach liczono w Excelu
na podstawie ręcznych wpisów lidera zmiany. Z własnej inicjatywy przygotowałem prototyp, który ten proces zastępuje.

Odpowiadałem za całość — od analizy do działającego rozwiązania:

- **analiza procesu i wymagań** — wymagania zebrane od kierownika magazynu i lidera zmiany oraz z własnej obserwacji procesu,
- **projekt ekranów i modelu danych**,
- **implementacja**,
- **testy akceptacyjne** wymagań.

Prototyp nie był jeszcze testowany z użytkownikami na zmianie — to następny krok.

Od pomysłu do działającego prototypu minął około miesiąc. Repozytorium nie zawiera danych ani nazwy firmy —
wszystkie dane są przykładowe.

## Licencja

[MIT](LICENSE)
