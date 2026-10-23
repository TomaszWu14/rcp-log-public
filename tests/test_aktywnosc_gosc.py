"""Aktywność gościa bramki demo: ekrany, czas wizyty, sekcje i push „zaangażowany gość”."""
import json
import os
import re
import shutil
import time
import unittest
from datetime import datetime, timedelta
from unittest import mock

from flask import Flask
from flask.sessions import SecureCookieSessionInterface
from test_wymagania import load_app

import visitor_activity as VA
import visitor_notify as VN

DANE = {"imie": "Anna", "nazwisko": "Nowak", "firma": "Acme", "rodo": "1"}
ENV = ("RCP_DEMO", "DEMO_VISITOR_GATE", "NTFY_URL", "NTFY_TOKEN", "NTFY_WATCH_COMPANIES", "NTFY_ENGAGED_VIEWS")


def synchronicznie(fn, *args):
    fn(*args)


class AktywnoscGoscia(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        for k in ENV:
            os.environ.pop(k, None)
        self.A, self.tmp = load_app()
        self.A.VISITOR_GATE = True
        self.c = self.A.app.test_client()
        p1 = mock.patch.object(VN, "_uruchom_w_tle", side_effect=synchronicznie)
        p2 = mock.patch.object(VN, "_wyslij")
        p1.start()
        self.wyslij_http = p2.start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        for k in ENV:
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wejdz(self, **zmiany):
        html = self.c.get("/wejscie").get_data(as_text=True)
        tok = re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)
        r = self.c.post("/wejscie", data={"csrf": tok, "next": "/", **DANE, **zmiany})
        self.assertEqual(r.status_code, 302)

    def wiersz(self):
        w, = self.A.read_goscie()
        return w

    def test_trzy_ekrany_policzone_z_sekcjami(self):
        self.wejdz()
        for url in ("/", "/", "/admin/login"):
            self.assertEqual(self.c.get(url).status_code, 200, url)
        w = self.wiersz()
        self.assertEqual(w["page_views"], "3")
        self.assertEqual(json.loads(w["sections"]), {"start": 2, "admin": 1})
        self.assertTrue(datetime.fromisoformat(w["last_seen_at"]) >= datetime.fromisoformat(w["created_at"]))
        self.assertEqual(len(w["id"]), 16)

    def test_static_health_api_404_i_przekierowania_nie_liczone(self):
        self.wejdz()
        self.c.get("/static/nie-ma.js")
        self.c.get("/health")
        self.c.get("/api/status")
        self.c.get("/api/alerts/new")
        self.c.get("/nie-ma-takiej-strony")
        self.c.get("/admin")       # 302 do logowania — nie liczone
        self.c.get("/wejscie")     # sama bramka
        self.c.post("/api/scan", json={"kod": "HU_KOWALSKI_JAN"})
        self.assertEqual(self.wiersz()["page_views"], "0")
        for s in ("/static/x.css", "/health", "/api/scan", "/admin/api/status"):
            self.assertFalse(VA.liczona_sciezka(s), s)
        for s in ("/", "/admin", "/admin/login"):
            self.assertTrue(VA.liczona_sciezka(s), s)

    def test_gosc_bez_flagi_lub_ze_stara_flaga_bez_id_nie_liczony(self):
        self.A.zapisz_goscia("Anna", "Nowak", "Acme")
        self.A.VISITOR_GATE = False
        self.c.get("/")
        self.A.VISITOR_GATE = True
        with self.c.session_transaction() as s:
            s["gosc_ts"] = time.time()   # flaga sprzed zmiany: bez id
        self.assertEqual(self.c.get("/").status_code, 200)
        self.assertEqual(self.wiersz()["page_views"], "0")

    def test_podrobiona_flaga_nie_liczona(self):
        self.wejdz()
        gid = self.wiersz()["id"]
        obca = Flask("obca")
        obca.secret_key = "inny-klucz-" * 4
        ciastko = SecureCookieSessionInterface().get_signing_serializer(obca).dumps(
            {"gosc_ts": time.time(), "gosc_id": gid})
        c2 = self.A.app.test_client()
        c2.set_cookie("session", ciastko)
        self.assertEqual(c2.get("/").status_code, 302)   # bramka też nie wpuszcza
        self.assertEqual(self.wiersz()["page_views"], "0")

    def test_prog_zaangazowania_dokladnie_jeden_push(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        os.environ["NTFY_ENGAGED_VIEWS"] = "3"
        self.wejdz()
        for _ in range(6):
            self.c.get("/")
        self.assertEqual(self.wyslij_http.call_count, 2)   # wejście + jeden „zaangażowany”
        _, body, headers = self.wyslij_http.call_args.args
        self.assertEqual(body, "Anna Nowak (Acme) obejrzał już 3 ekranów w rcp-log")
        self.assertEqual((headers["Title"], headers["Tags"], headers["Priority"]),
                         ("Gosc oglada demo: rcp-log", "eyes", "default"))

    def test_prog_firma_z_listy_urgent_i_zero_wylacza(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        os.environ["NTFY_WATCH_COMPANIES"] = "acme"
        os.environ["NTFY_ENGAGED_VIEWS"] = "1"
        self.wejdz()
        self.c.get("/")
        self.assertEqual(self.wyslij_http.call_args.args[2]["Priority"], "urgent")
        self.assertEqual(self.wyslij_http.call_args.args[2]["Tags"], "eyes")
        os.environ["NTFY_ENGAGED_VIEWS"] = "0"
        self.wyslij_http.reset_mock()
        self.c.get("/")
        self.wyslij_http.assert_not_called()

    def test_wyjatek_przy_liczeniu_nie_psuje_odpowiedzi(self):
        self.wejdz()
        with mock.patch.object(self.A, "zarejestruj_aktywnosc", side_effect=OSError("dysk")), \
                self.assertLogs("rcp", "WARNING"):
            r = self.c.get("/")
        self.assertEqual(r.status_code, 200)

    def test_lista_pokazuje_kolumny_aktywnosci(self):
        self.wejdz()
        self.c.get("/")
        self.c.get("/admin/login")
        self.A.zapisz_goscia("Stary", "Format", "Firma")   # wiersz bez aktywności
        os.environ["VISITORS_TOKEN"] = "tajny-token"
        try:
            html = self.c.get("/admin/goscie?token=tajny-token").get_data(as_text=True)
            csv_ = self.c.get("/admin/goscie.csv?token=tajny-token").get_data(as_text=True)
        finally:
            os.environ.pop("VISITORS_TOKEN", None)
        for kol in ("Ekrany", "Czas", "Najczęściej", "ok. 1 min", "admin (1), start (1)", "—"):
            self.assertIn(kol, html)
        self.assertIn("created_at;imie;nazwisko;firma;ekrany;czas;najczesciej", csv_)
        self.assertIn(";2;ok. 1 min;admin (1), start (1)", csv_)

    def test_stary_plik_bez_nowych_kolumn_dziala(self):
        self.A.GOSCIE_FILE.write_text("created_at;imie;nazwisko;firma\n"
                                      f"{datetime.now().isoformat(timespec='seconds')};Ola;Kot;Firma\n",
                                      encoding="utf-8-sig")
        self.wejdz()
        self.c.get("/")
        stary, nowy = self.A.read_goscie()
        self.assertEqual((stary["imie"], stary["page_views"], stary["id"]), ("Ola", "", ""))
        self.assertEqual(nowy["page_views"], "1")
        self.assertEqual(VA.czas_wizyty(stary), "—")

    def test_limit_20_sekcji_i_normalizacja_sekcji(self):
        w = {"page_views": "0", "sections": "{}"}
        now = datetime.now()
        for i in range(25):
            VA.zarejestruj_ekran(w, f"s{i}", now)
        VA.zarejestruj_ekran(w, "s0", now)
        d = VA.sekcje(w)
        self.assertEqual(len(d), 20)
        self.assertNotIn("s24", d)
        self.assertEqual((d["s0"], w["page_views"]), (2, "26"))
        self.assertEqual(VA.sekcja_ze_sciezki("/palety/123"), "palety")
        self.assertEqual(VA.sekcja_ze_sciezki("/"), "start")
        self.assertEqual(VA.sekcja_ze_sciezki("/Ab%3Cx>!/y"), "ab3cx")
        self.assertEqual(VA.sekcja_ze_sciezki("/" + "a" * 60), "a" * 40)
        self.assertIsNone(VA.sekcja_ze_sciezki("/żółć"))

    def test_czas_wizyty(self):
        t0 = datetime(2026, 10, 1, 12, 0, 0)
        w = {"created_at": t0.isoformat(), "last_seen_at": (t0 + timedelta(minutes=7, seconds=20)).isoformat()}
        self.assertEqual(VA.czas_wizyty(w), "ok. 7 min")
        self.assertEqual(VA.czas_wizyty({"created_at": t0.isoformat(), "last_seen_at": ""}), "—")


if __name__ == "__main__":
    unittest.main()
