"""
RCP Log v3
"""
import csv
import hmac
import json
import logging
import os
import re
import secrets
import shutil
import threading
import time as time_module
from contextlib import suppress
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path

import openpyxl
from flask import Flask, has_request_context, jsonify, redirect, render_template, request, send_file, session, url_for
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from werkzeug.security import check_password_hash, generate_password_hash

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rcp")   # błędy w tle i odczytach trafiają tu, nie w `except: pass` (US-010)

app = Flask(__name__)
DEMO = os.environ.get("RCP_DEMO") == "1"   # tryb demo — opis w sekcji DEMO na końcu pliku

def _secret_key():
    """Klucz podpisu sesji: wymagany poza trybem demo (US-001). Demo bez zmiennej losuje klucz."""
    key = os.environ.get("RCP_SECRET_KEY", "")
    if DEMO and not key:
        return secrets.token_hex(32)
    if len(key) < 32:
        raise SystemExit("RCP_SECRET_KEY: ustaw losowy klucz o długości co najmniej 32 znaków, "
                         "np. python -c \"import secrets; print(secrets.token_hex(32))\"")
    return key

app.secret_key = _secret_key()

# Za proxy TLS (Coolify): ciasteczko tylko po HTTPS, adres klienta z X-Forwarded-For (US-003)
PROXY = os.environ.get("RCP_PROXY") == "1"
app.config.update(SESSION_COOKIE_SAMESITE="Lax", SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SECURE=PROXY,
                  MAX_CONTENT_LENGTH=2 * 1024 * 1024)   # największe żądanie to import grafiku (.xlsx); 413 powyżej (US-011)

@app.after_request
def naglowki_bezpieczenstwa(resp):
    # Szablony mają skrypty i style inline (D1: brak builda frontendu), stąd 'unsafe-inline' — ryzyko R13 (US-011)
    resp.headers.setdefault("Content-Security-Policy",
        "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; frame-ancestors 'none'; base-uri 'self'; form-action 'self'")
    resp.headers.setdefault("X-Content-Type-Options", "nosniff")
    resp.headers.setdefault("Referrer-Policy", "same-origin")
    resp.headers.setdefault("X-Frame-Options", "DENY")
    # Skaner działa jak klawiatura (bez kamery/mikrofonu/lokalizacji); izolacja okna od otwieranych stron
    resp.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=(), usb=()")
    resp.headers.setdefault("Cross-Origin-Opener-Policy", "same-origin")
    if resp.mimetype == "application/json":   # dane pracowników z API nie trafiają do cache przeglądarki/proxy
        resp.headers.setdefault("Cache-Control", "no-store")
    if PROXY:
        resp.headers.setdefault("Strict-Transport-Security", "max-age=31536000")
    return resp

@app.errorhandler(413)
def za_duze_zadanie(_e):
    return jsonify({"ok": False, "error": "Plik lub żądanie za duże (limit 2 MB)"}), 413
BASE_DIR     = Path(__file__).parent
DATA_DIR     = BASE_DIR / ("data_demo" if DEMO else "data")
DATA_DIR.mkdir(exist_ok=True)

WORKERS_FILE = DATA_DIR / "pracownicy.json"
STATE_FILE   = DATA_DIR / "aktywne_sesje.json"
STREFY_FILE  = DATA_DIR / "strefy.json"
ADMINS_FILE  = DATA_DIR / "admins.json"
CONFIG_FILE  = DATA_DIR / "config.json"
KOREKTY_FILE = DATA_DIR / "korekty.json"
NADWYZKI_FILE= DATA_DIR / "nadwyzki_przerw.json"
GRAFIK_FILE  = DATA_DIR / "grafik.json"

PROG_PRZERWA  = 30  # alert po X min przerwy
ALERT_DYZUR_H = 10  # jeden próg długiego dyżuru dla alertu i podglądu Live (Z13)

CSV_HEADERS = [
    "id","pracownik","imie_nazwisko","strefa","podstrefa",
    "ts_wejscia","ts_wyjscia","czas_min","czas_fmt","flaga","korekta_info"
]

DEFAULT_STREFY = {
    "PICKING":    {"kolor":"#185FA5","podstrefy":["PICKING_A","PICKING_B","PICKING_C"]},
    "PRZYJECIA":  {"kolor":"#1e8c45","podstrefy":["PRZYJECIA_DOKLADNE","PRZYJECIA_EKSPRES"]},
    "KURIER1":    {"kolor":"#7b3fa0","podstrefy":["KURIER1_PAKOWANIE","KURIER1_SORTOWANIE"]},
    "KURIER2":    {"kolor":"#7b3fa0","podstrefy":[]},
    "BUS":        {"kolor":"#d35400","podstrefy":["BUS_ZALADUNK","BUS_ROZLADUNEK"]},
    "EXPORT":     {"kolor":"#c0392b","podstrefy":[]},
    "INV":        {"kolor":"#2980b9","podstrefy":["INV_CYKLICZNY","INV_ROCZNY"]},
    "ZWROTY":     {"kolor":"#e67e22","podstrefy":[]},
    "KONTENERY":  {"kolor":"#16a085","podstrefy":["KONTENERY_IN","KONTENERY_OUT"]},
    "ADMIN_MAG":  {"kolor":"#7f8c8d","podstrefy":[]},
    "PRZERWA":    {"kolor":"#f39c12","podstrefy":[]},
}

DEFAULT_CONFIG = {
    "backup_path": str(BASE_DIR / "backup"),
    "prog_przerwa_min": 30,
    "ostrzezenie_szybka_zmiana_min": 5,
    "alert_dlugi_dyżur_h": 10,
    "grafik_tolerancja_min": 15,
    # Retencja w dniach (US-009, RODO.md, Z31); 0 = bez usuwania. Ewidencja 0 do decyzji IOD (Z28).
    "retencja_ewidencja_dni": 0,
    "retencja_alerty_dni": 90,
    "retencja_audyt_dni": 365,
    "retencja_kopie_dni": 30,
}
# Zakresy progów (biała lista kluczy konfiguracji, R7 / US-011); kopie tylko pod RCP_BACKUP_ROOT (domyślnie katalog aplikacji)
CONFIG_ZAKRESY = {
    "retencja_ewidencja_dni": (0, 4000),
    "retencja_alerty_dni": (0, 3650),
    "retencja_audyt_dni": (0, 3650),
    "retencja_kopie_dni": (0, 365),
    "prog_przerwa_min": (1, 240),
    "ostrzezenie_szybka_zmiana_min": (0, 60),
    "alert_dlugi_dyżur_h": (1, 24),
    "grafik_tolerancja_min": (0, 120),
}
BACKUP_ROOT = Path(os.environ.get("RCP_BACKUP_ROOT") or BASE_DIR).resolve()

def sprawdz_konfiguracje(d):
    """Normalizuje wartości w `d` i zwraca komunikat błędu albo None."""
    for k in d:
        if k not in CONFIG_ZAKRESY and k != "backup_path":
            return f"Nieznany klucz konfiguracji: {k}"
    for k, (lo, hi) in CONFIG_ZAKRESY.items():
        if k in d:
            try: d[k] = int(d[k])
            except (TypeError, ValueError): return f"{k}: wymagana liczba całkowita"
            if not lo <= d[k] <= hi: return f"{k}: wartość spoza zakresu {lo}–{hi}"
    if "backup_path" in d:
        p = Path(str(d["backup_path"]).strip() or DEFAULT_CONFIG["backup_path"]).expanduser()
        p = (BACKUP_ROOT / p).resolve() if not p.is_absolute() else p.resolve()
        if not p.is_relative_to(BACKUP_ROOT):
            return f"backup_path: katalog kopii musi leżeć w {BACKUP_ROOT}"
        d["backup_path"] = str(p)
    return None

# ── I/O ────────────────────────────────────────────────────────────────────────
_lock = threading.Lock()

def _r(path, default=None):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except FileNotFoundError:
        pass
    except (OSError, json.JSONDecodeError) as e:
        log.error("Nie można odczytać %s — używam wartości domyślnej: %s", path, e)
    return default if default is not None else {}

def _w(path, data):
    # Zapis przez plik tymczasowy i os.replace — przerwany zapis nie uszkadza pliku (US-006)
    tmp = Path(str(path) + ".tmp")
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise

def load_workers():  return _r(WORKERS_FILE, {})
def save_workers(d): _w(WORKERS_FILE, d)
def load_strefy():   return _r(STREFY_FILE, {})
def save_strefy(d):  _w(STREFY_FILE, d)
def load_admins():
    # wartość: {"hash", "must_change"}; stary format (sam skrót jako tekst) jest podnoszony w locie
    return {u: (v if isinstance(v, dict) else {"hash": v, "must_change": False})
            for u, v in _r(ADMINS_FILE, {}).items()}
def save_admins(d):  _w(ADMINS_FILE, d)
def load_config():   return _r(CONFIG_FILE, DEFAULT_CONFIG)
def save_config(d):  _w(CONFIG_FILE, d)
def load_korekty():  return _r(KOREKTY_FILE, [])
def save_korekty(d): _w(KOREKTY_FILE, d)
def load_nadwyzki(): return _r(NADWYZKI_FILE, [])
def save_nadwyzki(d):_w(NADWYZKI_FILE, d)

def load_grafik():   return _r(GRAFIK_FILE, {})
def save_grafik(d):  _w(GRAFIK_FILE, d)

# ── GRAFIK helpers ─────────────────────────────────────────────────────────────

_SHIFT_MAP = {
    "r": ("05:00","13:00"), "ranna": ("05:00","13:00"),
    "p": ("13:00","21:00"), "popoł": ("13:00","21:00"), "popołudniowa": ("13:00","21:00"),
    "n": ("21:00","05:00"), "noc":   ("21:00","05:00"), "nocna": ("21:00","05:00"),
}

