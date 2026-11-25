"""Deck : mot de passe changé pendant que NEXUS tourne (configurer.bat, « Configurer NEXUS », config.json
modifié à la main). config.json est relu dès qu'il change, l'ancien mot de passe est refusé et les sessions
ouvertes avec l'ancien sont révoquées. Ancien format du fichier de sessions toujours lu."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

BASE = Path(sys.argv[1])
os.chdir(BASE)
sys.path.insert(0, str(BASE))
os.environ.update(NEXUS_NO_BOT="1", NEXUS_DECK_DRYRUN="1")
tmp = Path(tempfile.mkdtemp(prefix="nexus-deck-")).resolve()  # nom long (TEMP en 8.3 sur la CI)
os.environ["NEXUS_DATA_DIR"] = str(tmp)

import config
import deck as deck_mod

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
    else:
        failed += 1
        print("  [ECHEC]", m)


assert config.CONFIG_FILE.parent == tmp, config.CONFIG_FILE


def ecrire(hash_):
    config.CONFIG_FILE.write_text(json.dumps({"deck": {"password_hash": hash_}}), encoding="utf-8")
    t = time.time() + 2  # (horloge du système de fichiers : date bien différente)
    os.utime(config.CONFIG_FILE, (t, t))


ecrire(deck_mod.hash_password("ancien-mdp-1"))
d = deck_mod.Deck()
cfg = config.get("deck")
jeton = d.login(cfg, "ancien-mdp-1")
ok(jeton and d.check_session(jeton), "connexion avec le mot de passe en vigueur")

# --- changement de mot de passe par un autre processus (config.json réécrit)
ecrire(deck_mod.hash_password("nouveau-mdp-2"))
cfg2 = config.get("deck")
ok(cfg2["password_hash"] != cfg["password_hash"], "config.json relu sans redémarrer (nouveau mot de passe vu)")
ok(d.login(cfg2, "ancien-mdp-1") is None, "l'ancien mot de passe est refusé")
ok(not d.check_session(jeton), "la session ouverte avec l'ancien mot de passe est révoquée")
j2 = d.login(cfg2, "nouveau-mdp-2")
ok(j2 and d.check_session(j2), "connexion avec le nouveau mot de passe")

# --- persistance : un redémarrage garde la session et l'empreinte
d2 = deck_mod.Deck()
d2.suivre_mot_de_passe(config.get("deck"))
ok(d2.check_session(j2), "session gardée après redémarrage (même mot de passe)")
ecrire(deck_mod.hash_password("troisieme-3"))
d2.suivre_mot_de_passe(config.get("deck"))
ok(not d2.check_session(j2), "mot de passe changé NEXUS éteint : session révoquée au démarrage suivant")

# --- ancien format du fichier (sessions seules) : toujours lu
fut = time.time() + 3600
deck_mod.SESSIONS_FILE.write_text(json.dumps({"abc": fut, "vieux": time.time() - 10}), encoding="utf-8")
d3 = deck_mod.Deck()
ok(d3._sessions == {"abc": fut}, f"ancien format lu, sessions expirées écartées : {d3._sessions}")

print(f"{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
