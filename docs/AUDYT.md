# Audyt stanu wyjściowego

Data: 2026-10-15 · Stan kodu: `main` po PR #13 (commit `d79ffe0`) · Wynik testów: 18/18 OK
(`python -m unittest discover tests`).

Audyt otwiera pracę w trybie zespołu BA / DEV / SEC. Nie powtarza dokumentacji `00–05` — odwołuje się
do niej i dopisuje to, czego tam brakuje. Identyfikatory T1–T15 (dług techniczny), B1–B9 (bezpieczeństwo)
i lista „przed wdrożeniem" pochodzą z [05-decyzje-i-ograniczenia](05-decyzje-i-ograniczenia.md),
ustalenia Z1–Z16 z [00-przeglad](00-przeglad.md#ustalenia-potwierdzone).

---

## [BA] Analiza biznesowa

### Co aplikacja robi

Rejestruje czas pracy w strefach magazynu jednym skanem kodu QR; administrator widzi obsadę na żywo,
dostaje alerty, rozlicza nadwyżki przerw i korekty, porównuje grafik z obecnością, eksportuje CSV.
Procesy P1–P7: [01-procesy](01-procesy/), 37 wymagań WF z Given/When/Then, 58 reguł BR.
Publiczne demo z danymi fikcyjnymi: [rcp.log.twapp.pl](https://rcp.log.twapp.pl) (D11).

### Co już jest dobre

- Procesy w BPMN z torami aktorów, SIPOC, reguły biznesowe i wymagania w formie historyjek z kryteriami
  Given/When/Then — to, czego zwykle brakuje w prototypach.
- 16 ustaleń potwierdzonych z właścicielem projektu (Z1–Z16) zamiast domysłów.
- Dziennik 11 decyzji z alternatywami, uczciwy dług techniczny T1–T15 i lista 12 kroków przed wdrożeniem.
- 18 testów nazwanych ID wymagań.

### Luki w wymaganiach

| # | Luka | Dlaczego ważne |
|---|---|---|
| A1 | Brak wymagań niefunkcjonalnych: czas odpowiedzi skanu, równoczesność stanowisk, trwałość zapisu, odtworzenie po awarii. | Bez NFR nie da się ocenić, czy pliki JSON/CSV (D1) wystarczą przy ~60 osobach na zmianie. → [WYMAGANIA](analiza/WYMAGANIA.md) |
| A2 | WF-1–37 nie mają priorytetów MoSCoW ani statusu realizacji; lista „przed wdrożeniem" ma kolejność, ale nie jest backlogiem z kryteriami. | Nie widać, co blokuje wydanie. → [HISTORYJKI](analiza/HISTORYJKI.md) |
| A3 | Brak wymagań RODO: podstawa przetwarzania, informacja dla pracowników, retencja (poza kopiami — Z7). Ewidencja miejsca i czasu pracy to dane osobowe i potencjalnie monitoring pracownika. Wdrożenie produkcyjne jest planowane (Z16), więc to Must, nie opis. | → `bezpieczenstwo/RODO.md` (US-007) |
| A4 | Brak mierników sukcesu: o ile ma spaść czas rozliczenia zmiany, ile korekt jest akceptowalne. | Nie da się stwierdzić, że prototyp rozwiązał problem. → [WIZJA](analiza/WIZJA.md) |
| A5 | Macierz śledzenia kończy się na teście (kolumna w tabelach WF) — brak historyjki i PR. | → [SLEDZENIE](analiza/SLEDZENIE.md) |
| A6 | Progi (Z4) nadal otwarte — wartości robocze bez potwierdzenia z kierownikiem magazynu. | Kryteria akceptacji WF-12, WF-13 opierają się na liczbach, które mogą się zmienić. |

---

## [DEV] Kod, testy, architektura

| # | Ustalenie | Waga | Gdzie |
|---|---|---|---|
| DEV-1 | ~~Logika zamykania pobytu skopiowana trzykrotnie~~ — **naprawione w US-005**: `zamknij_pobyt()` + `sprawdz_strefe()`; kontrola w tle wydzielona do `kontrola_pobytow()` i przetestowana. | ~~wysoka~~ | `app.py:415-463, 529-579` |
| DEV-2 | ~~Zapisy JSON nieatomowe; korekty i nadwyżki bez blokady~~ — **naprawione w US-006**: `_w()` przez plik tymczasowy + `os.replace`; zgłoszenia i decyzje pod `_lock`, druga decyzja → 409. Zostaje brak logowania błędów (DEV-3). | ~~wysoka~~ | `app.py:144-153, 757, 938, 958` |
| DEV-3 | ~~17 miejsc `except: pass`; wątek alertów ginął po cichu~~ — **naprawione w US-010**: `logging` (logger `rcp`), `_przebieg()` dla zadań w tle, wyjątki zawężone do oczekiwanych typów; ruff bez wyjątków. | ~~średnia~~ | `app.py:24-25, 496-503` |
| DEV-4 | Efekty uboczne przy imporcie modułu: tworzenie katalogów, plików startowych, 2–3 wątków (D10). Wiele procesów = zdublowane alerty. | średnia | `app.py:65, 491, 524, 586` |
| DEV-5 | Jeden plik ~1350 linii (D1) i `admin.html` z całym JS inline. OK dla prototypu; podział na moduły, gdy pojawi się druga domena. Reguły ruff spłacone w całości (US-005, US-010). | niska | `app.py`, `templates/admin.html` |
| DEV-6 | Zależności były nieprzypięte (`>=`) — **naprawione w tym PR** (`requirements.txt`, `requirements-dev.txt`). | — | — |
| DEV-7 | Brak CI, lintera, pre-commit — **naprawione w tym PR** (ruff, unittest, bandit, pip-audit, gitleaks, trivy). | — | `.github/workflows/ci.yml` |
| DEV-8 | Konfiguracja przez env: `RCP_SECRET_KEY`, `RCP_ADMIN_PASSWORD`, `PORT`, `RCP_DEMO*`; ścieżki danych i kopii nadal w kodzie/konfiguracji. Dockerfile: slim, użytkownik bez roota, healthcheck — dobrze. | niska | `app.py:28-40, 397-404`, `Dockerfile` |
| DEV-9 | Brak CHANGELOG i CONTRIBUTING — **dodane w tym PR**. | — | — |
| DEV-10 | Martwy kod: sumy dashboardu (T13); ~~alert `PRZEKROCZENIE_ZMIANY`~~ usunięty (US-005). | niska | `app.py:870-879` |

Testy: 18 akceptacyjnych (`unittest`, bez zależności). Brakuje testów jednostkowych logiki czystej
(`parse_shift`, `fmt_czas`, `get_flaga`), testu „brak dostępu" dla **każdego** endpointu `/admin/api/*`
(dziś jeden, WF-28) i testu trybu demo (blokady `DEMO_BLOCKED`).

---

## [SEC] Najważniejsze ryzyka (top 10)

Skala: **krytyczna** — przejęcie panelu lub danych bez wiedzy; **wysoka** — wyciek danych osobowych
albo fałszowanie ewidencji; **średnia** — wymaga dodatkowego warunku; **niska** — ograniczony wpływ.
Klasyfikacja danych: [KLASYFIKACJA_DANYCH](bezpieczenstwo/KLASYFIKACJA_DANYCH.md). Instancja demo
przetwarza wyłącznie dane fikcyjne, więc ryzyka poniżej dotyczą **planowanej instancji produkcyjnej** (Z16).

| # | Ryzyko | Waga | Źródło | Zalecenie |
|---|---|---|---|---|
| R1 | ~~Klucz sesji z wartością domyślną w kodzie~~ — **naprawione w US-001**: poza demo brak `RCP_SECRET_KEY` = błąd startu. | ~~krytyczna~~ | B1 | zamknięte |
| R2 | ~~Konto `admin/admin123` bez wymuszenia zmiany; migracja hashy ustawiała to samo hasło~~ — **naprawione w US-001**: hasło startowe z env lub losowe wypisane raz, zmiana wymuszona przy pierwszym logowaniu. | ~~krytyczna~~ | B2, B3 | zamknięte |
| R3 | ~~`/api/status` bez logowania zwracał nazwiska obecnych, strefę i godzinę wejścia~~ — **naprawione w US-002**: bez sesji 401 z pustym ciałem. | ~~wysoka~~ | B4 | zamknięte |
| R4 | Kody QR przewidywalne (`HU_NAZWISKO_IMIE`), zgubiona karta dostaje duplikat z tym samym kodem (Z3) — rejestracja w cudzym imieniu. | **wysoka** | B5 | losowy token na karcie, unieważnianie |
| R5 | ~~Brak limitu prób logowania~~ — **naprawione w US-003**: 5 prób / 10 min z adresu → blokada 15 min. | ~~wysoka~~ | B6 | zamknięte |
| R6 | ~~CSRF formularzy; cookie bez `SameSite`/`Secure`~~ — **naprawione w US-003**: token na formularzach i imporcie, `SameSite=Lax`, `HttpOnly`, `Secure` za proxy (`RCP_PROXY=1`); wylogowanie GET zostaje (skutek: tylko wylogowanie). | ~~średnia~~ | B6 | zamknięte |
| R7 | ~~Konfiguracja przyjmowała dowolne klucze; `backup_path` dowolny katalog~~ — **naprawione w US-011**: biała lista, zakresy, katalog kopii pod `RCP_BACKUP_ROOT`. | ~~średnia~~ | B7 | zamknięte |
| R8 | ~~CSV injection przez nieznany kod~~ — **naprawione w US-003**: apostrof przed `= + - @` i tabulatorem we wszystkich zapisach CSV. | ~~średnia~~ | B8 | zamknięte |
| R9 | ~~Brak `MAX_CONTENT_LENGTH` i walidacji xlsx; brak nagłówków~~ — **naprawione w US-011**: limit 2 MB (413), tylko `.xlsx` z obsługą uszkodzonych plików, CSP / nosniff / Referrer-Policy / X-Frame-Options, HSTS za proxy. Zostaje: nasłuch `0.0.0.0` (zamierzony) i demo bez limitu żądań (wyjątek w rejestrze). CSP dopuszcza inline (R13). | ~~średnia~~ | nowe | zamknięte |
| R10 | Brak retencji (poza kopiami, Z7) i dziennika audytu operacji administratora (poza `korekta_info`). Polityka opisana w [RODO.md](bezpieczenstwo/RODO.md) (US-007); mechanizm — US-009. | **średnia** | A3 | US-009, audit log |

Poza top 10 (niska): nazwy pracowników bez `escHtml` w trzech miejscach panelu (`admin.html:688, 740, 1229`;
w 740 wewnątrz `onclick` — apostrof w nazwisku psuje przycisk); dane tylko od administratora, więc self-XSS.
Pozytywnie: opis korekty i kod ze skanu są escapowane; hasła hashowane; eksport ze stałej listy plików
(brak path traversal); demo z losowym kluczem sesji i osobnym katalogiem danych; Dockerfile bez roota.

**Weto SEC:** zdjęte 2026-10-15 — R1, R2 (US-001) i R3 (US-002) zamknięte. Przed instancją produkcyjną (Z16)
pozostają warunki z listy „przed wdrożeniem" w [05](05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym),
w szczególności retencja (US-007) i walidacja na serwerze (R7, T9). Demo publiczne jest w porządku,
dopóki zawiera wyłącznie dane fikcyjne.

---

## Backlog

Historyjki US-001…US-008 z priorytetami w [HISTORYJKI](analiza/HISTORYJKI.md). Kolejność zgodna z listą
„przed wdrożeniem" z [05](05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym)
(założenie Z21).