def parse_shift(val):
    """Zamienia wartość komórki Excela na {od, do, typ}.
    Obsługuje: R/P/N, 05-13, 05:00-13:00, wolne/W/-/puste."""
    if val is None:
        return {"od": None, "do": None, "typ": "W"}
    s = str(val).strip().lower().replace(" ", "")
    if not s or s in ("-", "–", "w", "wolne", "x"):
        return {"od": None, "do": None, "typ": "W"}
    if s in _SHIFT_MAP:
        od, do = _SHIFT_MAP[s]
        return {"od": od, "do": do, "typ": "P"}
    # format HH-HH lub HH:MM-HH:MM
    m = re.match(r'^(\d{1,2})(?::(\d{2}))?[-–](\d{1,2})(?::(\d{2}))?$', s)
    if m:
        h1, m1, h2, m2 = m.groups()
        od = f"{int(h1):02d}:{m1 or '00'}"
        do = f"{int(h2):02d}:{m2 or '00'}"
        return {"od": od, "do": do, "typ": "P"}
    return {"od": None, "do": None, "typ": "W"}

def _data_z_naglowka(s, ref):
    """Data z nagłówka grafiku: YYYY-MM-DD, DD.MM.YYYY, DD.MM (bieżący rok) albo sam dzień (bieżący miesiąc)."""
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        with suppress(ValueError):
            return datetime.strptime(s, fmt).date()
    with suppress(ValueError):
        return datetime.strptime(s, "%d.%m").date().replace(year=ref.year)
    with suppress(ValueError):
        day = int(float(s))
        if 1 <= day <= 31:
            return date(ref.year, ref.month, day)
    return None

def import_grafik_excel(file_bytes, workers):
    """Parsuje plik Excel z grafikiem.
    Oczekiwany format:
      Wiersz 1: nagłówki — kolumna A = 'Pracownik', kolejne = daty (YYYY-MM-DD lub DD.MM.YYYY lub DD)
      Kolejne wiersze: kolumna A = imię i nazwisko, kolejne = kody zmian.
    Zwraca (grafik_patch, bledy)."""
    wb = openpyxl.load_workbook(BytesIO(file_bytes), data_only=True)
    ws = wb.active

    # buduj mapę imię→kod (porównujemy upper bez spacji)
    name_map = {}
    for kod, w in workers.items():
        key = w.get("imie","").upper().replace(" ","")
        if key:
            name_map[key] = kod

    rows = list(ws.iter_rows(values_only=True))
    if len(rows) < 2:
        return {}, ["Plik jest pusty lub ma tylko jeden wiersz"]

    header = rows[0]
    # wykryj daty z nagłówka (od kolumny B wzwyż)
    col_dates = {}   # col_index → date_iso
    ref = date.today()
    for ci, cell in enumerate(header[1:], start=1):
        if cell is None:
            continue
        d = _data_z_naglowka(str(cell).strip(), ref)
        if d:
            col_dates[ci] = d.isoformat()

    if not col_dates:
        return {}, ["Nie wykryto dat w nagłówku. Upewnij się że wiersz 1 zawiera daty (np. 2026-05-01 lub 01.05.2026 lub 1)."]

    grafik_patch = {}
    bledy = []

    for ri, row in enumerate(rows[1:], start=2):
        if not row or row[0] is None:
            continue
        name_raw = str(row[0]).strip()
        key = name_raw.upper().replace(" ","")
        kod = name_map.get(key)
        if not kod:
            # próba częściowego dopasowania (samo nazwisko)
            parts = name_raw.upper().split()
            for p in parts:
                for k, v in name_map.items():
                    if p in k:
                        kod = v; break
                if kod: break
        if not kod:
            bledy.append(f"Wiersz {ri}: nie znaleziono pracownika '{name_raw}'")
            continue

        if kod not in grafik_patch:
            grafik_patch[kod] = {}
        for ci, date_iso in col_dates.items():
            if ci < len(row):
                grafik_patch[kod][date_iso] = parse_shift(row[ci])

    return grafik_patch, bledy

def load_state():
    return _r(STATE_FILE, {})

def save_state(d):
    _w(STATE_FILE, d)

# ── CSV helpers ────────────────────────────────────────────────────────────────
def get_csv_paths(ts: datetime):
    day   = ts.strftime("%Y-%m-%d")
    month = ts.strftime("%Y-%m")
    daily   = DATA_DIR / f"ewidencja_{day}.csv"
    monthly = DATA_DIR / f"ewidencja_{month}.csv"
    return daily, monthly

def ensure_csv(path):
    if not path.exists():
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow(CSV_HEADERS)

def _csv_safe(v):
    """Pole zaczynające się od = + - @ lub tabulatora dostaje apostrof — Excel nie wykona go jako formuły (B8)."""
    return "'" + v if isinstance(v, str) and v and v[0] in "=+-@\t\r" else v

def append_csv_row(row: dict, ts: datetime):
    daily, monthly = get_csv_paths(ts)
    row = {k: _csv_safe(v) for k, v in row.items()}
    for path in (daily, monthly):
        ensure_csv(path)
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADERS, delimiter=";").writerow(row)

def next_id(ts: datetime):
    _, monthly = get_csv_paths(ts)
    try:
        with open(monthly, encoding="utf-8-sig") as f:
            return sum(1 for _ in f)
    except OSError: return 1

def read_csv_rows(path: Path):
    if not Path(path).exists():
        return []
    try:
        with open(path, encoding="utf-8-sig") as f:
            return list(csv.DictReader(f, delimiter=";"))
    except OSError as e:
        log.error("Nie można odczytać %s: %s", path, e)
        return []

# ── Alerts CSV ────────────────────────────────────────────────────────────────
ALERTS_FILE_PATH = DATA_DIR / "alerty.csv"
ALERTS_HEADERS   = ["ts","pracownik","imie","typ","opis","potwierdzone"]

