# ADR 0012. Proces zespołu BA/DEV/SEC i zestaw narzędzi CI

Data: 2026-10-15 · Status: przyjęta (założenia Z18, Z24 zaakceptowane przez PO)

## Kontekst

Repo prowadzi jedna osoba. Chcemy, żeby ślad pracy wyglądał jak proces dojrzałego zespołu
(analiza → bezpieczeństwo → projekt → kod → przegląd → odbiór), nie psując dokumentacji `00–05`,
do której linkują README i materiały CV.

## Opcje

1. Przenieść `00–05` do struktury `analiza/architektura/bezpieczenstwo`.
2. Zostawić `00–05` jako źródło prawdy; nowe katalogi dopisują brakujące treści i linkują.
3. Pełny zestaw narzędzi (ruff, mypy, pytest-cov, bandit, semgrep, pip-audit, gitleaks, trivy).
4. Zestaw minimalny: ruff, bandit, pip-audit, gitleaks, trivy; reszta, gdy pojawi się potrzeba.

## Decyzja

**2 + 4.** Struktura z promptu istnieje w całości, ale pliki, które dublowałyby `00–05`, są wskaźnikami
(`PROCESY`, `MODEL_DANYCH`, `API`, `SLOWNIK`). Trivy wchodzi, bo jest Dockerfile i publiczna instancja.
Semgrep i mypy odłożone: jeden plik bez adnotacji typów. `pytest-cov` dojdzie z refaktorem DEV-1 (Z22).
Testy zostają na `unittest` (18 testów istnieje, bez nowej zależności).

## Konsekwencje

- Czytelnik zaczyna od README → `docs/AUDYT.md` → `docs/analiza/HISTORYJKI.md`.
- Ruff z regułami ignorowanymi dla `app.py` (`pyproject.toml`) — dług spłacany przy US-005, bo każda
  poprawka przesuwa numery linii w `docs/01-procesy` i `05`.
- CI blokuje PR przy: błędzie lintera, testów, bandit ≥ średnia, CVE w zależnościach lub obrazie
  (HIGH/CRITICAL z poprawką), sekrecie w historii.
- Dwa udokumentowane wyjątki, do usunięcia z US-001: bandit B104 (nasłuch `0.0.0.0` — zamierzony, kontener
  za proxy) i allowlista gitleaks dla domyślnego klucza sesji (B1).
