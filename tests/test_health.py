"""GET /health: żywotność dla monitora demo — bez logowania, bramki gości, sesji i statystyk."""
import os
import shutil
import unittest

from test_wymagania import load_app


class Health(unittest.TestCase):
    def setUp(self):
        os.environ["RCP_SECRET_KEY"] = "klucz-testowy-" * 4
        os.environ["RCP_ADMIN_PASSWORD"] = "admin123"
        os.environ.pop("RCP_DEMO", None)
        os.environ.pop("DEMO_VISITOR_GATE", None)
        self.A, self.tmp = load_app()
        self.c = self.A.app.test_client()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_200_json_bez_logowania(self):
        r = self.c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})
        self.assertEqual(r.headers["Cache-Control"], "no-store")
        self.assertNotIn("Set-Cookie", r.headers)

    def test_z_wlaczona_bramka_gosci_bez_wpisu_goscia(self):
        self.A.VISITOR_GATE = True
        self.assertEqual(self.c.get("/").status_code, 302)   # kontrola: bramka działa
        r = self.c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.get_json(), {"status": "ok"})
        self.assertEqual(self.A.read_goscie(), [])
        with self.c.session_transaction() as s:
            self.assertNotIn("gosc_id", s)
            self.assertNotIn("gosc_ts", s)

    def test_tryb_demo_nie_tworzy_sesji(self):
        self.A.DEMO = True
        self.A.VISITOR_GATE = True
        r = self.c.get("/health")
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("Set-Cookie", r.headers)


if __name__ == "__main__":
    unittest.main()
