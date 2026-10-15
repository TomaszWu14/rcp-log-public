# Strategia testów

## Dziś

18 testów akceptacyjnych w `tests/test_wymagania.py` (`unittest`, klient testowy Flask, własny katalog
danych w `tempfile`). Nazwa testu = ID z [archiwum/05](../archiwum/05-wymagania.md); mapa na WF-n
w kolumnie „Test" tabel wymagań w [01-procesy](../01-procesy/). Pokryte 18 z 37 WF — te sprawdzalne
przez API bez zegara i przeglądarki.

## Zasady

| Poziom | Co | Kiedy |
|---|---|---|
| Akceptacyjny (API) | jedno kryterium Given/When/Then = jeden test nazwany ID wymagania | każda historyjka |
| Bezpieczeństwa | „brak dostępu" dla **każdego** endpointu `/admin/api/*` (dziś jeden, WF-28); limit prób; CSRF; blokady `DEMO_BLOCKED` | US-002, US-003 |
| Jednostkowy | logika czysta: `parse_shift`, `fmt_czas`, `get_flaga`, przyszła `zamknij_pobyt()` | od US-005 |
| Ręczny | alerty w tle (60 s), kopia o 02:00, interfejs skanera i panelu | checklista w PR, zrzuty ekranu |
| E2E w przeglądarce | skan → strefa → przerwa → koniec zmiany | po testach z użytkownikami (krok 12) |

Nie testujemy wyglądu ani bibliotek zewnętrznych. Nie wyłączamy testów, żeby „przeszło" — test czerwony
= błąd albo zmiana wymagania z aktualizacją `docs/01-procesy`. Test `test_P13` pilnuje opisu długu T6:
gdy ktoś naprawi import legendy, test ma przestać przechodzić i wtedy usuwamy wpis z dokumentacji.

## Uruchomienie

```bash
python -m unittest discover tests -v
```
