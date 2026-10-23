"""Powiadomienia push (ntfy) o gościach bramki demo.

Bez `NTFY_URL` nic się nie dzieje (zero ruchu sieciowego). Wysyłka w wątku w tle z limitem 5 s;
każdy błąd trafia do logu jako ostrzeżenie i nigdy nie dociera do gościa.

`NTFY_WATCH_COMPANIES` (frazy rozdzielone przecinkami, tylko w env) podnosi priorytet powiadomień
o gościach z pasujących firm; `NTFY_ENGAGED_VIEWS` (domyślnie 10, 0 = wyłączone) — próg ekranów,
po którym idzie jedno powiadomienie „gość ogląda demo”.
"""
import logging
import os
import re
import threading
import unicodedata
import urllib.request

APP = "rcp-log"
TIMEOUT_S = 5
MAX_BODY = 300
DOMYSLNY_PROG_EKRANOW = 10
log = logging.getLogger("rcp")


def _wyslij(url, body, headers):
    req = urllib.request.Request(url, data=body.encode("utf-8"), headers=headers, method="POST")
    # Schemat sprawdzony w _push (tylko http/https); adres pochodzi z env właściciela, nie od gościa.
    with urllib.request.urlopen(req, timeout=TIMEOUT_S):  # nosec B310  # nosemgrep: python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected
        pass


def _wyslij_bezpiecznie(url, body, headers):
    try:
        _wyslij(url, body, headers)
    except Exception as e:  # noqa: BLE001 — powiadomienie jest dodatkiem, nie może przerwać niczego
        log.warning("Powiadomienie ntfy o gościu nie zostało wysłane: %s", e)


def _uruchom_w_tle(fn, *args):
    threading.Thread(target=fn, args=args, daemon=True).start()


def normalizuj(tekst):
    """casefold + bez polskich znaków diakrytycznych (NFKD; „ł” osobno, bo się nie rozkłada) + pojedyncze spacje."""
    t = unicodedata.normalize("NFKD", str(tekst or "").casefold().replace("ł", "l"))
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", t).strip()


def firma_na_liscie(firma):
    """True, gdy któraś fraza z `NTFY_WATCH_COMPANIES` (po normalizacji, min. 2 znaki) zawiera się w nazwie firmy."""
    frazy = [normalizuj(f) for f in os.environ.get("NTFY_WATCH_COMPANIES", "").split(",")]
    nazwa = normalizuj(firma)
    return any(len(f) >= 2 and f in nazwa for f in frazy)


def prog_ekranow():
    """`NTFY_ENGAGED_VIEWS` jako liczba ≥ 0; błędna wartość = domyślne 10."""
    try:
        return max(0, int(os.environ.get("NTFY_ENGAGED_VIEWS", DOMYSLNY_PROG_EKRANOW)))
    except ValueError:
        log.warning("NTFY_ENGAGED_VIEWS musi być liczbą całkowitą — przyjmuję %d", DOMYSLNY_PROG_EKRANOW)
        return DOMYSLNY_PROG_EKRANOW


def _push(body, title, tags, priority):
    """Wysyła w tle powiadomienie ntfy; bez `NTFY_URL` — no-op. Nagłówki muszą być ASCII."""
    url = os.environ.get("NTFY_URL", "").strip()
    if not url:
        return
    if not url.lower().startswith(("https://", "http://")):
        log.warning("NTFY_URL musi zaczynać się od https:// lub http:// — powiadomienie pominięte")
        return
    headers = {"Title": title, "Tags": tags, "Priority": priority, "Content-Type": "text/plain; charset=utf-8"}
    token = os.environ.get("NTFY_TOKEN", "").strip()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        _uruchom_w_tle(_wyslij_bezpiecznie, url, body[:MAX_BODY], headers)
    except Exception as e:  # noqa: BLE001 — np. brak możliwości utworzenia wątku
        log.warning("Powiadomienie ntfy o gościu nie zostało uruchomione: %s", e)


def powiadom_o_gosciu(imie, nazwisko, firma):
    """Nowy gość; firma z listy `NTFY_WATCH_COMPANIES` → priorytet urgent i ostrzeżenie w treści."""
    body = f"{imie} {nazwisko} ({firma}) wszedł do {APP}"
    if firma_na_liscie(firma):
        _push("⚠️ " + body, f"UWAGA firma z listy: {APP}", "rotating_light", "urgent")
    else:
        _push(body, f"Nowy gosc: {APP}", "bell", "high")


def powiadom_o_zaangazowaniu(imie, nazwisko, firma, ekrany):
    """Gość obejrzał `ekrany` ekranów (wywoływane raz, przy osiągnięciu progu)."""
    body = f"{imie} {nazwisko} ({firma}) obejrzał już {ekrany} ekranów w {APP}"
    _push(body, f"Gosc oglada demo: {APP}", "eyes", "urgent" if firma_na_liscie(firma) else "default")
