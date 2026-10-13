"""
RCP Log — generator fikcyjnych danych do trybu demo (RCP_DEMO=1).

Funkcja build() nie zapisuje niczego na dysk — zwraca gotowe struktury,
które app.py zapisuje własnymi funkcjami. Dzięki temu moduł nie zależy od app.py.

Co powstaje:
  - 12 fikcyjnych pracowników (w tym trzech z danych startowych),
  - ewidencja z ostatnich 10 dni roboczych (zmiany R 05–13 i P 13–21),
  - dzisiejsza zmiana do chwili obecnej + aktywne sesje (podgląd Live),
  - jedna przekroczona przerwa trwająca teraz, nadwyżki przerw, alerty, korekty,
  - grafik bieżącego miesiąca ze spóźnieniem i nieobecnością.
"""
from datetime import datetime, date, timedelta, time
import random

WORKERS = {
    "HU_KOWALSKI_JAN":       {"imie": "Kowalski Jan",       "strefy": ["PICKING", "PRZYJECIA", "KURIER1", "PRZERWA"]},
    "HU_NOWAK_ANNA":         {"imie": "Nowak Anna",         "strefy": ["KURIER1", "KURIER2", "BUS", "PRZERWA"]},
    "HU_WISNIEWSKI_PIOTR":   {"imie": "Wisniewski Piotr",   "strefy": ["PICKING", "INV", "PRZERWA"]},
    "HU_WOJCIK_MARTA":       {"imie": "Wojcik Marta",       "strefy": ["PICKING", "ZWROTY", "PRZERWA"]},
    "HU_KAMINSKI_TOMASZ":    {"imie": "Kaminski Tomasz",    "strefy": ["PRZYJECIA", "KONTENERY", "PRZERWA"]},
    "HU_LEWANDOWSKA_EWA":    {"imie": "Lewandowska Ewa",    "strefy": ["PICKING", "KURIER1", "KURIER2", "PRZERWA"]},
    "HU_ZIELINSKI_MAREK":    {"imie": "Zielinski Marek",    "strefy": ["BUS", "EXPORT", "KONTENERY", "PRZERWA"]},
    "HU_SZYMANSKA_KATARZYNA":{"imie": "Szymanska Katarzyna","strefy": ["INV", "ADMIN_MAG", "PRZERWA"]},
    "HU_WOZNIAK_PAWEL":      {"imie": "Wozniak Pawel",      "strefy": ["PICKING", "PRZYJECIA", "PRZERWA"]},
    "HU_DABROWSKI_ADAM":     {"imie": "Dabrowski Adam",     "strefy": ["EXPORT", "BUS", "PRZERWA"]},
    "HU_KOZLOWSKA_AGNIESZKA":{"imie": "Kozlowska Agnieszka","strefy": ["ZWROTY", "PICKING", "PRZERWA"]},
    "HU_JANKOWSKI_MICHAL":   {"imie": "Jankowski Michal",   "strefy": ["KONTENERY", "PRZYJECIA", "PRZERWA"]},
}

# Zmiana stała dla każdego pracownika — prościej czytać porównanie z grafikiem.
SHIFT = {kod: ("R" if i % 2 == 0 else "P") for i, kod in enumerate(WORKERS)}
SHIFT_HOURS = {"R": ("05:00", "13:00"), "P": ("13:00", "21:00")}

# Role w dzisiejszej scenie demo
SCAN_DEMO   = "HU_KOWALSKI_JAN"      # skaner: w strefie od ~40 min, bez ostrzeżenia o szybkiej zmianie
LONG_BREAK  = "HU_NOWAK_ANNA"        # przerwa trwa teraz ponad próg -> alert na Live
SHORT_BREAK = "HU_ZIELINSKI_MAREK"   # zwykła przerwa
LATE_TODAY  = "HU_WOZNIAK_PAWEL"     # dziś spóźniony względem grafiku
ABSENT      = "HU_JANKOWSKI_MICHAL"  # dziś w grafiku, brak skanu -> nieobecność
OFF_TODAY   = "HU_DABROWSKI_ADAM"    # dziś wolne

PROG_PRZERWA = 30


def _fmt(minutes):
    s = int(abs(minutes) * 60)
    return f"{s // 3600:02d}:{s % 3600 // 60:02d}:{s % 60:02d}"


def _iso(dt):
    return dt.isoformat(timespec="seconds")


def _row(kod, strefa, pod, ts_in, ts_out, flaga="", korekta=""):
    czas = round((ts_out - ts_in).total_seconds() / 60, 2)
    return {
        "pracownik": kod, "imie_nazwisko": WORKERS[kod]["imie"],
        "strefa": strefa, "podstrefa": pod,
        "ts_wejscia": _iso(ts_in), "ts_wyjscia": _iso(ts_out),
        "czas_min": czas, "czas_fmt": _fmt(czas),
        "flaga": flaga or ("DLUGA_PRZERWA" if strefa == "PRZERWA" and czas > PROG_PRZERWA else ""),
        "korekta_info": korekta,
    }


