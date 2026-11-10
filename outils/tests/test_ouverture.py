"""Test : passage au sommaire choisi et retenu PAR PROFIL (Réglages), puis animation réellement jouée.
Prérequis : serveur de TEST sur le port 8001 (jamais le NEXUS en service) et Edge sans fenêtre avec
--remote-debugging-port=9333 (voir cdp.py). Usage : python outils/tests/test_ouverture.py"""
import json, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from cdp import Page
pg = Page()
B = "http://127.0.0.1:8001"
ok = ko = 0
def check(c, m):
    global ok, ko
    print(("OK  " if c else "ÉCHEC ") + m, flush=True); ok += c; ko += not c

def charge(profil, intro=False):
    pg.ev(f"localStorage['nexus-theme']='terminal';localStorage['nexus-profil-terminal']={json.dumps(profil)}")
    pg.go(B + ("/?intro" if intro else "/") + f"?t={time.time()}#accueil", 3)

def menu():                    # ouvre ⚙ Réglages et lit le sélecteur
    return pg.ev("""(() => { const m = document.getElementById('rg-menu'); if (m.hidden) document.getElementById('btn-reglages').click();
      const s = m.querySelector('[data-act=ouverture]');
      return s ? { profil: s.dataset.profil, val: s.value, label: m.querySelector('.rg-sel span').textContent.trim(), opts: [...s.options].map(o => o.textContent) } : { note: m.querySelector('.rg-note').textContent.trim().slice(0, 60) }; })()""")

def choisit(v):
    pg.ev(f"(() => {{ const s = document.querySelector('#rg-menu [data-act=ouverture]'); s.value = {json.dumps(v)}; s.dispatchEvent(new Event('change', {{ bubbles: true }})); }})()")

def joue(profil):              # page de garde -> clic -> quel passage ?
    charge(profil, intro=True)
    return pg.ev("""(async () => { const w = ms => new Promise(r => setTimeout(r, ms));
      const S = document.getElementById('splash'); let n = 0;
      while (S.dataset.state !== 'ready' && n++ < 60) { S.click(); await w(250); }
      await w(800); S.querySelector('.sp-enter').click();
      for (let i = 0; i < 120; i++) { await w(40);
        if (document.querySelector('.sp-tele')) return 'tele'; if (S.classList.contains('sp-iris')) return 'cercle'; if (S.classList.contains('sp-fondu')) return 'fondu'; }
      return 'aucun'; })()""")

pg.go(B + "/?prep", 1)
pg.ev("localStorage.removeItem('nexus-ouverture-profils'); localStorage.removeItem('nexus-ouverture')")
charge("")
m = menu(); check("note" in m, f"profil Défaut : pas de sélecteur, une note ({m})")
charge("sakura"); m = menu()
check(m.get("profil") == "sakura" and m.get("val") == "", f"Sakura : sélecteur du profil, valeur « du profil » ({m.get('label')} · {m.get('opts', [''])[0]})")
check(joue("sakura") == "cercle", "Sakura sans choix : son passage prévu (cercle)")
charge("sakura"); menu(); choisit("tele")
charge("pluie-d-etoiles"); m = menu()
check(m.get("profil") == "pluie-d-etoiles" and m.get("val") == "", f"Pluie : non touché par le choix de Sakura ({m.get('val')!r})")
choisit("fondu")
charge("sakura"); m = menu(); check(m.get("val") == "tele", f"retour sur Sakura : « tele » retenu ({m.get('val')!r})")
charge("pluie-d-etoiles"); m = menu(); check(m.get("val") == "fondu", f"Pluie : « fondu » retenu ({m.get('val')!r})")
check(joue("sakura") == "tele", "Sakura joue la vieille télé")
check(joue("pluie-d-etoiles") == "fondu", "Pluie joue le fondu")
check(joue("des-du-destin") == "cercle", "Dés du destin (jamais réglé) : son passage prévu (cercle)")
charge("sakura"); menu(); choisit("")
check(joue("sakura") == "cercle", "Sakura remis sur « celui du profil » : cercle")
# ancien réglage commun (avant cette version) : sert de repli aux profils jamais réglés
pg.ev("localStorage.setItem('nexus-ouverture', 'tele')")
check(joue("des-du-destin") == "tele", "ancien réglage commun repris pour un profil jamais réglé")
check(joue("pluie-d-etoiles") == "fondu", "… mais le choix propre à un profil reste prioritaire")
check(joue("sakura") == "cercle", "… et « celui du profil » choisi explicitement aussi")
pg.ev("localStorage.removeItem('nexus-ouverture')")
print(f"\n{ok} réussis, {ko} échec(s)")
