# WHO-SCAN

System ewidencji czasu pracy w strefach magazynowych.

## Funkcje

- Skanowanie kodów QR pracowników (format `HU_NAZWISKO_IMIE`)
- Rejestracja przejść między strefami magazynowymi
- Podstrefy dla strefy INNE
- Panel admina z podglądem live, historią, raportami
- Macierz uprawnień stref per pracownik
- Ręczne zarządzanie sesjami przez admina
- Alerty przy przekroczeniu czasu przerwy
- Raport nadwyżek czasu przerwy
- Backup danych co noc
- CSV per dzień i per miesiąc
- Ciemny / jasny motyw

## Instalacja

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
python run.py
```

Aplikacja dostępna pod:
- Skaner: `http://localhost:5050/`
- Admin: `http://localhost:5050/admin`

Domyślne dane logowania: `admin / admin123`

## Struktura

```
HUSCAN/
├── app.py              # Logika Flask + API
├── run.py              # Uruchomienie produkcyjne (Waitress)
├── requirements.txt
├── templates/
│   ├── index.html      # Ekran skanowania
│   ├── admin.html      # Panel admina
│   └── admin_login.html
└── data/               # Dane (nie w repo)
    ├── pracownicy.json
    ├── strefy.json
    ├── admins.json
    ├── aktywne_sesje.json
    ├── config.json
    └── ewidencja_*.csv
```

## Format kodów QR

`HU_NAZWISKO_INICJAL` — np. `HU_KOWALSKI_JAN`

## Dane startowe

Przed pierwszym uruchomieniem wrzuć do `data/`:
- `pracownicy.json` — lista pracowników z uprawnieniami stref
- `strefy.json` — definicje stref i podstref

Pliki generuje się przez macierz uprawnień w panelu admina.
