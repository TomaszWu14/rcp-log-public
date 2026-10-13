# 02. Proces biznesowy

## Aktorzy

| Aktor | Kanał | Co robi |
|---|---|---|
| Pracownik magazynu | ekran skanera `/` | rejestruje wejście do strefy, przerwę, koniec zmiany; zgłasza korektę |
| Administrator | panel `/admin` | monitoruje obsadę, reaguje na alerty, rozlicza nadwyżki i korekty, zarządza słownikami i grafikiem, eksportuje dane |
| System | zadania w tle (`app.py:332-424`) | co minutę sprawdza alerty i zamyka sesje z poprzedniego dnia; o 02:00 robi kopię danych |

## Proces PRZED — ewidencja w Excelu

```mermaid
flowchart TD
    A[Pracownik zmienia strefę lub idzie na przerwę] --> B[Lider zmiany zbiera informacje<br/>i wpisuje godziny do arkusza]
    B --> C[(Arkusz Excel)]
    C --> D[Formuły w arkuszu liczą czas per strefa<br/>i nadwyżki przerw]
    D --> E[Kierownik magazynu: obsada i wydajność stref<br/>Lider zmiany: kontrola przerw]
```

Słabe punkty procesu PRZED:
- brak informacji na bieżąco, kto jest w której strefie,
- przekroczenie przerwy widoczne dopiero przy rozliczeniu,
- każda zmiana strefy wymaga przekazania informacji liderowi i ręcznego wpisu — dodatkowa praca lidera na każdej zmianie,
- dane w arkuszu są tak aktualne, jak ostatni wpis lidera.

## Proces PO — rejestracja w RCP Log

```mermaid
flowchart TD
    A([Pracownik podchodzi do skanera]) --> B[Skanuje kod QR]
    B --> C{Kod znany?}
    C -- nie --> C1[Komunikat: Nieznany kod<br/>+ alert NIEZNANY_KOD] --> A
    C -- tak --> D[Ekran: imię, bieżąca strefa,<br/>czas dziś, dozwolone strefy]
    D --> E{Wybór}
    E -- strefa z podstrefami --> F[Wybór podstrefy<br/>lub bez podstrefy]
    E -- strefa bez podstref --> G
    E -- Koniec zmiany --> G
    F --> G[Potwierdzenie wyboru]
    G --> H{Bieżąca sesja<br/>krótsza niż 5 min?}
    H -- tak --> H1{Pracownik potwierdza<br/>mimo ostrzeżenia?}
    H1 -- nie --> D
    H1 -- tak --> I
    H -- nie --> I[Zamknięcie bieżącej sesji<br/>= wiersz w ewidencji CSV]
    I --> J{Zamykana sesja to PRZERWA<br/>dłuższa niż próg?}
    J -- tak --> J1[Flaga DLUGA_PRZERWA<br/>+ nadwyżka do rozliczenia<br/>+ alert]
    J -- nie --> K
    J1 --> K{Koniec zmiany?}
    K -- tak --> K1[Brak nowej sesji]
    K -- nie --> K2[Nowa sesja w wybranej strefie]
    K1 --> L[Ekran potwierdzenia z czasem dziś]
    K2 --> L
    L --> A
```

### Zadania systemu w tle (co 60 sekund)

```mermaid
flowchart TD
    S([Co minutę, dla każdej otwartej sesji]) --> T1{Strefa PRZERWA<br/>i czas ponad próg?}
    T1 -- tak, pierwszy raz --> T2[Alert DLUGA_PRZERWA]
    T1 -- nie --> T3
    T2 --> T3{Sesja trwa<br/>ponad 10 h?}
    T3 -- tak, pierwszy raz --> T4[Alert DLUGI_DYZUR]
    T3 -- nie --> T5
    T4 --> T5{Sesja rozpoczęta<br/>przed dzisiejszą datą?}
    T5 -- tak --> T6[Zamknięcie na 23:59:59 dnia wejścia<br/>flaga AUTO_ZAMKNIETO + alert]
    T5 -- nie --> Z([Koniec])
    T6 --> Z
```

### Proces administratora

```mermaid
flowchart TD
    P1[Dashboard i podgląd Live] --> P2{Co wymaga reakcji?}
    P2 -- alert długiej przerwy --> P3[Zakładka Przerwy:<br/>przypisz nadwyżkę do strefy]
    P2 -- zgłoszona korekta --> P4[Zakładka Korekty:<br/>zatwierdź lub odrzuć]
    P4 -- zatwierdzona --> P4b[/Poza aplikacją: administrator lub kierownik<br/>poprawia wpis w CSV dnia i miesiąca/]
    P2 -- pracownik w złej strefie<br/>lub bez zakończenia zmiany --> P5[Live: przesuń<br/>lub zakończ zmianę<br/>bez kontroli uprawnień]
    P2 -- nowa osoba / strefa --> P6[Pracownicy, Strefy,<br/>Macierz uprawnień]
    P1 --> P7[Grafik: import z Excela<br/>i porównanie z obecnością]
    P1 --> P8[Eksport CSV:<br/>dzień, miesiąc, alerty]
```

## Punkty decyzyjne

| Punkt | Kto decyduje | Reguła | Kod |
|---|---|---|---|
| Czy kod jest znany | system | kod musi istnieć w słowniku pracowników | `app.py:440-442` |
| Czy strefa jest dozwolona | system | strefa musi być na liście uprawnień pracownika | `app.py:501-503` |
| Czy zmiana nie jest zbyt szybka | pracownik (po ostrzeżeniu) | ostrzeżenie, gdy bieżąca sesja trwa krócej niż próg (domyślnie 5 min) | `app.py:509-520` |
| Czy przerwa jest za długa | system | przerwa dłuższa niż próg (domyślnie 30 min) dostaje flagę i nadwyżkę | `app.py:292-297, 549-569` |
| Do jakiej strefy przypisać nadwyżkę | administrator | wybór z listy stref | `app.py:778-790` |
| Czy uznać korektę | administrator | zatwierdzenie lub odrzucenie | `app.py:798-809` |
| Jak nanieść zatwierdzoną korektę | administrator lub kierownik, poza aplikacją | ręczna poprawka wpisu w obu plikach: dziennym i miesięcznym | `app.py:217-222` (zapis do dwóch plików) |
| Do jakiej strefy przesunąć pracownika | administrator | dowolna nazwa — serwer nie sprawdza uprawnień ani istnienia strefy | `app.py:812-852, 854-888` |
| Co przy zgubionym identyfikatorze | lider / administrator, poza aplikacją | drukowany jest duplikat z tym samym kodem — zgubiona karta nadal działa (patrz [07](07-ograniczenia.md) B5) | — |

## Wejścia i wyjścia

| Wejścia | Wyjścia |
|---|---|
| skan kodu QR, wybór strefy i podstrefy | ewidencja CSV dzienna i miesięczna |
| słowniki: pracownicy, strefy, uprawnienia | alerty (CSV + baner w panelu) |
| grafik zmian w Excelu | lista nadwyżek przerw do rozliczenia |
| konfiguracja progów | lista zgłoszeń korekt i decyzji |
| | porównanie grafik–obecność |
| | kopia zapasowa danych |
