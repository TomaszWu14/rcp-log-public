"""Bramka gości demo (DEMO_VISITOR_GATE): przedstawienie się przed stroną skanera i panelu."""
import os
import re
import shutil
import unittest
from datetime import datetime, timedelta

from test_wymagania import load_app

DANE = {"imie": "Anna", "nazwisko": "Nowak", "firma": "Acme", "rodo": "1"}


class BramkaGosci(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        os.environ.pop("RCP_DEMO", None)
        os.environ.pop("DEMO_VISITOR_GATE", None)
        self.A, self.tmp = load_app()
        self.c = self.A.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def token(self, url="/wejscie"):
        html = self.c.get(url).get_data(as_text=True)
        return re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)

    def wyslij(self, **zmiany):
        return self.c.post("/wejscie", data={"csrf": self.token(), "next": "/admin", **DANE, **zmiany})

    def test_domyslnie_wylaczona_poza_demo(self):
        self.assertFalse(self.A.VISITOR_GATE)
        self.assertEqual(self.c.get("/").status_code, 200)

    def test_bez_danych_odmowa_i_przekierowanie_do_formularza(self):
        self.A.VISITOR_GATE = True
        for url in ("/", "/admin"):
            r = self.c.get(url)
            self.assertEqual(r.status_code, 302, url)
            self.assertIn("/wejscie?next=", r.headers["Location"])
        for pole in ("imie", "nazwisko", "firma"):
            self.assertEqual(self.wyslij(**{pole: " a "}).status_code, 400)
        self.assertEqual(self.wyslij(imie="An\x07na").status_code, 400)
        self.assertEqual(self.wyslij(imie="x" * 101).status_code, 400)
        self.assertEqual(self.wyslij(rodo="").status_code, 400)
        self.assertEqual(self.A.read_goscie(), [])
        self.assertEqual(self.c.get("/").status_code, 302)

    def test_csrf_wymagany(self):
        self.A.VISITOR_GATE = True
        self.assertEqual(self.c.post("/wejscie", data={**DANE}).status_code, 403)

    def test_z_danymi_zapis_dostep_i_bezpieczny_next(self):
        self.A.VISITOR_GATE = True
        r = self.wyslij(imie="  Anna  ")
        self.assertEqual((r.status_code, r.headers["Location"]), (302, "/admin"))
        self.assertEqual(self.c.get("/").status_code, 200)
        wiersz, = self.A.read_goscie()
        self.assertEqual((wiersz["imie"], wiersz["nazwisko"], wiersz["firma"]), ("Anna", "Nowak", "Acme"))
        self.assertEqual(list(wiersz), ["created_at", "imie", "nazwisko", "firma", "id", "page_views",
                                        "last_seen_at", "sections"])   # bez IP i user-agenta
        for zly in ("//evil.com", "https://evil.com", "/\\evil.com", "evil"):
            self.assertEqual(self.wyslij(next=zly).headers["Location"], "/")

    def test_honeypot_odmowa(self):
        self.A.VISITOR_GATE = True
        self.assertEqual(self.wyslij(www="http://spam").status_code, 400)
        self.assertEqual(self.A.read_goscie(), [])
        self.assertEqual(self.c.get("/").status_code, 302)

    def test_api_i_statyczne_nie_sa_blokowane(self):
        self.A.VISITOR_GATE = True
        self.assertEqual(self.c.post("/api/scan", json={"kod": "HU_KOWALSKI_JAN"}).status_code, 200)
        self.assertEqual(self.c.get("/api/status").status_code, 401)   # własna autoryzacja, nie bramka
        self.assertNotEqual(self.c.get("/static/nie-ma.js").status_code, 302)

    def test_retencja_90_dni(self):
        A = self.A
        now = datetime.now()
        A.zapisz_goscia("Stary", "Wpis", "Firma", now - timedelta(days=91))
        A.zapisz_goscia("Swiezy", "Wpis", "Firma", now - timedelta(days=89))
        A.zapisz_goscia("Nowy", "Wpis", "Firma", now)
        self.assertEqual([r["imie"] for r in A.read_goscie()], ["Swiezy", "Nowy"])

    def test_sesja_30_dni_wygasa(self):
        self.A.VISITOR_GATE = True
        self.wyslij()
        with self.c.session_transaction() as s:
            s["gosc_ts"] = s["gosc_ts"] - 31 * 86400
        self.assertEqual(self.c.get("/").status_code, 302)

    def test_lista_gosci_tylko_dla_admina(self):
        self.A.zapisz_goscia("Anna", "Nowak", "=Acme", datetime.now())
        for url in ("/admin/goscie", "/admin/goscie.csv"):
            self.assertEqual(self.c.get(url).status_code, 302)
        tok = self.token("/admin/login")
        self.c.post("/admin/login", data={"username": "admin", "password": "admin123", "csrf": tok})
        self.c.post("/admin/haslo", data={"password": "Nowe-haslo-testowe-1", "password2": "Nowe-haslo-testowe-1", "csrf": tok})
        html = self.c.get("/admin/goscie").get_data(as_text=True)
        self.assertIn("Nowak", html)
        csv_ = self.c.get("/admin/goscie.csv").get_data(as_text=True)
        self.assertIn("'=Acme", csv_)

    def test_demo_lista_gosci_tylko_z_tokenem(self):
        self.A.zapisz_goscia("Anna", "Nowak", "Acme", datetime.now())
        self.A.DEMO = True
        with self.c.session_transaction() as s:
            s["admin_logged"], s["admin_user"] = True, "demo"
        for url in ("/admin/goscie", "/admin/goscie.csv", "/admin/goscie?token=x"):   # brak zmiennej env
            self.assertEqual(self.c.get(url).status_code, 404, url)
        os.environ["VISITORS_TOKEN"] = "tajny-token"
        try:
            for url in ("/admin/goscie", "/admin/goscie?token=zly", "/admin/goscie.csv?token="):
                self.assertEqual(self.c.get(url).status_code, 404, url)
            self.assertIn("Nowak", self.c.get("/admin/goscie?token=tajny-token").get_data(as_text=True))
            self.assertIn("Nowak", self.c.get("/admin/goscie.csv?token=tajny-token").get_data(as_text=True))
        finally:
            os.environ.pop("VISITORS_TOKEN", None)


if __name__ == "__main__":
    unittest.main()
