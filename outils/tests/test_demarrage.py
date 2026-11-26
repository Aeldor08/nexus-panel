"""Démarrage de Windows (demarrage.py) : commande de démarrage automatique, clé Run, état, scripts administrateur.

Rien de réel n'est touché : la clé Run est testée sous un AUTRE nom de valeur (NEXUS_TEST_RUN_NOM), supprimé à la fin ;
les scripts administrateur (tâche planifiée, copie dans Program Files) sont seulement générés et analysés par
PowerShell, jamais exécutés (ils demanderaient la fenêtre d'autorisation de Windows).
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
os.environ["NEXUS_TEST_RUN_NOM"] = f"NEXUS-test-{os.getpid()}"
os.environ.setdefault("NEXUS_DATA_DIR", tempfile.mkdtemp(prefix="nexus-test-demarrage-"))
sys.path.insert(0, str(BASE))

passed = failed = 0


def ok(c, m):
    global passed, failed
    print(("OK    " if c else "ÉCHEC ") + m, flush=True)
    passed += bool(c)
    failed += not c


import demarrage as D

ok(D.NOM_RUN.startswith("NEXUS-test-"), "tests : la vraie valeur « NEXUS » de la clé Run n'est jamais touchée")

# --- commande de démarrage automatique ------------------------------------------------------------------------
cmd = D.commande_autostart()
ok("nexus.pyw" in cmd and cmd.endswith("--demarrage") and "pythonw" in cmd.lower(),
   "version source : pythonw.exe nexus.pyw --demarrage (icône seulement, pas de navigateur)")
sys.frozen = True
try:
    exe = sys.executable
    sys.executable = r"C:\Programmes\NEXUS\NEXUS.exe"
    ok(D.commande_autostart() == r'"C:\Programmes\NEXUS\NEXUS.exe" --minimized', "version exe : NEXUS.exe --minimized")
finally:
    sys.executable = exe
    del sys.frozen

# --- clé Run (sous le nom de test) ----------------------------------------------------------------------------
if os.name == "nt":
    try:
        e0 = D.etat()
        ok(e0["windows"] and not e0["autostart"], "état : démarrage automatique désactivé au départ")
        D.regler_autostart(True)
        ok(D._lire_run() == D.commande_autostart() and D.etat()["autostart"], "case cochée : valeur Run écrite pour cette copie")
        import winreg

        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, D.CLE_RUN, 0, winreg.KEY_SET_VALUE) as k:
            winreg.SetValueEx(k, D.NOM_RUN, 0, winreg.REG_SZ, r'"D:\Autre\NEXUS.exe" --minimized')
        e1 = D.etat()
        ok(not e1["autostart"] and e1["autostart_ailleurs"], "une autre copie de NEXUS au démarrage : signalée, case décochée")
        D.regler_autostart(False)
        ok(D._lire_run() is None and not D.etat()["autostart_ailleurs"], "case décochée : valeur Run supprimée")
        D.regler_autostart(False)
        ok(True, "décocher deux fois : aucune erreur")
    finally:
        try:
            D.regler_autostart(False)
        except D.DemarrageErreur:
            pass
else:
    print("      (clé Run : Windows seulement)")

# --- état de LibreHardwareMonitor --------------------------------------------------------------------------------
e = D.etat()
ok(set(e) >= {"lhm_present", "lhm_sans_fenetre", "lhm_en_marche"} and all(isinstance(e[k], bool) for k in e),
   "état : présence, tâche planifiée et LibreHardwareMonitor en marche (booléens)")
ok(str(D.dossier_protege()).lower().endswith(r"program files\nexus\librehardwaremonitor"),
   f"copie protégée dans Program Files ({D.dossier_protege()})")
appels = []
D.demarrer_lhm(Path(tempfile.mkdtemp()) / "absent", None, appels.append) if not D.tache_existe() else None
ok(appels == [], "LibreHardwareMonitor absent et pas de tâche : rien n'est lancé, aucune fenêtre")

# --- scripts administrateur : générés et analysés, jamais exécutés -------------------------------------------------
act = D._script_activer(Path(r"C:\Users\NOM\AppData\Local\Programs\NEXUS\LibreHardwareMonitor"),
                        Path(r"C:\x\LibreHardwareMonitor.config"), r"PC\Test")
des = D._script_desactiver()
ok("-RunLevel Highest" in act and "-LogonType Interactive" in act and "-UserId 'PC\\Test'" in act,
   "activer : tâche pour TON compte, autorisations maximales, seulement session ouverte")
ok("TaskPath '\\NEXUS\\'" in act and str(D.dossier_protege()) in act and "New-ScheduledTaskTrigger" not in act,
   "activer : tâche \\NEXUS\\, exe dans la copie protégée, aucun déclencheur (seul NEXUS la lance)")
ok("Unregister-ScheduledTask" in des and "Remove-Item" in des, "désactiver : tâche et copie supprimées")
ok("O''Brien" in D._ps("O'Brien"), "chemins et noms protégés (apostrophes doublées pour PowerShell)")
if os.name == "nt":
    for nom, script in (("activer", act), ("désactiver", des)):
        f = Path(tempfile.mkdtemp()) / "s.ps1"
        f.write_text(script, encoding="utf-8-sig")
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            f"$e=$null;$null=[System.Management.Automation.Language.Parser]::ParseFile('{f}',[ref]$null,[ref]$e);"
                            "if($e){$e|%{$_.Message};exit 1}"], capture_output=True, text=True)
        ok(r.returncode == 0, f"script « {nom} » : syntaxe PowerShell valide {r.stdout.strip()[:200]}")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
