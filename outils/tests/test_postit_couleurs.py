"""Post-it : fond, écriture, police (enregistrés), et lisibilité des boutons (contraste) sur chaque profil et mode.
Prérequis : serveur de TEST sur le port 8001 avec une base VIDE (jamais le NEXUS en service) et Edge sans fenêtre
avec --remote-debugging-port=9333 (voir cdp.py). Usage : python outils/tests/test_postit_couleurs.py"""

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


def page(prof, mode="terminal"):
    pg.go("http://127.0.0.1:8001/?prep", 1)
    pg.ev(f"localStorage['nexus-theme']={json.dumps(mode)};localStorage['nexus-profil-{mode}']={json.dumps(prof)}")
    pg.go(f"http://127.0.0.1:8001/?t={time.time()}#souvenirs", 3)
    pg.ev("document.getElementById('splash').style.display='none'")
    pg.ev("location.hash='#souvenirs'")
    time.sleep(1.6)


CONTRASTE = r"""(() => {
  const lum = c => { const k = c.startsWith("color(") ? 1 : 255; const m = c.match(/[\d.]+/g).map(Number); const [r, g, b] = m.slice(0, 3).map(v => { v /= k; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); }); return .2126 * r + .7152 * g + .0722 * b; };
  const n = document.querySelector('#tab-souvenirs .sv-note');
  const bg = getComputedStyle(n).backgroundColor, out = [];
  for (const b of n.querySelectorAll('.sv-nbar .btn, .sv-nbar .sv-nfont')) {
    const cs = getComputedStyle(b), L1 = lum(cs.color), L2 = lum(bg);
    out.push(+((Math.max(L1, L2) + .05) / (Math.min(L1, L2) + .05)).toFixed(1));
  }
  return { min: Math.min(...out), fond: bg };
})()"""
# 1. création + réglages (profil Défaut)
page("")
pg.ev("document.querySelector('#sv-note-add').click()")
time.sleep(1.2)
pg.call("Input.insertText", {"text": "Partie de D&D samedi"})
time.sleep(0.8)
pg.ev("document.querySelector('#tab-souvenirs .sv-note [data-npal]').click()")
time.sleep(0.3)
vis = pg.ev("!document.querySelector('#tab-souvenirs .sv-npal').hidden")
check(vis, "🎨 ouvre la palette (fond + écriture)")
n = pg.ev(
    "[document.querySelectorAll('#tab-souvenirs .sv-npal [data-ncolor]').length, document.querySelectorAll('#tab-souvenirs .sv-npal [data-nink]').length, document.querySelectorAll('#tab-souvenirs .sv-nfont option').length]"
)
check(n == [16, 9, 9], f"16 fonds, 9 couleurs d'écriture, 9 polices ({n})")
pg.ev("document.querySelector('#tab-souvenirs [data-ncolor=nuit]').click()")
time.sleep(1)
pg.ev("document.querySelector('#tab-souvenirs [data-nink=or]').click()")
time.sleep(1)
pg.ev(
    "(() => { const s = document.querySelector('#tab-souvenirs .sv-nfont'); s.value = 'manuscrite'; s.dispatchEvent(new Event('change', { bubbles: true })); })()"
)
time.sleep(1.2)
st = pg.ev(
    "(() => { const n = document.querySelector('#tab-souvenirs .sv-note'), t = n.querySelector('.sv-ntext'); return { cls: n.className, fond: getComputedStyle(n).backgroundColor, encre: getComputedStyle(t).color, police: getComputedStyle(t).fontFamily, edition: n.classList.contains('sv-editing'), palette: !n.querySelector('.sv-npal').hidden }; })()"
)
check(
    "c-nuit" in st["cls"] and "e-or" in st["cls"] and "f-manuscrite" in st["cls"],
    f"fond Nuit, écriture Or, police Manuscrite appliqués ({st['fond']}, {st['encre']}, {st['police'][:30]})",
)
check(st["edition"] and st["palette"], "la note reste en édition et la palette ouverte après chaque choix")
pg.shot(
    str(S / "pi-edition.png"),
    pg.ev(
        "(() => { const b = document.querySelector('#tab-souvenirs .sv-note').getBoundingClientRect(); return {x:b.left-10, y:b.top-10+scrollY, width:b.width+20, height:b.height+20}; })()"
    ),
)
pg.ev("document.querySelector('#tab-souvenirs .sv-ndone').click()")
time.sleep(0.5)
pg.shot(
    str(S / "pi-lecture.png"),
    pg.ev(
        "(() => { const b = document.querySelector('#tab-souvenirs .sv-note').getBoundingClientRect(); return {x:b.left-10, y:b.top-10+scrollY, width:b.width+20, height:b.height+20}; })()"
    ),
)
page("")
st = pg.ev("document.querySelector('#tab-souvenirs .sv-note').className")
check("c-nuit" in st and "e-or" in st and "f-manuscrite" in st, f"après rechargement : réglages enregistrés ({st})")
pg.ev("document.querySelector('#tab-souvenirs .sv-nedit').click()")
time.sleep(0.4)
pg.ev("document.querySelector('#tab-souvenirs .sv-note [data-npal]').click()")
time.sleep(0.2)
pg.ev("document.querySelector('#tab-souvenirs [data-nink=auto]').click()")
time.sleep(1)
pg.ev("document.querySelector('#tab-souvenirs [data-ncolor=jaune]').click()")
time.sleep(1)
# 2. lisibilité des boutons sur chaque profil et mode, fond clair (jaune) et foncé (nuit)
for mode in ("terminal", "sentinelle"):
    for prof in ("", "sakura", "pluie-d-etoiles", "des-du-destin"):
        page(prof, mode)
        pg.ev("document.querySelector('#tab-souvenirs .sv-nedit').click()")
        time.sleep(0.4)
        for fond in ("jaune", "nuit"):
            pg.ev(
                "(() => { const p = document.querySelector('#tab-souvenirs .sv-npal'); if (p.hidden) document.querySelector('#tab-souvenirs [data-npal]').click(); })()"
            )
            time.sleep(0.2)
            pg.ev(f"document.querySelector('#tab-souvenirs [data-ncolor={fond}]').click()")
            time.sleep(1.1)
            r = pg.ev(CONTRASTE)
            check(r["min"] >= 4.5, f"{mode}/{prof or 'défaut'} fond {fond} : contraste des boutons ≥ 4,5 ({r['min']})")
            if prof == "des-du-destin" and fond == "jaune" and mode == "terminal":
                pg.ev("document.querySelector('#tab-souvenirs [data-npal]').click()")
                time.sleep(0.3)
                pg.shot(
                    str(S / "pi-des.png"),
                    pg.ev(
                        "(() => { const b = document.querySelector('#tab-souvenirs .sv-note').getBoundingClientRect(); return {x:b.left-10, y:b.top-10+scrollY, width:b.width+20, height:b.height+20}; })()"
                    ),
                )
print(f"\n{ok} réussis, {ko} échec(s)")