def _pick_zone(rnd, kod, strefy, last):
    work = [s for s in WORKERS[kod]["strefy"] if s != "PRZERWA" and s != last]
    z = rnd.choice(work or [last])
    pods = strefy.get(z, {}).get("podstrefy", [])
    return z, (rnd.choice(pods) if pods else "")


def _simulate(rnd, kod, strefy, start, end, long_break=False):
    """Pobyty od start do end: bloki pracy 40–140 min i jedna-dwie przerwy."""
    rows, t, last = [], start, None
    breaks_left = 2 if (end - start) > timedelta(hours=6) else 1
    while t < end:
        worked = (t - start).total_seconds() / 3600
        if breaks_left and worked > 2.2 * (3 - breaks_left) - 0.5 and last != "PRZERWA":
            dur = rnd.randint(36, 48) if long_break else rnd.randint(14, 26)
            long_break = False
            z, pod = "PRZERWA", ""
            breaks_left -= 1
        else:
            dur = rnd.randint(40, 140)
            z, pod = _pick_zone(rnd, kod, strefy, last)
        t2 = min(t + timedelta(minutes=dur, seconds=rnd.randint(0, 59)), end)
        if (t2 - t) < timedelta(minutes=3):
            break
        rows.append(_row(kod, z, pod, t, t2))
        t, last = t2, z
    return rows


def _workdays_before(today, n):
    days, d = [], today
    while len(days) < n:
        d -= timedelta(days=1)
        if d.weekday() < 5:
            days.append(d)
    return sorted(days)


