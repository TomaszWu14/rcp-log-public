"""Powiadomienie push (ntfy) o nowym gościu bramki demo — bez prawdziwego ruchu sieciowego."""
import os
import re
import shutil
import unittest
from unittest import mock

from test_wymagania import load_app

import visitor_notify as VN

DANE = {"imie": "Anna", "nazwisko": "Żółć", "firma": "Acme", "rodo": "1"}


def synchronicznie(fn, *args):
    fn(*args)


class PowiadomienieGosc(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        for k in ("RCP_DEMO", "DEMO_VISITOR_GATE", "NTFY_URL", "NTFY_TOKEN", "NTFY_WATCH_COMPANIES"):
            os.environ.pop(k, None)
        self.A, self.tmp = load_app()
        self.A.VISITOR_GATE = True
        self.c = self.A.app.test_client()
        # wątek uruchamiany synchronicznie, HTTP zawsze zamockowane
        p1 = mock.patch.object(VN, "_uruchom_w_tle", side_effect=synchronicznie)
        p2 = mock.patch.object(VN, "_wyslij")
        self.watek, self.wyslij_http = p1.start(), p2.start()
        self.addCleanup(mock.patch.stopall)

    def tearDown(self):
        for k in ("NTFY_URL", "NTFY_TOKEN", "NTFY_WATCH_COMPANIES"):
            os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def wyslij(self, **zmiany):
        html = self.c.get("/wejscie").get_data(as_text=True)
        tok = re.search(r'name="csrf" value="([0-9a-f]+)"', html).group(1)
        return self.c.post("/wejscie", data={"csrf": tok, "next": "/admin", **DANE, **zmiany})

    def test_poprawny_formularz_jedno_powiadomienie(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/tajny-temat"
        r = self.wyslij()
        self.assertEqual((r.status_code, r.headers["Location"]), (302, "/admin"))
        self.wyslij_http.assert_called_once()
        url, body, headers = self.wyslij_http.call_args.args
        self.assertEqual(url, "https://ntfy.example/tajny-temat")
        self.assertEqual(body, "Anna Żółć (Acme) wszedł do rcp-log")
        self.assertEqual(headers["Title"], "Nowy gosc: rcp-log")
        self.assertEqual((headers["Tags"], headers["Priority"]), ("bell", "high"))
        self.assertNotIn("Authorization", headers)
        for k, v in headers.items():
            self.assertTrue(v.isascii(), k)

    def test_token_daje_naglowek_authorization(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        os.environ["NTFY_TOKEN"] = "tk_abc"
        self.wyslij()
        self.assertEqual(self.wyslij_http.call_args.args[2]["Authorization"], "Bearer tk_abc")

    def test_honeypot_i_bledne_dane_bez_powiadomienia(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        self.assertEqual(self.wyslij(www="http://spam").status_code, 400)
        self.assertEqual(self.wyslij(imie="a").status_code, 400)
        self.assertEqual(self.wyslij(rodo="").status_code, 400)
        self.watek.assert_not_called()
        self.wyslij_http.assert_not_called()

    def test_bez_ntfy_url_brak_wysylki(self):
        self.assertEqual(self.wyslij().status_code, 302)
        self.watek.assert_not_called()
        self.wyslij_http.assert_not_called()

    def test_niedozwolony_schemat_brak_wysylki(self):
        os.environ["NTFY_URL"] = "file:///etc/passwd"
        self.assertEqual(self.wyslij().status_code, 302)
        self.wyslij_http.assert_not_called()

    def test_wyjatek_wysylki_nie_psuje_odpowiedzi(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        self.wyslij_http.side_effect = OSError("timeout")
        with self.assertLogs("rcp", "WARNING"):
            r = self.wyslij()
        self.assertEqual((r.status_code, r.headers["Location"]), (302, "/admin"))
        self.assertEqual(len(self.A.read_goscie()), 1)

    def test_wyjatek_przy_starcie_watku_nie_psuje_odpowiedzi(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        self.watek.side_effect = RuntimeError("can't start new thread")
        with self.assertLogs("rcp", "WARNING"):
            self.assertEqual(self.wyslij().status_code, 302)

    def test_body_przyciete_do_300_znakow(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        self.wyslij(imie="x" * 100, nazwisko="y" * 100, firma="z" * 100)
        self.assertEqual(len(self.wyslij_http.call_args.args[1]), 300)

    def test_wysylka_w_watku_daemon_z_timeoutem(self):
        mock.patch.stopall()
        with mock.patch.object(VN.threading, "Thread") as T, \
                mock.patch.object(VN.urllib.request, "urlopen") as U:
            os.environ["NTFY_URL"] = "https://ntfy.example/t"
            VN.powiadom_o_gosciu("Anna", "Nowak", "Acme")
            self.assertTrue(T.call_args.kwargs["daemon"])
            T.return_value.start.assert_called_once()
            VN._wyslij(*T.call_args.kwargs["args"])
            req = U.call_args.args[0]
            self.assertEqual((req.get_method(), U.call_args.kwargs["timeout"]), ("POST", 5))
            self.assertEqual(req.data.decode("utf-8"), "Anna Nowak (Acme) wszedł do rcp-log")

    def test_firma_z_listy_urgent(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        os.environ["NTFY_WATCH_COMPANIES"] = " firma-testowa , acme "
        self.wyslij(firma="ÄCME   Sp. z o.o.")
        _, body, headers = self.wyslij_http.call_args.args
        self.assertEqual((headers["Priority"], headers["Tags"]), ("urgent", "rotating_light"))
        self.assertEqual(headers["Title"], "UWAGA firma z listy: rcp-log")
        self.assertEqual(body, "⚠️ Anna Żółć (ÄCME   Sp. z o.o.) wszedł do rcp-log")
        for k, v in headers.items():
            self.assertTrue(v.isascii(), k)

    def test_dopasowanie_firmy_diakrytyki_i_wielkosc_liter(self):
        os.environ["NTFY_WATCH_COMPANIES"] = "zolw, x,  łódź  przemysł "
        self.assertTrue(VN.firma_na_liscie("Żółw Logistics"))
        self.assertTrue(VN.firma_na_liscie("LODZ   PRZEMYSL S.A."))
        self.assertFalse(VN.firma_na_liscie("Xenon"))   # fraza krótsza niż 2 znaki jest pomijana
        self.assertFalse(VN.firma_na_liscie("Inna"))

    def test_firma_spoza_listy_i_pusta_lista_zwykly_push(self):
        os.environ["NTFY_URL"] = "https://ntfy.example/t"
        for lista in ("globex", "", " , "):
            os.environ["NTFY_WATCH_COMPANIES"] = lista
            self.wyslij_http.reset_mock()
            self.wyslij()
            _, body, headers = self.wyslij_http.call_args.args
            self.assertEqual((headers["Priority"], headers["Tags"], headers["Title"]),
                             ("high", "bell", "Nowy gosc: rcp-log"), lista)
            self.assertEqual(body, "Anna Żółć (Acme) wszedł do rcp-log")

    def test_firma_z_listy_bez_ntfy_url_nic_nie_wysyla(self):
        os.environ["NTFY_WATCH_COMPANIES"] = "acme"
        self.assertEqual(self.wyslij().status_code, 302)
        self.wyslij_http.assert_not_called()
        self.watek.assert_not_called()

    def test_klauzula_rodo_wspomina_ntfy(self):
        html = self.c.get("/wejscie").get_data(as_text=True)
        self.assertIn("O każdej wizycie (imię, nazwisko, firma) dostaję powiadomienie na telefon przez usługę "
                      "powiadomień push ntfy. Zapisuję też, ile i jakie ekrany wersji demonstracyjnej obejrzałeś "
                      "(bez adresu IP), żeby wiedzieć, co zainteresowało gości. Poza tym nikomu danych nie "
                      "przekazuję.", html)
        self.assertNotIn("push ntfy; poza tym", html)
        self.assertNotIn("i nikomu ich nie przekazuję", html)


if __name__ == "__main__":
    unittest.main()
