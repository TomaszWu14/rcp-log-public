# Threat model — wersja 0.1

STRIDE per przepływ danych. Ryzyka R1–R10 z [AUDYT](../AUDYT.md#sec-najważniejsze-ryzyka-top-10),
problemy B1–B9 z [05](../05-decyzje-i-ograniczenia.md#bezpieczeństwo), rejestr decyzji w [RYZYKA](RYZYKA.md).
Diagram kontekstu i interfejsy I1–I8: [04-integracje](../04-integracje.md).

## Przepływy

```mermaid
flowchart LR
    P[Pracownik przy skanerze] -->|kod QR, bez uwierzytelnienia| S["/api/scan, /api/rejestruj, /api/korekta"]
    A[Administrator] -->|login + hasło, sesja cookie| L["/admin/login"]
    A -->|sesja| M["/admin/api/*"]
    X[Każdy w sieci] -->|bez sesji: 401| ST["/api/status"]
    G[Gość internetu] -->|auto-sesja admina, RCP_DEMO=1| DM["instancja demo rcp.log.twapp.pl"]
    S --> F[(JSON + CSV w data/)]
    M --> F
    ST --> F
    DM --> FD[(data_demo/ — fikcyjne, reset co 30 min)]
    M -->|xlsx| I[import grafiku]
    F -->|02:00| B[(backup/)]
```

## STRIDE

| Przepływ | Zagrożenie | Kategoria | Ryzyko | Zabezpieczenie (stan) |
|---|---|---|---|---|
| Skaner → rejestracja | rejestracja w cudzym imieniu — kod przewidywalny, duplikat karty z tym samym kodem (Z3) | Spoofing | R4 / B5 | brak; *Could* US-008 |
| Skaner → korekta | opis wolnego tekstu bez limitu długości | Tampering / DoS | — | escapowany w panelu; brak limitu (niska) |
| Skaner → alerty.csv | nieznany kod z `=` jako formuła w Excelu | Tampering | R8 (zamknięte) | apostrof przed `= + - @` i tabulatorem w każdym zapisie CSV (US-003) |
| Każdy → /api/status | wyciek obecności z nazwiskami | Information disclosure | R3 (zamknięte) | sesja administratora wymagana, bez niej 401 (US-002) |
| Admin → logowanie | brute force | Spoofing / Elevation | R5 (zamknięte), R12 | hash werkzeug; hasło startowe jednorazowe (US-001); 5 prób / 10 min z adresu → 429 na 15 min (US-003); ograniczenia limitu: R12 |
| Cookie sesji | podrobienie sesji dzięki domyślnemu kluczowi | Spoofing / Elevation | R1 (zamknięte) | klucz wymagany poza demo, ≥ 32 znaki; demo losuje (US-001) |
| Admin → zmiana hasła | CSRF na formularz `/admin/haslo`; przejęcie hasła startowego z logu | Tampering / Spoofing | R6, R11 | min. 12 znaków, powtórzenie; token CSRF (US-003); R11 zaakceptowane |
| Admin → formularze | CSRF (logowanie, import xlsx, wylogowanie GET) | Tampering | R6 (zamknięte) | token CSRF w sesji na formularzach i nagłówku importu; `SameSite=Lax`, `HttpOnly`, `Secure` za proxy (US-003); wylogowanie GET bez tokenu — skutek tylko wylogowanie |
| Admin → import grafiku | spreparowany/duży xlsx | DoS | R9 | brak `MAX_CONTENT_LENGTH` |
| Admin → config | dowolne klucze, `backup_path` dowolny katalog | Tampering | R7 / B7 | brak walidacji; w demo zablokowane |
| Admin → operacje wrażliwe | brak dziennika kto co zmienił (poza `korekta_info`) | Repudiation | R10 | częściowo (`ADMIN:<login>`) |
| Gość → instancja demo | każdy jest administratorem: edycja grafiku, przesunięcia, korekty bez limitu — zaśmiecenie lub DoS demo | Tampering / DoS | R9 | `DEMO_BLOCKED`, reset co 30 min, dane fikcyjne; brak limitu żądań |
| Gość → instancja demo | pomylenie demo z produkcją — wpisanie prawdziwych danych | Information disclosure | — | baner demo w szablonach (`demo` w kontekście); osobna instancja produkcyjna (Z16) |
| data/, backup/ | dane osobowe bezterminowo (kopie: retencja 30 dni do zbudowania, Z7) | Information disclosure | R10 | brak retencji; RODO.md |
| Serwer | HTTP bez TLS w kontenerze | Information disclosure | R9 | TLS na proxy Coolify (Let's Encrypt) |

## Poza modelem

Fizyczny dostęp do stanowiska skanera i do karty QR — proces organizacyjny (Z1, Z2), nie aplikacja.
