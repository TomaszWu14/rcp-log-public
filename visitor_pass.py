"""Przepustka z portfolio: gość, który przedstawił się w portfolio, nie widzi formularza bramki dema.

Portfolio ustawia ciasteczko `gosc` (domena `.twapp.pl`); demo pyta `GET {PORTFOLIO_URL}/api/gosc`
z samym tym ciasteczkiem i interpretuje wyłącznie kod statusu (200 = ważna przepustka).
Błąd sieci, timeout, przekierowanie albo inny kod = brak przepustki (formularz bramki jak dotąd).
Wartość ciasteczka nie trafia do logów. Wynik pozytywny jest pamiętany w pamięci procesu (po hashu tokenu).

Zmienne: `PORTFOLIO_URL` (domyślnie https://portfolio.twapp.pl; musi zaczynać się od https://),
`PORTFOLIO_PASS` (`0` wyłącza sprawdzanie).
"""
import hashlib
import logging
import os
import time
import urllib.error
import urllib.request

DOMYSLNY_URL = "https://portfolio.twapp.pl"
TIMEOUT_S = 2
MAX_TOKEN = 200
CACHE_S = 600
CACHE_MAX = 1000
log = logging.getLogger("rcp")
_cache = {}   # sha256(token) -> czas ważności (monotonic)


class _BezPrzekierowan(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None   # 3xx kończy się HTTPError, czyli odmową


def _adres():
    """Adres endpointu przepustki albo None, gdy sprawdzanie jest wyłączone lub skonfigurowane błędnie."""
    if os.environ.get("PORTFOLIO_PASS", "1").strip().lower() in ("0", "false", "no", "off"):
        return None
    base = (os.environ.get("PORTFOLIO_URL") or DOMYSLNY_URL).strip().rstrip("/")
    if not base.startswith("https://"):
        log.warning("PORTFOLIO_URL musi zaczynać się od https:// — sprawdzanie przepustki wyłączone")
        return None
    return base + "/api/gosc"


def _status(url, token):
    """Kod HTTP odpowiedzi portfolio (do podmiany w testach). Idzie tylko ciasteczko `gosc`."""
    req = urllib.request.Request(url, headers={"Cookie": f"gosc={token}"}, method="GET")
    opener = urllib.request.build_opener(_BezPrzekierowan)
    try:
        with opener.open(req, timeout=TIMEOUT_S) as r:  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def _token_ok(token):
    return (isinstance(token, str) and 0 < len(token) <= MAX_TOKEN
            and all(32 < ord(ch) < 127 and ch not in ";," for ch in token))


def przepustka_wazna(token):
    """True tylko gdy portfolio potwierdziło token kodem 200. Nigdy nie rzuca wyjątku."""
    if not _token_ok(token):
        return False
    url = _adres()
    if url is None:
        return False
    klucz, teraz = hashlib.sha256(token.encode()).hexdigest(), time.monotonic()
    if _cache.get(klucz, 0) > teraz:
        return True
    try:
        ok = _status(url, token) == 200
    except Exception as e:  # noqa: BLE001 — przepustka jest dodatkiem, bramka działa jak dotąd
        log.warning("Sprawdzenie przepustki z portfolio nie powiodło się (%s)", type(e).__name__)
        return False
    if ok:
        if len(_cache) >= CACHE_MAX:
            _cache.clear()
        _cache[klucz] = teraz + CACHE_S
    return ok
