"""Tests du mode portable : détection du drapeau, mutex par dossier, archive ZIP."""

from __future__ import annotations

import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "outils"))

passed = failed = 0


def ok(condition, message):
    global passed, failed
    print(("OK    " if condition else "[ECHEC] ") + message)
    passed += bool(condition)
    failed += not condition


root = Path(tempfile.mkdtemp(prefix="nexus-portable-test-"))
try:
    import build_native
    import nexus_launcher

    # --- drapeau portable -------------------------------------------------
    dossier = root / "portable"
    dossier.mkdir()
    (dossier / "portable.flag").write_text("portable", encoding="utf-8")
    ancien_frozen = getattr(sys, "frozen", None)
    sys.frozen = True
    try:
        ok(nexus_launcher._portable_flag(dossier), "portable.flag détecté à côté de l'exe")
        ok(not nexus_launcher._portable_flag(root / "ailleurs"), "absence de drapeau : mode installé")
    finally:
        if ancien_frozen is None:
            del sys.frozen
        else:
            sys.frozen = ancien_frozen

    os.environ["NEXUS_PORTABLE"] = "1"
    nom = nexus_launcher._mutex_name()
    ok(nom.startswith("Local\\NEXUS-") and nom.count("-") >= 2, "mutex portable propre au dossier")
    os.environ.pop("NEXUS_PORTABLE", None)
    nom_installe = nexus_launcher._mutex_name()
    ok(not nom_installe.endswith(nom.split("-")[-1]), "mutex installé distinct du mutex portable")

    # --- archive portable -------------------------------------------------
    ancien_dist = build_native.DIST
    build_native.DIST = root / "dist"
    source = build_native.DIST / "NEXUS"
    (source / "_internal").mkdir(parents=True)
    (source / "NEXUS.exe").write_bytes(b"MZ-fake")
    (source / "_internal" / "app.py").write_text("print('ok')", encoding="utf-8")
    (source / "NEXUS.exe.sha256").write_text("hash  NEXUS.exe\n", encoding="utf-8")
    try:
        archive = build_native.write_portable("9.9.9")
        ok(archive.is_file() and archive.name == "NEXUS-Portable-9.9.9.zip", "archive portable créée")
        with zipfile.ZipFile(archive) as z:
            noms = set(z.namelist())
            ok("NEXUS-Portable-9.9.9/NEXUS.exe" in noms, "exe inclus")
            ok("NEXUS-Portable-9.9.9/_internal/app.py" in noms, "_internal inclus")
            ok("NEXUS-Portable-9.9.9/portable.flag" in noms, "drapeau portable inclus")
            ok("NEXUS-Portable-9.9.9/Lancer NEXUS.bat" in noms, "lanceur inclus")
            ok("NEXUS-Portable-9.9.9/LISEZMOI.txt" in noms, "notice incluse")
            ok("NEXUS-Portable-9.9.9/NEXUS.exe.sha256" not in noms, "ancien .sha256 non embarqué")
            ok(b"NEXUS portable" in z.read("NEXUS-Portable-9.9.9/portable.flag"), "contenu du drapeau")
    finally:
        build_native.DIST = ancien_dist
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
