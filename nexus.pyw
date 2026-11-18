"""NEXUS sans fenêtre noire : icône près de l'horloge (raccourci du Bureau : runtime\\pythonw.exe nexus.pyw).
Tout le travail est dans superviseur.py ; pour dépanner avec la fenêtre noire d'avant : lancer.bat console."""
import os
import sys
import time
import traceback

os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.getcwd())

try:
    import superviseur
    code = superviseur.main()
except Exception:
    # pythonw n'a pas de fenêtre : sans ceci, une erreur passerait inaperçue
    detail = traceback.format_exc()
    try:
        os.makedirs("logs", exist_ok=True)
        with open(os.path.join("logs", "nexus.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [Icône] ERREUR :\n{detail}\n")
    except OSError:
        pass
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(None, "NEXUS n'a pas pu démarrer :\n\n" + detail.strip().splitlines()[-1]
                                         + "\n\nDétails : logs\\nexus.log. Pour dépanner : lancer.bat console.",
                                         "NEXUS", 0x10)
    except Exception:
        pass
    code = 1
sys.exit(code)
