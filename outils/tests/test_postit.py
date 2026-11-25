"""Test des post-it du mur des Souvenirs : lecture (texte + ✎) / édition (barre d'options), enregistrement, réouverture.
Prérequis : serveur de TEST sur le port 8001 (jamais le NEXUS en service) et Edge sans fenêtre avec
--remote-debugging-port=9333 (voir cdp.py). Usage : python outils/tests/test_postit.py"""

import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import tempfile

from cdp import Page

S = Path(tempfile.gettempdir())
pg = Page()
pg.call("Emulation.setDeviceMetricsOverride", {"width": 1720, "height": 1000, "deviceScaleFactor": 1, "mobile": False})
ok = ko = 0


def check(c, m):
    global ok, ko
    print(("OK   " if c else "ÉCHEC ") + m, flush=True)
    ok += bool(c)
    ko += not c


ETAT = r"""(() => { const n = document.querySelector('#tab-souvenirs .sv-note'); if (!n) return null;
  const bar = n.querySelector('.sv-nbar'), t = n.querySelector('.sv-ntext'), pen = n.querySelector('.sv-nedit');
  return { edition: n.classList.contains('sv-editing'), barre: getComputedStyle(bar).display !== 'none', lecture_seule: t.readOnly,
           crayon: getComputedStyle(pen).display !== 'none', focus: document.activeElement === t, texte: t.value,
           couleur: [...n.classList].find(c => c.startsWith('c-')) }; })()"""


def etat():
    return pg.ev(ETAT)


def clic(sel):
    pg.ev(f"document.querySelector({json.dumps(sel)}).click()")
    time.sleep(0.8)


for prof in ("", "sakura"):
    pg.go("http://127.0.0.1:8001/?prep", 1)
    pg.ev(f"localStorage['nexus-theme']='terminal';localStorage['nexus-profil-terminal']={json.dumps(prof)}")
    pg.go("http://127.0.0.1:8001/?p#souvenirs", 3)
    pg.ev("document.getElementById('splash').style.display='none'")
    pg.ev("location.hash='#souvenirs'")
    time.sleep(1.5)
    if prof == "":
        clic("#sv-note-add")
        time.sleep(0.8)
        e = etat()
        check(
            e and e["edition"] and e["barre"] and not e["lecture_seule"] and e["focus"] and not e["crayon"],
            f"nouvelle note : ouverte en édition, barre visible, curseur dedans ({e})",
        )
        pg.call("Input.insertText", {"text": "Acheter des dés"})
        time.sleep(0.3)
        pg.call("Input.dispatchMouseEvent", {"type": "mousePressed", "x": 900, "y": 960, "button": "left", "clickCount": 1})
        pg.call("Input.dispatchMouseEvent", {"type": "mouseReleased", "x": 900, "y": 960, "button": "left", "clickCount": 1})
        time.sleep(1.2)
        e = etat()
        check(not e["edition"] and not e["barre"] and e["lecture_seule"] and e["crayon"], f"clic ailleurs : lecture seule, barre cachée, crayon visible ({e})")
        pg.go("http://127.0.0.1:8001/?p2#souvenirs", 3)
        pg.ev("document.getElementById('splash').style.display='none'")
        pg.ev("location.hash='#souvenirs'")
        time.sleep(1.5)
        e = etat()
        check(e["texte"] == "Acheter des dés" and not e["edition"] and e["crayon"], f"après rechargement : texte enregistré, en lecture ({e['texte']!r})")
    clic("#tab-souvenirs .sv-nedit")
    e = etat()
    check(e["edition"] and e["barre"] and not e["lecture_seule"] and e["focus"], f"{prof or 'défaut'} : ✎ rouvre l'édition et les options ({e})")
    pg.shot(str(S / f"postit-edition-{prof or 'def'}.png"), {"x": 0, "y": 250, "width": 900, "height": 450})
    clic("#tab-souvenirs .sv-note .sv-dot.c-rose")
    e = etat()
    check(e["edition"] and e["couleur"] == "c-rose", f"couleur changée, toujours en édition ({e['couleur']}, édition {e['edition']})")
    pg.ev("document.querySelector('#tab-souvenirs .sv-ntext').dispatchEvent(new KeyboardEvent('keydown', {key:'Escape', bubbles:true}))")
    time.sleep(0.5)
    e = etat()
    check(not e["edition"] and e["crayon"] and not e["barre"], f"Échap : retour en lecture ({e})")
    pg.ev("location.hash")
    pg.shot(str(S / f"postit-lecture-{prof or 'def'}.png"), {"x": 0, "y": 250, "width": 900, "height": 450})
    pg.ev("document.querySelector('#tab-souvenirs .sv-ntext').dispatchEvent(new MouseEvent('dblclick', {bubbles:true}))")
    time.sleep(0.5)
    e = etat()
    check(e["edition"], "double-clic sur le texte : édition")
    clic("#tab-souvenirs .sv-ndone")
    e = etat()
    check(not e["edition"] and e["crayon"], "✓ : retour en lecture")
    loc = pg.ev("location.hash")
    check(loc == "#souvenirs", f"Échap dans la note n'a pas quitté l'onglet ({loc})")
print(f"\n{ok} réussis, {ko} échec(s)")
