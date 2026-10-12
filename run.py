"""
TimeApp v3 — uruchomienie produkcyjne
Użycie: python run.py
Domyślne konto admina: admin / admin123
"""
from waitress import serve
from app import app

if __name__ == "__main__":
    print("=" * 52)
    print("  TimeApp v3")
    print("  Skaner:  http://0.0.0.0:5050/")
    print("  Admin:   http://0.0.0.0:5050/admin")
    print("  Login:   admin / admin123")
    print("  Zatrzymaj: Ctrl+C")
    print("=" * 52)
    serve(app, host="0.0.0.0", port=5050, threads=4)
