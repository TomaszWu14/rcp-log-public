"""
RCP Log v3
"""
from flask import (Flask, request, jsonify, render_template,
                   session, redirect, url_for, send_file)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from pathlib import Path
from io import BytesIO
import csv, json, threading, time as time_module, shutil, os, re
import openpyxl
from openpyxl.styles import PatternFill, Font, Alignment, Border, Side
from openpyxl.utils import get_column_letter

app = Flask(__name__)
app.secret_key = os.environ.get("RCP_SECRET_KEY") or "timeapp-secret-change-in-production-32ch"
DEMO = os.environ.get("RCP_DEMO") == "1"   # tryb demo — opis w sekcji DEMO na końcu pliku
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

PROG_PRZERWA = 30  # alert po X min przerwy

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
}

# ── I/O ────────────────────────────────────────────────────────────────────────
_lock = threading.Lock()

def _r(path, default=None):
    try:
        with open(path, encoding="utf-8") as f: return json.load(f)
    except (OSError, json.JSONDecodeError):
        return default if default is not None else {}

def _w(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_workers():  return _r(WORKERS_FILE, {})
def save_workers(d): _w(WORKERS_FILE, d)
def load_strefy():   return _r(STREFY_FILE, {})
def save_strefy(d):  _w(STREFY_FILE, d)
def load_admins():   return _r(ADMINS_FILE, {})
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
    ref_year  = date.today().year
    ref_month = date.today().month
    for ci, cell in enumerate(header[1:], start=1):
        if cell is None:
            continue
        d = None
        s = str(cell).strip()
        # YYYY-MM-DD
        try: d = datetime.strptime(s, "%Y-%m-%d").date(); col_dates[ci] = d.isoformat(); continue
        except: pass
        # DD.MM.YYYY
        try: d = datetime.strptime(s, "%d.%m.%Y").date(); col_dates[ci] = d.isoformat(); continue
        except: pass
        # DD.MM
        try:
            d = datetime.strptime(s, "%d.%m").date().replace(year=ref_year)
            col_dates[ci] = d.isoformat(); continue
        except: pass
        # same number (day of month) – przypisujemy do bieżącego miesiąca
        try:
            day = int(float(s))
            if 1 <= day <= 31:
                d = date(ref_year, ref_month, day)
                col_dates[ci] = d.isoformat()
        except: pass

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

def append_csv_row(row: dict, ts: datetime):
    daily, monthly = get_csv_paths(ts)
    for path in (daily, monthly):
        ensure_csv(path)
        with open(path, "a", newline="", encoding="utf-8-sig") as f:
            csv.DictWriter(f, fieldnames=CSV_HEADERS, delimiter=";").writerow(row)

def next_id(ts: datetime):
    _, monthly = get_csv_paths(ts)
    try:
        with open(monthly, encoding="utf-8-sig") as f:
            return sum(1 for _ in f)
    except: return 1

def read_csv_rows(path: Path):
    rows = []
    try:
        with open(path, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
    except: pass
    return rows

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
            [datetime.now().isoformat(), pracownik, imie, typ, opis, "NIE"])

def read_alerts(limit=100):
    rows = []
    try:
        with open(ALERTS_FILE_PATH, encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
    except: pass
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
    except: return 0

def hash_pw(pw): return generate_password_hash(pw)
def verify_pw(pw, hashed): return check_password_hash(hashed, pw)
def is_admin():  return session.get("admin_logged") is True

def get_dzien_min(pracownik, dt=None):
    dt = dt or datetime.now()
    daily, _ = get_csv_paths(dt)
    total = 0.0
    try:
        for row in read_csv_rows(daily):
            if row.get("pracownik") == pracownik:
                try: total += float(row.get("czas_min") or 0)
                except: pass
    except: pass
    return total

def get_flaga(strefa, czas_min):
    cfg = load_config()
    prog = cfg.get("prog_przerwa_min", PROG_PRZERWA)
    if strefa == "PRZERWA" and czas_min > prog:
        return "DLUGA_PRZERWA"
    return ""

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
        save_admins({"admin": hash_pw("admin123")})
    else:
        # Migracja starych hashów SHA-256 (64 znaki hex) do werkzeug
        adm = load_admins()
        migrated = False
        for user, h in adm.items():
            if len(h) == 64 and all(c in "0123456789abcdef" for c in h):
                adm[user] = hash_pw("admin123")
                migrated = True
        if migrated:
            save_admins(adm)
            print("[ADMINS] Hasła zmigrowane do bezpiecznego formatu. Zresetuj hasła!")

init_files()

# ── BACKUP THREAD ──────────────────────────────────────────────────────────────
_last_backup = None

def backup_job():
    global _last_backup
    while True:
        time_module.sleep(60)
        now = datetime.now()
        today = now.date()
        if _last_backup == today: continue
        if now.hour != 2: continue   # backup o 02:00
        try:
            cfg  = load_config()
            dest = Path(cfg.get("backup_path", BASE_DIR / "backup"))
            dest.mkdir(parents=True, exist_ok=True)
            stamp = now.strftime("%Y%m%d_%H%M")
            for f in DATA_DIR.glob("*.csv"):
                shutil.copy2(f, dest / f"{stamp}_{f.name}")
            for f in DATA_DIR.glob("*.json"):
                shutil.copy2(f, dest / f"{stamp}_{f.name}")
            _last_backup = today
            print(f"[BACKUP] OK → {dest}")
        except Exception as e:
            print(f"[BACKUP ERROR] {e}")

if not DEMO: threading.Thread(target=backup_job, daemon=True).start()

# ── ALERT CHECKER ──────────────────────────────────────────────────────────────
_active_alerts = {}   # {pracownik: True} — alerty które jeszcze nie były "odczytane"

def bg_check():
    while True:
        time_module.sleep(60)
        try:
            workers       = load_workers()
            cfg           = load_config()
            prog_przerwa  = cfg.get("prog_przerwa_min", PROG_PRZERWA)
            alert_dyżur_h = cfg.get("alert_dlugi_dyżur_h", 10)
            with _lock:
                state    = _r(STATE_FILE, {})
                changed  = False
                now      = datetime.now()
                today    = now.date()
                to_close = []

                for kod, sess in state.items():
                    imie   = workers.get(kod, {}).get("imie", kod)
                    m      = mins_since(sess["ts_wejscia"])
                    ts_wej = datetime.fromisoformat(sess["ts_wejscia"])

                    # --- Alert długa przerwa ---
                    if sess["strefa"] == "PRZERWA":
                        if m > prog_przerwa and not sess.get("alert_wyslany"):
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
                    # Sesja z poprzedniego dnia (lub starszych) → zamknij o 23:59:59 tamtego dnia
                    if ts_wej.date() < today:
                        to_close.append((kod, sess, imie, ts_wej))

                # Zamykamy przeterminowane sesje
                for kod, sess, imie, ts_wej in to_close:
                    ts_wyj = datetime(ts_wej.year, ts_wej.month, ts_wej.day, 23, 59, 59)
                    czas_m = (ts_wyj - ts_wej).total_seconds() / 60
                    append_csv_row({
                        "pracownik": kod, "imie_nazwisko": imie,
                        "strefa": sess["strefa"],
                        "podstrefa": sess.get("podstrefa",""),
                        "ts_wejscia": sess["ts_wejscia"],
                        "ts_wyjscia": ts_wyj.isoformat(timespec="seconds"),
                        "czas_min": round(czas_m, 2),
                        "flaga": "AUTO_ZAMKNIETO",
                    }, ts_wyj)
                    opis = f"{imie} auto-zamknięto o 23:59 dnia {ts_wej.date()} (strefa {sess['strefa']})"
                    append_alert(kod, imie, "AUTO_ZAMKNIETO", opis)
                    _active_alerts[kod] = {"typ":"AUTO_ZAMKNIETO","opis":opis,"ts":now.isoformat()}
                    del state[kod]
                    changed = True

                if changed:
                    _w(STATE_FILE, state)
        except (OSError, KeyError, ValueError): pass

threading.Thread(target=bg_check, daemon=True).start()

# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/api/scan", methods=["POST"])
def api_scan():
    kod = (request.json or {}).get("kod","").strip().upper()
    if not kod:
        return jsonify({"ok":False,"error":"Pusty kod QR"}), 400

    workers = load_workers()
    if kod not in workers:
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
    d         = request.json or {}
    kod       = d.get("pracownik","").strip().upper()
    nowa_str  = (d.get("strefa") or "").strip().upper()
    podstrefa = (d.get("podstrefa") or "").strip().upper()
    korekta   = d.get("korekta_info","")
    force     = d.get("force", False)

    if not kod or not nowa_str:
        return jsonify({"ok":False,"error":"Brak pracownika lub strefy"}), 400

    workers = load_workers()
    if kod not in workers:
        return jsonify({"ok":False,"error":"Nieznany pracownik"}), 403

    worker = workers[kod]

    if nowa_str != "KONIEC_ZMIANY":
        if nowa_str not in [s.upper() for s in worker.get("strefy",[])]:
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
            ts_in  = datetime.fromisoformat(sesja["ts_wejscia"])
            czas_m = round((now - ts_in).total_seconds() / 60, 2)
            flaga  = get_flaga(sesja["strefa"], czas_m)

            row = {
                "id":            next_id(ts_in),
                "pracownik":     kod,
                "imie_nazwisko": worker["imie"],
                "strefa":        sesja["strefa"],
                "podstrefa":     sesja.get("podstrefa",""),
                "ts_wejscia":    sesja["ts_wejscia"],
                "ts_wyjscia":    now_iso,
                "czas_min":      czas_m,
                "czas_fmt":      fmt_czas(czas_m),
                "flaga":         flaga,
                "korekta_info":  korekta,
            }
            append_csv_row(row, ts_in)

            if flaga == "DLUGA_PRZERWA":
                prog = cfg.get("prog_przerwa_min", PROG_PRZERWA)
                nadwyzka_min = round(czas_m - prog, 2)
                nadwyzki = load_nadwyzki()
                nadwyzki.append({
                    "id":           len(nadwyzki) + 1,
                    "pracownik":    kod,
                    "imie":         worker["imie"],
                    "ts_przerwy":   sesja["ts_wejscia"],
                    "czas_przerwy_min": czas_m,
                    "czas_przerwy_fmt": fmt_czas(czas_m),
                    "nadwyzka_min": nadwyzka_min,
                    "nadwyzka_fmt": fmt_czas(nadwyzka_min),
                    "przypisana_strefa": None,
                    "status": "oczekuje",
                })
                save_nadwyzki(nadwyzki)
                append_alert(kod, worker["imie"], "DLUGA_PRZERWA",
                    f"{worker['imie']} przerwa {fmt_czas(czas_m)} | nadwyzka {fmt_czas(nadwyzka_min)}")
                alerts.append({"typ":"DLUGA_PRZERWA",
                    "opis": f"Przerwa trwała {fmt_czas(czas_m)} (nadwyżka: {fmt_czas(nadwyzka_min)})"})

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
    state   = load_state()
    workers        = load_workers()
    now            = datetime.now()
    cfg            = load_config()
    prog           = cfg.get("prog_przerwa_min", PROG_PRZERWA)
    alert_dyżur_h  = cfg.get("alert_dlugi_dyżur_h", 12)
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
    d   = request.json or {}
    kod = d.get("pracownik","").strip().upper()
    workers = load_workers()
    if kod not in workers:
        return jsonify({"ok":False,"error":"Nieznany pracownik"}), 403
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
        user = request.form.get("username","").strip()
        pw   = request.form.get("password","")
        adm  = load_admins()
        if user in adm and verify_pw(pw, adm[user]):
            session["admin_logged"] = True
            session["admin_user"]   = user
            return redirect(url_for("admin_panel"))
        err = "Nieprawidłowy login lub hasło"
    return render_template("admin_login.html", error=err)

@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("admin_login"))

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
        try: per_strefa[s] = per_strefa.get(s,0) + float(r.get("czas_min",0) or 0)
        except: pass

    # Czas per pracownik
    per_pracownik = {}
    for r in rows:
        p = r.get("imie_nazwisko","")
        try: per_pracownik[p] = per_pracownik.get(p,0) + float(r.get("czas_min",0) or 0)
        except: pass

    # Aktywne sesje teraz
    state   = load_state()
    workers = load_workers()
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
    nadwyzki = load_nadwyzki()
    for n in nadwyzki:
        if n["id"] == nid:
            n["przypisana_strefa"] = strefa
            n["status"] = "przypisana"
            break
    save_nadwyzki(nadwyzki)
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
    korekty = load_korekty()
    for k in korekty:
        if k["id"] == kid:
            k["status"]  = "zatwierdzona" if decyzja=="tak" else "odrzucona"
            k["decyzja"] = decyzja
            break
    save_korekty(korekty)
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
    with _lock:
        now     = datetime.now()
        now_iso = now.isoformat(timespec="seconds")
        state   = _r(STATE_FILE, {})
        sesja   = state.get(kod)
        if sesja:
            ts_in  = datetime.fromisoformat(sesja["ts_wejscia"])
            czas_m = round((now - ts_in).total_seconds() / 60, 2)
            append_csv_row({
                "id":            next_id(ts_in),
                "pracownik":     kod,
                "imie_nazwisko": worker["imie"],
                "strefa":        sesja["strefa"],
                "podstrefa":     sesja.get("podstrefa",""),
                "ts_wejscia":    sesja["ts_wejscia"],
                "ts_wyjscia":    now_iso,
                "czas_min":      czas_m,
                "czas_fmt":      fmt_czas(czas_m),
                "flaga":         get_flaga(sesja["strefa"], czas_m),
                "korekta_info":  f"ADMIN:{session.get('admin_user','?')}",
            }, ts_in)
        if nowa_str == "KONIEC_ZMIANY":
            state.pop(kod, None)
            _w(STATE_FILE, state)
            return jsonify({"ok":True,"akcja":"koniec_zmiany","imie_nazwisko":worker["imie"]})
        state[kod] = {"strefa":nowa_str,"podstrefa":podstrefa,"ts_wejscia":now_iso}
        _w(STATE_FILE, state)
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
    now     = datetime.now()
    now_iso = now.isoformat(timespec="seconds")
    with _lock:
        state = _r(STATE_FILE, {})
        sesja = state.get(kod)
        if sesja:
            ts_in  = datetime.fromisoformat(sesja["ts_wejscia"])
            czas_m = round((now - ts_in).total_seconds() / 60, 2)
            append_csv_row({
                "id":            next_id(ts_in),
                "pracownik":     kod,
                "imie_nazwisko": worker["imie"],
                "strefa":        sesja["strefa"],
                "podstrefa":     sesja.get("podstrefa",""),
                "ts_wejscia":    sesja["ts_wejscia"],
                "ts_wyjscia":    now_iso,
                "czas_min":      czas_m,
                "czas_fmt":      fmt_czas(czas_m),
                "flaga":         get_flaga(sesja["strefa"], czas_m),
                "korekta_info":  f"ADMIN:{session.get('admin_user','?')}:start_override",
            }, ts_in)
        state[kod] = {"strefa":strefa,"podstrefa":podstrefa,"ts_wejscia":now_iso}
        _w(STATE_FILE, state)
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
    return jsonify({"ok":True})

@app.route("/admin/api/strefy/<nazwa>",    methods=["DELETE"])
def adm_del_strefa(nazwa):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    s = load_strefy(); s.pop(nazwa.upper(),None); save_strefy(s)
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
    return jsonify({"ok":True})

@app.route("/admin/api/strefy/<nazwa>/podstrefy/<pod>", methods=["DELETE"])
def adm_del_pod(nazwa,pod):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    s = load_strefy(); nazwa=nazwa.upper()
    if nazwa in s:
        s[nazwa]["podstrefy"]=[p for p in s[nazwa]["podstrefy"] if p!=pod.upper()]
        save_strefy(s)
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
    return jsonify({"ok":True})

@app.route("/admin/api/workers/<kod>",     methods=["DELETE"])
def adm_del_worker(kod):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    w=load_workers(); kod=kod.upper()
    if kod not in w: return jsonify({"ok":False,"error":"Nie znaleziono"}), 404
    del w[kod]; save_workers(w)
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
    a=load_admins(); a[u]=hash_pw(p); save_admins(a)
    return jsonify({"ok":True})

@app.route("/admin/api/admins/<user>",     methods=["DELETE"])
def adm_del_admin(user):
    if not is_admin(): return jsonify({"error":"Brak dostępu"}), 401
    if user==session.get("admin_user"):
        return jsonify({"ok":False,"error":"Nie możesz usunąć własnego konta"}), 400
    a=load_admins(); a.pop(user,None); save_admins(a)
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
    cfg=load_config(); cfg.update(d); save_config(cfg)
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
    for ri, (kod, w) in enumerate(workers.items(), start=3):
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
    workers = load_workers()
    patch, bledy = import_grafik_excel(f.read(), workers)
    if patch:
        grafik = load_grafik()
        for kod, dni in patch.items():
            if kod not in grafik:
                grafik[kod] = {}
            grafik[kod].update(dni)
        save_grafik(grafik)
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
        except: pass

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
                except: status = "obecny"
            wynik[kod]["dni"][date_iso] = {"zaplanowano": zaplan, "status": status,
                                           "pierwsza": scan["ts"], "spoznienie": spoznienie}
    return jsonify(wynik)


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
            f.unlink()
        save_strefy(DEFAULT_STREFY)
        save_config(DEFAULT_CONFIG)
        save_admins({"demo": hash_pw(os.urandom(16).hex())})
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
    print(f"[DEMO] Dane demo odtworzone ({len(d['rows'])} wpisów ewidencji)")

def demo_reset_job():
    while True:
        time_module.sleep(DEMO_RESET_MIN * 60)
        try: demo_reset()
        except Exception as e: print(f"[DEMO RESET ERROR] {e}")

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
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5050)), debug=False)
