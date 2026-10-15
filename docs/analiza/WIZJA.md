# Wizja

Cel biznesowy, zakres, aktorzy i SIPOC: [00-przeglad](../00-przeglad.md). Ten dokument dodaje
mierniki sukcesu (luka A4).

## Jedno zdanie

Dla lidera zmiany i administratora magazynu, którzy liczą czas pracy w strefach ręcznie w Excelu,
RCP Log jest rejestracją jednym skanem QR, która daje obsadę na żywo i alert o przekroczonej przerwie
w chwili, gdy ona trwa.

## Mierniki sukcesu (propozycja BA, Z25)

| Miernik | Dziś (Excel) | Cel | Jak zmierzyć |
|---|---|---|---|
| Czas rozliczenia zmiany przez lidera | ~30–60 min ręcznego przepisywania (szacunek) | < 5 min (eksport CSV) | pomiar na 5 zmianach po wdrożeniu |
| Opóźnienie wykrycia przekroczonej przerwy | przy rozliczeniu, czyli godziny | ≤ 1 min od przekroczenia progu | `alerty.csv`: ts alertu − (ts wejścia na przerwę + próg) |
| Udział wpisów wymagających korekty | nieznany | < 5% wpisów dnia | korekty zatwierdzone / wpisy w `ewidencja_<dzień>.csv` |
| Czas pojedynczej rejestracji na skanerze | n/d | ≤ 10 s od skanu do potwierdzenia | obserwacja na stanowisku |

Wartości „dziś" są szacunkami z obserwacji procesu — prototyp nie był testowany na zmianie
(krok 12 listy przed wdrożeniem).