def build(now, strefy, seed=2026):
    """Zwraca dict: workers, state, rows (lista wierszy ewidencji, chronologicznie),
    alerts (lista [ts, pracownik, imie, typ, opis, potwierdzone]), korekty, nadwyzki, grafik."""
    rnd = random.Random(seed)
    today = now.date()
    midnight = datetime.combine(today, time(0, 0))
    rows, alerts, nadwyzki = [], [], []
    grafik = {kod: {} for kod in WORKERS}

    # ── dni poprzednie ────────────────────────────────────────────────────────
    past_days = _workdays_before(today, 10)
    for di, d in enumerate(past_days):
        for wi, kod in enumerate(WORKERS):
            od, do = SHIFT_HOURS[SHIFT[kod]]
            grafik[kod][d.isoformat()] = {"od": od, "do": do, "typ": "P"}
            if (di + wi) % 11 == 0:          # od czasu do czasu nieobecność
                continue
            h, m = map(int, od.split(":"))
            late = rnd.random() < 0.12
            start = datetime.combine(d, time(h, m)) + timedelta(
                minutes=rnd.randint(17, 35) if late else rnd.randint(-8, 6), seconds=rnd.randint(0, 59))
            end = datetime.combine(d, time(h, m)) + timedelta(hours=8, minutes=rnd.randint(-4, 12))
            day_rows = _simulate(rnd, kod, strefy, start, end, long_break=rnd.random() < 0.07)
            rows.extend(day_rows)

        # weekendy w grafiku jako wolne
        nd = d + timedelta(days=1)
        while nd.weekday() >= 5 and nd < today:
            for kod in WORKERS:
                grafik[kod][nd.isoformat()] = {"od": None, "do": None, "typ": "W"}
            nd += timedelta(days=1)

    # ── dziś ─────────────────────────────────────────────────────────────────
    # Dzisiejsza zmiana jest „przesunięta” tak, żeby trwała niezależnie od godziny
    # uruchomienia demo — inaczej o 22:00 podgląd Live byłby pusty.
    state = {}
    floor = min(midnight + timedelta(minutes=1), now)
    active_len = {SCAN_DEMO: 41, LONG_BREAK: 43, SHORT_BREAK: 11}
    for wi, kod in enumerate(WORKERS):
        if kod == OFF_TODAY:
            grafik[kod][today.isoformat()] = {"od": None, "do": None, "typ": "W"}
            continue
        # plan na pełną godzinę 2,5–5,5 h temu; pierwszy skan kilka minut wokół planu
        shift_len = timedelta(minutes=150 + wi * 17)
        plan = max(midnight, (now - shift_len).replace(minute=0, second=0, microsecond=0))
        delay = 27 if kod == LATE_TODAY else rnd.randint(-6, 5)
        start = plan + timedelta(minutes=delay, seconds=rnd.randint(0, 59))
        start = min(max(floor, start), now)
        plan_end = plan + timedelta(hours=8)
        grafik[kod][today.isoformat()] = {
            "od": plan.strftime("%H:%M"),
            "do": plan_end.strftime("%H:%M") if plan_end.date() == today else "23:59",
            "typ": "P"}
        if kod == ABSENT:
            continue

        # ostatni pobyt to aktywna sesja; jej długość jest kontrolowana dla scen demo
        cur_len = active_len.get(kod, rnd.randint(15, 70))
        cur_start = max(start, now - timedelta(minutes=cur_len, seconds=rnd.randint(0, 59)))
        done = _simulate(rnd, kod, strefy, start, cur_start)
        rows.extend(done)
        last = done[-1]["strefa"] if done else None
        if kod in (LONG_BREAK, SHORT_BREAK):
            z, pod = "PRZERWA", ""
        elif kod == SCAN_DEMO:
            z, pod = "PICKING", "PICKING_B"
        else:
            work = [s for s in WORKERS[kod]["strefy"] if s != "PRZERWA"]
            z = work[wi % len(work)]
            pods = strefy.get(z, {}).get("podstrefy", [])
            pod = rnd.choice(pods) if pods else ""
        state[kod] = {"strefa": z, "podstrefa": pod, "ts_wejscia": _iso(cur_start)}
        if kod == LONG_BREAK and (now - cur_start) > timedelta(minutes=PROG_PRZERWA):
            state[kod]["alert_wyslany"] = True
            alerts.append([_iso(cur_start + timedelta(minutes=PROG_PRZERWA + 1)), kod, WORKERS[kod]["imie"],
                           "DLUGA_PRZERWA",
                           f"{WORKERS[kod]['imie']} na przerwie {_fmt(PROG_PRZERWA + 1)} (prog {PROG_PRZERWA} min)", "NIE"])

    # ── pochodne: nadwyżki przerw i alerty z historii ────────────────────────
    rows.sort(key=lambda r: r["ts_wejscia"])
    long_breaks = [r for r in rows if r["flaga"] == "DLUGA_PRZERWA"]
    for i, r in enumerate(long_breaks):
        nadw = round(r["czas_min"] - PROG_PRZERWA, 2)
        recent = i >= len(long_breaks) - 2
        kod = r["pracownik"]
        nadwyzki.append({
            "id": i + 1, "pracownik": kod, "imie": r["imie_nazwisko"],
            "ts_przerwy": r["ts_wejscia"],
            "czas_przerwy_min": r["czas_min"], "czas_przerwy_fmt": r["czas_fmt"],
            "nadwyzka_min": nadw, "nadwyzka_fmt": _fmt(nadw),
            "przypisana_strefa": None if recent else rnd.choice(
                [s for s in WORKERS[kod]["strefy"] if s != "PRZERWA"]),
            "status": "oczekuje" if recent else "przypisana",
        })
        alerts.append([r["ts_wyjscia"], kod, r["imie_nazwisko"], "DLUGA_PRZERWA",
                       f"{r['imie_nazwisko']} przerwa {r['czas_fmt']} | nadwyzka {_fmt(nadw)}",
                       "NIE" if recent else "TAK"])

    if past_days:
        d = past_days[-2] if len(past_days) > 1 else past_days[-1]
        alerts.append([_iso(datetime.combine(d, time(7, 42))), "HU_TEST_123", "HU_TEST_123",
                       "NIEZNANY_KOD", "Proba skanowania: HU_TEST_123", "TAK"])
    alerts.sort(key=lambda a: a[0])

    # ── korekty zgłoszone przez pracowników ──────────────────────────────────
    k_days = past_days[-3:] if len(past_days) >= 3 else past_days
    korekty = []
    opisy = [
        ("HU_KAMINSKI_TOMASZ", "Zapomniałem zeskanować wyjścia z PRZYJECIA o 10:15 — od 10:15 byłem na KONTENERY", "zatwierdzona"),
        ("HU_WOJCIK_MARTA",    "Skaner nie działał przy ZWROTY, weszłam ok. 14:40 zamiast 15:05", "oczekuje"),
        ("HU_LEWANDOWSKA_EWA", "Omyłkowo zeskanowałam PRZERWA zamiast KURIER2 o 9:30", "oczekuje"),
    ]
    for i, (kod, opis, status) in enumerate(opisy):
        d = k_days[min(i, len(k_days) - 1)] if k_days else today
        korekty.append({
            "id": i + 1, "pracownik": kod, "imie": WORKERS[kod]["imie"],
            "ts_zgloszenia": _iso(datetime.combine(d, time(15 if i == 1 else 11, 20 + i * 7))),
            "opis": opis, "status": status,
            "decyzja": "tak" if status == "zatwierdzona" else None,
        })

    # ── reszta miesiąca w grafiku (plan na przyszłe dni) ─────────────────────
    d = today + timedelta(days=1)
    while d.month == today.month:
        for kod in WORKERS:
            if d.weekday() >= 5:
                grafik[kod][d.isoformat()] = {"od": None, "do": None, "typ": "W"}
            else:
                od, do = SHIFT_HOURS[SHIFT[kod]]
                grafik[kod][d.isoformat()] = {"od": od, "do": do, "typ": "P"}
        d += timedelta(days=1)

    return {
        "workers": WORKERS, "state": state, "rows": rows, "alerts": alerts,
        "korekty": korekty, "nadwyzki": nadwyzki, "grafik": grafik,
    }
