"use strict";
/* Philibert en haut de la page : il se promène dans un petit couloir sous la barre du haut (il ne recouvre jamais
   un bouton), s'arrête, regarde autour de lui, cligne des yeux, hoche la tête, agite son fanon, se dore au soleil,
   dort la nuit, et montre son humeur dans une bulle (cœur, « ! » s'il a besoin de toi, Zzz, nuage s'il est malade).
   Un clic (ou Entrée) sur lui ouvre son île (js/philibert-ile.js).
   Léger : un seul SVG déplacé par une transition CSS de transform ; pattes en CSS pendant la marche seulement ;
   une petite minuterie de comportement toutes les quelques secondes ; rien quand l'onglet est caché ou en mode
   jeu ; immobile avec « réduire les animations ». Seul son corps dessiné est cliquable (philibert.css). */
(() => {
  const header = document.querySelector("body > header");
  // Philibert vit sur le PC seulement : depuis le téléphone (accès réseau), ni iguane, ni île (le serveur refuse aussi)
  const surPC = ["localhost", "127.0.0.1", "::1", "[::1]"].includes(location.hostname);
  if (!header || !window.PhilibertDessin || !surPC) return;
  const D = window.PhilibertDessin;
  const reduit = matchMedia("(prefers-reduced-motion: reduce)");
  const lane = document.createElement("div");
  lane.className = "phb-lane";
  lane.hidden = true;
  // « phb-anim » : active ses animations CSS (pattes, demi-tour selon le sens de marche, clignements, hochements)
  lane.innerHTML = `<button type="button" class="phb-mini phb-anim" aria-label="Philibert, ton iguane : ouvrir son île">
      <span class="phb-flip"></span><span class="phb-bulle" aria-hidden="true" hidden></span>
      <span class="phb-panneau" aria-hidden="true" hidden></span></button>`;
  header.appendChild(lane);
  const mini = lane.querySelector(".phb-mini"), flip = mini.querySelector(".phb-flip"),
    bulle = mini.querySelector(".phb-bulle"), panneau = mini.querySelector(".phb-panneau");
  // petit panneau de bois planté dans le sable (absent : chez le vétérinaire ou en pension)
  const PANCARTE = `<svg class="phb-svg" viewBox="0 0 128 64" role="img" aria-label=""><path d="M40 60 C52 55 74 55 88 60 Z" fill="#e6c98b"/>
    <rect x="61" y="24" width="5" height="34" fill="#9b6a3c"/><rect x="40" y="12" width="48" height="20" rx="3" fill="#c98f52" stroke="#7d5229" stroke-width="1.4"/>
    <path d="M46 19 h36 M46 25 h28" stroke="#7d5229" stroke-width="2" stroke-linecap="round"/></svg>`;
  const LARG = () => mini.offsetWidth || 115;        // largeur réelle (plus petite sur téléphone)
  let e = null, x = -1, gauche = false, timer = 0, cligneT = 0, html = "", pose = "debout", bulleTemp = 0, poll = 0;

  const ICONES = {
    coeur: `<svg viewBox="0 0 20 18"><path d="M10 17 C3 11.6 0 8.6 0 5.2 C0 2.2 2.4 0 5.2 0 C7.2 0 8.8 1.2 10 3 C11.2 1.2 12.8 0 14.8 0 C17.6 0 20 2.2 20 5.2 C20 8.6 17 11.6 10 17Z" fill="#ff5d7e"/></svg>`,
    nuage: `<svg viewBox="0 0 24 16"><path d="M6 15 C2.6 15 0 12.8 0 10 C0 7.4 2 5.4 4.6 5.2 C5.4 2.2 8 0 11.2 0 C14.6 0 17.4 2.4 17.8 5.6 C21.2 5.8 24 7.8 24 10.6 C24 13.2 21.8 15 19 15 Z" fill="#9aa7b4"/><path d="M8 9.6 h1.6 M14.4 9.6 h1.6" stroke="#4d5966" stroke-width="1.4" stroke-linecap="round"/></svg>`,
    flocon: `<svg viewBox="0 0 20 20"><g stroke="#5fb4ff" stroke-width="2" stroke-linecap="round"><path d="M10 1v18M2.2 5.5l15.6 9M2.2 14.5l15.6-9"/></g></svg>`,
    soleil: `<svg viewBox="0 0 20 20"><circle cx="10" cy="10" r="4.6" fill="#ffc83d"/><g stroke="#ffb020" stroke-width="1.8" stroke-linecap="round"><path d="M10 1v2.4M10 16.6V19M1 10h2.4M16.6 10H19M3.6 3.6l1.7 1.7M14.7 14.7l1.7 1.7M3.6 16.4l1.7-1.7M14.7 5.3l1.7-1.7"/></g></svg>`,
  };

  // « il réclame de l'attention » (caprice) : seulement quand son bonheur est à 30 ou moins (même règle que le serveur)
  const appelVrai = () => !!(e && e.appel && (e.appel.type !== "caprice" || e.jauges.bonheur <= 30));
  const besoinsVrais = () => (e && e.besoins || []).filter(b => b.id !== "ventre");
  const visible = () => !!(e && e.reglages && e.reglages.visible);
  const gm = () => document.body.classList.contains("gamemode");
  const largeur = () => Math.max(LARG(), lane.clientWidth - LARG());
  const nuitHeure = () => { const h = e && e.ciel ? e.ciel.heure : 12; return h >= 21 || h < 7; };

  function libelle() {
    if (!e) return "Philibert";
    if (e.niveau === "veto") return "Philibert se repose chez la tortue vétérinaire : voir son île";
    if (e.niveau === "pension") return "Philibert est en pension chez la voisine : voir son île";
    if (e.niveau === "oeuf") return "L'œuf de Philibert : voir son île";
    const b = besoinsVrais();
    return `${e.titre}${e.dort ? " dort" : ""}${b.length ? " : " + b[0].texte : ""} — ouvrir son île`;
  }

  function dessiner() {
    if (!e || ["veto", "pension"].includes(e.niveau)) return;
    const h = { appel: "calme", froid: "froid" }[e.humeur] || e.humeur;
    const out = D.svg({ stade: e.stade, variante: e.variante, mutation: e.mutation, marques: e.marques, humeur: e.dort ? "dort" : h, portes: e.portes, mue: e.mue,
      ventre: e.ventre_rond, malade: !!e.malade, froid: e.jauges && e.jauges.chaleur < 35, pose, label: "", fendu: false, uid: "w", leger: true });
    if (out !== html) { flip.innerHTML = out; html = out; }
  }

  function montrerBulle(icone, duree) {
    clearTimeout(bulleTemp);
    if (!icone) { bulle.hidden = true; return; }
    bulle.innerHTML = ICONES[icone] || `<b>${esc(icone)}</b>`;
    bulle.className = "phb-bulle phb-b-" + (ICONES[icone] ? icone : icone === "!" ? "appel" : "zzz");
    bulle.hidden = false;
    if (duree) bulleTemp = setTimeout(bulleFixe, duree);
  }
  // bulle qui reste tant que l'état dure (besoin, sommeil, maladie) ; sinon rien
  function bulleFixe() {
    if (!e || ["veto", "pension"].includes(e.niveau)) return montrerBulle(null);
    if (e.stade === "oeuf") return montrerBulle(null);
    if (e.dort) return montrerBulle("Zzz");
    if (e.malade) return montrerBulle("nuage");
    if (appelVrai() || besoinsVrais().some(b => b.id !== "lumiere")) return montrerBulle("!");
    if (e.jauges.chaleur < 35) return montrerBulle("flocon");
    montrerBulle(null);
  }

  function placer(nx, duree) {
    x = Math.max(0, Math.min(largeur(), nx));
    mini.style.transitionDuration = (duree || 0) + "s";
    mini.style.transform = `translateX(${x.toFixed(1)}px)`;
  }
  const classe = (c, on) => mini.classList.toggle(c, on);
  // Position réellement affichée (au milieu d'une marche, la transition n'est pas finie : x vaut déjà la cible)
  function posActuelle() {
    try { return new DOMMatrixReadOnly(getComputedStyle(mini).transform).m41; } catch (err) { return x; }
  }

  function cligner() {
    clearTimeout(cligneT);
    if (document.hidden || gm() || reduit.matches || !e || e.dort) return;
    classe("cligne", true);
    setTimeout(() => classe("cligne", false), 170);
    cligneT = setTimeout(cligner, 3500 + Math.random() * 4500);
  }

  // ---- comportements ----
  function suite(ms) { clearTimeout(timer); timer = setTimeout(agir, ms); }
  function arreter() { clearTimeout(timer); clearTimeout(cligneT); classe("marche", false); }
  function agir() {
    if (!e || lane.hidden) return;
    if (document.hidden) return;                                     // repris au retour sur l'onglet
    if (window.nxRepos && window.nxRepos.enCours()) return;          // mode repos : repris au retour (nexus:repos)
    if (gm()) { classe("marche", false); return suite(15000); }      // mode jeu : il ne bouge plus
    classe("marche", false); classe("hoche", false); classe("fanon", false); classe("regarde", false);
    if (e.stade === "oeuf" || ["veto", "pension"].includes(e.niveau) || reduit.matches) return;
    if (e.dort) { setPose("dort"); return suite(60000); }
    const malade = !!e.malade, froid = e.jauges.chaleur < 35;
    const soleil = ["soleil", "arc"].includes(e.ciel.meteo) && e.ciel.phase === "jour";
    const r = Math.random();
    const lent = malade || froid || e.jauges.energie < 25;
    if (soleil && !malade && e.jauges.chaleur < 85 && r < .14) {       // il se dore, à plat ventre
      setPose("plat");
      montrerBulle("soleil", 6000);
      return suite(9000 + Math.random() * 8000);
    }
    setPose("debout");
    if (r < (lent ? .3 : .55)) {                                       // il marche vers un autre endroit
      const W = largeur();
      // petits trajets (96 à 336 px), vers le côté où il y a de la place
      const pas = 96 + Math.random() * 240, versGauche = x - pas < 0 ? false : x + pas > W ? true : Math.random() < .5;
      const cible = Math.max(0, Math.min(W, x + (versGauche ? -pas : pas)));
      // vitesse accordée au rythme des pattes (sinon il « glisse ») : un pas de patte ≈ 8,5 px par cycle de 0,72 s
      const vitesse = lent ? 12 : 20 + Math.random() * 5;            // px/s
      const d = Math.abs(cible - x) / vitesse;
      // il regarde toujours là où il va : s'il change de sens, il fait d'abord demi-tour (0,3 s), puis il part
      const tourne = (cible < x) !== gauche;
      gauche = cible < x;
      classe("gauche", gauche);
      const partir = () => { classe("marche", true); placer(cible, d); suite(d * 1000 + 300); };
      if (tourne) { clearTimeout(timer); timer = setTimeout(partir, 340); return; }
      return partir();
    }
    if (r < .7) { classe("regarde", true); return suite(1400 + Math.random() * 1200); }       // il regarde autour
    if (r < .82) { classe("hoche", true); return suite(1600); }                               // hochements de tête
    if (r < .9) { classe("fanon", true); return suite(1500); }                                // fanon
    if (e.humeur === "joyeux" && r < .97) montrerBulle("coeur", 3500);
    suite(2500 + Math.random() * 4000);
  }
  function setPose(p) {
    if (p === pose) return;
    pose = p;
    classe("plat", p === "plat");
    dessiner();
  }

  // ---- état (lu sur le serveur) ----
  function appliquer(nv) {
    const avant = e;
    e = nv;
    dispatchEvent(new CustomEvent("philibert:maj", { detail: e }));     // (lu par la tuile du sommaire, même s'il est masqué en haut)
    const montre = visible();
    lane.hidden = !montre;
    document.body.classList.toggle("phb-on", montre);
    if (!montre) { arreter(); return; }
    mini.setAttribute("aria-label", libelle());
    mini.title = libelle().replace(" — ouvrir son île", "");
    const absent = ["veto", "pension"].includes(e.niveau);
    panneau.hidden = !absent;
    mini.classList.toggle("phb-absent", absent);
    if (absent) {
      const v = e.veto;
      if (html !== PANCARTE) { flip.innerHTML = PANCARTE; html = PANCARTE; }
      const t = v ? `Chez la tortue vétérinaire · retour vers ${new Date(v.retour * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}`
        : "En pension chez la voisine";
      panneau.textContent = t;
    } else {
      if (!e.dort && pose === "dort") pose = "debout";
      if (e.dort) pose = "dort";
      dessiner();
    }
    if (x < 0) placer(reduit.matches ? largeur() * .62 : Math.random() * largeur() * .8, 0);
    bulleFixe();
    notifier(avant);
    if (!avant || avant.niveau !== e.niveau || avant.dort !== e.dort) suite(800);
    if (!cligneT) cligner();
  }

  // Notification Windows (via le navigateur) : quand il tombe malade ou part chez le vétérinaire, une fois
  function notifier() {
    if (window.NEXUS_NATIVE || !e.reglages.notif_windows || gm() || !("Notification" in window) || Notification.permission !== "granted") return;
    const cle = e.veto ? "v" + e.veto.depart : e.malade ? "m" + e.malade.depuis : null;
    if (!cle) return;
    let vu = null;
    try { vu = localStorage.getItem("nexus-philibert-notif"); } catch (x) {}
    if (vu === cle) return;
    try { localStorage.setItem("nexus-philibert-notif", cle); } catch (x) {}
    try {
      new Notification(e.veto ? "🐢 Philibert se repose chez le vétérinaire" : "🦎 Philibert est malade",
        { body: e.veto ? "Il va bien : la tortue s'occupe de lui. Retour dans quelques heures." : `Il a ${e.malade.texte}. Un remède et un peu de chaleur l'aideront.`, tag: "philibert" });
    } catch (x) {}
  }

  async function charger() {
    clearTimeout(poll);
    if (!document.hidden) {
      try { appliquer(await api("/api/philibert")); } catch (x) { /* serveur indisponible : on réessaie plus tard */ }
    }
    poll = setTimeout(charger, 60000);
  }

  mini.addEventListener("click", () => {
    classe("saut", false); void mini.offsetWidth; classe("saut", true);        // petit saut de joie, puis son île s'ouvre
    setTimeout(() => classe("saut", false), 600);
    if (window.PhilibertIle) setTimeout(() => window.PhilibertIle.ouvrir(), reduit.matches ? 0 : 220);
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { arreter(); return; }
    charger();
    suite(500);
    cligner();
  });
  // Mode repos (NEXUS pas au premier plan) : il s'arrête là où il est, et repart au retour
  addEventListener("nexus:repos", ev => {
    if (ev.detail) { arreter(); placer(posActuelle(), 0); }
    else if (!document.hidden) { suite(500); cligner(); }
  });
  addEventListener("resize", () => { if (x > largeur()) placer(largeur(), 0); });
  addEventListener("philibert:etat", ev => { if (ev.detail) appliquer(ev.detail); });
  reduit.addEventListener && reduit.addEventListener("change", () => { arreter(); suite(300); });

  window.nxPhilibert = {
    etat: () => e, charger, visible,
    ouvrir: () => window.PhilibertIle && window.PhilibertIle.ouvrir(),
    async afficher(on) {
      try { appliquer((await api("/api/philibert/action", { action: "reglages", visible: !!on })).etat); } catch (x) { toast("Philibert : " + x.message, true); }
    },
  };
  charger();
})();
