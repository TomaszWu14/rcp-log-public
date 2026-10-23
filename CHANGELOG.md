# Changelog

Format: [Keep a Changelog](https://keepachangelog.com/pl/1.1.0/), wersjonowanie [SemVer](https://semver.org/lang/pl/).

## [Unreleased]

### Added
- Bramka gości wersji demonstracyjnej (`DEMO_VISITOR_GATE`, domyślnie włączona w trybie demo): pierwsza wizyta na stronie
  skanera i w panelu `/admin` wymaga podania imienia, nazwiska i firmy oraz zgody na informację RODO (honeypot, CSRF,
  bezpieczny `next`). `/api/*`, pliki statyczne i `/login` nie są blokowane. Dane w `goscie.csv` (bez IP i user-agenta),
  usuwane po 90 dniach przy zapisie; flaga sesji ważna 30 dni. Lista gości i eksport CSV: `/admin/goscie`
  (konto demo: 404, chyba że `?token=` zgadza się z `VISITORS_TOKEN`, porównanie `hmac.compare_digest`).
- Powiadomienie push (ntfy) o nowym gościu bramki: po udanym zapisie `POST` na `NTFY_URL` (opcjonalnie `NTFY_TOKEN`
  jako `Authorization: Bearer`), w wątku w tle z limitem 5 s; błąd tylko w logu, bez `NTFY_URL` brak ruchu sieciowego
  (`visitor_notify.py`, `urllib` ze stdlib). Klauzula RODO formularza informuje o powiadomieniu przez ntfy.

### Fixed
- Publiczne `/api/scan`, `/api/rejestruj`, `/api/korekta` zwracały 500 na JSON nie będący obiektem lub z polami nie-tekstowymi; teraz 400/403.

### Security
- Limit żądań publicznych `/api/scan`, `/api/rejestruj`, `/api/korekta` (kod pracownika to jedyne uwierzytelnienie):
  20 nieznanych kodów / 10 min i 120 żądań / min z adresu → 429 (adres wg `RCP_PROXY` jak przy logowaniu);
  po przekroczeniu limitu nie jest już zapisywany alert `NIEZNANY_KOD`, więc nie da się zalać listy alertów.
- Obraz Dockera bez `pip` po instalacji zależności — jego dołączone biblioteki (urllib3, certifi, msgpack,
  setuptools) Trivy zgłaszał jako HIGH/CRITICAL i blokowały job `image` (m.in. Dependabot #34, Python 3.14).
- Wspólna podstawa bezpieczeństwa: gitleaks jako przypięte binarium (sha256), Semgrep `p/owasp-top-ten` i Trivy `fs`
  jako bramki CI, pip-audit także dla `requirements-dev.txt`, akcje przypięte do SHA, Dependabot z grupami
  minor+patch (+ docker); nagłówki `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cache-Control: no-store` na JSON.
- US-011: konfiguracja z białą listą kluczy i zakresami, katalog kopii tylko pod `RCP_BACKUP_ROOT`; limit żądania 2 MB
  (413); import grafiku tylko `.xlsx`, uszkodzony plik → 400; nagłówki CSP, `X-Content-Type-Options`, `Referrer-Policy`,
  `X-Frame-Options`, HSTS za proxy (B7, R7, R9).
- US-003: limit prób logowania (5 / 10 min z adresu → 429 na 15 min); token CSRF na formularzach logowania,
  zmiany hasła i imporcie grafiku; ciasteczko sesji `SameSite=Lax`, `HttpOnly`, `Secure` przy `RCP_PROXY=1`;
  pola CSV zaczynające się od `= + - @` lub tabulatora dostają apostrof (B6, B8).
- US-002: `/api/status` (obecność z nazwiskami) wymaga sesji administratora; bez niej 401 z pustym ciałem (B4).
- US-001: poza trybem demo `RCP_SECRET_KEY` jest wymagany (≥ 32 znaki) — brak kończy start błędem; usunięty klucz
  domyślny z kodu (B1). Hasło startowe `admin` z `RCP_ADMIN_PASSWORD` albo losowe wypisane raz w konsoli;
  pierwsze logowanie wymusza zmianę na `/admin/haslo` (B2, B3). `admins.json` trzyma skrót i znacznik zmiany
  (stary format czytany w locie).

### Fixed
- US-010: błędy w tle i przy odczycie plików trafiają do logu (`logging`, logger `rcp`) zamiast `except: pass`;
  wątki kontroli, kopii i demo przeżywają każdy wyjątek przebiegu (`_przebieg`); uszkodzony JSON loguje ERROR
  i działa na wartości domyślnej; kopia zapasowa jako `kopia_zapasowa(now)` z testem; parsowanie dat grafiku
  w `_data_z_naglowka()`. Hasło startowe i komunikaty demo przez logger (stderr).
- US-006: zapis plików JSON przez plik tymczasowy i `os.replace` (przerwany zapis nie uszkadza danych); zgłoszenia
  korekt oraz decyzje o nadwyżkach i korektach pod blokadą — równoczesne zgłoszenia mają różne numery, druga decyzja
  o tej samej pozycji dostaje 409, nieistniejący numer 404 (T12); panel pokazuje komunikat.
- US-005: jedno miejsce zamykania pobytu (`zamknij_pobyt`) — nadwyżka przerwy powstaje także przy zamknięciu przez
  administratora i auto-zamknięciu (T1); wpis automatyczny ma numer i format czasu (T14); jeden próg długiego dyżuru 10 h
  (T2); przesunięcie, ręczny start i przypisanie nadwyżki sprawdzają słownik stref i uprawnienia (T9); usunięty martwy
  filtr `PRZEKROCZENIE_ZMIANY` (T15). Kontrola w tle wydzielona do `kontrola_pobytow()`.
- Odwołania `app.py:linia` w dokumentacji naprawione po podwójnym przeliczeniu w US-003; skrypt blokuje drugi przebieg.

### Added
- US-015: ustawienia retencji (ewidencja, alerty, audyt, kopie) w zakładce Config; 0 = bez usuwania.
- US-009: retencja danych — okresy w konfiguracji (`retencja_*_dni`; ewidencja domyślnie bez usuwania do decyzji IOD),
  usuwanie całych plików ewidencji, wierszy alertów i audytu oraz starych kopii raz na dobę; kopia zapasowa także,
  gdy serwer nie działał o 02:00 (T11).
- US-014: naniesienie zatwierdzonej korekty na wybrany wpis — plik dnia i miesiąca zmieniane razem, oznaczenie
  `KOREKTA#<nr>`, stara i nowa wartość w dzienniku audytu; panel Korekty → „✎ Nanieś” (D12 zmienia D6).
- US-013: zakładka „🧾 Audyt” w panelu — ostatnie 200 wpisów, filtr po loginie / akcji / obiekcie, link do pełnego CSV.
- US-012: dziennik audytu `audyt.csv` (kto, kiedy, co: logowania, zmiana hasła, słowniki, konta, konfiguracja,
  przesunięcia, decyzje, grafik), `/admin/api/audyt`, eksport `/admin/export/audyt`.
- US-007: `docs/bezpieczenstwo/RODO.md` v0.1 — role, cele i podstawy przetwarzania, monitoring (art. 22³ KP),
  minimalizacja, tabela retencji, prawa osób, wpis do rejestru czynności, checklista przed wdrożeniem;
  historyjka US-009 (mechanizm retencji).
- `tools/remap_line_refs.py` — przelicza odwołania `app.py:linia` w dokumentacji po zmianie kodu.
- Proces zespołu BA / DEV / SEC: `CONTRIBUTING.md`, `SECURITY.md`, szablony issue i PR, CODEOWNERS.
- CI (GitHub Actions): ruff, testy, bandit, pip-audit, gitleaks, build obrazu + trivy; Dependabot; pre-commit.
- Dokumenty: `docs/AUDYT.md`, `docs/analiza/` (wizja z miernikami, NFR v0.1, backlog US-001…008, śledzenie,
  założenia Z17–Z25), `docs/bezpieczenstwo/` (klasyfikacja danych, threat model STRIDE, rejestr ryzyk R1–R10),
  `docs/architektura/` (C4 kontenery, ADR 0012), `docs/testy/`, `docs/operacje/`.

### Changed
- Zależności przypięte do dokładnych wersji (`requirements.txt`); narzędzia deweloperskie w `requirements-dev.txt`.
- `demo_data.py`: usunięty nieużywany import i zmienna (lint).

## [0.2.0] — 2026-10-14

- Tryb demo (`RCP_DEMO=1`) z fikcyjnymi danymi, Dockerfile i compose, publiczna instancja na Coolify (PR #10, #12).
- Dokumentacja przedwdrożeniowa `docs/00–05`: procesy P1–P7, BR-1–58, WF-1–37, ustalenia Z1–Z16 (PR #13);
  logo i film (PR #11).

## [0.1.0] — 2026-10-13

Prototyp z pierwszą dokumentacją analityczną (dziś `docs/archiwum/`) i 18 testami akceptacyjnymi (PR #9).
