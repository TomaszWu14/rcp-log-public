"""Aktywność gościa bramki demo: ile ekranów, jak długo, jakie sekcje (bez IP i user-agenta).

Czyste funkcje na wierszu `goscie.csv` (słownik z polami tekstowymi); zapis i blokada są w app.py.
"""
import json
import re
from datetime import datetime

MAX_SEKCJI = 20
MAX_DLUGOSC_SEKCJI = 40
POMIJANE_PREFIKSY = ("/static", "/health", "/api/", "/admin/api/")


def sekcja_ze_sciezki(sciezka):
    """Pierwszy segment ścieżki (`/` → `start`), małe litery, tylko [a-z0-9_-], max 40 znaków; pusta → None."""
    seg = (sciezka or "/").lstrip("/").split("/", 1)[0]
    if not seg:
        return "start"
    seg = re.sub(r"[^a-z0-9_-]", "", seg.lower())[:MAX_DLUGOSC_SEKCJI]
    return seg or None


def liczona_sciezka(sciezka):
    """Strony HTML aplikacji — bez plików statycznych, /health i API."""
    s = sciezka or "/"
    return not (s.startswith(POMIJANE_PREFIKSY) or s in ("/api", "/health", "/admin/api"))


def sekcje(wiersz):
    """Słownik sekcja → liczba z pola `sections`; uszkodzone pole = pusty słownik."""
    try:
        d = json.loads(wiersz.get("sections") or "{}")
    except (TypeError, ValueError):
        return {}
    if not isinstance(d, dict):
        return {}
    return {str(k): v for k, v in d.items() if isinstance(v, int) and not isinstance(v, bool)}


def zarejestruj_ekran(wiersz, sekcja, now):
    """page_views += 1, last_seen_at = now, sekcja += 1 (nowa ponad limit 20 kluczy jest ignorowana).

    Zmienia `wiersz` w miejscu i zwraca nową liczbę ekranów."""
    try:
        ekrany = int(wiersz.get("page_views") or 0) + 1
    except ValueError:
        ekrany = 1
    d = sekcje(wiersz)
    if sekcja and (sekcja in d or len(d) < MAX_SEKCJI):
        d[sekcja] = d.get(sekcja, 0) + 1
    wiersz["page_views"] = str(ekrany)
    wiersz["last_seen_at"] = now.isoformat(timespec="seconds")
    wiersz["sections"] = json.dumps(d, ensure_ascii=True, separators=(",", ":"))
    return ekrany


def czas_wizyty(wiersz):
    """„ok. N min” (last_seen_at − created_at, min. 1) albo „—”, gdy gość nic nie oglądał."""
    try:
        sek = (datetime.fromisoformat(wiersz.get("last_seen_at") or "")
               - datetime.fromisoformat(wiersz.get("created_at") or "")).total_seconds()
    except ValueError:
        return "—"
    return f"ok. {max(1, round(sek / 60))} min"


def najczesciej(wiersz, ile=3):
    """Trzy sekcje z największą liczbą wyświetleń, np. „admin (5), start (2)”."""
    top = sorted(sekcje(wiersz).items(), key=lambda kv: (-kv[1], kv[0]))[:ile]
    return ", ".join(f"{k} ({v})" for k, v in top)
