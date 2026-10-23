# RCP Log — obraz produkcyjny (Coolify lub dowolny Docker).
#   docker build -t rcp-log .
#   docker run --rm -p 5050:5050 -e RCP_DEMO=1 rcp-log
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Europe/Warsaw \
    PORT=5050

# Ewidencja zapisuje czas lokalny (Europe/Warsaw); obraz slim nie ma baz stref czasowych.
RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
# pip jest potrzebny tylko przy budowaniu. Usuwamy go z obrazu, bo jego dołączone biblioteki
# (urllib3, certifi, msgpack, setuptools) zgłasza Trivy jako HIGH/CRITICAL, a aplikacja ich nie używa.
RUN pip install -r requirements.txt \
    && pip uninstall -y pip

COPY app.py run.py demo_data.py visitor_notify.py ./
COPY templates/ templates/

# Katalogi data/, data_demo/ i backup/ tworzy aplikacja przy starcie — muszą być zapisywalne
# dla użytkownika bez uprawnień roota.
RUN useradd --system --uid 1000 --create-home app \
    && mkdir -p /app/data /app/data_demo /app/backup \
    && chown -R app:app /app
USER app

EXPOSE 5050

# Strona skanera (/) odpowiada bez logowania; start-period pokrywa generowanie danych demo.
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD ["python", "-c", "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:%s/' % os.environ.get('PORT', '5050'), timeout=4)"]

CMD ["python", "run.py"]
