"""
RCP Log v3 — uruchomienie produkcyjne
Użycie: python run.py
Domyślne konto admina: admin / admin123
Tryb demo (bez logowania, dane fikcyjne): RCP_DEMO=1 python run.py
"""
import os
from waitress import serve
from app import app, DEMO

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print("=" * 52)
    print("  RCP Log v3" + ("  —  TRYB DEMO" if DEMO else ""))
    print(f"  Skaner:  http://0.0.0.0:{port}/")
    print(f"  Admin:   http://0.0.0.0:{port}/admin")
    print("  Login:   " + ("automatyczny (demo)" if DEMO else "admin / admin123"))
    print("  Zatrzymaj: Ctrl+C")
    print("=" * 52)
    serve(app, host="0.0.0.0", port=port, threads=4)