def ensure_alerts():
    if not ALERTS_FILE_PATH.exists():
        with open(ALERTS_FILE_PATH, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow(ALERTS_HEADERS)

def append_alert(pracownik, imie, typ, opis):
    ensure_alerts()
    with open(ALERTS_FILE_PATH, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerow(
            [_csv_safe(v) for v in (datetime.now().isoformat(), pracownik, imie, typ, opis, "NIE")])

# ── Dziennik audytu (US-012) ──────────────────────────────────────────────────
AUDYT_FILE_PATH = DATA_DIR / "audyt.csv"
AUDYT_HEADERS   = ["ts", "admin", "akcja", "obiekt", "szczegoly"]

def zapisz_audyt(akcja, obiekt="", szczegoly=""):
    """Kto, kiedy, co zmienił w panelu — plik tylko dopisywany, bez edycji z aplikacji."""
    if not AUDYT_FILE_PATH.exists():
        with open(AUDYT_FILE_PATH, "w", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerow(AUDYT_HEADERS)
    with open(AUDYT_FILE_PATH, "a", newline="", encoding="utf-8-sig") as f:
        csv.writer(f, delimiter=";").writerow([_csv_safe(v) for v in (
            datetime.now().isoformat(timespec="seconds"), (session.get("admin_user", "?") if has_request_context() else "system"), akcja, obiekt, szczegoly)])

def read_audyt(limit=200):
    return list(reversed(read_csv_rows(AUDYT_FILE_PATH)[-limit:]))

def read_alerts(limit=100):
    rows = read_csv_rows(ALERTS_FILE_PATH)
    return list(reversed(rows[-limit:]))

# ── Helpers ────────────────────────────────────────────────────────────────────
def pad(n): return str(n).zfill(2)

def fmt_czas(minutes):
    total_s = int(abs(minutes) * 60)
    h = total_s // 3600
    m = (total_s % 3600) // 60
    s = total_s % 60
    return f"{pad(h)}:{pad(m)}:{pad(s)}"

def mins_since(ts_str):
    try: return (datetime.now() - datetime.fromisoformat(ts_str)).total_seconds() / 60
    except (TypeError, ValueError): return 0

def hash_pw(pw): return generate_password_hash(pw)
def verify_pw(pw, hashed): return check_password_hash(hashed, pw)
def is_admin():  return session.get("admin_logged") is True

# ── Ochrona logowania i formularzy (US-003) ───────────────────────────────────
LOGIN_LIMIT, LOGIN_WINDOW_MIN, LOGIN_BLOCK_MIN = 5, 10, 15
_login_fail = {}   # adres -> czasy nieudanych prób; ponytail: pamięć jednego procesu, przy replikach wspólny magazyn

def _client_ip():
    if PROXY and request.headers.get("X-Forwarded-For"):
        return request.headers["X-Forwarded-For"].split(",")[0].strip()
    return request.remote_addr or "?"

def _login_blocked(ip):
    fails = _login_fail.get(ip, [])
    return len(fails) >= LOGIN_LIMIT and time_module.time() - fails[-1] < LOGIN_BLOCK_MIN * 60

def _login_failed(ip):
    now = time_module.time()
    _login_fail[ip] = [t for t in _login_fail.get(ip, []) if now - t < LOGIN_WINDOW_MIN * 60] + [now]

# ── Limit żądań publicznych endpointów skanera (kod pracownika to jedyne uwierzytelnienie) ──
SCAN_RATE_MAX, SCAN_RATE_WINDOW_S = 120, 60          # wszystkie żądania z adresu: 120 / min
SCAN_FAIL_MAX, SCAN_FAIL_WINDOW_S = 20, 10 * 60      # nieznane kody z adresu: 20 / 10 min
_scan_hits, _scan_fails = {}, {}                     # adres -> czasy żądań / nieudanych prób (pamięć jednego procesu)
_scan_guard = threading.Lock()

def _scan_prune(store, ip, now, window):
    times = [t for t in store.get(ip, []) if now - t < window]
    if times: store[ip] = times
    else: store.pop(ip, None)
    return times

def _scan_over_limit():
    """Rejestruje żądanie; True gdy adres przekroczył limit ogólny lub limit nieznanych kodów (żądanie nie jest wtedy liczone)."""
    ip, now = _client_ip(), time_module.time()
    with _scan_guard:
        fails = _scan_prune(_scan_fails, ip, now, SCAN_FAIL_WINDOW_S)
        hits = _scan_prune(_scan_hits, ip, now, SCAN_RATE_WINDOW_S)
        if len(fails) >= SCAN_FAIL_MAX or len(hits) >= SCAN_RATE_MAX:
            return True
        _scan_hits[ip] = hits + [now]
    return False

def _scan_failed():
    ip, now = _client_ip(), time_module.time()
    with _scan_guard:
        _scan_fails[ip] = _scan_prune(_scan_fails, ip, now, SCAN_FAIL_WINDOW_S) + [now]

def _scan_limit_response():
    return jsonify({"ok": False, "error": "Zbyt wiele prób. Spróbuj ponownie za kilka minut."}), 429

def _body():
    """Treść JSON jako słownik; lista, liczba lub null dają {} (publiczne endpointy nie mogą kończyć się 500)."""
    d = request.get_json(silent=True)
    return d if isinstance(d, dict) else {}

def _txt(v):
    return v.strip() if isinstance(v, str) else ""

def csrf_token():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]

app.jinja_env.globals["csrf_token"] = csrf_token

# Formularze HTML i multipart z panelu; JSON API chroni SameSite=Lax i wymóg Content-Type: application/json
CSRF_FORMS = {"admin_login", "admin_haslo", "adm_grafik_import", "wejscie"}

@app.before_request
def sprawdz_csrf():
    if request.method == "POST" and request.endpoint in CSRF_FORMS:
        token = request.form.get("csrf") or request.headers.get("X-CSRF-Token")
        if not token or token != session.get("csrf"):
            return "Nieprawidłowy token formularza — odśwież stronę i spróbuj ponownie.", 403

def _konto_startowe(user):
    """Hasło startowe z RCP_ADMIN_PASSWORD; bez zmiennej losowe, wypisane raz w logu (US-001).
    Konto wymusza zmianę hasła przy pierwszym zalogowaniu."""
    pw = os.environ.get("RCP_ADMIN_PASSWORD") or secrets.token_urlsafe(12)
    if not os.environ.get("RCP_ADMIN_PASSWORD"):
        log.warning("Hasło startowe konta '%s': %s  — jednorazowe, zmiana wymuszona przy logowaniu", user, pw)
    return {"hash": hash_pw(pw), "must_change": True}

def _minuty(v):
    """Pole czas_min z CSV jako liczba; puste lub uszkodzone pole liczy się jako 0."""
    try: return float(v or 0)
    except (TypeError, ValueError): return 0.0

def get_dzien_min(pracownik, dt=None):
    dt = dt or datetime.now()
    daily, _ = get_csv_paths(dt)
    return sum(_minuty(row.get("czas_min")) for row in read_csv_rows(daily) if row.get("pracownik") == pracownik)

def zamknij_pobyt(kod, imie, sesja, ts_wyj, korekta_info="", flaga=None):
    """Jedno miejsce zamykania pobytu dla skanera, administratora i auto-zamknięcia (US-005):
    wpis ewidencji, flaga długiej przerwy, nadwyżka i alert — niezależnie od tego, kto zamyka.
    Wywoływać pod _lock. Zwraca listę alertów dla ekranu potwierdzenia."""
    ts_in  = datetime.fromisoformat(sesja["ts_wejscia"])
    czas_m = round((ts_wyj - ts_in).total_seconds() / 60, 2)
    prog   = load_config().get("prog_przerwa_min", PROG_PRZERWA)
    dluga  = sesja["strefa"] == "PRZERWA" and czas_m > prog
    append_csv_row({
        "id":            next_id(ts_in),
        "pracownik":     kod,
        "imie_nazwisko": imie,
        "strefa":        sesja["strefa"],
        "podstrefa":     sesja.get("podstrefa", ""),
        "ts_wejscia":    sesja["ts_wejscia"],
        "ts_wyjscia":    ts_wyj.isoformat(timespec="seconds"),
        "czas_min":      czas_m,
        "czas_fmt":      fmt_czas(czas_m),
        "flaga":         flaga or ("DLUGA_PRZERWA" if dluga else ""),
        "korekta_info":  korekta_info,
    }, ts_in)
    if not dluga:
        return []
    nadwyzka_min = round(czas_m - prog, 2)
    nadwyzki = load_nadwyzki()
    nadwyzki.append({
        "id":               len(nadwyzki) + 1,
        "pracownik":        kod,
        "imie":             imie,
        "ts_przerwy":       sesja["ts_wejscia"],
        "czas_przerwy_min": czas_m,
        "czas_przerwy_fmt": fmt_czas(czas_m),
        "nadwyzka_min":     nadwyzka_min,
        "nadwyzka_fmt":     fmt_czas(nadwyzka_min),
        "przypisana_strefa": None,
        "status":           "oczekuje",
    })
    save_nadwyzki(nadwyzki)
    append_alert(kod, imie, "DLUGA_PRZERWA", f"{imie} przerwa {fmt_czas(czas_m)} | nadwyzka {fmt_czas(nadwyzka_min)}")
    return [{"typ": "DLUGA_PRZERWA", "opis": f"Przerwa trwała {fmt_czas(czas_m)} (nadwyżka: {fmt_czas(nadwyzka_min)})"}]

def sprawdz_strefe(worker, strefa):
    """Strefa docelowa musi istnieć w słowniku i być na liście uprawnień pracownika (T9).
    Zwraca (komunikat, kod HTTP) albo None, gdy wszystko gra."""
    if strefa not in load_strefy():
        return f"Nieznana strefa {strefa}", 400
    if strefa not in [s.upper() for s in worker.get("strefy", [])]:
        return f"Brak uprawnień do strefy {strefa}", 403
    return None

# ── INIT ───────────────────────────────────────────────────────────────────────
def init_files():
    ensure_alerts()
    if not STREFY_FILE.exists():  save_strefy(DEFAULT_STREFY)
    if not CONFIG_FILE.exists():  save_config(DEFAULT_CONFIG)
    if not KOREKTY_FILE.exists(): save_korekty([])
    if not NADWYZKI_FILE.exists():save_nadwyzki([])
    if not STATE_FILE.exists():   save_state({})
    if not WORKERS_FILE.exists():
        save_workers({
            "HU_KOWALSKI_JAN":     {"imie":"Kowalski Jan",    "strefy":["PICKING","PRZYJECIA","KURIER1","PRZERWA"]},
            "HU_NOWAK_ANNA":       {"imie":"Nowak Anna",      "strefy":["KURIER1","KURIER2","BUS","PRZERWA"]},
            "HU_WISNIEWSKI_PIOTR": {"imie":"Wisniewski Piotr","strefy":["PICKING","INV","PRZERWA"]},
        })
    if not ADMINS_FILE.exists():
        save_admins({"admin": _konto_startowe("admin")})
    else:
        # Konta ze skrótem w starym formacie (SHA-256, 64 znaki hex) dostają nowe hasło startowe
        adm   = load_admins()
        stare = [u for u, v in adm.items()
                 if len(v["hash"]) == 64 and all(c in "0123456789abcdef" for c in v["hash"])]
        for u in stare:
            adm[u] = _konto_startowe(u)
        if stare:
            save_admins(adm)

init_files()

# ── BACKUP THREAD ──────────────────────────────────────────────────────────────
_last_backup = None

def _przebieg(nazwa, fn):
    """Jeden przebieg zadania w tle: wyjątek trafia do logu, wątek działa dalej (US-010). Zwraca True, gdy się udał."""
    try:
        fn()
        return True
    except Exception:
        log.exception("%s: błąd przebiegu, wątek działa dalej", nazwa)
        return False

def kopia_zapasowa(now=None):
    """Kopiuje wszystkie pliki CSV i JSON do katalogu z konfiguracji, z prefiksem daty i godziny."""
    now  = now or datetime.now()
    dest = Path(load_config().get("backup_path", BASE_DIR / "backup"))
    dest.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d_%H%M")
    for f in list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.json")):
        shutil.copy2(f, dest / f"{stamp}_{f.name}")
    log.info("Kopia zapasowa zapisana w %s", dest)

def _przytnij_csv(path, naglowki, dni, now):
    """Usuwa z pliku wiersze z kolumną ts starszą niż `dni`; przepisanie przez plik tymczasowy."""
    rows = read_csv_rows(path)
    granica = (now - timedelta(days=dni)).isoformat()
    zostaja = [r for r in rows if (r.get("ts") or "") >= granica]
    if len(zostaja) == len(rows): return 0
    tmp = Path(str(path) + ".tmp")
    with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=naglowki, delimiter=";", extrasaction="ignore")
        w.writeheader(); w.writerows(zostaja)
    os.replace(tmp, path)
    return len(rows) - len(zostaja)

def retencja(now=None):
    """Usuwa dane po okresach z konfiguracji (US-009): całe pliki ewidencji dnia/miesiąca, wiersze alertów
    i audytu, stare kopie zapasowe. Każde usunięcie trafia do logu i do dziennika audytu."""
    now, cfg, usuniete = now or datetime.now(), load_config(), []
    dni = cfg.get("retencja_ewidencja_dni", 0)
    if dni:
        granica = (now - timedelta(days=dni)).date()
        for f in DATA_DIR.glob("ewidencja_*.csv"):
            stem = f.stem.replace("ewidencja_", "")
            try:
                koniec = (date.fromisoformat(stem) if len(stem) == 10
                          else (date.fromisoformat(stem + "-01") + timedelta(days=31)).replace(day=1) - timedelta(days=1))
            except ValueError:
                continue
            if koniec < granica:
                f.unlink(); usuniete.append(f.name)
    for path, nagl, klucz in ((ALERTS_FILE_PATH, ALERTS_HEADERS, "retencja_alerty_dni"),
                              (AUDYT_FILE_PATH, AUDYT_HEADERS, "retencja_audyt_dni")):
        if cfg.get(klucz, 0) and path.exists() and (n := _przytnij_csv(path, nagl, cfg[klucz], now)):
            usuniete.append(f"{path.name}: {n} wierszy")
    dni = cfg.get("retencja_kopie_dni", 0)
    dest = Path(cfg.get("backup_path", BASE_DIR / "backup"))
    if dni and dest.is_dir():
        granica = (now - timedelta(days=dni)).strftime("%Y%m%d")
        for f in dest.iterdir():
            if f.is_file() and f.name[:8].isdigit() and f.name[:8] < granica:
                f.unlink(); usuniete.append(f"kopia {f.name}")
    for u in usuniete:
        log.info("Retencja: usunięto %s", u)
    if usuniete:
        zapisz_audyt("retencja", "", "; ".join(usuniete)[:2000])
    return usuniete

def backup_job():
    # Kopia raz na dobę: o 02:00 albo — jeśli serwer wtedy nie działał — przy pierwszym przebiegu po 02:00 (T11).
    # Po kopii przebieg retencji (US-009).
    global _last_backup
    while True:
        time_module.sleep(60)
        now = datetime.now()
        if _last_backup == now.date() or now.hour < 2: continue
        if _przebieg("kopia zapasowa", kopia_zapasowa):
            _last_backup = now.date()
            _przebieg("retencja", retencja)

if not DEMO: threading.Thread(target=backup_job, daemon=True).start()

# ── ALERT CHECKER ──────────────────────────────────────────────────────────────
_active_alerts = {}   # {pracownik: True} — alerty które jeszcze nie były "odczytane"

def kontrola_pobytow(now=None):
    """Jeden przebieg kontroli w tle: alerty długiej przerwy i dyżuru, auto-zamknięcie pobytów
    z poprzednich dni o 23:59:59 dnia wejścia. Wydzielone z pętli, żeby dało się przetestować."""
    workers       = load_workers()
    cfg           = load_config()
    prog_przerwa  = cfg.get("prog_przerwa_min", PROG_PRZERWA)
    alert_dyżur_h = cfg.get("alert_dlugi_dyżur_h", ALERT_DYZUR_H)
    now           = now or datetime.now()
    today         = now.date()
    with _lock:
        state    = _r(STATE_FILE, {})
        changed  = False
        to_close = []

        for kod, sess in state.items():
            imie   = workers.get(kod, {}).get("imie", kod)
            m      = (now - datetime.fromisoformat(sess["ts_wejscia"])).total_seconds() / 60
            ts_wej = datetime.fromisoformat(sess["ts_wejscia"])

            # --- Alert długa przerwa ---
            if sess["strefa"] == "PRZERWA" and m > prog_przerwa and not sess.get("alert_wyslany"):
                opis = f"{imie} na przerwie {fmt_czas(m)} (prog {prog_przerwa} min)"
                append_alert(kod, imie, "DLUGA_PRZERWA", opis)
                _active_alerts[kod] = {"typ":"DLUGA_PRZERWA","opis":opis,"ts":now.isoformat()}
                state[kod]["alert_wyslany"] = True
                changed = True

            # --- Alert długi dyżur (każda strefa) ---
            if m > alert_dyżur_h * 60 and not sess.get("alert_dlugi_dyżur"):
                opis = f"{imie} w strefie {sess['strefa']} od {fmt_czas(m)}"
                append_alert(kod, imie, "DLUGI_DYZUR", opis)
                _active_alerts[kod] = {"typ":"DLUGI_DYZUR","opis":opis,"ts":now.isoformat()}
                state[kod]["alert_dlugi_dyżur"] = True
                changed = True

            # --- Auto-zamknięcie o północy dnia rozpoczęcia ---
            # Pobyt z poprzedniego dnia (lub starszych) → zamknij o 23:59:59 tamtego dnia
            if ts_wej.date() < today:
                to_close.append((kod, sess, imie, ts_wej))

        for kod, sess, imie, ts_wej in to_close:
            ts_wyj = datetime(ts_wej.year, ts_wej.month, ts_wej.day, 23, 59, 59)
            zamknij_pobyt(kod, imie, sess, ts_wyj, flaga="AUTO_ZAMKNIETO")
            opis = f"{imie} auto-zamknięto o 23:59 dnia {ts_wej.date()} (strefa {sess['strefa']})"
            append_alert(kod, imie, "AUTO_ZAMKNIETO", opis)
            _active_alerts[kod] = {"typ":"AUTO_ZAMKNIETO","opis":opis,"ts":now.isoformat()}
            del state[kod]
            changed = True

        if changed:
            _w(STATE_FILE, state)

def bg_check():
    while True:
        time_module.sleep(60)
        _przebieg("kontrola pobytów", kontrola_pobytow)

threading.Thread(target=bg_check, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scan", methods=["POST"])
def api_scan():
    if _scan_over_limit(): return _scan_limit_response()
    kod = _txt(_body().get("kod")).upper()
    if not kod:
        return jsonify({"ok":False,"error":"Pusty kod QR"}), 400

    workers = load_workers()
    if kod not in workers:
        _scan_failed()
        append_alert(kod, kod, "NIEZNANY_KOD", f"Proba skanowania: {kod}")
        return jsonify({"ok":False,"error":"Nieznany kod QR. Skontaktuj się z liderem."}), 403

    worker  = workers[kod]
    strefy  = load_strefy()
    state   = load_state()
    sesja   = state.get(kod)
    cfg     = load_config()
    dzien_m = get_dzien_min(kod)

    dozwolone = []
    for nazwa in worker.get("strefy", []):
        s = strefy.get(nazwa, {})
        dozwolone.append({
            "nazwa":     nazwa,
            "kolor":     s.get("kolor","#7f8c8d"),
            "podstrefy": s.get("podstrefy",[]),
        })

    aktywna_min = mins_since(sesja["ts_wejscia"]) if sesja else 0
    ostrzezenie_szybka = False
    if sesja:
        prog_szybka = cfg.get("ostrzezenie_szybka_zmiana_min", 5)
        ostrzezenie_szybka = aktywna_min < prog_szybka

    return jsonify({
        "ok":                  True,
        "pracownik":           kod,
        "imie_nazwisko":       worker["imie"],
        "dozwolone":           dozwolone,
        "aktywna_strefa":      sesja["strefa"]        if sesja else None,
        "aktywna_podstrefa":   sesja.get("podstrefa") if sesja else None,
        "ts_wejscia":          sesja["ts_wejscia"]    if sesja else None,
        "aktywna_min":         round(aktywna_min, 2),
        "aktywna_fmt":         fmt_czas(aktywna_min),
        "dzien_min":           round(dzien_m, 1),
        "dzien_fmt":           fmt_czas(dzien_m),
        "ostrzezenie_szybka":  ostrzezenie_szybka,
        "szybka_strefa":       sesja["strefa"] if ostrzezenie_szybka else None,
        "szybka_min":          round(aktywna_min, 1) if ostrzezenie_szybka else None,
    })

@app.route("/api/rejestruj", methods=["POST"])
def api_rejestruj():
    if _scan_over_limit(): return _scan_limit_response()
    d         = _body()
    kod       = _txt(d.get("pracownik")).upper()
    nowa_str  = _txt(d.get("strefa")).upper()
    podstrefa = _txt(d.get("podstrefa")).upper()
    korekta   = d.get("korekta_info","")
    force     = d.get("force", False)

    if not kod or not nowa_str:
        return jsonify({"ok":False,"error":"Brak pracownika lub strefy"}), 400

    workers = load_workers()
    if kod not in workers:
        _scan_failed()
        return jsonify({"ok":False,"error":"Nieznany pracownik"}), 403

    worker = workers[kod]

    if nowa_str != "KONIEC_ZMIANY" and nowa_str not in [s.upper() for s in worker.get("strefy",[])]:
        return jsonify({"ok":False,"error":f"Brak uprawnień do strefy {nowa_str}"}), 403

    cfg     = load_config()
    alerts  = []

    # Ostrzeżenie szybka zmiana — czyt. stanu bez locka (tylko ostrzeżenie UX)
    if not force:
        sesja_check = load_state().get(kod)
        if sesja_check:
            prog_szybka = cfg.get("ostrzezenie_szybka_zmiana_min", 5)
            mins_in_current = (datetime.now() - datetime.fromisoformat(sesja_check["ts_wejscia"])).total_seconds() / 60
            if mins_in_current < prog_szybka:
                return jsonify({
                    "ok": False,
                    "wymaga_potwierdzenia": True,
                    "error": f"Byłeś w {sesja_check['strefa']} tylko {fmt_czas(mins_in_current)}. Na pewno zmieniasz strefę?",
                    "mins_in_current": round(mins_in_current, 1),
                }), 409

    with _lock:
        now     = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        state   = _r(STATE_FILE, {})
        sesja   = state.get(kod)

        # Zamknij poprzednią strefę
        if sesja:
            alerts = zamknij_pobyt(kod, worker["imie"], sesja, now, korekta)

        if nowa_str == "KONIEC_ZMIANY":
            state.pop(kod, None)
            _w(STATE_FILE, state)

        else:
            state[kod] = {"strefa":nowa_str,"podstrefa":podstrefa,"ts_wejscia":now_iso}
            _w(STATE_FILE, state)

    if nowa_str == "KONIEC_ZMIANY":
        dzien_min = get_dzien_min(kod)
        return jsonify({"ok":True,"akcja":"koniec_zmiany",
            "imie_nazwisko":worker["imie"],
            "dzien_fmt":fmt_czas(dzien_min),"alerts":alerts})

    dzien_min = get_dzien_min(kod)
    return jsonify({"ok":True,"akcja":"zmiana_strefy",
        "imie_nazwisko":worker["imie"],
        "nowa_strefa":nowa_str,"podstrefa":podstrefa,
        "ts":now_iso,"dzien_fmt":fmt_czas(dzien_min),"alerts":alerts})

@app.route("/api/status")
def api_status():
    if not is_admin(): return "", 401   # obecność z nazwiskami tylko dla administratora (US-002)
    state   = load_state()
    workers        = load_workers()
    now            = datetime.now()
    cfg            = load_config()
    prog           = cfg.get("prog_przerwa_min", PROG_PRZERWA)
    alert_dyżur_h  = cfg.get("alert_dlugi_dyżur_h", ALERT_DYZUR_H)
    wynik          = []
    for kod, sess in state.items():
        m = (now - datetime.fromisoformat(sess["ts_wejscia"])).total_seconds() / 60
        alert_przerwa  = sess["strefa"] == "PRZERWA" and m > prog
        alert_dyzur    = m > alert_dyżur_h * 60
        wynik.append({
            "pracownik":     kod,
            "imie_nazwisko": workers.get(kod,{}).get("imie", kod),
            "strefa":        sess["strefa"],
            "podstrefa":     sess.get("podstrefa",""),
            "ts_wejscia":    sess["ts_wejscia"],
            "czas_min":      round(m, 2),
            "czas_fmt":      fmt_czas(m),
            "alert":         alert_przerwa or alert_dyzur,
            "alert_dyzur":   alert_dyzur,
        })
    wynik.sort(key=lambda x: (-x["alert"], -x["czas_min"]))
    return jsonify(wynik)

# Nowe alerty (dla dźwiękowego powiadomienia w adminie)
@app.route("/api/alerts/new")
def api_new_alerts():
    if not is_admin(): return jsonify([])
    alerts = list(_active_alerts.values())
    _active_alerts.clear()
    return jsonify(alerts)

# Korekta zgłoszenie od pracownika (po skanie)
@app.route("/api/korekta", methods=["POST"])
def api_korekta():
    if _scan_over_limit(): return _scan_limit_response()
    d   = _body()
    kod = _txt(d.get("pracownik")).upper()
    workers = load_workers()
    if kod not in workers:
        _scan_failed()
        return jsonify({"ok":False,"error":"Nieznany pracownik"}), 403
    with _lock:   # numer zgłoszenia i zapis pod blokadą — równoczesne zgłoszenia nie kolidują (US-006)
        korekty = load_korekty()
        korekty.append({
            "id":        len(korekty)+1,
            "pracownik": kod,
            "imie":      workers[kod]["imie"],
            "ts_zgloszenia": datetime.now().isoformat(timespec="seconds"),
            "opis":      d.get("opis",""),
            "status":    "oczekuje",
            "decyzja":   None,
        })
        save_korekty(korekty)
    return jsonify({"ok":True})

# ══════════════════════════════════════════════════════════════════════════════
# ADMIN
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/admin/login", methods=["GET","POST"])
def admin_login():
    err = None
    if request.method == "POST":
        ip = _client_ip()
        if _login_blocked(ip):
            return render_template("admin_login.html",
                error=f"Zbyt wiele nieudanych prób. Spróbuj ponownie za {LOGIN_BLOCK_MIN} min."), 429
        user = request.form.get("username","").strip()
        pw   = request.form.get("password","")
        adm  = load_admins()
        if user in adm and verify_pw(pw, adm[user]["hash"]):
            _login_fail.pop(ip, None)
            session["admin_logged"] = True
            session["admin_user"]   = user
            session["must_change"]  = adm[user]["must_change"]
            zapisz_audyt("logowanie", user, ip)
            return redirect(url_for("admin_panel"))
        _login_failed(ip)
        zapisz_audyt("logowanie_nieudane", user, ip)
        err = "Nieprawidłowy login lub hasło"
    return render_template("admin_login.html", error=err)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

@app.before_request
def wymus_zmiane_hasla():
    # Hasło startowe działa tylko do pierwszego zalogowania — do zmiany panel jest niedostępny (US-001)
    if (session.get("must_change") and request.path.startswith("/admin")
            and request.endpoint not in ("admin_haslo", "admin_logout")):
        return redirect(url_for("admin_haslo"))

@app.route("/admin/haslo", methods=["GET","POST"])
def admin_haslo():
    if not is_admin(): return redirect(url_for("admin_login"))
    err = None
    if request.method == "POST":
        p1 = request.form.get("password","")
        p2 = request.form.get("password2","")
        if len(p1) < 12: err = "Hasło musi mieć co najmniej 12 znaków"
        elif p1 != p2:   err = "Hasła różnią się"
        else:
            adm  = load_admins()
            user = session.get("admin_user")
            if user in adm:
                adm[user] = {"hash": hash_pw(p1), "must_change": False}
                save_admins(adm)
            session["must_change"] = False
            zapisz_audyt("zmiana_hasla", user)
            return redirect(url_for("admin_panel"))
    return render_template("admin_haslo.html", error=err, wymuszona=bool(session.get("must_change")))

@app.route("/admin")
def admin_panel():
    if not is_admin(): return redirect(url_for("admin_login"))
    return render_template("admin.html", admin_user=session.get("admin_user",""))

# Admin status
@app.route("/admin/api/status")
def adm_status():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return api_status()

# Historia
@app.route("/admin/api/historia")
def adm_historia():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    pracownik = request.args.get("pracownik","")
    strefa    = request.args.get("strefa","")
    data_od   = request.args.get("data_od","")
    data_do   = request.args.get("data_do","")

    # Zbierz pliki CSV z zakresu dat
    rows = []
    for f in sorted(DATA_DIR.glob("ewidencja_????-??-??.csv")):
        # Filtr dat
        fname_date = f.stem.replace("ewidencja_","")
        if data_od and fname_date < data_od: continue
        if data_do and fname_date > data_do: continue
        rows.extend(read_csv_rows(f))

    if pracownik: rows = [r for r in rows if pracownik.upper() in r.get("pracownik","").upper()]
    if strefa:    rows = [r for r in rows if strefa.upper() in r.get("strefa","").upper()]

    rows.reverse()
    return jsonify(rows[:500])

# Dashboard dane
@app.route("/admin/api/dashboard")
def adm_dashboard():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    data = request.args.get("data", date.today().isoformat())
    daily, _ = get_csv_paths(datetime.fromisoformat(data))
    rows = read_csv_rows(daily)

    # Czas per strefa
    per_strefa = {}
    for r in rows:
        s = r.get("strefa","")
        per_strefa[s] = per_strefa.get(s,0) + _minuty(r.get("czas_min"))

    # Czas per pracownik
    per_pracownik = {}
    for r in rows:
        p = r.get("imie_nazwisko","")
        per_pracownik[p] = per_pracownik.get(p,0) + _minuty(r.get("czas_min"))

    # Aktywne sesje teraz
    state   = load_state()
    strefy  = load_strefy()
    cfg     = load_config()
    prog    = cfg.get("prog_przerwa_min", PROG_PRZERWA)
    aktywne = len(state)
    na_przerwie    = sum(1 for s in state.values() if s["strefa"]=="PRZERWA")
    alerty_przerwa = sum(1 for k,s in state.items()
                         if s["strefa"]=="PRZERWA" and mins_since(s["ts_wejscia"])>prog)

    # Aktywni per strefa (teraz)
    aktywni_per_strefa = {}
    for sess in state.values():
        sn = sess["strefa"]
        aktywni_per_strefa[sn] = aktywni_per_strefa.get(sn, 0) + 1

    # Scal czas dziś + aktywni + kolor w jeden słownik per strefa
    all_strefy = set(per_strefa) | set(aktywni_per_strefa) | set(strefy)
    strefy_kafelki = []
    for sn in sorted(all_strefy):
        strefy_kafelki.append({
            "strefa":   sn,
            "kolor":    strefy.get(sn, {}).get("kolor", "#555"),
            "aktywni":  aktywni_per_strefa.get(sn, 0),
            "min_dzis": round(per_strefa.get(sn, 0), 1),
        })
    # sortuj: aktywni malejąco, potem czas
    strefy_kafelki.sort(key=lambda x: (-x["aktywni"], -x["min_dzis"]))

    return jsonify({
        "per_strefa":     [{"strefa":k,"min":round(v,1)} for k,v in sorted(per_strefa.items(), key=lambda x:-x[1])],
        "per_pracownik":  [{"imie":k,"min":round(v,1)} for k,v in sorted(per_pracownik.items(), key=lambda x:-x[1])[:15]],
        "strefy_kafelki": strefy_kafelki,
        "aktywne":        aktywne,
        "na_przerwie":    na_przerwie,
        "alerty_przerwa": alerty_przerwa,
        "wpisy_dzis":     len(rows),
    })

# Alerty
@app.route("/admin/api/alerty")
def adm_alerty():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(read_alerts(200))

# Dziennik audytu (US-012): tylko odczyt; plik dopisywany przez zapisz_audyt()
@app.route("/admin/api/audyt")
def adm_audyt():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(read_audyt(200))

# Nadwyżki przerw
@app.route("/admin/api/nadwyzki")
def adm_nadwyzki():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(load_nadwyzki())

@app.route("/admin/api/nadwyzki/<int:nid>/przypisz", methods=["POST"])
def adm_nadwyzka_przypisz(nid):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    strefa = (request.json or {}).get("strefa","").strip().upper()
    if not strefa: return jsonify({"ok":False,"error":"Brak strefy"}), 400
    if strefa not in load_strefy(): return jsonify({"ok":False,"error":f"Nieznana strefa {strefa}"}), 400
    with _lock:   # decyzja pod blokadą; druga decyzja o tej samej pozycji dostaje 409 (T12, US-006)
        nadwyzki = load_nadwyzki()
        n = next((n for n in nadwyzki if n["id"] == nid), None)
        if not n: return jsonify({"ok":False,"error":"Nie znaleziono nadwyżki"}), 404
        if n["status"] != "oczekuje": return jsonify({"ok":False,"error":"Nadwyżka już rozliczona"}), 409
        n["przypisana_strefa"] = strefa
        n["status"] = "przypisana"
        save_nadwyzki(nadwyzki)
        zapisz_audyt("nadwyzka_przypisana", str(nid), f"{n['pracownik']} → {strefa}")
    return jsonify({"ok":True})

# Korekty
@app.route("/admin/api/korekty")
def adm_korekty():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(load_korekty())

@app.route("/admin/api/korekty/<int:kid>", methods=["POST"])
def adm_korekta_decyzja(kid):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    decyzja = (request.json or {}).get("decyzja","")
    with _lock:   # jak przy nadwyżce: 404 / 409 zamiast cichego nadpisania (T12, US-006)
        korekty = load_korekty()
        k = next((k for k in korekty if k["id"] == kid), None)
        if not k: return jsonify({"ok":False,"error":"Nie znaleziono zgłoszenia"}), 404
        if k["status"] != "oczekuje": return jsonify({"ok":False,"error":"Zgłoszenie już rozpatrzone"}), 409
        k["status"]  = "zatwierdzona" if decyzja=="tak" else "odrzucona"
        k["decyzja"] = decyzja
        save_korekty(korekty)
        zapisz_audyt("korekta_decyzja", str(kid), f"{k['pracownik']}: {k['status']}")
    return jsonify({"ok":True})

# ── Naniesienie zatwierdzonej korekty na wpis ewidencji (US-014, D6 → D12) ────────
def _przepisz_csv(path, zmien):
    """Przepisuje plik ewidencji atomowo; `zmien(row)` zwraca nowy wiersz albo None (bez zmian)."""
    rows, trafione = read_csv_rows(path), 0
    for i, r in enumerate(rows):
        nowy = zmien(r)
        if nowy is not None:
            rows[i], trafione = nowy, trafione + 1
    if trafione:
        tmp = Path(str(path) + ".tmp")
        with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS, delimiter=";", extrasaction="ignore")
            w.writeheader()
            w.writerows({k: _csv_safe(v) for k, v in r.items()} for r in rows)
        os.replace(tmp, path)
    return trafione

@app.route("/admin/api/korekty/<int:kid>/wpisy")
def adm_korekta_wpisy(kid):
    """Wpisy pracownika z danego dnia — do wyboru wpisu, na który nanosi się korektę."""
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    k = next((k for k in load_korekty() if k["id"] == kid), None)
    if not k: return jsonify({"ok":False,"error":"Nie znaleziono zgłoszenia"}), 404
    try: dzien = datetime.fromisoformat(request.args.get("data") or k["ts_zgloszenia"][:10])
    except ValueError: return jsonify({"ok":False,"error":"Zła data"}), 400
    daily, _ = get_csv_paths(dzien)
    return jsonify([r for r in read_csv_rows(daily) if r.get("pracownik") == k["pracownik"]])

@app.route("/admin/api/korekty/<int:kid>/nanies", methods=["POST"])
def adm_korekta_nanies(kid):
    """Zmienia wybrany wpis w pliku dziennym i miesięcznym; korekta musi być zatwierdzona albo oczekiwać
    (wtedy zostaja zatwierdzona). Ślad: korekta_info = KOREKTA#<nr>, wpis w audycie ze starą i nową wartością."""
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d = request.json or {}
    try:
        stare_wej = datetime.fromisoformat(d["ts_wejscia"])
        nowe_wej  = datetime.fromisoformat(d.get("nowe_wejscie") or d["ts_wejscia"])
        nowe_wyj  = datetime.fromisoformat(d["nowe_wyjscie"])
    except (KeyError, ValueError):
        return jsonify({"ok":False,"error":"Podaj wpis (ts_wejscia) i poprawne godziny"}), 400
    if not nowe_wej < nowe_wyj:
        return jsonify({"ok":False,"error":"Wyjście musi być późniejsze niż wejście"}), 400
    if not (nowe_wej.date() == nowe_wyj.date() == stare_wej.date()):
        return jsonify({"ok":False,"error":"Korekta nie może przenosić wpisu na inny dzień (D3)"}), 400
    strefa = (d.get("strefa") or "").strip().upper()
    if strefa and strefa not in load_strefy():
        return jsonify({"ok":False,"error":f"Nieznana strefa {strefa}"}), 400
    with _lock:
        korekty = load_korekty()
        k = next((k for k in korekty if k["id"] == kid), None)
        if not k: return jsonify({"ok":False,"error":"Nie znaleziono zgłoszenia"}), 404
        if k["status"] == "odrzucona": return jsonify({"ok":False,"error":"Korekta odrzucona — nie można jej nanieść"}), 409
        if k.get("naniesiona"): return jsonify({"ok":False,"error":"Korekta już naniesiona"}), 409
        stary = {}
        def zmien(r):
            if r.get("pracownik") != k["pracownik"] or r.get("ts_wejscia") != stare_wej.isoformat(timespec="seconds"):
                return None
            stary.update(r)
            czas = round((nowe_wyj - nowe_wej).total_seconds() / 60, 2)
            return {**r, "ts_wejscia": nowe_wej.isoformat(timespec="seconds"), "ts_wyjscia": nowe_wyj.isoformat(timespec="seconds"),
                    "strefa": strefa or r["strefa"], "czas_min": czas, "czas_fmt": fmt_czas(czas), "korekta_info": f"KOREKTA#{kid}"}
        daily, monthly = get_csv_paths(stare_wej)
        if not _przepisz_csv(daily, zmien):
            return jsonify({"ok":False,"error":"Nie znaleziono wpisu pracownika z tą godziną wejścia"}), 404
        _przepisz_csv(monthly, zmien)
        k.update(status="zatwierdzona", decyzja=k.get("decyzja") or "tak", naniesiona=True,
                 wpis=stare_wej.isoformat(timespec="seconds"))
        save_korekty(korekty)
        zapisz_audyt("korekta_naniesiona", str(kid),
                     f"{k['pracownik']}: {stary.get('strefa')} {stary.get('ts_wejscia','')[11:16]}–{stary.get('ts_wyjscia','')[11:16]}"
                     f" → {strefa or stary.get('strefa')} {nowe_wej:%H:%M}–{nowe_wyj:%H:%M}")
    return jsonify({"ok":True})

# ── ADMIN: ręczne zarządzanie sesjami ────────────────────────────────────────
@app.route("/admin/api/move", methods=["POST"])
def adm_move():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d        = request.json or {}
    kod      = d.get("pracownik","").strip().upper()
    nowa_str = d.get("strefa","").strip().upper()
    podstrefa= d.get("podstrefa","").strip().upper()
    if not kod or not nowa_str:
        return jsonify({"ok":False,"error":"Brak pracownika lub strefy"}), 400
    workers = load_workers()
    if kod not in workers:
        return jsonify({"ok":False,"error":"Nieznany pracownik"}), 404
    worker  = workers[kod]
    if nowa_str != "KONIEC_ZMIANY" and (blad := sprawdz_strefe(worker, nowa_str)):
        return jsonify({"ok":False,"error":blad[0]}), blad[1]
    with _lock:
        now     = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        state   = _r(STATE_FILE, {})
        sesja   = state.get(kod)
        if sesja:
            zamknij_pobyt(kod, worker["imie"], sesja, now, f"ADMIN:{session.get('admin_user','?')}")
        if nowa_str == "KONIEC_ZMIANY":
            state.pop(kod, None)
            _w(STATE_FILE, state)
            zapisz_audyt("koniec_zmiany", kod)
            return jsonify({"ok":True,"akcja":"koniec_zmiany","imie_nazwisko":worker["imie"]})
        state[kod] = {"strefa":nowa_str,"podstrefa":podstrefa,"ts_wejscia":now_iso}
        _w(STATE_FILE, state)
    zapisz_audyt("przesuniecie", kod, f"→ {nowa_str}" + (f"/{podstrefa}" if podstrefa else ""))
    return jsonify({"ok":True,"akcja":"zmiana_strefy","imie_nazwisko":worker["imie"],"nowa_strefa":nowa_str})

@app.route("/admin/api/start", methods=["POST"])
def adm_start():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d        = request.json or {}
    kod      = d.get("pracownik","").strip().upper()
    strefa   = d.get("strefa","").strip().upper()
    podstrefa= d.get("podstrefa","").strip().upper()
    workers  = load_workers()
    if kod not in workers: return jsonify({"ok":False,"error":"Nieznany pracownik"}), 404
    if not strefa: return jsonify({"ok":False,"error":"Brak strefy"}), 400
    worker  = workers[kod]
    if blad := sprawdz_strefe(worker, strefa):
        return jsonify({"ok":False,"error":blad[0]}), blad[1]
    now     = datetime.now()
    now_iso = now.isoformat(timespec="seconds")
    with _lock:
        state = _r(STATE_FILE, {})
        sesja = state.get(kod)
        if sesja:
            zamknij_pobyt(kod, worker["imie"], sesja, now, f"ADMIN:{session.get('admin_user','?')}:start_override")
        state[kod] = {"strefa":strefa,"podstrefa":podstrefa,"ts_wejscia":now_iso}
        _w(STATE_FILE, state)
    zapisz_audyt("start_reczny", kod, f"→ {strefa}")
    return jsonify({"ok":True,"imie_nazwisko":worker["imie"],"strefa":strefa})

# Strefy CRUD
@app.route("/admin/api/strefy", methods=["GET"])
def adm_get_strefy():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(load_strefy())

@app.route("/admin/api/strefy",            methods=["POST"])
def adm_add_strefa():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d = request.json or {}
    n = d.get("nazwa","").strip().upper()
    if not n: return jsonify({"ok":False,"error":"Brak nazwy"}), 400
    s = load_strefy(); s[n]={"kolor":d.get("kolor","#185FA5"),"podstrefy":[]}; save_strefy(s)
    zapisz_audyt("strefa_dodana", n)
    return jsonify({"ok":True})

@app.route("/admin/api/strefy/<nazwa>",    methods=["DELETE"])
def adm_del_strefa(nazwa):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    s = load_strefy(); s.pop(nazwa.upper(),None); save_strefy(s)
    zapisz_audyt("strefa_usunieta", nazwa.upper())
    return jsonify({"ok":True})

@app.route("/admin/api/strefy/<nazwa>/podstrefy", methods=["POST"])
def adm_add_pod(nazwa):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    pod = (request.json or {}).get("podstrefa","").strip().upper()
    if not pod: return jsonify({"ok":False,"error":"Brak nazwy"}), 400
    s = load_strefy(); nazwa=nazwa.upper()
    if nazwa not in s: return jsonify({"ok":False,"error":"Brak strefy"}), 404
    if pod not in s[nazwa]["podstrefy"]: s[nazwa]["podstrefy"].append(pod)
    save_strefy(s)
    zapisz_audyt("podstrefa_dodana", nazwa, pod)
    return jsonify({"ok":True})

@app.route("/admin/api/strefy/<nazwa>/podstrefy/<pod>", methods=["DELETE"])
def adm_del_pod(nazwa,pod):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    s = load_strefy(); nazwa=nazwa.upper()
    if nazwa in s:
        s[nazwa]["podstrefy"]=[p for p in s[nazwa]["podstrefy"] if p!=pod.upper()]
        save_strefy(s)
        zapisz_audyt("podstrefa_usunieta", nazwa, pod.upper())
    return jsonify({"ok":True})

# Workers CRUD
@app.route("/admin/api/workers",           methods=["GET"])
def adm_get_workers():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(load_workers())

@app.route("/admin/api/workers",           methods=["POST"])
def adm_add_worker():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d=request.json or {}
    kod=d.get("kod","").strip().upper(); imie=d.get("imie","").strip()
    if not kod or not imie: return jsonify({"ok":False,"error":"Brak kodu lub imienia"}), 400
    if not kod.startswith("HU_"): return jsonify({"ok":False,"error":"Kod musi zaczynać się od HU_"}), 400
    w=load_workers(); w[kod]={"imie":imie,"strefy":[]}; save_workers(w)
    zapisz_audyt("pracownik_dodany", kod, imie)
    return jsonify({"ok":True})

@app.route("/admin/api/workers/<kod>",     methods=["DELETE"])
def adm_del_worker(kod):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    w=load_workers(); kod=kod.upper()
    if kod not in w: return jsonify({"ok":False,"error":"Nie znaleziono"}), 404
    del w[kod]; save_workers(w)
    zapisz_audyt("pracownik_usuniety", kod)
    with _lock:
        s = _r(STATE_FILE, {}); s.pop(kod, None); _w(STATE_FILE, s)
    return jsonify({"ok":True})

@app.route("/admin/api/workers/<kod>/strefy", methods=["PUT"])
def adm_set_worker_strefy(kod):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    lista=request.json or []
    w=load_workers(); kod=kod.upper()
    if kod not in w: return jsonify({"ok":False,"error":"Nie znaleziono"}), 404
    w[kod]["strefy"]=[s.upper() for s in lista]; save_workers(w)
    zapisz_audyt("uprawnienia", kod, ", ".join(w[kod]["strefy"]))
    return jsonify({"ok":True})

# Admins CRUD
@app.route("/admin/api/admins",            methods=["GET"])
def adm_get_admins():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(list(load_admins().keys()))

@app.route("/admin/api/admins",            methods=["POST"])
def adm_add_admin():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d=request.json or {}
    u=d.get("username","").strip(); p=d.get("password","")
    if not u or not p: return jsonify({"ok":False,"error":"Brak danych"}), 400
    a=load_admins(); a[u]={"hash":hash_pw(p),"must_change":False}; save_admins(a)
    zapisz_audyt("admin_dodany", u)
    return jsonify({"ok":True})

@app.route("/admin/api/admins/<user>",     methods=["DELETE"])
def adm_del_admin(user):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    if user==session.get("admin_user"):
        return jsonify({"ok":False,"error":"Nie możesz usunąć własnego konta"}), 400
    a=load_admins(); a.pop(user,None); save_admins(a)
    zapisz_audyt("admin_usuniety", user)
    return jsonify({"ok":True})

# Config
@app.route("/admin/api/config",            methods=["GET"])
def adm_get_config():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    return jsonify(load_config())

@app.route("/admin/api/config",            methods=["POST"])
def adm_save_config():
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    d=request.json or {}
    if blad := sprawdz_konfiguracje(d):
        return jsonify({"ok":False,"error":blad}), 400
    cfg=load_config(); cfg.update(d); save_config(cfg)
    zapisz_audyt("konfiguracja", "", json.dumps(d, ensure_ascii=False))
    return jsonify({"ok":True})

# Eksport
@app.route("/admin/export/<typ>")
def adm_export(typ):
    if not is_admin(): return redirect(url_for("admin_login"))
    today = date.today().isoformat()
    month = date.today().strftime("%Y-%m")
    files = {
        "dzien":   DATA_DIR / f"ewidencja_{today}.csv",
        "miesiac": DATA_DIR / f"ewidencja_{month}.csv",
        "alerty":  ALERTS_FILE_PATH,
        "audyt":   AUDYT_FILE_PATH,
    }
    f = files.get(typ)
    if not f or not f.exists():
        return f"Brak pliku: {f}", 404
    return send_file(f, as_attachment=True, download_name=f.name)

# ══════════════════════════════════════════════════════════════════════════════
# GRAFIK
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/admin/api/grafik/template")
def adm_grafik_template():
    if not is_admin(): return redirect(url_for("admin_login"))
    workers = load_workers()
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grafik"

    hdr_fill = PatternFill("solid", fgColor="1a2535")
    hdr_font = Font(color="e8edf3", bold=True)
    thin     = Side(style="thin", color="2d3f56")
    border   = Border(left=thin, right=thin, top=thin, bottom=thin)

    today = date.today()
    first = today.replace(day=1)
    if first.month == 12:
        last = first.replace(year=first.year+1, month=1, day=1) - timedelta(days=1)
    else:
        last = first.replace(month=first.month+1, day=1) - timedelta(days=1)
    days = [(first + timedelta(days=i)) for i in range((last-first).days+1)]

    # nagłówek
    ws.cell(1,1,"Pracownik").font = hdr_font
    ws.cell(1,1).fill = hdr_fill
    ws.cell(1,1).border = border
    ws.column_dimensions["A"].width = 24
    for ci, d in enumerate(days, start=2):
        c = ws.cell(1, ci, d.strftime("%d.%m.%Y"))
        c.font = hdr_font; c.fill = hdr_fill; c.border = border
        c.alignment = Alignment(horizontal="center")
        ws.column_dimensions[get_column_letter(ci)].width = 12

    # legenda w wierszu 2
    ws.cell(2,1,"LEGENDA →").font = Font(italic=True, color="7a90a8")
    for ci, (code, desc) in enumerate([
        ("R","05:00-13:00"),("P","13:00-21:00"),("N","21:00-05:00"),("W","Wolne")
    ], start=2):
        ws.cell(2, ci, f"{code} = {desc}").font = Font(italic=True, color="7a90a8")

    # wiersze pracowników
    for ri, w in enumerate(workers.values(), start=3):
        ws.cell(ri, 1, w.get("imie","")).border = border

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    fn = f"grafik_szablon_{today.strftime('%Y-%m')}.xlsx"
    return send_file(buf, as_attachment=True, download_name=fn,
                     mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")


@app.route("/admin/api/grafik/import", methods=["POST"])
def adm_grafik_import():
    if not is_admin(): return jsonify({"ok":False,"error":"Brak dostępu"}), 403
    f = request.files.get("file")
    if not f:
        return jsonify({"ok":False,"error":"Brak pliku"}), 400
    if not (f.filename or "").lower().endswith(".xlsx"):
        return jsonify({"ok":False,"error":"Wymagany plik .xlsx (szablon z przycisku „Pobierz szablon”)"}), 400
    workers = load_workers()
    try:
        patch, bledy = import_grafik_excel(f.read(), workers)
    except Exception as e:   # uszkodzony lub podrobiony plik: openpyxl/zipfile rzucają różne typy (T6 / US-011)
        log.warning("Import grafiku odrzucony (%s): %s", f.filename, e)
        return jsonify({"ok":False,"error":"Nieprawidłowy plik .xlsx — nie udało się go odczytać"}), 400
    if patch:
        grafik = load_grafik()
        for kod, dni in patch.items():
            if kod not in grafik:
                grafik[kod] = {}
            grafik[kod].update(dni)
        save_grafik(grafik)
        zapisz_audyt("grafik_import", f.filename, f"{sum(len(v) for v in patch.values())} wpisów, {len(patch)} pracowników")
    return jsonify({"ok": bool(patch), "zaimportowano": sum(len(v) for v in patch.values()),
                    "pracownicy": len(patch), "bledy": bledy})


@app.route("/admin/api/grafik", methods=["GET"])
def adm_grafik_get():
    if not is_admin(): return jsonify({"ok":False}), 403
    month = request.args.get("month", date.today().strftime("%Y-%m"))
    grafik  = load_grafik()
    workers = load_workers()
    wynik   = {}
    for kod, dni in grafik.items():
        month_dni = {d: v for d, v in dni.items() if d.startswith(month)}
        if month_dni:
            wynik[kod] = {"imie": workers.get(kod,{}).get("imie",kod), "dni": month_dni}
    # dodaj pracowników bez grafiku w tym miesiącu
    for kod, w in workers.items():
        if kod not in wynik:
            wynik[kod] = {"imie": w.get("imie",kod), "dni": {}}
    return jsonify(wynik)


@app.route("/admin/api/grafik/entry", methods=["POST"])
def adm_grafik_entry():
    if not is_admin(): return jsonify({"ok":False}), 403
    d = request.json or {}
    kod      = d.get("pracownik","").strip()
    date_iso = d.get("data","").strip()
    shift    = d.get("shift","")
    if not kod or not date_iso:
        return jsonify({"ok":False,"error":"Brak danych"}), 400
    grafik = load_grafik()
    if kod not in grafik:
        grafik[kod] = {}
    grafik[kod][date_iso] = parse_shift(shift) if shift else {"od":None,"do":None,"typ":"W"}
    save_grafik(grafik)
    zapisz_audyt("grafik_edycja", kod, f"{date_iso}: {shift or 'W'}")
    return jsonify({"ok":True})


@app.route("/admin/api/grafik/porownanie", methods=["GET"])
def adm_grafik_porownanie():
    if not is_admin(): return jsonify({"ok":False}), 403
    month   = request.args.get("month", date.today().strftime("%Y-%m"))
    grafik  = load_grafik()
    workers = load_workers()
    cfg     = load_config()
    tolerancja = cfg.get("grafik_tolerancja_min", 15)

    # scany z CSV tego miesiąca
    try:
        ref_dt = datetime.strptime(month + "-01", "%Y-%m-%d")
    except ValueError:
        return jsonify({"ok":False,"error":"Zły format miesiąca"}), 400
    _, monthly_path = get_csv_paths(ref_dt)
    rows = read_csv_rows(monthly_path) if monthly_path.exists() else []

    # grupuj po (kod, date_iso) → pierwsza sesja (najwcześniejsza)
    first_scan = {}
    for row in rows:
        ts_str = row.get("ts_wejscia","")
        if not ts_str: continue
        try:
            dt  = datetime.fromisoformat(ts_str)
            key = (row["pracownik"], dt.date().isoformat())
            if key not in first_scan or ts_str < first_scan[key]["ts"]:
                first_scan[key] = {"ts": ts_str, "strefa": row.get("strefa","")}
        except (KeyError, ValueError):
            log.warning("Porównanie z grafikiem: pomijam wpis z nieczytelnym czasem wejścia %r", ts_str)

    today_iso = date.today().isoformat()
    wynik = {}
    for kod, dni in grafik.items():
        month_dni = {d: v for d, v in dni.items() if d.startswith(month)}
        if not month_dni: continue
        imie = workers.get(kod,{}).get("imie", kod)
        wynik[kod] = {"imie": imie, "dni": {}}
        for date_iso, zaplan in month_dni.items():
            if zaplan["typ"] == "W":
                wynik[kod]["dni"][date_iso] = {"zaplanowano": zaplan, "status":"wolne",
                                               "pierwsza":"", "spoznienie":None}
                continue
            scan = first_scan.get((kod, date_iso))
            if not scan:
                status = "nieobecnosc" if date_iso <= today_iso else "planowane"
                wynik[kod]["dni"][date_iso] = {"zaplanowano": zaplan, "status": status,
                                               "pierwsza":"", "spoznienie":None}
                continue
            spoznienie = None
            status     = "obecny"
            if zaplan.get("od"):
                try:
                    h, m = map(int, zaplan["od"].split(":"))
                    ts_scan   = datetime.fromisoformat(scan["ts"])
                    ts_plan   = datetime(ts_scan.year, ts_scan.month, ts_scan.day, h, m)
                    diff_min  = (ts_scan - ts_plan).total_seconds() / 60
                    spoznienie = round(diff_min, 1)
                    status = "na_czas" if diff_min <= tolerancja else "spoznienie"
                except ValueError: status = "obecny"   # nieczytelna godzina zmiany w grafiku
            wynik[kod]["dni"][date_iso] = {"zaplanowano": zaplan, "status": status,
                                           "pierwsza": scan["ts"], "spoznienie": spoznienie}
    return jsonify(wynik)


# ══════════════════════════════════════════════════════════════════════════════
# BRAMKA GOŚCI DEMO (DEMO_VISITOR_GATE)
# ══════════════════════════════════════════════════════════════════════════════
# Miękka kontrola odwiedzin: pierwsza wizyta na stronach HTML (skaner, panel) wymaga przedstawienia się.
# /api/*, pliki statyczne i /login nie są blokowane. Domyślnie włączona tylko w trybie demo.
VISITOR_GATE = os.environ.get("DEMO_VISITOR_GATE", "1" if DEMO else "0").lower() in ("1", "true", "yes", "on")
GOSCIE_FILE = DATA_DIR / "goscie.csv"
GOSCIE_HEADERS = ["created_at", "imie", "nazwisko", "firma"]   # bez IP i user-agenta (minimalizacja danych)
GOSCIE_RETENTION_DAYS, GOSCIE_SESSION_DAYS = 90, 30
GATED_ENDPOINTS = {"index", "admin_panel", "admin_login"}

def _pole_goscia(v):
    """Pole formularza: tekst 2–100 znaków po przycięciu, bez znaków sterujących; inaczej None."""
    v = _txt(v)
    if not 2 <= len(v) <= 100 or any(ord(ch) < 32 or 0x7f <= ord(ch) < 0xa0 for ch in v):
        return None
    return v

def _bezpieczny_next(v):
    """Tylko ścieżka względna w tej aplikacji (bez //host, bez backslasha i znaków sterujących) — inaczej strona główna."""
    if (isinstance(v, str) and v.startswith("/") and not v.startswith("//") and "\\" not in v
            and all(ord(ch) >= 32 and ord(ch) != 127 for ch in v)):
        return v
    return "/"

def read_goscie():
    return read_csv_rows(GOSCIE_FILE)

def zapisz_goscia(imie, nazwisko, firma, now=None):
    """Dopisuje gościa i usuwa wpisy starsze niż 90 dni; zapis atomowy pod blokadą jak inne pliki."""
    now = now or datetime.now()
    granica = now - timedelta(days=GOSCIE_RETENTION_DAYS)
    with _lock:
        zostaja = []
        for r in read_goscie():
            try:
                if datetime.fromisoformat(r.get("created_at", "")) >= granica: zostaja.append(r)
            except ValueError: pass   # uszkodzony znacznik czasu = wpis do usunięcia
        zostaja.append({"created_at": now.isoformat(timespec="seconds"), "imie": _csv_safe(imie),
                        "nazwisko": _csv_safe(nazwisko), "firma": _csv_safe(firma)})
        tmp = Path(str(GOSCIE_FILE) + ".tmp")
        try:
            with open(tmp, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.DictWriter(f, fieldnames=GOSCIE_HEADERS, delimiter=";", extrasaction="ignore")
                w.writeheader()
                w.writerows(zostaja)
            os.replace(tmp, GOSCIE_FILE)
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise

def _gosc_wpuszczony():
    try:
        return time_module.time() - float(session.get("gosc_ts", 0)) < GOSCIE_SESSION_DAYS * 86400
    except (TypeError, ValueError):
        return False

@app.before_request
def bramka_gosci():
    if not VISITOR_GATE or request.method not in ("GET", "HEAD") or request.endpoint not in GATED_ENDPOINTS:
        return
    if _gosc_wpuszczony() or (is_admin() and not DEMO):   # w demo każdy jest "adminem", więc nie zwalnia z bramki
        return
    return redirect(url_for("wejscie", next=request.full_path.rstrip("?")))

@app.route("/wejscie", methods=["GET", "POST"])
def wejscie():
    nast, err = _bezpieczny_next(request.values.get("next")), None
    if not VISITOR_GATE:
        return redirect(nast)
    if request.method == "POST":
        pola = [_pole_goscia(request.form.get(k)) for k in ("imie", "nazwisko", "firma")]
        if request.form.get("www"):   # pułapka na boty (honeypot) — człowiek tego pola nie widzi
            return "Odrzucono.", 400
        if None in pola:
            err = "Uzupełnij imię, nazwisko i firmę (2–100 znaków, bez znaków sterujących)."
        elif not request.form.get("rodo"):
            err = "Potwierdź zapoznanie się z informacją o przetwarzaniu danych."
        else:
            zapisz_goscia(*pola)
            session.permanent = True
            session["gosc_ts"] = time_module.time()
            return redirect(nast)
    return render_template("wejscie.html", error=err, next=nast, form=request.form), (400 if err else 200)

def _dostep_do_goscow():
    """None = dostęp; inaczej odpowiedź odmowna. Token VISITORS_TOKEN (?token=) działa także dla konta demo."""
    oczekiwany, podany = os.environ.get("VISITORS_TOKEN", ""), request.args.get("token", "")
    if oczekiwany and hmac.compare_digest(podany.encode(), oczekiwany.encode()):
        return None
    if DEMO and session.get("admin_user") == "demo":   # w demo każdy jest "adminem demo" — bez tokenu listy nie ma
        return "Nie znaleziono.", 404
    return None if is_admin() else redirect(url_for("admin_login"))

@app.route("/admin/goscie")
def adm_goscie():
    if (odmowa := _dostep_do_goscow()) is not None: return odmowa
    return render_template("goscie.html", goscie=list(reversed(read_goscie())), dni=GOSCIE_RETENTION_DAYS)

@app.route("/admin/goscie.csv")
def adm_goscie_csv():
    if (odmowa := _dostep_do_goscow()) is not None: return odmowa
    out = StringIO()
    w = csv.DictWriter(out, fieldnames=GOSCIE_HEADERS, delimiter=";", extrasaction="ignore")
    w.writeheader()
    w.writerows({k: _csv_safe(v) for k, v in r.items()} for r in read_goscie())
    buf = BytesIO(out.getvalue().encode("utf-8-sig"))
    return send_file(buf, as_attachment=True, download_name="goscie.csv", mimetype="text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# DEMO (RCP_DEMO=1)
# ══════════════════════════════════════════════════════════════════════════════
# Logowanie automatyczne, fikcyjne dane z demo_data.py odtwarzane co RCP_DEMO_RESET_MIN minut,
# operacje zmieniające konfigurację zablokowane. Dane demo leżą w data_demo/, więc reset
# nigdy nie dotyka prawdziwej ewidencji w data/.
DEMO_RESET_MIN = int(os.environ.get("RCP_DEMO_RESET_MIN", "30"))

# Endpointy niedostępne dla gościa demo: słowniki, konta, konfiguracja i wgrywanie plików.
# Rejestracja wejść, korekty, przesunięcia pracowników i edycja grafiku działają.
DEMO_BLOCKED = {
    "adm_add_strefa", "adm_del_strefa", "adm_add_pod", "adm_del_pod",
    "adm_add_worker", "adm_del_worker",
    "adm_add_admin", "adm_del_admin",
    "adm_save_config", "adm_grafik_import",
}

def demo_reset():
    import demo_data
    with _lock:
        for f in list(DATA_DIR.glob("*.csv")) + list(DATA_DIR.glob("*.json")):
            if f != GOSCIE_FILE: f.unlink()   # lista gości przeżywa reset danych demo (retencja 90 dni)
        save_strefy(DEFAULT_STREFY)
        save_config(DEFAULT_CONFIG)
        save_admins({"demo": {"hash": hash_pw(secrets.token_hex(16)), "must_change": False}})
        d = demo_data.build(datetime.now(), DEFAULT_STREFY)
        save_workers(d["workers"])
        _w(STATE_FILE, d["state"])
        save_korekty(d["korekty"])
        save_nadwyzki(d["nadwyzki"])
        save_grafik(d["grafik"])
        ensure_alerts()
        with open(ALERTS_FILE_PATH, "a", newline="", encoding="utf-8-sig") as f:
            csv.writer(f, delimiter=";").writerows(d["alerts"])
        ids = {}
        for row in d["rows"]:
            ts_in = datetime.fromisoformat(row["ts_wejscia"])
            month = ts_in.strftime("%Y-%m")
            ids[month] = ids.get(month, 0) + 1
            append_csv_row({"id": ids[month], **row}, ts_in)
        _active_alerts.clear()
    log.info("Dane demo odtworzone (%d wpisów ewidencji)", len(d["rows"]))

def demo_reset_job():
    while True:
        time_module.sleep(DEMO_RESET_MIN * 60)
        _przebieg("odtwarzanie danych demo", demo_reset)

@app.before_request
def demo_guard():
    if not DEMO: return
    if not is_admin():
        session["admin_logged"] = True
        session["admin_user"]   = "demo"
    if request.endpoint == "admin_login":
        return redirect(url_for("admin_panel"))
    if request.endpoint in DEMO_BLOCKED:
        resp = jsonify({"ok": False, "error": "Niedostępne w trybie demo"})
        resp.headers["X-RCP-Demo"] = "blocked"
        return resp, 403

@app.context_processor
def demo_context():
    return {"demo": DEMO, "demo_reset_min": DEMO_RESET_MIN}

if DEMO:
    demo_reset()
    threading.Thread(target=demo_reset_job, daemon=True).start()


if __name__ == "__main__":
    # 0.0.0.0 zamierzone: skanery łączą się z sieci lokalnej (ryzyko R9, jak B104 w pyproject.toml)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)), debug=False)  # nosemgrep: python.flask.security.audit.app-run-param-config.avoid_app_run_with_bad_host
