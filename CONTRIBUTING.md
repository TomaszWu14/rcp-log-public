# Jak pracujemy

Repo prowadzone jak przez trzyosobowy zespół — **[BA]** analityk, **[DEV]** developer, **[SEC]**
bezpieczeństwo — z Product Ownerem, który akceptuje zakres, ryzyka i wydania. Każdy krok jest
oznaczony rolą. Stan wyjściowy: [docs/AUDYT.md](docs/AUDYT.md).

## Proces dla każdej funkcji

| Krok | Rola | Wynik |
|---|---|---|
| 1. Analiza | BA | historyjka w `docs/analiza/HISTORYJKI.md` (Given/When/Then, MoSCoW), Definition of Ready |
| 2. Wymagania bezpieczeństwa | SEC | klasa danych, mini threat model, wpis do `RYZYKA.md`, jeśli coś zostaje otwarte |
| 3. Projekt | DEV | opis rozwiązania; ADR w `docs/architektura/adr/`, gdy decyzja jest trudno odwracalna |
| 4. Implementacja | DEV | gałąź `feature/<id>-<nazwa>`, małe commity, testy na każde kryterium |
| 5. Przegląd bezpieczeństwa | SEC | checklista z szablonu PR; ✅ / ⚠️ / ❌ |
| 6. Odbiór | BA | kryteria punkt po punkcie, `SLEDZENIE.md` |
| 7. PR | — | szablon PR, wpis w `CHANGELOG.md`; **merge po akceptacji PO** |

## Definition of Ready

Cel jasny · kryteria testowalne · zależności znane · dane i uprawnienia określone.

## Definition of Done

- wszystkie kryteria akceptacji (funkcjonalne i bezpieczeństwa) spełnione i pokryte testami,
- CI zielone: ruff, testy, bandit, pip-audit, gitleaks, trivy — bez nowych ustaleń średnich i wyższych,
- dokumentacja zaktualizowana (`docs/01-procesy` WF/BR, `04` interfejsy, `02` model danych, ADR jeśli dotyczy, CHANGELOG),
- przegląd SEC i odbiór BA zapisane w PR,
- brak sekretów, danych osobowych i danych produkcyjnych w repo, testach i logach,
- PO zaakceptował.

## Konwencje

- **Gałęzie:** `feature/<US-id>-<nazwa>`, `fix/<id>-<nazwa>`, `security/<R-id>-<nazwa>`, `docs/<nazwa>`.
- **Commity:** Conventional Commits z typem po angielsku i opisem po polsku (Z20):
  `feat: …`, `fix: …`, `docs: …`, `test: …`, `refactor: …`, `chore: …`, `security: …`; w treści ID historyjki.
- **Język:** dokumentacja po polsku; kod, nazwy i typy commitów po angielsku. Polskie nazwy domenowe
  w `app.py` (`strefa`, `pracownik`) zostają — to język domeny ([02-dane](docs/02-dane/model-danych.md)).
- **Numery linii** w `docs/01-procesy`, `04`, `05` odwołują się do `app.py`. Zmiana kodu = aktualizacja
  odwołań w tym samym PR.
- **Numeracja** identyfikatorów jest ciągła w całym repo: Z17+, ADR 0012+, US-009+, R11+, NFR-011+.

## Lokalnie

```bash
pip install -r requirements-dev.txt
ruff check .
python -m unittest discover tests
bandit -c pyproject.toml -r app.py run.py demo_data.py --severity-level medium
pip-audit -r requirements.txt
docker build -t rcp-log:ci .     # obraz skanuje trivy w CI
```

Dlaczego te narzędzia: [ADR 0012](docs/architektura/adr/0012-proces-zespolu-i-narzedzia-ci.md).
Semgrep, mypy i próg pokrycia — odłożone (Z22, Z24).
