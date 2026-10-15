# Wymagania niefunkcjonalne — wersja 0.1

Wymagania funkcjonalne WF-1–37 z kryteriami Given/When/Then są w [01-procesy](../01-procesy/) i tam
pozostają źródłem prawdy. Tu są **wymagania niefunkcjonalne** (luka A1). Skala wg Z23: ~60 osób,
~15 stref, jedno stanowisko skanera, 1–2 administratorów.

| ID | Wymaganie | Kryterium | Status |
|---|---|---|---|
| NFR-001 | Czas odpowiedzi skanu | `/api/scan` i `/api/rejestruj` odpowiadają w < 1 s przy 60 trwających pobytach i 1000 wpisów dnia | do zmierzenia |
| NFR-002 | Równoczesność | skaner i 2 administratorów jednocześnie nie gubią ani nie duplikują wpisów | częściowo: zamykanie pobytu pod jedną blokadą (US-005); korekty i nadwyżki bez blokady (DEV-2, T12) |
| NFR-003 | Trwałość danych | przerwany zapis nie uszkadza pliku; po restarcie trwające pobyty są zachowane | częściowo (zapis nieatomowy) |
| NFR-004 | Przeglądarki | skaner i panel działają w aktualnym Chrome i Edge bez kroku budowania | spełnione |
| NFR-005 | Dostępność skanera | obsługa klawiaturą (czytnik USB jako klawiatura, Z2), czytelne kontrasty | do sprawdzenia |
| NFR-006 | Odtworzenie po awarii | przywrócenie z kopii w < 15 min wg [RUNBOOK](../operacje/RUNBOOK.md); kopie z retencją 30 dni (Z7) | częściowo (T11) |
| NFR-007 | Ochrona danych osobowych | podgląd obecności tylko po zalogowaniu; retencja wg `RODO.md` | podgląd: spełnione (US-002); retencja: niespełnione (R10) |
| NFR-008 | Konfiguracja | sekrety i ścieżki ze zmiennych środowiskowych; poza demo brak klucza = błąd startu | sekrety: spełnione (US-001); ścieżki danych i kopii nadal w kodzie (DEV-8) |
| NFR-009 | Powtarzalny build | zależności przypięte, CI na każdym PR, obraz Docker bez roota i bez CVE wysokich | spełnione |
| NFR-010 | Strefa czasowa | serwer i kontener w Europe/Warsaw (Z10) | spełnione (`Dockerfile`) |
