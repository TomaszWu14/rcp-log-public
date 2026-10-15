"""Przelicza odwołania `plik.py:N`, `plik.py:N-M` i listy `plik.py:N, M-K` w dokumentacji po zmianie kodu.

Użycie: python tools/remap_line_refs.py <ref-bazowy> [plik.md ...]
Bez listy plików: docs/**/*.md (poza archiwum) i README.md. Odwołania do linii wewnątrz
zmienionych fragmentów nie są przepisywane — skrypt wypisuje je do ręcznego sprawdzenia.
"""
import pathlib
import re
import subprocess
import sys

base = sys.argv[1]
files = sys.argv[2:] or [str(p) for p in pathlib.Path("docs").rglob("*.md") if "archiwum" not in p.parts] + ["README.md"]

diff = subprocess.run(["git", "diff", "-U0", base, "--", "*.py"], capture_output=True, text=True, encoding="utf-8").stdout

# Blokada przed podwójnym uruchomieniem na tym samym diffie — drugi przebieg dublowałby przesunięcia.
STAMP = pathlib.Path(".remap_line_refs.last")
digest = __import__("hashlib").sha1(diff.encode("utf-8")).hexdigest()
if STAMP.exists() and STAMP.read_text() == digest:
    sys.exit("Ten diff już został zastosowany do dokumentacji — pomijam (usuń .remap_line_refs.last, żeby wymusić).")
STAMP.write_text(digest)
hunks = {}   # plik -> [(old_start, old_len, new_start, new_len)]
cur = None
for line in diff.splitlines():
    if line.startswith("+++ b/"):
        cur = line[6:]
        hunks[cur] = []
    m = re.match(r"@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
    if m and cur:
        a, b, c, d = m.groups()
        hunks[cur].append((int(a), 1 if b is None else int(b), int(c), 1 if d is None else int(d)))


def remap(f, n):
    delta = 0
    for os_, ol, _ns, nl in hunks.get(f, []):
        if ol == 0:
            os_ += 1          # czysta wstawka "-a,0" oznacza: po linii a
        if n < os_:
            break
        if n < os_ + ol:
            return None       # linia zmieniona lub usunięta
        delta += nl - ol
    return n + delta


flagged = []
pat = re.compile(r"\b([\w.-]+\.py):(\d+(?:-\d+)?(?:,\s*\d+(?:-\d+)?)*)")


def sub(m, path):
    f, lista = m.group(1), m.group(2)
    if f not in hunks:
        return m.group(0)
    out = []
    for part in re.split(r",\s*", lista):
        a, _, b = part.partition("-")
        na = remap(f, int(a))
        nb = remap(f, int(b)) if b else None
        if na is None or (b and nb is None):
            flagged.append(f"{path}: {f}:{part}")
            out.append(part)
        else:
            out.append(f"{na}-{nb}" if b else str(na))
    return f"{f}:" + ", ".join(out)


for path in files:
    p = pathlib.Path(path)
    s = p.read_text(encoding="utf-8")
    new = pat.sub(lambda m, path=path: sub(m, path), s)
    if new != s:
        p.write_text(new, encoding="utf-8", newline="\n")
        print(f"przepisano: {path}")

print("\n".join(flagged) if flagged else "brak odwołań do ręcznego sprawdzenia")
