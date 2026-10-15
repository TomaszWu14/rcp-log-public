## Co i dlaczego

<!-- 1–3 zdania. Link do historyjki: docs/analiza/HISTORYJKI.md#us-xxx -->

Historyjka: US-

## Jak przetestować

<!-- komendy albo kroki w UI; zrzut ekranu, jeśli zmienia się interfejs -->

## Przegląd [BA]

- [ ] kryteria akceptacji sprawdzone punkt po punkcie
- [ ] komunikaty i UI zrozumiałe dla pracownika / administratora
- [ ] `docs/analiza/SLEDZENIE.md` zaktualizowane (wymaganie → historyjka → test → PR)

## Przegląd [DEV]

- [ ] test na każde kryterium akceptacji, `python -m unittest discover tests` zielone
- [ ] `ruff check .` zielone
- [ ] dokumentacja zaktualizowana (05-wymagania / API / model danych / ADR / CHANGELOG)

## Przegląd [SEC]

- [ ] uwierzytelnianie i autoryzacja sprawdzane po stronie serwera (test „brak dostępu” dla nowego endpointu)
- [ ] walidacja wejścia, escapowanie wyjścia, brak CSV injection
- [ ] brak sekretów, danych osobowych i danych produkcyjnych w diffie, testach i logach
- [ ] `bandit`, `pip-audit`, `gitleaks` zielone; fałszywe alarmy opisane, nie wyciszone hurtowo
- [ ] nowe ryzyko wpisane do `docs/bezpieczenstwo/RYZYKA.md`, jeśli coś zostaje otwarte

Wynik SEC: ✅ / ⚠️ uwagi / ❌ blokada —

## Ryzyka i decyzje PO

<!-- co zostaje otwarte; czego potrzebujesz od Product Ownera -->
