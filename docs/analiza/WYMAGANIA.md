# Wymagania niefunkcjonalne — wersja 0.1

Wymagania funkcjonalne WF-1–37 z kryteriami Given/When/Then są w [01-procesy](../01-procesy/) i tam
pozostają źródłem prawdy. Tu są **wymagania niefunkcjonalne** (luka A1). Skala wg Z23: ~60 osób,
~15 stref, jedno stanowisko skanera, 1–2 administratorów.

| ID | Wymaganie | Kryterium | Status |
|---|---|---|---|
| NFR-001 | Czas odpowiedzi skanu | `/api/scan` i `/api/rejestruj` odpowiadają w < 1 s przy 60 trwających pobytach i 1000 wpisów dnia | do zmierzenia |
| NFR-002 | Równoczesność | skaner i 2 administratorów jednocześnie nie gubią ani nie duplikują wpisów | spełnione dla jednego procesu (US-005, US-006): pobyty, zgłoszenia i decyzje pod jedną blokadą; wiele replik — poza zakresem (DEV-4) |
| NFR-003 | Trwałość danych | przerwany zapis nie uszkadza pliku; po restarcie trwające pobyty są zachowane | spełnione (US-006): zapis przez plik tymczasowy i `os.replace`; CSV dopisywane wierszami |
| NFR-004 | Przeglądarki | skaner i panel działają w aktualnym Chrome i Edge bez kroku budowania | spełnione |
| NFR-005 | Dostępność skanera | obsługa klawiaturą (czytnik USB jako klawiatura, Z2), czytelne kontrasty | do sprawdzenia |
| NFR-006 | Odtworzenie po awarii | przywrócenie z kopii w < 15 min wg [RUNBOOK](../operacje/RUNBOOK.md); kopie z retencją 30 dni (Z7) | częściowo (T11) |
| NFR-007 | Ochrona danych osobowych | podgląd obecności tylko po zalogowaniu; retencja wg `RODO.md` | podgląd: spełnione (US-002); retencja: polityka opisana (US-007), mechanizm — US-009 |
| NFR-008 | Konfiguracja | sekrety i ścieżki ze zmiennych środowiskowych; poza demo brak klucza = błąd startu | sekrety: spełnione (US-001); ścieżki danych i kopii nadal w kodzie (DEV-8) |
| NFR-009 | Powtarzalny build | zależności przypięte, CI na każdym PR, obraz Docker bez roota i bez CVE wysokich | spełnione |
| NFR-010 | Strefa czasowa | serwer i kontener w Europe/Warsaw (Z10) | spełnione (`Dockerfile`) |
