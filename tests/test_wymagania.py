"""Testy akceptacyjne — nazwa testu = ID wymagania z docs/archiwum/05-wymagania.md
(mapa na wymagania WF-n jest w tabelach "Wymagania funkcjonalne" w docs/01-procesy/).

Uruchomienie: python -m unittest discover tests

app.py przy imporcie tworzy katalog data/ obok siebie, dlatego każdy test
ładuje kopię aplikacji w katalogu tymczasowym — prawdziwe dane nie są ruszane.
"""
import contextlib
import importlib.util
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl

REPO = Path(__file__).resolve().parent.parent
NOWE_HASLO = "Nowe-haslo-testowe-1"


def load_app():
    tmp = Path(tempfile.mkdtemp())
    shutil.copy(REPO / "app.py", tmp / "app.py")
    shutil.copytree(REPO / "templates", tmp / "templates")
    spec = importlib.util.spec_from_file_location(f"rcp_{tmp.name}", tmp / "app.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod, tmp


class Wymagania(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        os.environ.pop("RCP_DEMO", None)
        self.A, self.tmp = load_app()
        self.c = self.A.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def csrf(self):
        """Token CSRF z formularza logowania (ustawia też ciasteczko sesji)."""
        html = self.c.get("/admin/login").get_data(as_text=True)
        return re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)

    def login(self, password="admin123"):
        """Logowanie hasłem startowym i wymuszona zmiana — dopiero potem panel jest dostępny."""
        self.token = self.csrf()
        r = self.c.post("/admin/login", data={"username": "admin", "password": password, "csrf": self.token})
        self.c.post("/admin/haslo", data={"password": NOWE_HASLO, "password2": NOWE_HASLO, "csrf": self.token})
        return r

    def rejestruj(self, strefa, force=True, kod="HU_KOWALSKI_JAN"):
        return self.c.post("/api/rejestruj", json={"pracownik": kod, "strefa": strefa, "force": force})

    def ewidencja_dzis(self):
        daily, _ = self.A.get_csv_paths(datetime.now())
        return self.A.read_csv_rows(daily)

    # ── Rejestracja ──────────────────────────────────────────────────────────
    def test_REJ_01_kod_bez_wzgledu_na_wielkosc_liter_i_spacje(self):
        r = self.c.post("/api/scan", json={"kod": "  hu_kowalski_jan "})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["imie_nazwisko"], "Kowalski Jan")

    def test_REJ_02_nieznany_kod_odrzucony_i_odnotowany(self):
        r = self.c.post("/api/scan", json={"kod": "HU_NIEMA"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json["error"], "Nieznany kod QR. Skontaktuj się z liderem.")
        self.assertEqual(self.A.read_alerts()[0]["typ"], "NIEZNANY_KOD")

    def test_REJ_03_tylko_przypisane_strefy(self):
        r = self.c.post("/api/scan", json={"kod": "HU_KOWALSKI_JAN"})
        nazwy = [s["nazwa"] for s in r.json["dozwolone"]]
        self.assertEqual(nazwy, ["PICKING", "PRZYJECIA", "KURIER1", "PRZERWA"])
        r = self.rejestruj("EXPORT")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.json["error"], "Brak uprawnień do strefy EXPORT")

    def test_REJ_06_szybka_zmiana_wymaga_potwierdzenia(self):
        self.rejestruj("PICKING")
        r = self.rejestruj("PRZYJECIA", force=False)
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.json["wymaga_potwierdzenia"])
        self.assertEqual(self.rejestruj("PRZYJECIA", force=True).status_code, 200)

    def test_REJ_07_koniec_zmiany_zamyka_sesje(self):
        self.rejestruj("PICKING")
        r = self.rejestruj("KONIEC_ZMIANY")
        self.assertEqual(r.json["akcja"], "koniec_zmiany")
        self.assertNotIn("HU_KOWALSKI_JAN", self.A.load_state())

    # ── Sesje i ewidencja ────────────────────────────────────────────────────
    def test_SES_01_najwyzej_jedna_otwarta_sesja(self):
        self.rejestruj("PICKING")
        self.rejestruj("PRZYJECIA")
        self.login()
        status = self.c.get("/api/status").json
        self.assertEqual([(w["pracownik"], w["strefa"]) for w in status],
                         [("HU_KOWALSKI_JAN", "PRZYJECIA")])

    def test_SES_02_zamkniecie_sesji_tworzy_wpis(self):
        self.rejestruj("PICKING")
        r = self.rejestruj("PRZYJECIA")
        wpisy = self.ewidencja_dzis()
        self.assertEqual(len(wpisy), 1)
        self.assertEqual(wpisy[0]["strefa"], "PICKING")
        self.assertEqual(wpisy[0]["ts_wyjscia"], r.json["ts"])
        _, monthly = self.A.get_csv_paths(datetime.now())
        self.assertEqual(len(self.A.read_csv_rows(monthly)), 1)

    def test_SES_03_csv_otwiera_sie_w_excelu(self):
        self.rejestruj("PICKING")
        self.rejestruj("PRZYJECIA")
        daily, _ = self.A.get_csv_paths(datetime.now())
        raw = daily.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))  # BOM
        self.assertIn(b"id;pracownik;imie_nazwisko", raw)

    # ── Przerwy ──────────────────────────────────────────────────────────────
    def test_PRZ_02_PRZ_03_dluga_przerwa_flaga_i_nadwyzka(self):
        start = (datetime.now() - timedelta(minutes=42)).isoformat(timespec="seconds")
        self.A.save_state({"HU_KOWALSKI_JAN": {"strefa": "PRZERWA", "podstrefa": "", "ts_wejscia": start}})
        r = self.rejestruj("PICKING")
        self.assertEqual(r.json["alerts"][0]["typ"], "DLUGA_PRZERWA")
        self.assertEqual(self.ewidencja_dzis()[0]["flaga"], "DLUGA_PRZERWA")
        n = self.A.load_nadwyzki()[0]
        self.assertAlmostEqual(n["nadwyzka_min"], 12, delta=0.1)
        self.assertEqual(n["status"], "oczekuje")

    # ── Korekty ──────────────────────────────────────────────────────────────
    def test_KOR_02_korekta_tylko_od_znanego_pracownika(self):
        r = self.c.post("/api/korekta", json={"pracownik": "HU_NIEMA", "opis": "x"})
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.A.load_korekty(), [])

    # ── Panel administratora ─────────────────────────────────────────────────
    def test_ADM_01_panel_tylko_po_zalogowaniu(self):
        self.assertEqual(self.c.get("/admin").status_code, 302)
        self.assertEqual(self.c.get("/admin/api/status").status_code, 401)
        r = self.c.post("/admin/login", data={"username": "admin", "password": "zle", "csrf": self.csrf()})
        self.assertIn("Nieprawidłowy login lub hasło", r.get_data(as_text=True))

    def test_ADM_07_kod_pracownika_z_prefiksem_HU(self):
        self.login()
        r = self.c.post("/admin/api/workers", json={"kod": "XYZ_NOWY", "imie": "Nowy Jan"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json["error"], "Kod musi zaczynać się od HU_")

    def test_ADM_09_nie_mozna_usunac_wlasnego_konta(self):
        self.login()
        r = self.c.delete("/admin/api/admins/admin")
        self.assertEqual(r.status_code, 400)
        self.assertIn("admin", self.A.load_admins())

    # ── Grafik ───────────────────────────────────────────────────────────────
    def test_GRF_02_kody_zmian(self):
        p = self.A.parse_shift
        self.assertEqual(p("R"), {"od": "05:00", "do": "13:00", "typ": "P"})
        self.assertEqual(p("05-13"), {"od": "05:00", "do": "13:00", "typ": "P"})
        self.assertEqual(p("13:00-21:00"), {"od": "13:00", "do": "21:00", "typ": "P"})
        self.assertEqual(p("wolne")["typ"], "W")

    def test_GRF_04_porownanie_planu_z_obecnoscia(self):
        self.login()
        for dzien in ("2026-01-05", "2026-01-06", "2026-01-07"):
            self.c.post("/admin/api/grafik/entry",
                        json={"pracownik": "HU_KOWALSKI_JAN", "data": dzien, "shift": "R"})
        for start in (datetime(2026, 1, 5, 5, 10), datetime(2026, 1, 6, 5, 30)):
            self.A.append_csv_row({"pracownik": "HU_KOWALSKI_JAN", "strefa": "PICKING",
                                   "ts_wejscia": start.isoformat(), "czas_min": 60}, start)
        dni = self.c.get("/admin/api/grafik/porownanie?month=2026-01").json["HU_KOWALSKI_JAN"]["dni"]
        self.assertEqual(dni["2026-01-05"]["status"], "na_czas")
        self.assertEqual(dni["2026-01-06"]["status"], "spoznienie")
        self.assertEqual(dni["2026-01-06"]["spoznienie"], 30)
        self.assertEqual(dni["2026-01-07"]["status"], "nieobecnosc")

    # ── Bezpieczeństwo i start ───────────────────────────────────────────────
    def test_SYS_02_haslo_nie_jest_zapisane_jawnie(self):
        self.assertNotIn("admin123", (self.tmp / "data" / "admins.json").read_text(encoding="utf-8"))

    def test_ADM_01_status_bez_sesji_401(self):
        self.rejestruj("PICKING")
        r = self.c.get("/api/status")
        self.assertEqual((r.status_code, r.data), (401, b""))
        self.login()
        self.assertEqual(self.c.get("/api/status").json[0]["pracownik"], "HU_KOWALSKI_JAN")

    def test_ADM_11_limit_prob_logowania(self):
        token = self.csrf()
        for _ in range(5):
            r = self.c.post("/admin/login", data={"username": "admin", "password": "zle", "csrf": token})
            self.assertEqual(r.status_code, 200)
        r = self.c.post("/admin/login", data={"username": "admin", "password": "admin123", "csrf": token})
        self.assertEqual(r.status_code, 429)
        self.assertIn("Zbyt wiele nieudanych prób", r.get_data(as_text=True))
        self.assertEqual(self.c.get("/admin").status_code, 302)   # poprawne hasło w blokadzie nie loguje

    def test_ADM_12_csrf_formularzy_i_importu(self):
        r = self.c.post("/admin/login", data={"username": "admin", "password": "admin123"})
        self.assertEqual(r.status_code, 403)
        self.login()
        xlsx = io.BytesIO()
        openpyxl.Workbook().save(xlsx)
        bez = self.c.post("/admin/api/grafik/import", data={"file": (io.BytesIO(xlsx.getvalue()), "g.xlsx")},
                          content_type="multipart/form-data")
        self.assertEqual(bez.status_code, 403)
        z = self.c.post("/admin/api/grafik/import", data={"file": (io.BytesIO(xlsx.getvalue()), "g.xlsx")},
                        content_type="multipart/form-data", headers={"X-CSRF-Token": self.token})
        self.assertNotEqual(z.status_code, 403)

    def test_ADM_13_ciasteczko_sesji_samesite_httponly(self):
        self.assertEqual(self.A.app.config["SESSION_COOKIE_SAMESITE"], "Lax")
        cookie = self.c.get("/admin/login").headers.get("Set-Cookie", "")
        self.assertIn("SameSite=Lax", cookie)
        self.assertIn("HttpOnly", cookie)

    def test_REJ_09_kod_z_formula_nie_trafia_do_csv_jako_formula(self):
        self.c.post("/api/scan", json={"kod": "=1+1"})
        self.assertEqual(self.A.read_alerts()[0]["pracownik"], "'=1+1")
        self.rejestruj("PICKING")
        self.c.post("/api/rejestruj", json={"pracownik": "HU_KOWALSKI_JAN", "strefa": "PRZYJECIA",
                                            "force": True, "korekta_info": "-2+3"})
        self.assertEqual(self.ewidencja_dzis()[0]["korekta_info"], "'-2+3")

    def test_SYS_04_start_bez_klucza_sesji_konczy_sie_bledem(self):
        env = {k: v for k, v in os.environ.items() if k not in ("RCP_SECRET_KEY", "RCP_DEMO")}
        r = subprocess.run([sys.executable, "-c", "import app"], cwd=self.tmp, env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("RCP_SECRET_KEY", r.stderr)
        env["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        r = subprocess.run([sys.executable, "-c", "import app"], cwd=self.tmp, env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=60)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_SYS_05_haslo_startowe_wymusza_zmiane(self):
        t = self.csrf()
        self.c.post("/admin/login", data={"username": "admin", "password": "admin123", "csrf": t})
        self.assertEqual(self.c.get("/admin").headers["Location"].split("?")[0], "/admin/haslo")
        self.assertEqual(self.c.get("/admin/api/status").status_code, 302)
        r = self.c.post("/admin/haslo", data={"password": "krotkie", "password2": "krotkie", "csrf": t})
        self.assertIn("co najmniej 12", r.get_data(as_text=True))
        r = self.c.post("/admin/haslo", data={"password": NOWE_HASLO, "password2": NOWE_HASLO, "csrf": t})
        self.assertEqual(r.headers["Location"], "/admin")
        self.assertEqual(self.c.get("/admin").status_code, 200)
        self.assertFalse(self.A.load_admins()["admin"]["must_change"])
        self.c.get("/admin/logout")
        t = self.csrf()   # wylogowanie kasuje sesję razem z tokenem
        self.c.post("/admin/login", data={"username": "admin", "password": "admin123", "csrf": t})
        self.assertEqual(self.c.get("/admin").status_code, 302)   # stare hasło już nie działa
        self.c.post("/admin/login", data={"username": "admin", "password": NOWE_HASLO, "csrf": t})
        self.assertEqual(self.c.get("/admin").status_code, 200)

    def test_SYS_06_bez_zmiennej_haslo_startowe_losowe_i_wypisane_raz(self):
        os.environ.pop("RCP_ADMIN_PASSWORD")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            A, tmp = load_app()
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        m = re.search(r"Hasło startowe konta 'admin': (\S+)", buf.getvalue())
        self.assertIsNotNone(m, buf.getvalue())
        c = A.app.test_client()
        tok = re.search(r'name="csrf" value="([0-9a-f]+)"', c.get("/admin/login").get_data(as_text=True)).group(1)
        c.post("/admin/login", data={"username": "admin", "password": m.group(1), "csrf": tok})
        self.assertEqual(c.get("/admin").headers["Location"].split("?")[0], "/admin/haslo")
        self.assertNotIn(m.group(1), (tmp / "data" / "admins.json").read_text(encoding="utf-8"))

    def test_SYS_03_start_bez_przygotowania_danych(self):
        self.assertEqual(len(self.A.load_workers()), 3)
        self.assertIn("PRZERWA", self.A.load_strefy())

    # ── Znane problemy (docs/05-decyzje-i-ograniczenia.md, T6) — test pilnuje opisu ──
    def test_P13_import_szablonu_zglasza_wiersz_legendy(self):
        """Gdy ktoś to naprawi, test przestanie przechodzić — wtedy usuń P13 z docs."""
        self.login()
        wb = openpyxl.load_workbook(io.BytesIO(self.c.get("/admin/api/grafik/template").data))
        buf = io.BytesIO()
        wb.save(buf)
        r = self.c.post("/admin/api/grafik/import", data={"file": (io.BytesIO(buf.getvalue()), "g.xlsx")},
                        content_type="multipart/form-data", headers={"X-CSRF-Token": self.token})
        self.assertEqual(r.json["bledy"], ["Wiersz 2: nie znaleziono pracownika 'LEGENDA →'"])


if __name__ == "__main__":
    unittest.main()
