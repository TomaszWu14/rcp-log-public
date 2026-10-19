# Polityka bezpieczeństwa

## Status

RCP Log jest prototypem i **nie przeszedł przeglądu bezpieczeństwa**. Publiczna instancja
[rcp.log.twapp.pl](https://rcp.log.twapp.pl) działa w trybie demo: dane fikcyjne odtwarzane co 30 min,
każdy gość jest administratorem — to zamierzone. Ryzyka krytyczne i wysokie R1–R3 zamknięte (US-001, US-002);
przed uruchomieniem z prawdziwymi danymi pracowników sprawdź listę „przed wdrożeniem" w
[docs/05](docs/05-decyzje-i-ograniczenia.md#co-trzeba-zrobić-przed-wdrożeniem-produkcyjnym) i rejestr
[docs/bezpieczenstwo/RYZYKA.md](docs/bezpieczenstwo/RYZYKA.md).

## Zgłaszanie podatności

Nie otwieraj publicznego issue z działającym exploitem. Zgłoś podatność prywatnie przez GitHub:
zakładka *Security → Report a vulnerability*
([formularz](https://github.com/TomaszWu14/rcp-log-public/security/advisories/new)).
Odpowiedź najczęściej do 7 dni.
Zgłoszenia dotyczące instancji demo (zaśmiecenie danych, niedostępność) nie są podatnościami —
dane resetują się same.

## Zakres

W zakresie: gałąź domyślna (`main`) — `app.py`, `run.py`, `demo_data.py`, `templates/`, `Dockerfile`, `docker-compose.yaml`.
Poza zakresem: biblioteki zewnętrzne (zgłaszaj u ich autorów), infrastruktura Coolify.
