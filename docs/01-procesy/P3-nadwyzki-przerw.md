# P3. Rozliczanie nadwyżek przerw

| Pole | Treść |
|---|---|
| **Nazwa procesu** | Rozliczanie nadwyżek przerw |
| **Właściciel** | administrator ([Z1](../00-przeglad.md#ustalenia-potwierdzone)) |
| **Cel biznesowy** | każda przerwa dłuższa niż dopuszczalny próg ma wskazaną strefę, która ponosi koszt nadwyżki czasu; żadna nadwyżka nie ginie w ewidencji |
| **Zdarzenie inicjujące** | pracownik kończy skanem przerwę dłuższą niż próg (domyślnie 30 min) |
| **Rezultat końcowy** | nadwyżka ze statusem „przypisana” i nazwą strefy; nadwyżka obciąża czas pracy wskazanej strefy w rozliczeniu miesięcznym prowadzonym poza aplikacją ([Z5](../00-przeglad.md#ustalenia-potwierdzone)) |
| **Granice** | od zamknięcia przerwy do przypisania strefy; sam zapis pobytu przerwy należy do [P1](P1-rejestracja-pobytu.md), alert w trakcie przerwy do [P2](P2-nadzor-i-alerty.md) |
| **Częstotliwość** | zależna od liczby przekroczonych przerw; w danych demo kilka na dziesięć dni roboczych |

## Diagram procesu

```mermaid
flowchart TD
    subgraph PR["Pracownik magazynu"]
        E1(["Pracownik kończy przerwę skanem"])
        T4["Przeczytaj komunikat o nadwyżce na ekranie potwierdzenia"]
    end
    subgraph SYS["RCP Log"]
        T1["Zamknij pobyt w strefie PRZERWA"]
        G1{"Czas przerwy ponad próg?"}
        T2["Utwórz nadwyżkę ze statusem oczekuje"]
        T3["Zapisz alert i dołącz komunikat"]
        T6["Zmień status na przypisana"]
        E2(["Przerwa bez nadwyżki"])
    end
    subgraph ADM["Administrator"]
        T5["Wybierz strefę dla nadwyżki w zakładce Przerwy"]
        E3(["Nadwyżka przypisana do strefy"])
    end
    subgraph OUT["Poza aplikacją"]
        T7["Uwzględnij nadwyżkę w rozliczeniu strefy"]
    end
    E1 --> T1 --> G1
    G1 -->|"nie"| E2
    G1 -->|"tak"| T2 --> T3 --> T4
    T3 --> T5 --> T6 --> E3 --> T7
```

## Tabela kroków

| Nr | Krok | Aktor | Wejście | Wyjście | Reguła biznesowa | Źródło w kodzie |
|---|---|---|---|---|---|---|
| 1 | Zamknij pobyt w strefie PRZERWA | system | trwający pobyt w `PRZERWA`, chwila skanu | wpis ewidencji przerwy; flaga `DLUGA_PRZERWA`, gdy czas przekracza próg | BR-9, BR-13 | `app.py:592-610` |
| 2 | Policz nadwyżkę | system | czas przerwy, próg z konfiguracji | nadwyżka w minutach = czas minus próg | BR-25 | `app.py:386-388` |
| 3 | Utwórz nadwyżkę ze statusem oczekuje | system | nadwyżka, pracownik, chwila rozpoczęcia przerwy | pozycja na liście nadwyżek bez przypisanej strefy | BR-24, BR-26 | `app.py:389-401` |
| 4 | Zapisz alert i dołącz komunikat | system | czas przerwy, nadwyżka | wiersz `DLUGA_PRZERWA` w pliku alertów; ramka „Przerwa trwała … (nadwyżka: …)” na ekranie potwierdzenia | BR-9 | `app.py:402-404`, `index.html:616-621` |
| 5 | Przeczytaj komunikat o nadwyżce | pracownik | ekran potwierdzenia | pracownik wie, że przerwa została przekroczona | — | `index.html:616-621` |
| 6 | Przejrzyj nadwyżki | administrator | zakładka Przerwy z licznikiem oczekujących | lista: pracownik, czas przerwy, nadwyżka, data, przypisana strefa | BR-28 | `admin.html:745-770` |
| 7 | Wybierz strefę dla nadwyżki | administrator | okno „Przypisz strefę do nadwyżki” z listą stref ze słownika | wybrana strefa | BR-26 | `admin.html:772-792` |
| 8 | Zmień status na przypisana | system | numer nadwyżki, nazwa strefy | nadwyżka ze strefą i statusem „przypisana”; licznik oczekujących maleje | BR-26, BR-27 | `app.py:878-891` |
| 9 | Uwzględnij nadwyżkę w rozliczeniu strefy | administrator, poza aplikacją | lista nadwyżek | czas pracy strefy obciążony nadwyżką w rozliczeniu miesięcznym (Z5) | — | — |

## Podprocesy

### P3.1 Przypisanie strefy do nadwyżki

```mermaid
flowchart TD
    subgraph ADM["Administrator"]
        S1(["Zakładka Przerwy otwarta"]) --> A1["Przejrzyj listę: pozycje oczekujące są wyróżnione"]
        A1 --> A2["Kliknij Przypisz strefę przy pozycji"]
        A2 --> A3["Wybierz strefę z listy i zapisz"]
    end
    subgraph SYS["RCP Log"]
        G1{"Podano nazwę strefy?"}
        A4["Odrzuć: Brak strefy"]
        A5["Zapisz strefę i status przypisana"]
        E1(["Licznik oczekujących zmniejszony"])
    end
    A3 --> G1
    G1 -->|"nie"| A4 --> A2
    G1 -->|"tak"| A5 --> E1
```

| Krok | Opis | Źródło w kodzie |
|---|---|---|
| A1 | lista w kolejności powstania; pozycje „oczekuje” wyróżnione kolorem; przy zakładce licznik oczekujących | `admin.html:745-770` |
| A2, A3 | okno pokazuje nazwisko i wielkość nadwyżki; lista stref to cały słownik stref, nie tylko uprawnienia pracownika | `admin.html:772-792` |
| A5 | zapis wpisuje nazwę strefy (wielkimi literami) i status; pozycja przypisana nie ma już przycisku | `app.py:878-891`, `admin.html:755-760` |

## Ścieżki alternatywne i wyjątki

| Wyjątek | Warunek wystąpienia | Obsługa | Skutek dla procesu | Źródło w kodzie |
|---|---|---|---|---|
| Przerwa zamknięta nie przez pracownika | administrator przesuwa lub kończy zmianę osobie na przerwie; automatyczne zamknięcie o północy | wpis ma flagę i powstaje nadwyżka jak przy zamknięciu przez pracownika (US-005) | nadwyżka trafia na listę do rozliczenia | `app.py:365-404` |
| Zmiana progu po fakcie | administrator zmienia próg przerwy w konfiguracji | istniejące nadwyżki nie są przeliczane | nadwyżki sprzed zmiany liczone starym progiem | `app.py:386-388` |
| Nieistniejący numer nadwyżki | żądanie z numerem spoza listy (możliwe tylko poza ekranem) | serwer odpowiada sukcesem, nic nie zmienia | brak | `app.py:884-891` |
| Strefa spoza słownika | nazwa spoza listy w oknie (np. z ręcznie zbudowanego żądania) | serwer odrzuca: 400 „Nieznana strefa X” (US-005) | nadwyżka zostaje w statusie „oczekuje” | `app.py:883` |
| Dwóch administratorów rozlicza tę samą nadwyżkę | równoczesny zapis | wygrywa ostatni zapis, bez ostrzeżenia | możliwa nadpisana decyzja | `app.py:884-890` |
| Cofnięcie przypisania | administrator chce zmienić strefę | brak takiej funkcji | zmiana tylko przez edycję pliku poza aplikacją | `app.py:878-891` |
| Pracownik usunięty ze słownika | usunięcie po powstaniu nadwyżki | nadwyżka zostaje z kopią nazwiska | lista zawiera pozycje osób spoza słownika | `app.py:1024-1032` |

## Reguły biznesowe

| ID | Warunek → działanie | Źródło w kodzie |
|---|---|---|
| BR-24 | Przerwę ponad próg zamyka ktokolwiek (pracownik na skanerze, administrator, auto-zamknięcie) → utwórz nadwyżkę; jedno miejsce zamykania pobytu | `app.py:365-404` |
| BR-25 | Nadwyżka powstaje → jej wielkość to czas przerwy minus próg obowiązujący w chwili zamknięcia; późniejsza zmiana progu niczego nie przelicza | `app.py:386-388` |
| BR-26 | Administrator przypisuje strefę → nazwa musi istnieć w słowniku stref; status zmienia się z „oczekuje” na „przypisana” i nie wraca | `app.py:878-892` |
| BR-27 | Nadwyżka przypisana → ewidencja i wpis przerwy pozostają bez zmian | `app.py:878-891` |
| BR-28 | Zakładka Przerwy → licznik przy nazwie zakładki pokazuje liczbę nadwyżek „oczekuje” | `admin.html:748-749` |

## Wymagania funkcjonalne

| ID | Historyjka | Kryterium akceptacji | Test |
|---|---|---|---|
| WF-20 | Jako administrator chcę przypisać nadwyżkę przerwy do strefy, aby wskazać, która strefa ponosi jej koszt. | **Given** na liście jest nadwyżka ze statusem „oczekuje”. **When** administrator klika „Przypisz strefę”, wybiera strefę i zapisuje. **Then** pozycja pokazuje nazwę strefy zamiast „oczekuje”, przycisk znika, a licznik przy zakładce maleje o jeden. | ręcznie |

Powstawanie nadwyżki (flaga, wielkość, status „oczekuje”, komunikat dla pracownika) jest objęte
wymaganiem [WF-12](P1-rejestracja-pobytu.md#wymagania-funkcjonalne) i testem `test_PRZ_02_PRZ_03`.
