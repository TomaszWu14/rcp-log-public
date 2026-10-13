# 01. Problem i zakres

## Problem

Na zmianie pracuje około 60 osób w około 15 strefach magazynu. Pracownik w ciągu zmiany przechodzi
między strefami: kompletacja, przyjęcia, wysyłka, przerwa. Czas spędzony w każdej strefie lider zmiany
ewidencjonuje ręcznie w Excelu. W takim układzie:

- nie ma bieżącej informacji, kto jest w której strefie,
- długą przerwę widać dopiero przy rozliczeniu, a nie w chwili, gdy trwa,
- dane o czasie per strefa powstają z opóźnieniem i wymagają ręcznego przepisywania.

## Cel

Zastąpić ręczną ewidencję w Excelu rejestracją jednym skanem kodu QR, z podglądem obsady na żywo
i automatycznym wykrywaniem przekroczonych przerw.

Status: **prototyp** — rozwiązanie zbudowane do sprawdzenia procesu, nie wdrożenie produkcyjne.
Prototyp nie był jeszcze testowany z użytkownikami; opis interesariuszy poniżej to rola docelowa.

## Interesariusze

| Interesariusz | Rola w procesie | Czego potrzebuje |
|---|---|---|
| Pracownik magazynu | ma rejestrować wejście do strefy, przerwę i koniec zmiany | szybkiej rejestracji bez formularzy; informacji, ile przepracował dziś |
| Administrator | ma monitorować obsadę, reagować na alerty, rozliczać nadwyżki przerw i korekty, utrzymywać słowniki | podglądu na żywo, alertów, eksportu danych |
| Kierownik magazynu | ma korzystać z ewidencji i dashboardu; razem z administratorem nanosi zatwierdzone korekty na ewidencję | czasu per strefa do planowania obsady stref i oceny wydajności |
| Lider zmiany | dziś wpisuje godziny do Excela; docelowo korzysta z podglądu na żywo | bieżącej informacji, kto jest w której strefie i ile trwają przerwy |

## W zakresie

| Obszar | Co aplikacja robi | Szczegóły |
|---|---|---|
| Rejestracja | skan QR → wybór strefy i podstrefy → potwierdzenie; koniec zmiany | [03-user-flow](03-user-flow.md) |
| Uprawnienia | pracownik widzi i może wybrać tylko przypisane mu strefy | [05-wymagania](05-wymagania.md) REJ-03 |
| Ewidencja | każde przejście zapisuje zamknięty pobyt do CSV dziennego i miesięcznego | [04-model-danych](04-model-danych.md) |
| Kontrola przerw | alert przy przekroczeniu progu; nadwyżka do rozliczenia przez administratora | [02-proces](02-proces.md) |
| Kontrola sesji | alert długiego dyżuru; automatyczne zamknięcie sesji z poprzedniego dnia | [05-wymagania](05-wymagania.md) SES-04, SES-05 |
| Korekty | pracownik zgłasza, administrator zatwierdza lub odrzuca | [05-wymagania](05-wymagania.md) KOR-* |
| Panel administratora | dashboard, podgląd na żywo, historia, ręczne przesunięcia, słowniki, konfiguracja | [03-user-flow](03-user-flow.md) |
| Grafik | import z Excela, edycja, porównanie planu z obecnością | [05-wymagania](05-wymagania.md) GRF-* |
| Eksport i kopie | CSV dnia, miesiąca i alertów; kopia danych co noc | [05-wymagania](05-wymagania.md) EKS-*, SYS-* |

## Poza zakresem

| Czego nie ma | Dlaczego |
|---|---|
| Naliczanie wynagrodzeń i integracja z systemem kadrowo-płacowym | prototyp ma potwierdzić proces rejestracji; eksport CSV jest punktem styku |
| Automatyczna zmiana ewidencji po zatwierdzeniu korekty | decyzję i poprawkę zostawiono człowiekowi; zatwierdzenie zmienia tylko status zgłoszenia |
| Zmiana nocna przechodząca przez północ | w strefach objętych rejestracją nie ma zmian nocnych; sesja jest zamykana o 23:59:59 dnia rozpoczęcia — patrz [06-decyzje](06-decyzje.md) D3 |
| Uprawnienia na poziomie podstref | okazały się zbędne — uprawnienia działają na strefach, podstrefa jest tylko doprecyzowaniem ([06-decyzje](06-decyzje.md) D8) |
| Praca offline skanera | skan wymaga połączenia z serwerem |
| Wielu użytkowników z różnymi rolami w panelu | jest jedna rola: administrator |
| Baza danych | dane w plikach JSON i CSV — patrz [06-decyzje](06-decyzje.md) D1 |
| Polityka retencji danych osobowych | nie ustalono — prototyp działał na danych przykładowych; polityka retencji jest wymagana przed wdrożeniem |

Pełna lista ograniczeń i znanych problemów: [07-ograniczenia](07-ograniczenia.md).
