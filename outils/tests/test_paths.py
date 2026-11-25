"""Chemins et runtime : NEXUS_DATA_DIR, arborescence, fichier port/jeton.

Le test tourne dans un sous-processus (run_all.py) avec un dossier de données temporaire ;
il ne touche ni au projet ni au vrai %LOCALAPPDATA%.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

BASE = Path(sys.argv[1])
root = Path(tempfile.mkdtemp(prefix="nexus-paths-"))
os.environ["NEXUS_DATA_DIR"] = str(root)
os.environ["NEXUS_APP_DIR"] = str(BASE)
sys.path.insert(0, str(BASE))

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


try:
    import paths

    ok(root.resolve() == paths.USER_ROOT, f"USER_ROOT : {paths.USER_ROOT}")
    ok(root.resolve() / "data" == paths.DATA_DIR, f"DATA_DIR : {paths.DATA_DIR}")
    ok(root.resolve() / "config.json" == paths.CONFIG_FILE, "config.json dans le dossier de données")
    ok(root.resolve() / "logs" / "nexus.log" == paths.LOG_FILE, "journal dans logs/")
    ok(root.resolve() / "actions" == paths.ACTIONS_DIR, "actions/ dans le dossier de données")
    paths.prepare()
    ok(paths.DATA_DIR.is_dir() and paths.LOG_DIR.is_dir() and paths.ACTIONS_DIR.is_dir(), "arborescence créée")
    ok(paths.DECK_FILE.is_file() and paths.JEUX_FILE.is_file(), "fichiers d'exemple copiés")
    ok(paths.PROFILES_DIR.is_dir() and any(paths.PROFILES_DIR.iterdir()), "profils officiels copiés")
    paths.write_runtime(4321, "jeton-test")
    runtime = paths.read_runtime()
    ok(runtime.get("port") == 4321 and runtime.get("token") == "jeton-test", "runtime.json écrit et relu")
    paths.clear_runtime()
    ok(not paths.RUNTIME_FILE.exists(), "runtime.json effacé")
finally:
    shutil.rmtree(root, ignore_errors=True)

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
