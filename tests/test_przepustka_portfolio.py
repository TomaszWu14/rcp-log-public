"""Przepustka z portfolio: ciasteczko `gosc` potwierdzone przez portfolio zwalnia z formularza bramki."""
import os
import shutil
import unittest
import urllib.error
from unittest import mock

from test_wymagania import load_app

ENV = ("RCP_DEMO", "DEMO_VISITOR_GATE", "NTFY_URL", "PORTFOLIO_URL", "PORTFOLIO_PASS")


class PrzepustkaPortfolio(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        for k in ENV: os.environ.pop(k, None)
        self.A, self.tmp = load_app()
        self.A.VISITOR_GATE = True
        self.c = self.A.app.test_client()
        self.c.set_cookie("gosc", "tajny-token-123", domain="localhost")
        self.push = mock.patch.object(self.A.visitor_notify, "powiadom_o_gosciu").start()
        self.push2 = mock.patch.object(self.A.visitor_notify, "powiadom_o_zaangazowaniu").start()
        self.A.visitor_pass._cache.clear()

    def tearDown(self):
        mock.patch.stopall()
        for k in ENV: os.environ.pop(k, None)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def status(self, wartosc):
        return mock.patch.object(self.A.visitor_pass, "_status", side_effect=wartosc if isinstance(wartosc, Exception) else None,
                                 return_value=None if isinstance(wartosc, Exception) else wartosc)

    def test_wazna_przepustka_bez_formularza_i_bez_pusha(self):
        with self.status(200) as st:
            self.assertEqual(self.c.get("/").status_code, 200)
            self.assertEqual(self.c.get("/admin/login").status_code, 200)
            self.assertEqual(self.c.get("/wejscie?next=/admin/login").headers["Location"], "/admin/login")
        st.assert_called_once_with("https://portfolio.twapp.pl/api/gosc", "tajny-token-123")   # reszta z sesji/cache
        self.assertEqual(self.A.read_goscie(), [])
        self.push.assert_not_called()
        self.push2.assert_not_called()

    def test_401_formularz_jak_dotad(self):
        with self.status(401):
            r = self.c.get("/")
            self.assertEqual(r.status_code, 302)
            self.assertIn("/wejscie?next=", r.headers["Location"])
            self.assertEqual(self.c.get("/wejscie").status_code, 200)

    def test_blad_sieci_i_timeout_formularz_jak_dotad_nie_500(self):
        for blad in (TimeoutError("t"), urllib.error.URLError("brak"), OSError("x")):
            self.A.visitor_pass._cache.clear()
            with self.status(blad):
                self.assertEqual(self.c.get("/").status_code, 302)
                self.assertEqual(self.c.get("/wejscie").status_code, 200)

    def test_inny_kod_to_odmowa(self):
        for kod in (204, 302, 500):
            with self.status(kod):
                self.assertEqual(self.c.get("/").status_code, 302, kod)

    def test_brak_ciasteczka_bez_wywolania_sieci(self):
        c = self.A.app.test_client()
        with self.status(200) as st:
            self.assertEqual(c.get("/").status_code, 302)
            self.assertEqual(c.get("/wejscie").status_code, 200)
        st.assert_not_called()

    def test_zle_ciasteczko_bez_wywolania_sieci(self):
        for token in ("x" * 201, "a b", "a;b"):
            c = self.A.app.test_client()
            c.set_cookie("gosc", token, domain="localhost")
            with self.status(200) as st:
                c.get("/")
            st.assert_not_called()

    def test_przepustka_wylaczona_albo_http(self):
        for env in ({"PORTFOLIO_PASS": "0"}, {"PORTFOLIO_URL": "http://portfolio.twapp.pl"}):
            os.environ.update(env)
            with self.status(200) as st:
                self.assertEqual(self.c.get("/").status_code, 302, env)
            st.assert_not_called()
            for k in env: os.environ.pop(k)

    def test_cache_nie_pyta_portfolio_ponownie(self):
        with self.status(200) as st:
            self.A.visitor_pass.przepustka_wazna("t")
            self.A.visitor_pass.przepustka_wazna("t")
        self.assertEqual(st.call_count, 1)

    def test_formularz_bez_piksela_portfolio(self):
        with self.status(401):
            self.assertNotIn("/px/", self.c.get("/wejscie").get_data(as_text=True))

    def test_tylko_ciasteczko_gosc_i_bez_przekierowan(self):
        z = {}
        class Odp:
            status = 200
            def __enter__(s): return s
            def __exit__(s, *a): pass
        class Op:
            def open(s, req, timeout): z["h"], z["t"] = dict(req.header_items()), timeout; return Odp()
        with mock.patch.object(self.A.visitor_pass.urllib.request, "build_opener", return_value=Op()) as bo:
            self.assertEqual(self.A.visitor_pass._status("https://p/api/gosc", "abc"), 200)
        self.assertEqual(z["h"], {"Cookie": "gosc=abc"})
        self.assertEqual(z["t"], 2)
        self.assertIsNone(bo.call_args.args[0]().redirect_request())


if __name__ == "__main__":
    unittest.main()
