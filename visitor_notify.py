"""Powiadomienie push (ntfy) o nowym gościu bramki demo.

Bez `NTFY_URL` nic się nie dzieje (zero ruchu sieciowego). Wysyłka w wątku w tle z limitem 5 s;
każdy błąd trafia do logu jako ostrzeżenie i nigdy nie dociera do gościa.
"""
import logging
import os
import threading
import urllib.request

APP = "rcp-log"
TIMEOUT_S = 5
MAX_BODY = 300
log = logging.getLogger("rcp")


def _wyslij(url, body, headers):
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    # Schemat sprawdzony w powiadom_o_gosciu (tylko http/https); adres pochodzi z env właściciela, nie od gościa.
    with urllib.request.urlopen(req, timeout=TIMEOUT_S):  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        pass


def _wyslij_bezpiecznie(url, body, headers):
    try:
        _wyslij(url, body, headers)
    except Exception as e:  # noqa: BLE001 — powiadomienie jest dodatkiem, nie może przerwać niczego
        log.warning("Powiadomienie ntfy o gościu nie zostało wysłane: %s", e)


def _uruchom_w_tle(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def powiadom_o_gosciu(imie, nazwisko, firma):
    """Wysyła w tle powiadomienie ntfy o gościu; bez `NTFY_URL` — no-op."""
    url = os.environ.get("NTFY_URL", "").strip()
    if not url:
        return
    if not url.lower().startswith(("https://", "http://")):
        log.warning("NTFY_URL musi zaczynać się od https:// lub http:// — powiadomienie pominięte")
        return
    body = f"{imie} {nazwisko} ({firma}) wszedł do {APP}"[:MAX_BODY]
    headers = {"Title": f"Nowy gosc: {APP}", "Tags": "bell", "Priority": "high",
               "Content-Type": "text/plain; charset=utf-8"}
    token = os.environ.get("NTFY_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        _uruchom_w_tle(_wyslij_bezpiecznie, url, body, headers)
    except Exception as e:  # noqa: BLE001 — np. brak możliwości utworzenia wątku
        log.warning("Powiadomienie ntfy o gościu nie zostało uruchomione: %s", e)
