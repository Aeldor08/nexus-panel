"use strict";
/* L'île de Philibert (fenêtre ouverte par un clic sur l'iguane du haut, la tuile du sommaire ou ⚙ Réglages).
   Une île au milieu de la mer, en couches : ciel à l'heure réelle (aube, jour, coucher, nuit étoilée), soleil et
   ses rayons, lune, nuages, mouettes, mer et reflets, vagues, écume autour de l'île, palmier dont les palmes
   ondulent (il y dort), rocher chaud, flaque, lanterne, lampe chauffante, déco, crabes, papillons, lucioles,
   guirlande en décembre, pluie et arc-en-ciel ; et les SAISONS de l'île (printemps, été, saison des pluies,
   saison fraîche) qui changent les couleurs et le décor.
   En dessous : ses jauges, ce qu'il dit, ce qui ne va pas, et les soins. Panneaux : nourrir, bain, jouer,
   boutique, garde-robe, carnet (album compris), réglages ; carte postale de la tortue vétérinaire.
   Tout est calculé par le serveur (philibert.py) : la page n'envoie que des intentions.
   Seules les couches animées bougent, par transform/opacity (aucune boucle JavaScript) ; coupées en mode jeu,
   en pause onglet caché, et figées avec « réduire les animations ». */
(() => {
  const D = window.PhilibertDessin, I = window.PhilibertIcones, N = window.PhilibertNature;
  if (!D || !I || !N || !["localhost", "127.0.0.1", "::1", "[::1]"].includes(location.hostname)) return;      // (sur le PC seulement)
  const ico = I.ico;
  const dlg = document.createElement("dialog");
  dlg.className = "phb-dlg";
  dlg.setAttribute("aria-labelledby", "phb-titre");
  document.body.appendChild(dlg);
  let e = null, cat = null, cleScene = "", feuille = null, message = "", messageT = 0, reaction = "", reactionT = 0, pollT = 0, flanerT = 0, flaneX = 50;
  let carnetOnglet = "historique", boutiqueOnglet = "nourriture", carnetDonnees = null, dernierAliment = "";
  const reduit = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

  const JAUGES = [
    ["faim", "Faim", "nourrir", "#3a9e4a"], ["bonheur", "Bonheur", "coeur", "#e0507a"], ["energie", "Énergie", "eclair", "#d69a0b"],
    ["proprete", "Propreté", "bulles", "#2a86cc"], ["sante", "Santé", "soin", "#d4483b"], ["chaleur", "Chaleur", "thermo", "#e8731a"],
  ];
  const ICO_BESOIN = { malade: "soin", froid: "thermo", faim: "nourrir", fatigue: "lune", proprete: "bulles", ennui: "coeur", mue: "etoile",
    soleil: "soleil", ventre: "nourrir", lumiere: "ampoule" };
  const ICO_METEO = { soleil: "soleil", nuages: "nuage", pluie: "pluie", arc: "arc" };
  const ICO_SAISON = { printemps: "fleur", ete: "soleil", automne: "goutte", hiver: "vent" };
  const fmtH = s => { const h = Math.floor(s / 3600), m = Math.round(s % 3600 / 60); return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`; };
  const age = j => j < 1 ? `${Math.max(0, Math.round(j * 24))} h` : `${j.toFixed(j < 10 ? 1 : 0).replace(".", ",")} jour${j >= 2 ? "s" : ""}`;
  const poids = g => g >= 1000 ? `${(g / 1000).toFixed(2).replace(".", ",")} kg` : `${g} g`;
  const date = t => new Date(t * 1000).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "numeric" });
  const nuitHeure = () => e.ciel.heure >= 21 || e.ciel.heure < 7;
  const absent = () => ["veto", "pension"].includes(e.niveau);

  // ---- couleurs de l'interface : réglage « clair », « sombre » ou « automatique » ----
  // Automatique : sombre si le panel l'est (couleur de fond du profil choisi, mesurée) ou s'il fait nuit sur l'île.
  function panelSombre() {
    for (const el of [document.body, document.documentElement]) {
      const m = getComputedStyle(el).backgroundColor.match(/[\d.]+/g);
      if (!m || (m.length > 3 && +m[3] === 0)) continue;              // fond transparent : on regarde le parent
      const [r, g, b] = m.slice(0, 3).map(v => { v /= 255; return v <= .03928 ? v / 12.92 : Math.pow((v + .055) / 1.055, 2.4); });
      return .2126 * r + .7152 * g + .0722 * b < .25;
    }
    return matchMedia("(prefers-color-scheme: dark)").matches;
  }
  function interfaceSombre() {
    const t = (e && e.reglages && e.reglages.theme) || "auto";
    return t === "sombre" || (t !== "clair" && ((e && e.ciel.phase === "nuit") || panelSombre()));
  }

  // ---- sons (synthèse très courte, seulement après un geste, si les sons sont activés) ----
  let ctxAudio = null;
  function son(type) {
    if (!e || !e.reglages.sons) return;
    try {
      ctxAudio = ctxAudio || new (window.AudioContext || window.webkitAudioContext)();
      const t = ctxAudio.currentTime, o = ctxAudio.createOscillator(), g = ctxAudio.createGain();
      const n = { croc: [520, 380, "square", .05], plouf: [420, 140, "sine", .25], ding: [880, 1320, "sine", .18], pop: [600, 700, "triangle", .06],
        non: [300, 220, "sawtooth", .12], joie: [660, 990, "sine", .2], saut: [380, 620, "triangle", .1] }[type] || [600, 600, "sine", .05];
      o.type = n[2];
      o.frequency.setValueAtTime(n[0], t);
      o.frequency.exponentialRampToValueAtTime(n[1], t + n[3]);
      g.gain.setValueAtTime(.0001, t);
      g.gain.exponentialRampToValueAtTime(.08, t + .01);
      g.gain.exponentialRampToValueAtTime(.0001, t + n[3] + .05);
      o.connect(g).connect(ctxAudio.destination);
      o.start(t); o.stop(t + n[3] + .08);
    } catch (x) { /* pas de son : tant pis */ }
  }
  window.PhilibertSon = son;

  // ---- bruits de l'île selon la météo (tout est synthétisé : aucun fichier son) ----
  // Vagues toujours (houle lente), pluie (et tonnerre lointain en saison des pluies), vent (ciel couvert, saison fraîche),
  // goélands le jour au soleil, grillons et petites grenouilles (« co-kî ») la nuit. Très discret ; seulement fenêtre de
  // l'île ouverte, onglet visible, hors mode jeu, avec les petits sons ET les bruits de l'île activés.
  const Ambiance = (() => {
    let maitre = null, noeuds = [], minut = [], cle = "", bruitBuf = null;
    const C = () => (ctxAudio = ctxAudio || new (window.AudioContext || window.webkitAudioContext)());
    const voulu = () => !!(e && e.reglages.sons && e.reglages.ambiance !== false && dlg.open && !document.hidden
      && !document.body.classList.contains("gamemode") && !absent() && !reduit());
    function bruit() {
      if (bruitBuf) return bruitBuf;
      const c = C(), n = c.sampleRate * 2, b = c.createBuffer(1, n, c.sampleRate), d = b.getChannelData(0);
      let rose = 0;
      for (let i = 0; i < n; i++) { rose = rose * .97 + (Math.random() * 2 - 1) * .03; d[i] = (Math.random() * 2 - 1) * .5 + rose * 6; }
      return (bruitBuf = b);
    }
    function source() { const s = C().createBufferSource(); s.buffer = bruit(); s.loop = true; s.start(0, Math.random() * 2); noeuds.push(s); return s; }
    function filtre(type, f, q = .7) { const x = C().createBiquadFilter(); x.type = type; x.frequency.value = f; x.Q.value = q; noeuds.push(x); return x; }
    function gain(v) { const g = C().createGain(); g.gain.value = v; noeuds.push(g); return g; }
    function lfo(freq, ampl, cible) { const o = C().createOscillator(), g = gain(ampl); o.frequency.value = freq; o.connect(g).connect(cible); o.start(); noeuds.push(o); }
    function chaine(...n) { for (let i = 0; i < n.length - 1; i++) n[i].connect(n[i + 1]); return n[n.length - 1]; }
    function plus_tard(fn, min, max) { const t = setTimeout(() => { if (maitre) { fn(); plus_tard(fn, min, max); } }, (min + Math.random() * (max - min)) * 1000); minut.push(t); }
    // un son bref : une note qui glisse de f0 à f1 avec une enveloppe douce
    function note(type, f0, f1, duree, vol, depart = 0, vibrato = 0) {
      const c = C(), t = c.currentTime + depart, o = c.createOscillator(), g = c.createGain();
      o.type = type; o.frequency.setValueAtTime(f0, t); o.frequency.exponentialRampToValueAtTime(f1, t + duree);
      if (vibrato) { const v = c.createOscillator(), vg = c.createGain(); v.frequency.value = vibrato; vg.gain.value = f0 * .04; v.connect(vg).connect(o.frequency); v.start(t); v.stop(t + duree + .05); }
      g.gain.setValueAtTime(.0001, t); g.gain.exponentialRampToValueAtTime(vol, t + Math.min(.04, duree / 3)); g.gain.exponentialRampToValueAtTime(.0001, t + duree);
      o.connect(g).connect(maitre); o.start(t); o.stop(t + duree + .05);
    }
    function demarrer() {
      const c = C();
      if (c.state === "suspended") c.resume().catch(() => {});
      const ph = e.ciel.phase, met = e.ciel.meteo, sa = e.ciel.saison, nuit = ph === "nuit";
      maitre = c.createGain(); maitre.gain.value = .0001; maitre.connect(c.destination);
      maitre.gain.exponentialRampToValueAtTime(.9, c.currentTime + 2);
      // houle : bruit grave dont le volume monte et descend lentement (une vague toutes les ~10 s), et l'écume plus aiguë
      const houle = gain(.025); chaine(source(), filtre("lowpass", 420), houle, maitre); lfo(.1, .018, houle.gain);
      const ecume = gain(.008); chaine(source(), filtre("bandpass", 1500, .5), ecume, maitre); lfo(.1, .007, ecume.gain);
      if (met === "pluie") {
        const p = gain(nuit ? .03 : .036); chaine(source(), filtre("highpass", 1300), filtre("lowpass", 7500), p, maitre); lfo(2.6, .006, p.gain);
        if (sa === "automne") plus_tard(() => {                         // tonnerre lointain : grondement grave qui roule
          const t = c.currentTime, s = c.createBufferSource(), f = c.createBiquadFilter(), g = c.createGain();
          s.buffer = bruit(); f.type = "lowpass"; f.frequency.value = 150; g.gain.setValueAtTime(.0001, t);
          g.gain.exponentialRampToValueAtTime(.09, t + .5); g.gain.exponentialRampToValueAtTime(.0001, t + 4.5);
          s.connect(f).connect(g).connect(maitre); s.start(t); s.stop(t + 4.6);
        }, 22, 55);
      }
      if (met === "nuages" || met === "pluie" || sa === "hiver") {         // vent : souffle filtré qui va et vient
        const f = filtre("bandpass", 480, 1.1), g = gain(met === "pluie" ? .012 : .018);
        chaine(source(), f, g, maitre); lfo(.05, 260, f.frequency); lfo(.08, .008, g.gain);
      }
      if (!nuit && (met === "soleil" || met === "arc")) plus_tard(() => {  // goéland au loin : « kéé-ow » deux ou trois fois
        const n = 2 + Math.floor(Math.random() * 2);
        for (let i = 0; i < n; i++) note("triangle", 1500 + Math.random() * 200, 820, .32, .012, i * .42, 9);
      }, 7, 16);
      if (nuit && met !== "pluie" && sa !== "hiver") {
        plus_tard(() => { for (let i = 0; i < 3; i++) note("sine", 4300, 4250, .05, .0035, i * .09); }, .7, 1.4);   // grillons
        plus_tard(() => { note("sine", 1150, 1180, .09, .009); note("sine", 1750, 2050, .16, .009, .12); }, 3, 8);    // grenouille « co-kî »
      }
    }
    function arreter() {
      minut.forEach(clearTimeout); minut = [];
      if (!maitre) return;
      const m = maitre, n = noeuds, c = C();
      maitre = null; noeuds = [];
      try { m.gain.cancelScheduledValues(c.currentTime); m.gain.setValueAtTime(Math.max(.0001, m.gain.value), c.currentTime); m.gain.exponentialRampToValueAtTime(.0001, c.currentTime + .5); } catch (x) { /* déjà fermé */ }
      setTimeout(() => { n.forEach(x => { try { x.stop && x.stop(); } catch (y) { /* déjà arrêté */ } try { x.disconnect(); } catch (y) { /* rien */ } }); try { m.disconnect(); } catch (y) { /* rien */ } }, 700);
    }
    function maj() {
      let k = "";
      try { k = voulu() ? [e.ciel.phase, e.ciel.meteo, e.ciel.saison].join("|") : ""; } catch (x) { k = ""; }
      if (k === cle) return;
      cle = k;
      arreter();
      if (k) try { demarrer(); } catch (x) { arreter(); }                 // pas de son possible : tant pis
    }
    document.addEventListener("visibilitychange", maj);
    dlg.addEventListener("pointerdown", () => { if (ctxAudio && ctxAudio.state === "suspended") ctxAudio.resume().catch(() => {}); });
    return { maj, actif: () => !!maitre };
  })();

  // ---- aliments et objets, dessinés d'après nature (volume par dégradés, une lumière en haut à gauche) ----
  let nIco = 0;
  function icone(id) {
    const u = "phbi" + (++nIco);
    const G = (k, stops, x2 = 0, y2 = 1, x1 = 0, y1 = 0) => `<linearGradient id="${u}${k}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}">${stops.map(([o, c, a]) => `<stop offset="${o}" stop-color="${c}"${a != null ? ` stop-opacity="${a}"` : ""}/>`).join("")}</linearGradient>`;
    const R = (k, stops, cx = .36, cy = .3, r = .78) => `<radialGradient id="${u}${k}" cx="${cx}" cy="${cy}" r="${r}">${stops.map(([o, c, a]) => `<stop offset="${o}" stop-color="${c}"${a != null ? ` stop-opacity="${a}"` : ""}/>`).join("")}</radialGradient>`;
    const f = k => `url(#${u}${k})`;
    const ombre = (rx = 10, cy = 29.2) => `<ellipse cx="16" cy="${cy}" rx="${rx}" ry="1.5" fill="#3b2a12" opacity=".16"/>`;
    const S = (defs, corps) => `<svg viewBox="0 0 32 32" aria-hidden="true"><defs>${defs}</defs>${corps}</svg>`;
    // bord denté d'une feuille : contour échantillonné, une dent sur deux poussée vers l'extérieur
    const dente = (pts, amp) => pts.map((p, i) => {
      const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)], dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1;
      const k = i % 2 ? amp : 0;
      return `${(p[0] + dy / L * k).toFixed(1)} ${(p[1] - dx / L * k).toFixed(1)}`;
    }).join(" L");
    const contour = (n, fx, fy) => Array.from({ length: n + 1 }, (_, i) => { const t = i / n * Math.PI * 2; return [fx(t), fy(t)]; });
    const feuilleCoeur = (cx, cy, w, h, rot) => contour(36, t => cx + Math.sin(t) * w * (1 - .25 * Math.cos(t)), t => cy - Math.cos(t) * h * .55 - (Math.abs(Math.sin(t)) * h * .12) + h * .1)
      .map(([x, y]) => { const a = rot * Math.PI / 180, dx = x - cx, dy = y - cy; return [cx + dx * Math.cos(a) - dy * Math.sin(a), cy + dx * Math.sin(a) + dy * Math.cos(a)]; });
    const fruitRond = (k, c1, c2, c3) => R(k, [[0, c1], [.55, c2], [1, c3]]);
    const M = {
      trefle: () => S(G("f", [[0, "#7fc95a"], [1, "#3f8a2e"]]),
        `${ombre(6)}<path d="M16 16 C16.4 21 17 25 17.6 29" stroke="#4f8a32" stroke-width="1.4" fill="none" stroke-linecap="round"/>
        ${[0, 120, 240].map(a => `<g transform="rotate(${a} 16 15)"><path d="M16 15 C12.4 13.4 10 8 12.6 5.2 C14.2 3.8 15.8 4.8 16 6.4 C16.2 4.8 17.8 3.8 19.4 5.2 C22 8 19.6 13.4 16 15 Z" fill="${f("f")}" stroke="#336f26" stroke-width=".6"/>
          <path d="M13.4 9.4 L16 11.6 L18.6 9.4" stroke="#e4f2cf" stroke-width="1" fill="none" opacity=".85"/><path d="M16 14.6 V6.8" stroke="#336f26" stroke-width=".45" opacity=".6"/></g>`).join("")}`),
      feuilles_pissenlit: () => S(G("f", [[0, "#8fcf62"], [1, "#3f8630"]], 1, 1),
        `${ombre(9)}<path d="M5 29 C8 24.4 9.2 22 8.2 19 L12.2 20 C11.2 17 11.2 15 12.2 12.8 L16.2 14 C15.4 11.2 16 9.2 17.4 7.6 L20.4 9 C20.6 6.8 22.6 4.8 26.6 3 C24.6 7 24.4 9.2 23.4 11.2 L20.4 11.2 C21.2 13.4 20.4 15.4 19.2 17.2 L15.4 16.2 C16.2 18.4 15.4 21 13.4 23.2 L10.4 22.2 C10.2 25 8.6 27.2 5 29 Z" fill="${f("f")}" stroke="#2f6d26" stroke-width=".6" stroke-linejoin="round"/>
        <path d="M5 29 C11 21 17 13 25.4 4.2" stroke="#e8f4c8" stroke-width="1" fill="none" opacity=".8"/><path d="M4.6 29.4 l-1.6 1.6" stroke="#b8d48a" stroke-width="1.6" stroke-linecap="round"/>`),
      feuilles_murier: () => S(G("f", [[0, "#6fbd52"], [1, "#2f7a33"]], 1, 1),
        `${ombre(9)}<path d="M${dente(feuilleCoeur(16, 15, 11, 24, 0), .9)} Z" fill="${f("f")}" stroke="#2a6a2c" stroke-width=".5" stroke-linejoin="round"/>
        <path d="M16 26 V6 M16 22 L9 16 M16 22 L23 16 M16 17 L10.4 11.4 M16 17 L21.6 11.4 M16 12 L12.6 8.6 M16 12 L19.4 8.6" stroke="#d4ebb8" stroke-width=".8" fill="none" opacity=".75" stroke-linecap="round"/>
        <path d="M16 26 v3.4" stroke="#5a8a3a" stroke-width="1.4" stroke-linecap="round"/>`),
      chou_vert: () => S(G("f", [[0, "#9cc88c"], [.6, "#6a9e6a"], [1, "#4a7c58"]], 1, 1),
        `${ombre(10)}<path d="M16 29 C8 27 3.6 21 4.4 13.6 C5 7.6 9.6 3.4 15.4 3.2 C21.8 3 27.2 7.4 27.6 13.6 C28 21 23.6 27 16 29 Z" fill="${f("f")}" stroke="#3f6e4a" stroke-width=".6"/>
        <path d="M5.6 11 q1.6 -1 2.4 .6 q1.4 -1.2 2.4 .4 M22 6.4 q1.4 -.6 2 .8 q1.4 -.4 1.6 1.2" stroke="#3f6e4a" stroke-width=".5" fill="none"/>
        <path d="M16 29 C15.4 20 15.6 11 16.4 4.4" stroke="#e8f2dc" stroke-width="1.8" fill="none" stroke-linecap="round"/>
        <path d="M15.6 22 C12 20 9 17.6 7 14 M15.6 16.4 C12.6 14.6 10.4 12 9.2 9 M16.2 22 C19.6 20 22.6 17.6 24.8 14 M16.2 16.4 C19 14.6 21.2 12 22.4 9" stroke="#dcebd0" stroke-width=".9" fill="none" opacity=".8"/>`),
      courge: () => S(fruitRond("f", "#f6d49a", "#e3a85a", "#b9782e"),
        `${ombre(9)}<path d="M16 5.6 C19.4 5.6 20.4 9 20.2 12 C20 14.6 25.6 16.6 25.6 22.4 C25.6 27 21 29.2 16 29.2 C11 29.2 6.4 27 6.4 22.4 C6.4 16.6 12 14.6 11.8 12 C11.6 9 12.6 5.6 16 5.6 Z" fill="${f("f")}" stroke="#a8692a" stroke-width=".5"/>
        <path d="M16 6 V29 M12.6 13 C10 17 9.6 24 11 28.4 M19.4 13 C22 17 22.4 24 21 28.4" stroke="#c48a42" stroke-width=".55" fill="none" opacity=".6"/>
        <path d="M15.4 6 C15.2 4.4 15.8 3 17.4 2.4" stroke="#6b5a2a" stroke-width="1.8" fill="none" stroke-linecap="round"/>
        <ellipse cx="12.4" cy="20" rx="2" ry="4" fill="#fff" opacity=".28" transform="rotate(12 12.4 20)"/>`),
      haricots: () => S(G("f", [[0, "#9bd16e"], [1, "#4f9a3a"]], 0, 1),
        `${ombre(10)}${[[0, 0], [2.8, 2.6], [-2.6, 3]].map(([dx, dy], i) => `<g transform="translate(${dx} ${dy}) rotate(${-6 + i * 7} 16 16)">
          <path d="M6.4 24 C9 14 15.6 7.2 25.4 5 C26.6 4.8 27 5.8 26 6.4 C17.6 10 11.6 16 8.4 24.6 C8 25.8 6.2 25.4 6.4 24 Z" fill="${f("f")}" stroke="#3f7f2e" stroke-width=".5"/>
          <path d="M8.6 21.6 q1 -1.6 2.4 -1.2 M11 17.4 q1.2 -1.6 2.6 -1 M14 13.6 q1.4 -1.4 2.8 -.8 M17.4 10.6 q1.4 -1.2 2.8 -.4" stroke="#d6f0b4" stroke-width=".6" fill="none" opacity=".7"/>
          <path d="M26 5.6 l2 -1.2" stroke="#7aa84a" stroke-width="1" stroke-linecap="round"/></g>`).join("")}`),
      hibiscus: () => S(R("p", [[0, "#7d0f2a"], [.28, "#c8243f"], [.8, "#ee4a5c"], [1, "#ff8f8f"]], .5, .5, .55),
        `${ombre(10)}${[0, 72, 144, 216, 288].map(a => `<path d="M16 16 C9.6 13.6 8 4.8 12.8 2.8 C15.2 1.8 16.8 1.8 19.2 2.8 C24 4.8 22.4 13.6 16 16 Z" transform="rotate(${a} 16 16)" fill="${f("p")}" stroke="#a3162f" stroke-width=".5"/>
          <path d="M16 15.2 C15.2 10.4 15.2 6.4 16 4" transform="rotate(${a} 16 16)" stroke="#8d1028" stroke-width=".45" fill="none" opacity=".5"/>`).join("")}
        <path d="M16 16 L24 7.2" stroke="#f3c94a" stroke-width="1.2" stroke-linecap="round"/>${[[24, 7.2], [22.8, 6.4], [24.8, 8.4], [23.6, 8.8]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".8" fill="#ffd54a"/>`).join("")}<circle cx="25.1" cy="6.7" r="1" fill="#e8483f"/>`),
      fleur_pissenlit: () => S(R("c", [[0, "#ffe35a"], [.6, "#f7c21a"], [1, "#e09a00"]], .5, .5, .55),
        `${ombre(7)}<path d="M16 22 C16.4 25 16.6 27 17 29.4" stroke="#5f9a3a" stroke-width="1.6" fill="none" stroke-linecap="round"/>
        <path d="M11.6 19.6 L16 22.4 L20.4 19.6 L18.6 22.6 L16 23.6 L13.4 22.6 Z" fill="#4f8a32"/>
        ${Array.from({ length: 30 }, (_, i) => { const a = i / 30 * Math.PI * 2, l = 9 + (i % 3) * .8; return `<path d="M${(16 + Math.cos(a) * 2).toFixed(1)} ${(14 + Math.sin(a) * 2).toFixed(1)} L${(16 + Math.cos(a) * l).toFixed(1)} ${(14 + Math.sin(a) * l).toFixed(1)}" stroke="${i % 2 ? "#ffd21f" : "#ffe75c"}" stroke-width="1.5" stroke-linecap="round"/>`; }).join("")}
        <circle cx="16" cy="14" r="4.2" fill="${f("c")}"/>${Array.from({ length: 14 }, (_, i) => { const a = i / 14 * Math.PI * 2; return `<path d="M${(16 + Math.cos(a) * 1.2).toFixed(1)} ${(14 + Math.sin(a) * 1.2).toFixed(1)} L${(16 + Math.cos(a) * 4).toFixed(1)} ${(14 + Math.sin(a) * 4).toFixed(1)}" stroke="#e8a800" stroke-width=".7"/>`; }).join("")}`),
      mangue: () => S(R("f", [[0, "#ffe28a"], [.35, "#ffb23e"], [.7, "#f07a2a"], [1, "#c0392b"]], .62, .62, .8) + G("v", [[0, "#7fae3a", .95], [.45, "#9cc04a", .5], [1, "#9cc04a", 0]], 1, 1),
        `${ombre(10)}<path d="M8.4 9.6 C12.6 4.4 22.6 4.6 26 11 C28.6 16 26.6 24.6 19.6 27.6 C13.4 30.2 6.4 27 5.2 20.6 C4.6 16.4 6 12.4 8.4 9.6 Z" fill="${f("f")}" stroke="#a8462a" stroke-width=".5"/>
        <path d="M8.4 9.6 C12.6 4.4 22.6 4.6 26 11 C22 9 15 9.4 10.4 13.6 C8.4 15.4 7 13 8.4 9.6 Z" fill="${f("v")}"/>
        <path d="M17.4 5.6 C17.6 4 18.6 3 20 2.6" stroke="#5a4020" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <ellipse cx="12" cy="13" rx="3" ry="1.6" fill="#fff" opacity=".4" transform="rotate(-30 12 13)"/>${[[20, 18], [16, 22], [22, 23], [13, 18]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".35" fill="#ffe9a8" opacity=".8"/>`).join("")}`),
      papaye: () => S(G("p", [[0, "#ffb07a"], [.6, "#ff7f45"], [1, "#e85a2a"]], 1, 1) + G("s", [[0, "#cfe07a"], [1, "#7fa83a"]], 1, 1),
        `${ombre(11)}<path d="M4 18 C4 10 10 4.4 17.6 4.4 C24.6 4.4 28.6 9.6 28.6 15.6 C28.6 23 22.6 28.4 15.4 28.4 C8.6 28.4 4 24.4 4 18 Z" fill="${f("s")}" stroke="#6a8a2e" stroke-width=".5"/>
        <path d="M5.8 18 C5.8 11 11 6.2 17.6 6.2 C23.6 6.2 26.8 10.4 26.8 15.6 C26.8 22 21.6 26.6 15.4 26.6 C9.6 26.6 5.8 23.4 5.8 18 Z" fill="${f("p")}"/>
        <path d="M10.4 17.6 C10.4 13 13.6 10.4 17.4 10.4 C20.8 10.4 22.6 12.8 22.6 15.6 C22.6 19.4 19.6 22 16 22 C12.6 22 10.4 20.4 10.4 17.6 Z" fill="#e8642e"/>
        ${[[13, 15], [15.4, 13], [18.2, 12.8], [20.6, 14.6], [21, 17.4], [19.2, 19.8], [16.4, 20.8], [13.4, 19.6], [12.4, 17.2], [15.4, 16.2], [18, 15.6], [17.4, 18.4], [14.8, 18.6]].map(([x, y]) =>
          `<circle cx="${x}" cy="${y}" r="1.05" fill="#1d1a18"/><circle cx="${x - .3}" cy="${y - .35}" r=".3" fill="#fff" opacity=".5"/>`).join("")}`),
      figue: () => S(R("f", [[0, "#b77ab0"], [.5, "#7e3c78"], [1, "#4a1f4a"]]),
        `${ombre(8)}<path d="M16 5 C17.4 5 18 7 19.6 9.4 C22.4 13 25.2 15.6 25.2 20.2 C25.2 25.6 21 28.8 16 28.8 C11 28.8 6.8 25.6 6.8 20.2 C6.8 15.6 9.6 13 12.4 9.4 C14 7 14.6 5 16 5 Z" fill="${f("f")}" stroke="#3e1a3e" stroke-width=".5"/>
        <path d="M16 6 C14.6 12 14 20 15.2 28.6 M12.6 10 C10.6 15 10 22 11.6 28 M19.4 10 C21.4 15 22 22 20.4 28" stroke="#c9a0c4" stroke-width=".5" fill="none" opacity=".45"/>
        <path d="M15.4 5.4 C15.2 3.6 16 2.4 17.6 2" stroke="#6a7a3a" stroke-width="1.5" fill="none" stroke-linecap="round"/>
        <ellipse cx="12" cy="17" rx="1.8" ry="4" fill="#fff" opacity=".22" transform="rotate(14 12 17)"/>`),
      banane: () => S(G("f", [[0, "#fff09a"], [.5, "#ffd84a"], [1, "#e0a91a"]], 0, 1),
        `${ombre(11)}<path d="M4.4 9.6 C5 19 11 26.6 20.4 26.8 C24 26.8 27 25.4 28.4 23.4 C26 24 23.4 24 20.6 23.2 C13.2 21 8.2 15.6 7 8 Z" fill="${f("f")}" stroke="#b8891a" stroke-width=".55"/>
        <path d="M6 9.4 C7.8 17.6 13 22.6 21 24.4" stroke="#c99a1e" stroke-width=".6" fill="none" opacity=".6"/>
        <path d="M4.2 9.8 L4 7.4 L6.4 6.8 L7 8" fill="#6b5420" stroke="#4a3a14" stroke-width=".5"/><path d="M28.4 23.4 l.8 .4 l-.6 .8 l-.9 -.6 Z" fill="#3a2e14"/>
        <path d="M8.6 12 C10.4 16.6 13.8 19.8 18 21.4" stroke="#fff" stroke-width="1" fill="none" opacity=".45" stroke-linecap="round"/>`),
      remede: () => S(G("v", [[0, "#d98a3a"], [.5, "#a85a1a"], [1, "#7a3a0a"]], 1, 0) + G("b", [[0, "#f6f6f6"], [1, "#c9ced3"]], 1, 0),
        `${ombre(7)}<rect x="12.4" y="2.4" width="7.2" height="5" rx="1.2" fill="${f("b")}" stroke="#8a9096" stroke-width=".5"/><path d="M13.6 3.4 v3 M15.2 3.4 v3 M16.8 3.4 v3 M18.4 3.4 v3" stroke="#a0a6ac" stroke-width=".4"/>
        <path d="M11.8 9.6 C11.8 8 12.6 7.4 13.4 7.4 L18.6 7.4 C19.4 7.4 20.2 8 20.2 9.6 L21.6 11.6 C22.6 12.6 23 13.6 23 15 L23 26.4 C23 28 21.8 29 20.2 29 L11.8 29 C10.2 29 9 28 9 26.4 L9 15 C9 13.6 9.4 12.6 10.4 11.6 Z" fill="${f("v")}" stroke="#5a2a08" stroke-width=".5"/>
        <rect x="10.4" y="16" width="11.2" height="8.4" rx="1" fill="#f8f4e8"/><path d="M16 17.4 v5.6 M13.2 20.2 h5.6" stroke="#2e9a5a" stroke-width="2"/>
        <path d="M10.4 14 C10.4 12.8 11 12 11.8 11.6" stroke="#fff" stroke-width="1" opacity=".45" fill="none" stroke-linecap="round"/><path d="M11 25.4 v2" stroke="#fff" stroke-width="1" opacity=".3" stroke-linecap="round"/>`),
      lampe: () => S(G("m", [[0, "#eef1f4"], [.5, "#aeb6bd"], [1, "#6d757c"]], 1, 0) + R("l", [[0, "#ffe2b0"], [.5, "#ff8a3d"], [1, "#c4401a"]], .5, .5, .6),
        `${ombre(7)}<path d="M16 15.4 V28" stroke="#6d757c" stroke-width="1.6"/><ellipse cx="16" cy="28.4" rx="6" ry="1.5" fill="#5f666c"/>
        <path d="M5 13.6 C5 7.4 9.8 3.4 16 3.4 C22.2 3.4 27 7.4 27 13.6 Z" fill="${f("m")}" stroke="#5f666c" stroke-width=".6"/>
        <path d="M8 11 C8.6 7.6 11.6 5.4 15 5.2" stroke="#fff" stroke-width="1.1" fill="none" opacity=".7" stroke-linecap="round"/>
        <ellipse cx="16" cy="13.6" rx="11" ry="2" fill="#4d545a"/><ellipse cx="16" cy="13.8" rx="5.4" ry="2.6" fill="${f("l")}"/><ellipse cx="16" cy="18" rx="8" ry="3" fill="#ff8a3d" opacity=".18"/>`),
      chapeau: () => S(G("p", [[0, "#f6e2a6"], [.6, "#dcbc6c"], [1, "#b39246"]]),
        `${ombre(13, 28.4)}<ellipse cx="16" cy="21.4" rx="14.4" ry="4.6" fill="${f("p")}" stroke="#9a7634" stroke-width=".6"/>
        <ellipse cx="16" cy="21.2" rx="11" ry="2.8" fill="none" stroke="#a8843c" stroke-width=".5" stroke-dasharray="1 .7"/>
        <path d="M8.4 21 C8.2 12.8 11.4 9 16 9 C20.6 9 23.8 12.8 23.6 21 Z" fill="${f("p")}" stroke="#9a7634" stroke-width=".6"/>
        <path d="M9.2 14.6 q6.8 -1.8 13.6 0 M8.8 17.6 q7.2 -1.8 14.4 0" stroke="#a8843c" stroke-width=".5" fill="none" stroke-dasharray="1 .7"/>
        <path d="M8.5 18.4 q7.5 -1.8 15 0 l0 2.2 q-7.5 -1.8 -15 0 Z" fill="#b83a3f"/><path d="M10.6 11.6 C12 10.2 13.6 9.6 15.2 9.6" stroke="#fff" stroke-width=".9" opacity=".5" fill="none"/>`),
      couronne: () => S(R("p", [[0, "#8e1230"], [.3, "#d8344f"], [1, "#ff8090"]], .5, .5, .55),
        `${ombre(12)}<path d="M4 18 C6 26 26 26 28 18" stroke="#4f7d34" stroke-width="2" fill="none"/>
        ${[[7, 19, "#5d9a3e"], [25, 19, "#5d9a3e"], [16, 23.6, "#4f8a32"]].map(([x, y, k]) => `<ellipse cx="${x}" cy="${y}" rx="3.6" ry="1.8" fill="${k}" transform="rotate(${x < 16 ? 30 : x > 16 ? -30 : 0} ${x} ${y})"/>`).join("")}
        ${[[9, 14, .75], [16, 12, .95], [23, 14, .75]].map(([x, y, k]) => `<g transform="translate(${x} ${y}) scale(${k})">${[0, 72, 144, 216, 288].map(a => `<path d="M0 0 C-3.6 -1.6 -3.4 -6.6 0 -7 C3.4 -6.6 3.6 -1.6 0 0 Z" transform="rotate(${a})" fill="${f("p")}" stroke="#a51f3a" stroke-width=".4"/>`).join("")}
          <path d="M0 0 l3.4 -3.8" stroke="#f4d24a" stroke-width=".9"/><circle cx="3.6" cy="-4" r=".9" fill="#ffe36a"/></g>`).join("")}`),
      lunettes: () => S(G("l", [[0, "#4a6a8e"], [.5, "#1a2433"], [1, "#0a0f16"]], 1, 1),
        `${ombre(12, 26)}<path d="M2.4 13.4 L5 12.6 M29.6 13.4 L27 12.6" stroke="#2b2f36" stroke-width="1.4" stroke-linecap="round"/>
        ${[8.6, 23.4].map(x => `<path d="M${x - 6} 12.4 C${x - 6} 11 ${x + 6} 11 ${x + 6} 12.4 C${x + 6} 18 ${x + 3} 21 ${x} 21 C${x - 3} 21 ${x - 6} 18 ${x - 6} 12.4 Z" fill="${f("l")}" stroke="#111318" stroke-width=".9"/>
          <path d="M${x - 4} 13.4 q3 -1.4 6.6 -.4" stroke="#a8ccf2" stroke-width=".8" fill="none" opacity=".85"/><path d="M${x + 2.6} 18.6 l1.6 -2" stroke="#fff" stroke-width=".6" opacity=".4"/>`).join("")}
        <path d="M14.6 12.8 q1.4 -1.2 2.8 0" stroke="#2b2f36" stroke-width="1.2" fill="none"/>`),
      collier: () => S(R("p", [[0, "#ffffff"], [.5, "#f3e6cf"], [1, "#c7ad86"]]),
        `${ombre(11)}<path d="M5 9 C5 20 10 26 16 26 C22 26 27 20 27 9" stroke="#6b5435" stroke-width=".6" fill="none"/>
        ${[[5.2, 10.4], [5.8, 14.2], [7.2, 17.8], [9.4, 21], [12.4, 23.6], [16, 24.6], [19.6, 23.6], [22.6, 21], [24.8, 17.8], [26.2, 14.2], [26.8, 10.4]].map(([x, y], i) => i % 3 === 2
          ? `<path d="M${x - 1.8} ${y + .6} C${x - 1.8} ${y - 2.2} ${x + 1.8} ${y - 2.2} ${x + 1.8} ${y + .6} Z" fill="#f2c7a8" stroke="#b9846a" stroke-width=".4"/><path d="M${x} ${y + .4} v-1.6" stroke="#b9846a" stroke-width=".35"/>`
          : `<circle cx="${x}" cy="${y}" r="1.7" fill="${f("p")}" stroke="#a88f6a" stroke-width=".3"/>`).join("")}`),
      foulard: () => S(G("r", [[0, "#e24a52"], [1, "#9a2430"]], 1, 1),
        `${ombre(10)}<path d="M3.6 7 L28.4 7 L16 28.6 Z" fill="${f("r")}" stroke="#7d1a22" stroke-width=".6" stroke-linejoin="round"/>
        <path d="M6.6 9.6 L25.4 9.6 L16 26" fill="none" stroke="#fff" stroke-width=".5" stroke-dasharray="1.2 1" opacity=".7"/>
        ${[[11, 12.4], [16, 11.6], [21, 12.4], [13.6, 16.4], [18.4, 16.4], [16, 20.8]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.1" fill="#fff4ee"/><circle cx="${x}" cy="${y}" r=".4" fill="#e24a52"/>`).join("")}
        <path d="M3.6 7 C1.6 5.4 2 3 4.4 3.4 C6.4 3.8 6 6 5 7 Z M28.4 7 C30.4 5.4 30 3 27.6 3.4 C25.6 3.8 26 6 27 7 Z" fill="#b5303a" stroke="#7d1a22" stroke-width=".5"/>`),
      hamac: () => S(G("h", ["#d9653a", "#f1c27a", "#3f8aa8", "#f6ead2", "#d9653a", "#f1c27a"].flatMap((k, i) => [[i / 6, k], [(i + 1) / 6, k]]), 1, 0) + G("b", [[0, "#5a3d22"], [.5, "#a87a4a"], [1, "#5a3d22"]], 1, 0),
        `${ombre(13)}<rect x="2.2" y="5" width="2.6" height="24" rx="1" fill="${f("b")}"/><rect x="27.2" y="5" width="2.6" height="24" rx="1" fill="${f("b")}"/>
        <path d="M4.6 8 L8 10.4 M4.6 8 L7.6 12 M27.4 8 L24 10.4 M27.4 8 L24.4 12" stroke="#e8dcc0" stroke-width=".7"/>
        <path d="M7.6 10.6 C11 20 21 20 24.4 10.6 C22 23.6 10 23.6 7.6 10.6 Z" fill="${f("h")}"/><path d="M7.6 10.6 C11 20 21 20 24.4 10.6" stroke="#000" stroke-opacity=".2" stroke-width="1" fill="none"/>`),
      chateau: () => S(G("s", [[0, "#ecd5a0"], [1, "#bd9c5e"]], 1, 0),
        `${ombre(13)}<path d="M3 28.6 V15.4 h1.6 v-1.6 h1.6 v1.6 h1.6 v-1.6 h1.6 v1.6 h1 V28.6 Z M21.6 28.6 V15.4 h1.6 v-1.6 h1.6 v1.6 h1.6 v-1.6 h1.6 v1.6 h1 V28.6 Z" fill="${f("s")}"/>
        <path d="M9 28.6 V11 h1.8 v-2 h1.8 v2 h1.8 v-2 h1.8 v2 h1.8 v-2 h1.8 v2 h1.8 v-2 h1.8 v2 h.8 V28.6 Z" fill="${f("s")}"/>
        <path d="M13.8 28.6 v-5.4 q2.2 -3 4.4 0 v5.4 Z" fill="#8a6f42"/><rect x="5" y="19" width="2" height="2.6" fill="#9a7e50"/><rect x="24.6" y="19" width="2" height="2.6" fill="#9a7e50"/>
        <path d="M16 9 V2.6" stroke="#7a5a3a" stroke-width=".8"/><path d="M16 2.6 l6 1.8 l-6 2.2 Z" fill="#d9434a"/>
        ${[[11, 16], [20, 18], [6, 25], [26, 24], [15, 14]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".4" fill="#8a6f42" opacity=".5"/>`).join("")}`),
      coquillages_deco: () => S(R("a", [[0, "#ffe6d8"], [.6, "#f6b39a"], [1, "#d8826a"]], .5, .8, .9) + R("b", [[0, "#c9905a"], [.6, "#9a5a2a"], [1, "#6a3a1a"]]),
        `${ombre(13)}<path d="M2.4 26 C2 16 14 14.6 14.8 26 Z" fill="${f("a")}" stroke="#c97f68" stroke-width=".5"/>
        <path d="M8.6 26 V17.6 M8.6 26 L5 18.6 M8.6 26 L12.2 18.6 M8.6 26 L3.2 21.6 M8.6 26 L14 21.6" stroke="#c97f68" stroke-width=".55"/>
        <path d="M6.4 26.4 h4.4 l-.8 1.6 h-2.8 Z" fill="#e8a088"/>
        <ellipse cx="23" cy="23.4" rx="7" ry="4.4" fill="${f("b")}"/><ellipse cx="21.4" cy="21.6" rx="3.4" ry="1.3" fill="#fff" opacity=".45"/>
        ${[[19.6, 24.4], [23, 25.2], [26.2, 23.6], [24.6, 21.2]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".8" fill="#f2dcc0"/>`).join("")}
        <path d="M18 15.6 C17 11 20.4 7.6 24.6 8.6 C28.4 9.6 29 14 26.6 16 C24.6 17.6 20.4 17.6 18 15.6 Z" fill="#f2dcc0" stroke="#b9987a" stroke-width=".5"/><path d="M21 13.4 q2 -3.4 5 -2" stroke="#c9a888" fill="none" stroke-width=".6"/>`),
      parasol: () => S(G("o", [[0, "#fff", .25], [1, "#000", .22]], 1, 0),
        `${ombre(12)}<path d="M16 9 V29" stroke="#c9c2b6" stroke-width="1.4"/>
        ${Array.from({ length: 6 }, (_, i) => { const x0 = 2 + i * 4.67, x1 = x0 + 4.67; return `<path d="M16 4 L${x0.toFixed(1)} 15 Q${((x0 + x1) / 2).toFixed(1)} 17.4 ${x1.toFixed(1)} 15 Z" fill="${i % 2 ? "#f6f1e6" : "#d9434a"}"/>`; }).join("")}
        <path d="M16 4 L2 15 Q16 18 30 15 Z" fill="${f("o")}"/><circle cx="16" cy="3.6" r="1.3" fill="#c9c2b6"/>`),
      bouee: () => S(R("r", [[.45, "#000", .3], [.62, "#000", 0], [.82, "#fff", .3], [1, "#000", .25]], .5, .45, .55),
        `${ombre(12)}<path d="M3 16 a13 11 0 1 0 26 0 a13 11 0 1 0 -26 0 Z M10 16 a6 5 0 1 1 12 0 a6 5 0 1 1 -12 0 Z" fill="#e5484d" fill-rule="evenodd"/>
        <path d="M12.6 5.6 l-2 5.2 M19.4 5.6 l2 5.2 M12.6 26.4 l-2 -5.2 M19.4 26.4 l2 -5.2" stroke="#f6f1ea" stroke-width="4.4"/>
        <path d="M3 16 a13 11 0 1 0 26 0 a13 11 0 1 0 -26 0 Z M10 16 a6 5 0 1 1 12 0 a6 5 0 1 1 -12 0 Z" fill="${f("r")}" fill-rule="evenodd"/>
        <path d="M3.4 16 a12.6 10.6 0 0 0 25.2 0" stroke="#e8dcc0" stroke-width=".7" fill="none" stroke-dasharray="2 1.6"/>`),
      bob: () => S(G("b", [[0, "#ddd6aa"], [.6, "#b3aa78"], [1, "#857b50"]]),
        `${ombre(11)}<path d="M8.4 16.4 C8.4 8.6 12 5.6 16 5.6 C20 5.6 23.6 8.6 23.6 16.4 Z" fill="${f("b")}" stroke="#7a7048" stroke-width=".6"/>
        <path d="M9 11 q7 -2 14 0" stroke="#857b50" stroke-width=".5" fill="none" stroke-dasharray="1 .7"/>
        <path d="M3 19.6 C6 15 26 15 29 19.6 C27.6 22.4 4.4 22.4 3 19.6 Z" fill="${f("b")}" stroke="#7a7048" stroke-width=".6"/>
        <path d="M5.4 19.2 C9 17.2 23 17.2 26.6 19.2" stroke="#857b50" stroke-width=".5" fill="none" stroke-dasharray="1 .7"/>
        <path d="M9.4 21.4 C10 25 12 27.4 14 28.4" stroke="#6b5a3a" stroke-width=".7" fill="none"/><circle cx="20.4" cy="9" r=".7" fill="#6b6440"/>`),
      tricorne: () => S(G("t", [[0, "#4a4a55"], [.55, "#22222a"], [1, "#0e0e12"]]) + G("o", [[0, "#fff4b8"], [.4, "#f1c84a"], [1, "#a8741a"]]),
        `${ombre(13)}<path d="M9 12 C6.4 6.4 2.6 5.2 1 6 C3.6 7 6 9.4 7.2 13 Z" fill="#c4283a" stroke="#7d1220" stroke-width=".4"/>
        <path d="M11 17 C10.6 9.6 13.4 7.6 16 7.6 C18.6 7.6 21.4 9.6 21 17 Z" fill="${f("t")}"/>
        <path d="M2 20.6 C4.6 13.6 9.6 14.6 12.4 16.8 C15 15.6 17 15.6 19.6 16.8 C22.4 14.6 27.4 13.6 30 20.6 C22.6 23.6 9.4 23.6 2 20.6 Z" fill="${f("t")}" stroke="#08080a" stroke-width=".5"/>
        <path d="M2 20.6 C4.6 13.6 9.6 14.6 12.4 16.8 M19.6 16.8 C22.4 14.6 27.4 13.6 30 20.6" stroke="${f("o")}" stroke-width="1.2" fill="none" stroke-linecap="round"/><circle cx="16" cy="18.6" r="1.8" fill="${f("o")}"/>`),
      couronne_or: () => S(G("o", [[0, "#fff4b8"], [.35, "#f1c84a"], [.7, "#c8901f"], [1, "#8a5a12"]]) + R("r", [[0, "#ffb3be"], [.5, "#d8143a"], [1, "#6e0418"]]) + R("s", [[0, "#b7d4ff"], [.5, "#2456c8"], [1, "#0d2466"]]) + R("e", [[0, "#b8f5cc"], [.5, "#16a04a"], [1, "#05501f"]]),
        `${ombre(12)}<path d="M5.4 20 L5.6 9.6 L10.4 14.6 L13.4 6.4 L16 12.6 L18.6 6.4 L21.6 14.6 L26.4 9.6 L26.6 20 Z" fill="#8e1c2c"/>
        <path d="M4.4 22 L4.4 10.4 L10 15.6 L13 7 L16 13.4 L19 7 L22 15.6 L27.6 10.4 L27.6 22 Z" fill="${f("o")}" stroke="#7a4e10" stroke-width=".6" stroke-linejoin="round"/>
        <rect x="3.8" y="20" width="24.4" height="6" rx="1.4" fill="${f("o")}" stroke="#7a4e10" stroke-width=".6"/>
        ${[[4.4, 9.8], [13, 6.3], [19, 6.3], [27.6, 9.8]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.4" fill="#fffaf0" stroke="#c9b890" stroke-width=".3"/>`).join("")}
        <ellipse cx="16" cy="23" rx="2.4" ry="1.8" fill="${f("r")}"/><ellipse cx="9.6" cy="23" rx="1.7" ry="1.4" fill="${f("s")}"/><ellipse cx="22.4" cy="23" rx="1.7" ry="1.4" fill="${f("e")}"/>
        <path d="M4.4 21.2 h23.4" stroke="#fff6c8" stroke-width=".6" opacity=".7"/>`),
      diademe: () => S(G("n", [[0, "#fdf7ff"], [.3, "#d8efff"], [.55, "#f7d8ff"], [.8, "#dcfff0"], [1, "#fff3d8"]], 1, 1) + R("p", [[0, "#ffffff"], [.6, "#f4eef6"], [1, "#c8bcd0"]]),
        `${ombre(12)}<path d="M3 25 C8 17.6 24 17.6 29 25" stroke="#c9d2dc" stroke-width="2.2" fill="none" stroke-linecap="round"/>
        <path d="M16 20 C11.4 19.6 9.6 16 10.4 13 C11.4 9.6 14.2 7.6 16 6.8 C17.8 7.6 20.6 9.6 21.6 13 C22.4 16 20.6 19.6 16 20 Z" fill="${f("n")}" stroke="#a9a0c0" stroke-width=".5"/>
        <path d="M16 19.6 V8.2 M16 19.6 L11.8 11.8 M16 19.6 L20.2 11.8 M16 19.6 L10.8 15.6 M16 19.6 L21.2 15.6" stroke="#b9aed0" stroke-width=".45"/>
        ${[[5.6, 22.4], [9.4, 20.4], [22.6, 20.4], [26.4, 22.4]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.5" fill="${f("p")}"/>`).join("")}<circle cx="16" cy="6" r="1.8" fill="${f("p")}"/>`),
      lunettes_coeur: () => S(G("l", [[0, "#ffb0cc"], [.6, "#f0548a"], [1, "#b8285c"]], 1, 1),
        `${ombre(12, 26)}<path d="M14.6 13.4 q1.4 -1.2 2.8 0" stroke="#f6f0f2" stroke-width="1.4" fill="none"/>
        ${[8.4, 23.6].map(x => `<path d="M${x} 21.4 C${x - 7} 17.4 ${x - 6.6} 10.6 ${x - 3} 10.6 C${x - 1.2} 10.6 ${x - .3} 11.8 ${x} 12.8 C${x + .3} 11.8 ${x + 1.2} 10.6 ${x + 3} 10.6 C${x + 6.6} 10.6 ${x + 7} 17.4 ${x} 21.4 Z" fill="${f("l")}" stroke="#fff" stroke-width="1.1"/>
          <path d="M${x - 3.6} 13 q1.4 -1.4 3 -.6" stroke="#fff" stroke-width=".8" fill="none" opacity=".85"/>`).join("")}`),
      monocle: () => S(G("o", [[0, "#fff4b8"], [.4, "#f1c84a"], [1, "#a8741a"]]),
        `${ombre(9)}<path d="M18 21.6 C17 25 13 27.6 7 27.4" stroke="${f("o")}" stroke-width="1" fill="none" stroke-dasharray="1.4 .7" stroke-linecap="round"/>
        <circle cx="18" cy="13" r="8.4" fill="#e8f4ff" fill-opacity=".25" stroke="${f("o")}" stroke-width="2"/><circle cx="18" cy="13" r="8.4" fill="none" stroke="#7a4e10" stroke-width=".4"/>
        <path d="M12.6 9.4 q3 -2.8 7.2 -2" stroke="#fff" stroke-width="1.1" fill="none" opacity=".8"/>`),
      noeud: () => S(G("n", [[0, "#ff5a64"], [.55, "#d0202e"], [1, "#86101a"]]),
        `${ombre(11)}<path d="M16 16 L4.6 9 C3 12.6 3 19.4 4.6 23 Z M16 16 L27.4 9 C29 12.6 29 19.4 27.4 23 Z" fill="${f("n")}" stroke="#6e0c14" stroke-width=".6" stroke-linejoin="round"/>
        <path d="M6.6 12 l6.4 3.4 M6.6 20 l6.4 -3 M25.4 12 l-6.4 3.4 M25.4 20 l-6.4 -3" stroke="#6e0c14" stroke-width=".5" opacity=".6"/>
        <rect x="13.2" y="12.6" width="5.6" height="6.8" rx="1.8" fill="${f("n")}" stroke="#6e0c14" stroke-width=".6"/><path d="M5.6 11 l3.6 2" stroke="#fff" stroke-width=".7" opacity=".5"/>`),
      perles: () => S(R("p", [[0, "#ffffff"], [.55, "#f6eef0"], [.85, "#dcc8d4"], [1, "#b8a2b4"]]),
        `${ombre(11)}${Array.from({ length: 13 }, (_, i) => { const a = Math.PI * (.08 + .84 * i / 12); return `<circle cx="${(16 - Math.cos(a) * 11.6).toFixed(1)}" cy="${(8 + Math.sin(a) * 15).toFixed(1)}" r="1.9" fill="${f("p")}"/>`; }).join("")}
        <ellipse cx="16" cy="26.4" rx="1.9" ry="2.4" fill="${f("p")}"/>`),
      medaille: () => S(G("o", [[0, "#fff4b8"], [.35, "#f1c84a"], [.7, "#c8901f"], [1, "#8a5a12"]]),
        `${ombre(9)}<path d="M5 4 C5 12 10 16 16 16.6 C22 16 27 12 27 4" stroke="${f("o")}" stroke-width="1.2" fill="none" stroke-dasharray="1.6 .6"/>
        <circle cx="16" cy="22" r="7" fill="${f("o")}" stroke="#7a4e10" stroke-width=".7"/><circle cx="16" cy="22" r="5.4" fill="none" stroke="#fff2b0" stroke-width=".6" opacity=".8"/>
        <path d="M11.6 24.6 C11.6 18.6 20.4 18.6 20.4 24.6 Z M16 24.6 V19.4 M16 24.6 L13.2 20.4 M16 24.6 L18.8 20.4" fill="#e9b938" stroke="#8a5a12" stroke-width=".5"/>`),
      cape: () => S(G("v", [[0, "#e0303f"], [.55, "#a5101e"], [1, "#5e0610"]]) + G("o", [[0, "#fff4b8"], [.4, "#f1c84a"], [1, "#a8741a"]]),
        `${ombre(12)}<path d="M10 5 C6 12 4 20 3.4 27 C6 28.4 8 26.8 10 28.2 C12 29.4 14 27.6 16 28.6 C18 27.6 20 29.4 22 28.2 C24 26.8 26 28.4 28.6 27 C28 20 26 12 22 5 Z" fill="${f("v")}"/>
        <path d="M3.4 27 C6 28.4 8 26.8 10 28.2 C12 29.4 14 27.6 16 28.6 C18 27.6 20 29.4 22 28.2 C24 26.8 26 28.4 28.6 27" stroke="${f("o")}" stroke-width="1.3" fill="none"/>
        <path d="M11 9 C9.6 15 9.2 21 9.6 27.6 M16 8 V28.4 M21 9 C22.4 15 22.8 21 22.4 27.6" stroke="#5e0610" stroke-width="1" opacity=".4"/>
        <path d="M8 6.4 C11 3.4 21 3.4 24 6.4 C22 8.8 10 8.8 8 6.4 Z" fill="#fbf8f2" stroke="#d9d2c4" stroke-width=".5"/>
        ${[[11, 6.2], [15, 6.8], [19, 6.6], [22, 5.8]].map(([x, y]) => `<path d="M${x} ${y - .6} l.5 1.4 l-.5 -.3 l-.5 .3 Z" fill="#1a1a1a"/>`).join("")}`),
      tiki: () => S(G("w", [[0, "#5a3d22"], [.5, "#9a6a3a"], [1, "#4a3018"]], 1, 0),
        `${ombre(8)}<path d="M9 28.6 V6.4 C9 3.6 11.6 2.2 16 2.2 C20.4 2.2 23 3.6 23 6.4 V28.6 Z" fill="${f("w")}" stroke="#3a2412" stroke-width=".6"/>
        <path d="M10.6 9.4 h4 M17.4 9.4 h4" stroke="#2a1a0c" stroke-width="1.6" stroke-linecap="round"/><ellipse cx="12.6" cy="12.4" rx="2" ry="1.6" fill="#f2e2c0"/><ellipse cx="19.4" cy="12.4" rx="2" ry="1.6" fill="#f2e2c0"/>
        <circle cx="12.6" cy="12.4" r=".8" fill="#1a1008"/><circle cx="19.4" cy="12.4" r=".8" fill="#1a1008"/><path d="M15 14.6 l1 3 l1 -3" fill="none" stroke="#2a1a0c" stroke-width=".8"/>
        <rect x="11.4" y="19" width="9.2" height="3.6" rx="1.4" fill="#2a1a0c"/><path d="M12.4 20.8 h7.2" stroke="#f2e2c0" stroke-width=".9" stroke-dasharray="1.2 .6"/>
        <path d="M9 25 h14" stroke="#3a2412" stroke-width=".8"/>`),
      phare: () => S(G("p", [[0, "#ffffff"], [1, "#c9ccd0"]], 1, 0),
        `${ombre(10)}<path d="M5 29 C6 25 10 23.6 16 23.6 C22 23.6 26 25 27 29 Z" fill="#7a7068"/>
        <path d="M11.6 24 L13 8.6 H19 L20.4 24 Z" fill="${f("p")}" stroke="#8a9096" stroke-width=".5"/>
        <path d="M12.2 17.4 L12.6 13.4 H19.4 L19.8 17.4 Z M11.8 22 L12 20.4 H20 L20.2 22 Z" fill="#d9434a"/>
        <rect x="12.4" y="5" width="7.2" height="3.8" rx=".6" fill="#ffe9a0" stroke="#3a3f44" stroke-width=".6"/><path d="M11.6 5 L16 1.6 L20.4 5 Z" fill="#3a3f44"/>
        <path d="M20 6.4 L30 3.4 L30 9.6 Z" fill="#ffe9a0" opacity=".55"/>`),
      coffre: () => S(G("w", [[0, "#9a5e2a"], [1, "#5a3010"]]) + G("o", [[0, "#fff4b8"], [.4, "#f1c84a"], [1, "#a8741a"]]),
        `${ombre(13)}<path d="M4 15 C4 8.6 8 6.4 16 6.4 C24 6.4 28 8.6 28 15 Z" fill="${f("w")}" stroke="#3a1e08" stroke-width=".6"/>
        <rect x="4" y="15" width="24" height="13" rx="1" fill="${f("w")}" stroke="#3a1e08" stroke-width=".6"/>
        <path d="M4 15 H28 M10 6.8 V28 M22 6.8 V28" stroke="${f("o")}" stroke-width="1.4"/>
        ${[[8, 14], [12, 13], [16, 13.6], [20, 12.8], [24, 14]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.8" fill="${f("o")}" stroke="#8a5a12" stroke-width=".4"/>`).join("")}
        <rect x="14" y="17" width="4" height="4.4" rx=".8" fill="${f("o")}" stroke="#7a4e10" stroke-width=".4"/><path d="M16 18.6 v1.4" stroke="#3a1e08" stroke-width=".7"/>`),
      benitier: () => S(G("c", [[0, "#f6f2e8"], [.5, "#d9cfb8"], [1, "#9a8c70"]]) + R("p", [[0, "#ffffff"], [.55, "#f6eef0"], [.85, "#dcc8d4"], [1, "#b8a2b4"]]) + G("m", [[0, "#3fb6a8"], [.5, "#2a6fb0"], [1, "#6a3fa0"]], 1, 0),
        `${ombre(13)}<path d="M2.6 20 C3 12 9 7.6 16 7.6 C23 7.6 29 12 29.4 20 C25 18.4 21 18.4 16 19 C11 18.4 7 18.4 2.6 20 Z" fill="${f("c")}" stroke="#8a7c60" stroke-width=".5"/>
        <path d="M2.6 20 C7 18.4 11 18.4 16 19 C21 18.4 25 18.4 29.4 20 C28 25.6 22 28.6 16 28.6 C10 28.6 4 25.6 2.6 20 Z" fill="${f("c")}" stroke="#8a7c60" stroke-width=".5"/>
        <path d="M5 20.4 C9 19.6 23 19.6 27 20.4 C24 22.6 8 22.6 5 20.4 Z" fill="${f("m")}" opacity=".9"/>
        <path d="M6 14 q2 -1 3 1 q2 -2 4 0 q2 -2 4 0 q2 -2 4 0 q1 -2 3 -1 M5 24 q2 1 3 -1 q2 2 4 0 q2 2 4 0 q2 2 4 0 q1 2 3 1" stroke="#a89878" stroke-width=".6" fill="none"/>
        <circle cx="16" cy="18.4" r="3.4" fill="${f("p")}"/><circle cx="14.8" cy="17.2" r="1" fill="#fff"/>`),
      coquillage: () => S(R("s", [[0, "#fff1e6"], [.55, "#ffc2a0"], [1, "#e08a6a"]], .5, .85, .95),
        `<path d="M3.4 19.6 C3.4 10.6 9.4 4.4 16 4.4 C22.6 4.4 28.6 10.6 28.6 19.6 L22 25.6 H10 Z" fill="${f("s")}" stroke="#c47458" stroke-width=".8" stroke-linejoin="round"/>
        <path d="M16 25.4 V5.4 M16 25.4 L11.4 6.4 M16 25.4 L20.6 6.4 M16 25.4 L7.2 9.4 M16 25.4 L24.8 9.4 M16 25.4 L4.6 14.6 M16 25.4 L27.4 14.6" stroke="#d98a6e" stroke-width=".9" fill="none"/>
        <path d="M10 25.6 L8.6 28.6 H13.4 Z M22 25.6 L23.4 28.6 H18.6 Z" fill="#f2a888" stroke="#c47458" stroke-width=".6" stroke-linejoin="round"/><path d="M12 28.4 h8 l-1.2 -2.8 h-5.6 Z" fill="#f6b498"/>
        <path d="M8 11 C10 7.6 13 6.2 16 6.2" stroke="#fff" stroke-width="1.2" fill="none" opacity=".6" stroke-linecap="round"/>`),
    };
    return (M[id] || M.feuilles_pissenlit)();
  }

  // ---- couleurs : phase du jour, météo et saison (teintes relevées sur des photos de lagons et de plages tropicales) ----
  function palette(e) {
    const ph = e.ciel.phase, met = e.ciel.meteo, sa = e.ciel.saison || "printemps", nuit = ph === "nuit";
    // ciel : [zénith, milieu, horizon] — l'horizon reste clair et un peu voilé (diffusion de la lumière)
    const CIELS = { aube: ["#38508e", "#c98aa0", "#fbd3a0"], jour: ["#2a6fc0", "#5aa3dd", "#cde6f2"], coucher: ["#252f66", "#b4577a", "#ff9a52"], nuit: ["#040a1c", "#0b1a3e", "#1a2f5a"] };
    let c = CIELS[ph];
    if (ph === "jour") c = { ete: ["#1f68c2", "#4e9fe0", "#c9e8f5"], hiver: ["#4f82b8", "#86b0d6", "#dde8ef"], automne: ["#3a78b8", "#6ea6d6", "#d3e4ee"] }[sa] || c;
    if (met === "pluie") c = nuit ? ["#070d18", "#121c2b", "#1f2a3a"] : ["#58687a", "#7c8b9a", "#a9b4bd"];
    else if (met === "nuages" && ph === "jour") c = ["#4f7fae", "#8fb4d2", "#d6e3ec"];
    // mer profonde : [à l'horizon, au premier plan] ; lagon (eau peu profonde sur le sable blanc) : [clair, turquoise, bleu-vert]
    const mer = nuit ? ["#10264a", "#061430"] : met === "pluie" ? ["#5a6e7a", "#2d4652"] : ph === "coucher" ? ["#7a5f78", "#1c3a5e"] : ph === "aube" ? ["#6e7fa6", "#1f4a72"]
      : { ete: ["#2f7fb0", "#0a4f80"], hiver: ["#4a7fa0", "#1a4f70"], automne: ["#3f7aa2", "#11507a"] }[sa] || ["#3580ad", "#0c5282"];
    const lagon = nuit ? ["#2c5a6e", "#1d4a62", "#143a56"] : met === "pluie" ? ["#9cc0ba", "#64a0a0", "#3f7a86"]
      : ph === "coucher" ? ["#a9cfc4", "#5aa3ac", "#2f7590"] : ph === "aube" ? ["#b1dcd6", "#62b4b8", "#2f7f98"]
        : { ete: ["#aef2e6", "#3fd2cc", "#16a0b6"], hiver: ["#b0e2db", "#56bcbf", "#2a8aa4"] }[sa] || ["#a9ece2", "#47cbc8", "#1b98b0"];
    const sable = nuit ? ["#7d735c", "#625a48", "#4d4639"] : met === "pluie" ? ["#dccba4", "#c4ad80", "#a8905f"]
      : ph === "coucher" ? ["#f4d9b4", "#ddb98a", "#bf9866"] : ph === "aube" ? ["#f0dcc0", "#dcc29a", "#c2a47a"]
        : { ete: ["#f7eaca", "#ead29e", "#d2b47c"], hiver: ["#ede2c6", "#dccaa0", "#c2a97c"] }[sa] || ["#f3e6c3", "#e5cf9e", "#cdb07a"];
    // palmes : [claire, foncée, nervure, palmes du fond, nervure du fond]
    const palmes = nuit ? ["#3a5a44", "#2b4638", "#66724c", "#1e3430", "#48553b"]
      : met === "pluie" ? ["#55804a", "#3c6238", "#8a9256", "#2a4a2c", "#687346"]
        : ph === "coucher" ? ["#6f8a3c", "#4c672c", "#a8984e", "#34482a", "#7d7440"] : ph === "aube" ? ["#6a9244", "#476c34", "#a8a058", "#324a30", "#7a7a48"]
          : { hiver: ["#7aa046", "#567f35", "#b4b45c", "#3d6430", "#8d9a4a"], automne: ["#5b9a3d", "#3f7a30", "#a6aa52", "#2c5a28", "#7f8c42"], ete: ["#6aac42", "#478a33", "#b2b552", "#336a2c", "#8a9a44"] }[sa]
        || ["#64a640", "#438532", "#adb050", "#30652b", "#879744"];
    const stipe = nuit ? ["#262426", "#3d3a3a", "#57514c"] : met === "pluie" ? ["#4e443a", "#6f6253", "#93826c"] : ["#5e4f40", "#8c7862", "#bca684"];
    const herbe = nuit ? ["#3b4a35", "#2c3a2a"] : ph === "coucher" ? ["#a09048", "#76703a"] : met === "pluie" ? ["#76884a", "#55683a"] : sa === "hiver" ? ["#a3a25a", "#7f8442"] : ["#8fa44c", "#64803a"];
    const rocher = nuit ? ["#6a6662", "#55514e", "#3f3c3a", "#2c2a29"] : met === "pluie" ? ["#9c948c", "#7a7068", "#5a524c", "#3e3833"] : ["#c9beb2", "#9b8e81", "#6e635a", "#4b423b"];
    return { c, mer, lagon, sable, palmes, stipe, herbe, rocher, nuit, ph, met, sa, sec: nuit ? ["#5a5040", "#433a2e"] : ["#b89c5c", "#8a6f3e"],
      noix: nuit ? ["#4a3a2a", "#2a2018", "#3e4a2c", "#28321c"] : ["#9a7344", "#5e4022", "#93a648", "#56702a"] };
  }
  const melange = D.melange;

  // Position du soleil (de 6 h à 21 h) ou de la lune (de 21 h à 6 h), dans les coordonnées 1000 × 500 de la scène
  function astrePos(e) {
    const h = e.ciel.heure;
    if (e.ciel.phase === "nuit") {
      const k = ((h + 24 - 21) % 24) / 9;
      return { x: (12 + k * 76) * 10, y: (46 - Math.sin(Math.PI * k) * 19) * 5, soleil: false, haut: Math.sin(Math.PI * k) };
    }
    const k = Math.min(1, Math.max(0, (h - 6) / 15));
    return { x: (9 + k * 82) * 10, y: (50 - Math.sin(Math.PI * k) * 23) * 5, soleil: true, haut: Math.sin(Math.PI * k) };
  }
  // Phase réelle de la Lune (mois synodique de 29,53 jours depuis la nouvelle lune du 6 janvier 2000)
  function phaseLune() {
    const p = ((Date.now() / 86400000 - 10962.76) / 29.530589) % 1;
    return p < 0 ? p + 1 : p;
  }

  function etoiles() {
    let s = "";
    for (let i = 0; i < 64; i++) {
      const x = (i * 379 + 97) % 1000 / 10, y = (8 + (i * i * 53 + i * 29) % 215) / 5, g = i % 7 === 0, f = i % 3 === 0;
      s += `<i class="phb-etoile${g ? " g" : f ? " f" : ""}" style="left:${x}%;top:${y}%;animation-delay:-${(i * .37) % 4}s${i % 5 === 0 ? ";background:#ffe9c4" : i % 4 === 0 ? ";background:#d6e4ff" : ""}"></i>`;
    }
    return `<div class="phb-l phb-etoiles" aria-hidden="true"><i class="phb-voie"></i>${s}</div>`;
  }
  function astre(e, P, S) {
    if (!S.soleil) {
      const p = phaseLune(), k = Math.cos(2 * Math.PI * p), r = 15, cx = 30, cy = 30, rx = Math.abs(k) * r;
      const croit = p < .5;
      const eclaire = `M${cx} ${cy - r} A${r} ${r} 0 0 ${croit ? 1 : 0} ${cx} ${cy + r} A${rx.toFixed(2)} ${r} 0 0 ${croit ? (k > 0 ? 0 : 1) : (k > 0 ? 1 : 0)} ${cx} ${cy - r} Z`;
      const lum = (1 - k) / 2;
      return `<div class="phb-astre phb-lune" style="left:${S.x / 10}%;top:${S.y / 5}%" aria-hidden="true">
        <svg viewBox="0 0 60 60"><defs><radialGradient id="phbd-lh"><stop offset="0" stop-color="#f4f1d6" stop-opacity="${(.12 + lum * .3).toFixed(2)}"/><stop offset="1" stop-color="#f4f1d6" stop-opacity="0"/></radialGradient>
          <radialGradient id="phbd-ld" cx=".42" cy=".38" r=".7"><stop offset="0" stop-color="#fbf9ee"/><stop offset=".7" stop-color="#e8e3cc"/><stop offset="1" stop-color="#cfc8ae"/></radialGradient>
          <clipPath id="phbd-lc"><path d="${eclaire}"/></clipPath></defs>
          <circle cx="30" cy="30" r="30" fill="url(#phbd-lh)"/>
          <circle cx="${cx}" cy="${cy}" r="${r}" fill="#2a3552" opacity=".55"/>
          <g clip-path="url(#phbd-lc)"><circle cx="${cx}" cy="${cy}" r="${r}" fill="url(#phbd-ld)"/>
            <g fill="#b9b39c" opacity=".55"><ellipse cx="25" cy="25" rx="4.6" ry="3.6"/><ellipse cx="33" cy="23" rx="3.4" ry="2.6"/><ellipse cx="34.4" cy="31.6" rx="4" ry="3.2"/><ellipse cx="26.6" cy="34" rx="2.6" ry="2"/><circle cx="31" cy="40" r="1.4"/></g>
            <circle cx="29" cy="41.4" r="1" fill="#fff" opacity=".5"/></g></svg></div>`;
    }
    const bas = P.ph !== "jour";
    const coeur = bas ? ["#fff4dc", "#ffcf8a", "#ff9a52"] : ["#fffef8", "#fff6d2", "#ffe9a0"];
    return `<div class="phb-astre phb-soleil" style="left:${S.x / 10}%;top:${S.y / 5}%" aria-hidden="true">
      <svg viewBox="0 0 60 60"><defs><radialGradient id="phbd-sh"><stop offset="0" stop-color="${coeur[1]}" stop-opacity=".75"/><stop offset=".35" stop-color="${coeur[2]}" stop-opacity=".3"/><stop offset="1" stop-color="${coeur[2]}" stop-opacity="0"/></radialGradient>
        <radialGradient id="phbd-sd"><stop offset="0" stop-color="${coeur[0]}"/><stop offset=".75" stop-color="${coeur[1]}"/><stop offset="1" stop-color="${coeur[2]}"/></radialGradient></defs>
        <circle cx="30" cy="30" r="30" fill="url(#phbd-sh)"/><circle cx="30" cy="30" r="9.5" fill="url(#phbd-sd)"/></svg></div>`;
  }
  let gouttesHtml = "";
  function gouttes() {
    if (gouttesHtml) return gouttesHtml;
    let d = "", d2 = "";
    for (let i = 0; i < 190; i++) {
      const x = (i * 613 + 41) % 1000, y = (i * i * 37 + i * 11) % 500, l = 14 + (i * 7) % 16;
      for (const dy of [0, 500]) { const _s = `M${x} ${y + dy} l-4 ${l} `; if (i % 3) d += _s; else d2 += _s; }
    }
    return (gouttesHtml = `<path d="${d}" stroke="#dfe8f2" stroke-opacity=".42" stroke-width="1.2" stroke-linecap="round" vector-effect="non-scaling-stroke"/>
      <path d="${d2}" stroke="#ffffff" stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`);
  }
  const COUL_NUAGE = {
    jour: { haut: "#ffffff", milieu: "#eef2f7", bas: "#a9b8c9" }, nuages: { haut: "#f4f6f8", milieu: "#d6dde5", bas: "#8e9dad" },
    pluie: { haut: "#a3acb5", milieu: "#86909a", bas: "#5a6570", flou: 2.2 }, rose: { haut: "#ffe4cc", milieu: "#f2b8a6", bas: "#86698a" },
    nuit: { haut: "#53668a", milieu: "#35476a", bas: "#1b2742" },
  };

  // ---- la plage : forme de l'île, et les mêmes formes agrandies pour le sable mouillé, l'écume et le lagon ----
  const ILE = "M108 500 C138 404 262 352 470 342 C560 338 640 340 702 352 C800 372 868 418 894 500 Z";
  const autour = (sx, sy) => `transform="translate(500 500) scale(${sx} ${sy}) translate(-500 -500)"`;
  const ILE_S = [[[108, 500], [138, 404], [262, 352], [470, 342]], [[470, 342], [560, 338], [640, 340], [702, 352]], [[702, 352], [800, 372], [868, 418], [894, 500]]];
  // écume : petites taches irrégulières semées le long du contour agrandi (sx, sy), plus serrées là où la vague se brise
  function ecume(sx, sy, k, n) {
    const r = N.alea(Math.round(sx * 1000)), L = [];
    for (let i = 0; i < n; i++) {
      const u = i / n * 3, s = ILE_S[Math.min(2, Math.floor(u))], p = N.bz(s, u - Math.floor(u));
      const x = 500 + (p[0] - 500) * sx + (r() - .5) * 8, y = 500 + (p[1] - 500) * sy + (r() - .5) * 3;
      if (y > 498) continue;
      const rx = (2 + r() * 9) * k, ry = (.8 + r() * 1.8) * k;
      L.push(`M${(x - rx).toFixed(1)} ${y.toFixed(1)} a${rx.toFixed(1)} ${ry.toFixed(1)} 0 1 0 ${(2 * rx).toFixed(1)} 0 a${rx.toFixed(1)} ${ry.toFixed(1)} 0 1 0 ${(-2 * rx).toFixed(1)} 0 Z`);
    }
    return L.join(" ");
  }

  // touffes d'herbe des dunes (avec épis), liseron de mer (feuilles en cœur, fleurs roses) : plantes des vraies plages
  function herbes(P, x, y, n, graine) {
    const r = N.alea(graine);
    let d = "", d2 = "", epis = "";
    for (let i = 0; i < n; i++) {
      const bx = x + (r() - .5) * 26, h = 14 + r() * 22, pen = (r() - .5) * 20;
      const seg = `M${bx.toFixed(1)} ${y} q${(pen * .3).toFixed(1)} ${(-h * .6).toFixed(1)} ${pen.toFixed(1)} ${(-h).toFixed(1)} `;
      { const _s = seg; if (i % 2) d += _s; else d2 += _s; }
      if (i % 4 === 1) epis += `M${(bx + pen).toFixed(1)} ${(y - h).toFixed(1)} l${(pen * .1).toFixed(1)} -7 `;
    }
    return `<path d="${d2}" stroke="${P.herbe[1]}" stroke-width="2" fill="none" stroke-linecap="round"/><path d="${d}" stroke="${P.herbe[0]}" stroke-width="1.7" fill="none" stroke-linecap="round"/>
      <path d="${epis}" stroke="${P.nuit ? "#5a5640" : "#c9b46a"}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  }
  function liseron(P, x0, y0, x1, y1, graine) {
    const r = N.alea(graine);
    let tige = `M${x0} ${y0} C${(x0 * 2 + x1) / 3} ${y0 - 10} ${(x0 + x1 * 2) / 3} ${y1 + 10} ${x1} ${y1}`, f = "", fl = "";
    for (let i = 1; i < 9; i++) {
      const t = i / 9, x = x0 + (x1 - x0) * t, y = y0 + (y1 - y0) * t + Math.sin(t * Math.PI * 2) * 4, s = 4 + r() * 3;
      f += `M${x.toFixed(1)} ${(y - 1).toFixed(1)} c${-s} ${-s * 1.2} ${-s * .4} ${-s * 2} 0 ${-s * 1.1} c${s * .4} ${-s * .9} ${s} ${-s * .1} 0 ${s * 1.1} Z `;
      if (i % 3 === 1 && !P.nuit) fl += `<g transform="translate(${(x + 6).toFixed(1)} ${(y - 2).toFixed(1)})"><path d="M0 0 l-4 -6 q4 -3 8 0 Z" fill="#c95aa8"/><ellipse cx="0" cy="-6" rx="4.6" ry="1.8" fill="#e27cc4"/><circle cx="0" cy="-6" r="1" fill="#fff4c0"/></g>`;
    }
    return `<path d="${tige}" stroke="${P.nuit ? "#3a3a2a" : "#7c6a3a"}" stroke-width="1.4" fill="none"/><path d="${f}" fill="${P.nuit ? "#2f4632" : "#5f9a3e"}" stroke="${P.nuit ? "#243626" : "#3f7a2c"}" stroke-width=".6"/>${fl}`;
  }

  // décor au sol selon la saison
  function solSaison(P) {
    const n = P.nuit;
    if (P.sa === "printemps") {
      // buisson d'hibiscus : feuilles ovales dentées, fleurs rouges et roses
      const r = N.alea(41);
      let fe = "", fe2 = "";
      for (let i = 0; i < 90; i++) {
        const a = r() * Math.PI, d = 8 + r() * 36, x = 172 + Math.cos(a) * d * 1.35, y = 430 - Math.sin(a) * d * .95, ang = r() * Math.PI * 2;
        const ux = Math.cos(ang) * 7, uy = Math.sin(ang) * 4.2, vx = -Math.sin(ang) * 3, vy = Math.cos(ang) * 2;
        { const _s = `M${(x - ux).toFixed(1)} ${(y - uy).toFixed(1)} Q${(x + vx).toFixed(1)} ${(y + vy).toFixed(1)} ${(x + ux).toFixed(1)} ${(y + uy).toFixed(1)} Q${(x - vx).toFixed(1)} ${(y - vy).toFixed(1)} ${(x - ux).toFixed(1)} ${(y - uy).toFixed(1)} Z `; if (i % 3) fe += _s; else fe2 += _s; }
      }
      const fleurs = [[150, 404, "#e2364f"], [178, 394, "#f05a78"], [200, 410, "#e2364f"], [160, 422, "#f05a78"], [192, 426, "#e2364f"]].map(([x, y, k]) =>
        `<g transform="translate(${x} ${y})">${[0, 72, 144, 216, 288].map(a => `<path d="M0 0 C-4 -2 -4 -8 0 -9 C4 -8 4 -2 0 0 Z" transform="rotate(${a})" fill="${n ? "#6a2a3a" : k}"/>`).join("")}
          <circle r="1.8" fill="${n ? "#4a1a26" : "#8d1028"}"/><path d="M0 0 l6 -5" stroke="#f3c94a" stroke-width="1.2"/></g>`).join("");
      return `<g><ellipse cx="172" cy="436" rx="56" ry="9" fill="#3b2a12" opacity=".15"/>
        <path d="M130 438 C128 414 146 396 172 396 C198 396 216 414 214 438 Z" fill="${n ? "#1f3a26" : "#2a5f2e"}"/>
        <path d="${fe2}" fill="${n ? "#233f2a" : "#3c7d3a"}"/><path d="${fe}" fill="${n ? "#2c4c32" : "#55984a"}"/>${fleurs}</g>`;
    }
    if (P.sa === "ete") return `<g>${[[612, 470, 1, 12], [372, 476, .72, -20]].map(([x, y, k, a]) => `<g transform="translate(${x} ${y}) rotate(${a}) scale(${k} .55)">
      <path d="M0 -15 C2 -6 4 -5 14 -5 C6 0 6 3 9 13 C2 7 -2 7 -9 13 C-6 3 -6 0 -14 -5 C-4 -5 -2 -6 0 -15 Z" fill="${n ? "#6a3a2a" : "#e0703a"}" stroke="${n ? "#4a2a1e" : "#b54d20"}" stroke-width="1.4" stroke-linejoin="round"/>
      ${[[0, -9], [7, -4], [4, 6], [-4, 6], [-7, -4], [0, -3], [3, 1], [-3, 1]].map(([u, v]) => `<circle cx="${u}" cy="${v}" r="1.2" fill="${n ? "#7a4a36" : "#f7b37a"}"/>`).join("")}</g>`).join("")}</g>`;
    if (P.sa === "automne") return `<g>${N.coco("phbd-c1", 298, 428, 9)}${N.coco("phbd-c2", 318, 434, 8)}
      <path d="M492 462 c10 -6 18 -2 24 -6 c8 -5 16 1 26 -3 c8 -3 14 2 22 0" stroke="${n ? "#4a3a22" : "#9a6a2a"}" stroke-width="5" fill="none" stroke-linecap="round" opacity=".8"/>
      ${[[500, 458], [518, 452], [536, 455], [556, 451], [572, 456]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.4" fill="${n ? "#4f4024" : "#b8842c"}"/>`).join("")}</g>`;
    return `<g><path d="M516 474 c18 -4 40 -10 66 -9 c4 0 6 3 2 4 c-22 1 -44 6 -66 10 c-4 .6 -6 -3 -2 -5 Z" fill="${n ? "#4a4642" : "#a89c8c"}"/>
      <path d="M540 467 c10 -6 18 -12 30 -14" stroke="${n ? "#3a3632" : "#8d8172"}" stroke-width="4" fill="none" stroke-linecap="round"/>
      <path d="M526 471 c16 -3 34 -7 52 -8" stroke="${n ? "#5a5650" : "#cdc2b2"}" stroke-width="1.2" fill="none" opacity=".7"/></g>`;
  }

  function decor(e) {
    const P = palette(e), { ph, met, nuit } = P;
    const S = astrePos(e);
    const deco = new Set(e.deco || []);
    const lumiere = e.lumiere, lampe = e.lampe.possede, lampeOn = e.lampe.possede && e.lampe.allumee;
    const jourSec = !nuit && met !== "pluie";
    const decembre = new Date().getMonth() === 11;
    const ombres = jourSec && met !== "nuages";                  // ombres portées nettes seulement au soleil
    const sens = S.x < 450 ? 1 : -1, long = 40 + 140 * (1 - S.haut);
    const lumD = S.x > 500 ? 1 : -1;
    const lune = phaseLune(), luneVisible = nuit && (1 - Math.cos(2 * Math.PI * lune)) / 2 > .25;
    const scintille = met !== "pluie" && (!nuit || luneVisible);
    const r = N.alea(17);
    // nuages : plus petits et plus plats vers l'horizon (perspective)
    const nbNuages = met === "pluie" ? 7 : met === "nuages" ? 6 : 3;
    const cn = met === "pluie" ? COUL_NUAGE.pluie : nuit ? COUL_NUAGE.nuit : ph === "jour" ? (met === "nuages" ? COUL_NUAGE.nuages : COUL_NUAGE.jour) : COUL_NUAGE.rose;
    const nuages = Array.from({ length: nbNuages }, (_, i) => {
      const top = 9 + (i * 37) % 27, larg = 13 + (36 - top) * .5 + (i * 7) % 6;
      return `<div class="phb-nuage" style="top:${top}%;--d:${80 + i * 27}s;--r:-${(i * 41) % 80}s;width:${larg.toFixed(1)}%;opacity:${nuit ? .7 : .96}">${N.nuage("phbd-n" + i, 101 + i * 13, { ...cn, plat: top > 22 })}</div>`;
    }).join("");
    // mer : texture de vagues en perspective (plus serrées et plus fines vers l'horizon)
    let crete = "", creux = "";
    for (let y = 255, k = 0; y < 500; k++, y += 3 + k * .55) {
      const ep = .5 + k * .07, len = 7 + k * 2.3;
      for (let x = -20 + r() * 30; x < 1000; x += len * (1.3 + r() * 1.7)) {
        crete += `M${x.toFixed(0)} ${y.toFixed(1)} q${(len / 2).toFixed(1)} ${(-ep * 1.3).toFixed(1)} ${len.toFixed(1)} 0 `;
        if (r() < .55) creux += `M${(x + len * .25).toFixed(0)} ${(y + ep * 1.7).toFixed(1)} h${(len * .75).toFixed(1)} `;
      }
    }
    let crete2 = "";
    for (let y = 257, k = 0; y < 500; k++, y += 3.4 + k * .6) {
      const ep = .5 + k * .07, len = 6 + k * 2;
      for (let x = r() * 60; x < 1000; x += len * (2 + r() * 2.4)) crete2 += `M${x.toFixed(0)} ${y.toFixed(1)} q${(len / 2).toFixed(1)} ${(-ep * 1.2).toFixed(1)} ${len.toFixed(1)} 0 `;
    }
    // reflets du soleil (ou de la lune) sur l'eau : une colonne de scintillements sous l'astre, plus large près de nous
    let glit = "";
    if (scintille) for (let i = 0; i < 110; i++) {
      const v = Math.pow(r(), 1.3), y = 254 + v * 236, l = 14 + v * 120, x = S.x + (r() - .5) * 2 * l * (.25 + r() * .75), w = 2 + v * 12 * r();
      glit += `M${x.toFixed(0)} ${y.toFixed(1)} h${w.toFixed(1)} `;
    }
    const coulGlit = nuit ? "#e2e8ff" : ph === "jour" ? "#fffbea" : "#ffd59a";
    const reflets = scintille ? `<div class="phb-l phb-reflets" aria-hidden="true">${Array.from({ length: 16 }, (_, i) => {
      const v = ((i * 37) % 100) / 100, x = S.x / 10 + ((i * 53) % 100 - 50) / 50 * (2 + v * 11);
      return `<i style="left:${x.toFixed(1)}%;top:${(51.5 + v * 45).toFixed(1)}%;animation-delay:-${(i * .7) % 3.4}s;${nuit ? "background:#e2e8ff;" : ""}"></i>`;
    }).join("")}</div>` : "";
    const grain = (() => {   // grains de sable (motif)
      const g = N.alea(5); let a = "", b = "";
      for (let i = 0; i < 14; i++) { const x = (g() * 23).toFixed(1), y = (g() * 17).toFixed(1); { const _s = `M${x} ${y} h.9 `; if (i % 2) a += _s; else b += _s; } }
      return `<pattern id="phbd-grain" width="23" height="17" patternUnits="userSpaceOnUse"><path d="${a}" stroke="#7a5f34" stroke-opacity=".28" stroke-width="1"/><path d="${b}" stroke="#fff" stroke-opacity=".35" stroke-width="1"/></pattern>`;
    })();
    const solFonce = melange(P.sable[2], P.lagon[2], .35);
    const ombre = (cx, cy, rx, ry, op = .2) => `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" fill="#3b2a12" opacity="${op}" filter="url(#phbd-flou)"/>`;
    const portee = (x, y, l, w, op = .2) => ombres ? `<path d="M${x - w} ${y} L${x + sens * l - w} ${y + 16} L${x + sens * l + w} ${y + 19} L${x + w} ${y + 2} Z" fill="#3b2a12" opacity="${op}" filter="url(#phbd-flou)"/>` : "";
    const bois = `<linearGradient id="phbd-bois" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${nuit ? "#2e241c" : "#6b4a2a"}"/><stop offset=".45" stop-color="${nuit ? "#4a3a2c" : "#a87a4a"}"/><stop offset="1" stop-color="${nuit ? "#2a2018" : "#5a3d22"}"/></linearGradient>`;
    const lanterneOn = lumiere;
    return `
      <div class="phb-l phb-l-ciel" style="background:linear-gradient(${P.c[0]}, ${P.c[1]} 29%, ${P.c[2]} 48.5%, ${P.c[2]} 51%)"></div>
      ${nuit && met !== "pluie" ? etoiles() : ""}${met === "pluie" ? "" : astre(e, P, S)}
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        ${met === "arc" ? `<defs><radialGradient id="phbd-arc" cx="500" cy="560" r="520" gradientUnits="userSpaceOnUse">
          <stop offset=".78" stop-color="#9b6bff" stop-opacity="0"/><stop offset=".8" stop-color="#8a5cff" stop-opacity=".35"/><stop offset=".83" stop-color="#4a8dff" stop-opacity=".4"/>
          <stop offset=".86" stop-color="#4fd06a" stop-opacity=".4"/><stop offset=".89" stop-color="#ffe45a" stop-opacity=".45"/><stop offset=".915" stop-color="#ff9a3a" stop-opacity=".42"/>
          <stop offset=".94" stop-color="#ff4a3a" stop-opacity=".38"/><stop offset=".97" stop-color="#ff4a3a" stop-opacity="0"/></radialGradient></defs>
          <rect x="0" y="0" width="1000" height="252" fill="url(#phbd-arc)"/>` : ""}
        <g>
          <path d="M758 253 C786 238 816 231 842 232 C868 233 892 242 910 253 Z" fill="${melange(nuit ? "#1f3a2e" : ph === "coucher" ? "#343a30" : "#5f8a4a", P.c[2], ph === "coucher" ? .25 : .45)}"/>
          <path d="M766 253 C800 249 868 249 904 253 Z" fill="${melange(P.sable[1], P.c[2], .45)}"/>
          <g opacity=".8">${N.cocotierLoin(784, 247, 22, [melange(nuit ? "#1f3a2e" : ph === "coucher" ? "#2e3428" : "#4f7a3c", P.c[2], .4), melange(nuit ? "#2a2420" : ph === "coucher" ? "#2a2420" : "#6f5a44", P.c[2], .4)], -.15)}
            ${N.cocotierLoin(800, 244, 26, [melange(nuit ? "#1f3a2e" : ph === "coucher" ? "#2e3428" : "#4f7a3c", P.c[2], .4), melange(nuit ? "#2a2420" : ph === "coucher" ? "#2a2420" : "#6f5a44", P.c[2], .4)], .1)}
            ${N.cocotierLoin(880, 247, 20, [melange(nuit ? "#1f3a2e" : ph === "coucher" ? "#2e3428" : "#4f7a3c", P.c[2], .4), melange(nuit ? "#2a2420" : ph === "coucher" ? "#2a2420" : "#6f5a44", P.c[2], .4)], .18)}</g>
          <rect x="836" y="236" width="16" height="11" fill="${melange(nuit ? "#3b3326" : "#efe2c4", P.c[2], .35)}"/><path d="M832 237 L844 228 L856 237 Z" fill="${melange(nuit ? "#3a2420" : "#b5523c", P.c[2], .35)}"/>
          ${nuit ? `<rect x="840" y="239.5" width="4" height="4" fill="#ffd27a"/><circle cx="842" cy="241.5" r="7" fill="#ffd27a" opacity=".2"/>` : `<rect x="840" y="239.5" width="4" height="4" fill="${melange("#4a3a2a", P.c[2], .35)}"/>`}
        </g>
      </svg>
      <div class="phb-l phb-nuages" aria-hidden="true">${nuages}</div>
      ${jourSec ? `<div class="phb-l phb-mouettes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-mouette" style="top:${22 + i * 8}%;--d:${30 + i * 9}s;--r:-${i * 11}s">${N.goeland()}</div>`).join("")}
        <div class="phb-mouette plane" style="top:17%;--d:70s;--r:-20s">${N.fregate()}</div></div>` : ""}
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="phbd-mer" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${melange(P.mer[0], P.c[2], .35)}"/><stop offset=".08" stop-color="${P.mer[0]}"/><stop offset="1" stop-color="${P.mer[1]}"/></linearGradient>
          <radialGradient id="phbd-lagon" cx=".5" cy=".5" r=".5"><stop offset=".62" stop-color="${P.lagon[0]}"/><stop offset=".74" stop-color="${P.lagon[1]}"/>
            <stop offset=".84" stop-color="${P.lagon[2]}" stop-opacity=".8"/><stop offset=".93" stop-color="${P.lagon[2]}" stop-opacity=".3"/><stop offset="1" stop-color="${P.lagon[2]}" stop-opacity="0"/></radialGradient>
          <filter id="phbd-caus" x="0" y="0" width="100%" height="100%"><feTurbulence type="turbulence" baseFrequency=".022 .07" numOctaves="2" seed="7" result="t"/>
            <feColorMatrix in="t" type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  -7 0 0 0 1.55"/><feComposite in2="SourceGraphic" operator="in"/></filter></defs>
        <rect x="0" y="250" width="1000" height="250" fill="url(#phbd-mer)"/>
        <path d="${creux}" stroke="${P.mer[1]}" stroke-opacity=".35" stroke-width="1.2"/>
        <path d="${crete}" stroke="#fff" stroke-opacity="${nuit ? .07 : .16}" stroke-width=".9" fill="none"/>
        <path d="${glit}" stroke="${coulGlit}" stroke-opacity="${nuit ? .45 : .75}" stroke-width="1.6" stroke-linecap="round"/>
        <ellipse cx="500" cy="522" rx="490" ry="200" fill="url(#phbd-lagon)"/>
        ${nuit ? "" : `<ellipse cx="500" cy="522" rx="470" ry="186" fill="#fff" opacity="${met === "pluie" ? .1 : .2}" filter="url(#phbd-caus)"/>`}
        <g fill="${P.lagon[2]}" opacity=".35"><ellipse cx="92" cy="420" rx="26" ry="6"/><ellipse cx="60" cy="455" rx="34" ry="8"/><ellipse cx="930" cy="430" rx="30" ry="7"/><ellipse cx="955" cy="470" rx="22" ry="6"/></g>
        <path d="M0 251 H1000" stroke="${P.c[2]}" stroke-opacity=".7" stroke-width="2"/>
      </svg>
      ${reflets}
      <svg class="phb-l phb-miroite" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true"><path d="${crete2}" stroke="#fff" stroke-opacity="${nuit ? .1 : .26}" stroke-width="1" fill="none"/></svg>
      <svg class="phb-l phb-ecume" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <path d="${ILE}" ${autour(1.028, 1.085)} fill="#effcf8" opacity=".35"/>
        <path d="${ecume(1.026, 1.08, 1, 150)}" fill="#fff" opacity="${nuit ? .5 : .9}"/>
        <path d="${ecume(1.05, 1.16, .6, 90)}" fill="#fff" opacity="${nuit ? .25 : .5}"/>
      </svg>
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="phbd-sable" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${P.sable[0]}"/><stop offset=".55" stop-color="${P.sable[1]}"/><stop offset="1" stop-color="${P.sable[2]}"/></linearGradient>
          <radialGradient id="phbd-dune"><stop offset="0" stop-color="#fff" stop-opacity="${nuit ? .08 : .38}"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
          <linearGradient id="phbd-flaque" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${nuit ? "#3a5a78" : melange(P.c[2], "#ffffff", .2)}"/><stop offset=".5" stop-color="${P.lagon[1]}"/><stop offset="1" stop-color="${P.lagon[2]}"/></linearGradient>
          <radialGradient id="phbd-cail" cx=".38" cy=".3" r=".75"><stop offset="0" stop-color="${P.rocher[0]}"/><stop offset="1" stop-color="${P.rocher[2]}"/></radialGradient>
          <radialGradient id="phbd-halo"><stop offset="0" stop-color="#ffd27a" stop-opacity=".55"/><stop offset="1" stop-color="#ffd27a" stop-opacity="0"/></radialGradient>
          <radialGradient id="phbd-feu"><stop offset="0" stop-color="#ffb070" stop-opacity=".5"/><stop offset="1" stop-color="#ff7a2a" stop-opacity="0"/></radialGradient>
          ${bois}${grain}
          <filter id="phbd-flou" x="-30%" y="-60%" width="160%" height="220%"><feGaussianBlur stdDeviation="3"/></filter></defs>
        <path d="${ILE}" ${autour(1.014, 1.04)} fill="${solFonce}"/>
        <path d="${ILE}" ${autour(1.014, 1.04)} fill="#fff" opacity="${nuit ? .04 : .12}"/>
        <path d="${ILE}" fill="url(#phbd-sable)"/>
        <path d="${ILE}" fill="url(#phbd-grain)"/>
        <ellipse cx="470" cy="372" rx="300" ry="30" fill="url(#phbd-dune)"/>
        <path d="M150 470 C200 418 330 384 500 378 C640 376 760 396 846 452" stroke="#fff" stroke-opacity="${nuit ? .03 : .1}" stroke-width="14" fill="none"/>
        <path d="M150 478 C160 452 200 418 260 398 M760 404 C810 424 840 448 856 480" stroke="${nuit ? "#2f2a20" : "#7f6a3c"}" stroke-width="2.6" stroke-dasharray="7 15 3 22 10 30 4 12" fill="none" opacity=".45" stroke-linecap="round"/>
        <path d="M205 468 q18 -5 36 0 M560 478 q22 -5 44 0 M700 454 q15 -4 30 0 M330 448 q13 -4 26 0 M470 470 q12 -3 24 0" stroke="#000" stroke-opacity=".06" stroke-width="3" fill="none" stroke-linecap="round"/>
        ${[[238, 474, "#f2d3c0"], [452, 486, "#fff"], [668, 488, "#e9d2b0"], [790, 470, "#f5e6d6"], [380, 470, "#d8c8b6"]].map(([x, y, k], i) => i % 2
          ? `<ellipse cx="${x}" cy="${y}" rx="3.4" ry="2.2" fill="${nuit ? "#6a6458" : k}" stroke="#a89880" stroke-width=".6"/>`
          : `<path d="M${x - 4} ${y + 1} C${x - 4} ${y - 4} ${x + 4} ${y - 4} ${x + 4} ${y + 1} Z" fill="${nuit ? "#6a6458" : k}" stroke="#b39880" stroke-width=".6"/>`).join("")}
        ${herbes(P, 176, 380, 16, 3)}${herbes(P, 806, 392, 14, 9)}${herbes(P, 742, 378, 9, 21)}
        ${liseron(P, 640, 384, 760, 396, 4)}${liseron(P, 108, 470, 190, 432, 8)}
        <g>
          <ellipse cx="${420}" cy="${441}" rx="${P.sa === "automne" ? 82 : 70}" ry="${P.sa === "automne" ? 19 : 17}" fill="${solFonce}" opacity=".7"/>
          <path d="M${P.sa === "automne" ? "340 442 C342 428 384 422 420 422 C458 422 500 428 500 442 C500 456 458 460 420 460 C382 460 338 456 340 442 Z" : "354 441 C356 429 390 424 420 424 C452 424 486 429 486 441 C486 453 452 457 420 457 C388 457 352 453 354 441 Z"}" fill="url(#phbd-flaque)"/>
          <path d="M372 433 q30 -6 70 -2" stroke="#fff" stroke-width="3" opacity="${nuit ? .12 : .45}" fill="none" stroke-linecap="round"/>
          <path d="M392 446 q16 -2 32 0 M440 450 q12 -2 22 0" stroke="#fff" stroke-width="1.2" opacity="${nuit ? .1 : .3}" fill="none" stroke-linecap="round"/>
          ${[[356, 444, 7, 4.6], [368, 454, 5, 3.4], [478, 448, 8, 5], [490, 438, 5.4, 3.6], [430, 459, 6, 3.4], [396, 424, 5, 3]].map(([x, y, rx, ry]) =>
            `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="url(#phbd-cail)"/><ellipse cx="${x - rx * .3}" cy="${y - ry * .35}" rx="${rx * .35}" ry="${ry * .25}" fill="#fff" opacity="${nuit ? .1 : .35}"/>`).join("")}
        </g>
        ${ombre(652, 414, 70, 7, .3)}${portee(652, 408, long * .55, 26, .22)}
        ${N.rocher("phbd-ro", 588, 413, 124, 55, { lum: lumD, coul: P.rocher })}
        ${[[580, 414, 6, 4], [722, 413, 7, 4.4], [732, 418, 4, 2.6]].map(([x, y, rx, ry]) => `<ellipse cx="${x}" cy="${y}" rx="${rx}" ry="${ry}" fill="url(#phbd-cail)"/>`).join("")}
        ${solSaison(P)}
        ${ombre(262, 426, 34, 6, .22)}${portee(262, 424, long * 1.15, 6, .2)}
        ${ombres ? `<ellipse cx="${262 + sens * long * 1.3}" cy="452" rx="74" ry="12" fill="#3b2a12" opacity=".14" filter="url(#phbd-flou)"/>` : ""}
        ${N.stipe({ id: "phbd", base: [262, 426], c1: [258, 362], c2: [246, 292], cime: [222, 200], w0: 23, w1: 12, lum: lumD, coul: P.stipe, clair: nuit ? "#7a7068" : "#e8d6b6" })}
        ${portee(330, 432, long * .7, 3, .2)}
        <rect x="326.5" y="362" width="7" height="72" rx="2" fill="url(#phbd-bois)"/>
        <path d="M327.5 374 v52 M331.5 368 v58" stroke="#000" stroke-opacity=".15" stroke-width=".8"/>
        <path d="M330 362 v-6" stroke="#2e2a26" stroke-width="1.6"/>
        <g>${lanterneOn && nuit ? `<ellipse cx="330" cy="436" rx="90" ry="16" fill="url(#phbd-halo)"/><circle cx="330" cy="364" r="70" fill="url(#phbd-halo)"/>` : lanterneOn ? `<circle cx="330" cy="364" r="20" fill="url(#phbd-halo)"/>` : ""}
          <path d="M321 352 L339 352 L336 346 L324 346 Z" fill="#2e2a26"/><rect x="322" y="352" width="16" height="20" rx="1.5" fill="${lanterneOn ? "#ffd98a" : nuit ? "#2a2a30" : "#5a5f63"}"/>
          ${lanterneOn ? `<ellipse cx="330" cy="363" rx="3" ry="5" fill="#fff8de"/><ellipse cx="330" cy="364" rx="6" ry="7" fill="#ffb347" opacity=".45"/>` : `<path d="M324.5 354 l3 0 l-1.4 15 l-2 0 Z" fill="#fff" opacity=".2"/>`}
          <path d="M322 352 h16 M322 372 h16 M326 352 v20 M334 352 v20" stroke="#2e2a26" stroke-width="1.3"/><path d="M321 372 L339 372 L337 376 L323 376 Z" fill="#2e2a26"/></g>
        ${lampe ? `<g>${portee(178, 432, long * .9, 3, .18)}
          <path d="M178 432 V262 Q178 248 194 244" stroke="${nuit ? "#3d4248" : "#8d959c"}" stroke-width="4.5" fill="none" stroke-linecap="round"/>
          <path d="M178 432 V262" stroke="#fff" stroke-opacity=".25" stroke-width="1.2"/><ellipse cx="178" cy="433" rx="14" ry="3.6" fill="${nuit ? "#2b2f33" : "#5f666c"}"/>
          <path d="M186 236 C192 226 208 222 214 230 L206 256 C198 254 188 246 186 236 Z" fill="${nuit ? "#4a4f55" : "#b9c0c6"}" stroke="${nuit ? "#2a2e32" : "#6d757c"}" stroke-width="1.5"/>
          <path d="M190 236 C196 229 206 227 210 232" stroke="#fff" stroke-opacity=".5" stroke-width="1.6" fill="none"/>
          ${lampeOn ? `<ellipse cx="206" cy="246" rx="5.6" ry="7" fill="#ff7a2a" transform="rotate(-20 206 246)"/><ellipse cx="206" cy="246" rx="3" ry="4" fill="#ffd2a0" transform="rotate(-20 206 246)"/>
            <path d="M206 236 L254 196 L240 238 Z" fill="url(#phbd-feu)"/><circle cx="214" cy="232" r="40" fill="url(#phbd-feu)"/>` : `<ellipse cx="206" cy="246" rx="5" ry="6.4" fill="#3a3330" transform="rotate(-20 206 246)"/>`}</g>` : ""}
        ${deco.has("hamac") ? `<g>${ombre(296, 438, 46, 6, .16)}<rect x="339" y="298" width="6" height="134" rx="2" fill="url(#phbd-bois)"/>
          <defs><linearGradient id="phbd-hamac" x1="0" y1="0" x2="1" y2="0">${["#d9653a", "#f1c27a", "#3f8aa8", "#f6ead2", "#d9653a", "#f1c27a", "#3f8aa8", "#f6ead2"].map((k, i) => `<stop offset="${i / 8}" stop-color="${k}"/><stop offset="${(i + 1) / 8}" stop-color="${k}"/>`).join("")}</linearGradient></defs>
          <path d="M252 300 l12 6 M252 300 l11 10 M342 302 l-12 5 M342 302 l-11 9" stroke="#e8dcc0" stroke-width="1.2"/>
          <path d="M262 306 C276 344 316 346 330 308 C320 352 272 352 262 306 Z" fill="url(#phbd-hamac)" opacity="${nuit ? .55 : 1}"/>
          <path d="M262 306 C276 344 316 346 330 308" stroke="#000" stroke-opacity=".18" stroke-width="2" fill="none"/>
          <path d="M268 330 C282 348 310 348 324 330" stroke="#000" stroke-opacity=".15" stroke-width="5" fill="none"/></g>` : ""}
        ${deco.has("parasol") ? `<g>${ombres ? `<ellipse cx="${470 + sens * long * .5}" cy="444" rx="56" ry="9" fill="#3b2a12" opacity=".2" filter="url(#phbd-flou)"/>` : ombre(470, 440, 40, 5, .12)}
          <path d="M470 440 V322" stroke="${nuit ? "#4a4440" : "#d9d2c6"}" stroke-width="3"/>
          ${Array.from({ length: 8 }, (_, i) => { const x0 = 410 + i * 15, x1 = x0 + 15; return `<path d="M470 316 L${x0} 352 Q${(x0 + x1) / 2} 358 ${x1} 352 Z" fill="${i % 2 ? (nuit ? "#5a5654" : "#f6f1e6") : (nuit ? "#5a2a2a" : "#d9434a")}"/>`; }).join("")}
          <path d="M410 352 C430 340 450 332 470 316 C490 332 510 340 530 352" fill="none" stroke="#000" stroke-opacity=".12" stroke-width="2"/>
          <path d="M470 316 L410 352 Q440 358 470 354 Z" fill="#fff" opacity="${lumD < 0 ? .18 : 0}"/><path d="M470 316 L530 352 Q500 358 470 354 Z" fill="#000" opacity=".14"/>
          <circle cx="470" cy="314" r="2.6" fill="#c9c2b6"/></g>` : ""}
        ${deco.has("chateau") ? `<g>${ombre(572, 472, 34, 4, .16)}
          <defs><linearGradient id="phbd-ch" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${nuit ? "#6a604c" : "#e3c994"}"/><stop offset="1" stop-color="${nuit ? "#4d4538" : "#b9995e"}"/></linearGradient></defs>
          <path d="M546 472 V448 h3 v-3 h3 v3 h3 v-3 h3 v3 h2 V472 Z M584 472 V448 h3 v-3 h3 v3 h3 v-3 h3 v3 h2 V472 Z" fill="url(#phbd-ch)"/>
          <path d="M558 472 V440 h3 v-4 h3 v4 h3 v-4 h3 v4 h3 v-4 h3 v4 h3 V472 Z" fill="url(#phbd-ch)"/>
          <path d="M567 472 v-8 q4 -5 8 0 v8 Z" fill="${nuit ? "#2e2a22" : "#8a6f42"}"/><rect x="551" y="454" width="3" height="4" fill="${nuit ? "#2e2a22" : "#9a7e50"}"/><rect x="589" y="454" width="3" height="4" fill="${nuit ? "#2e2a22" : "#9a7e50"}"/>
          <path d="M571 436 V418" stroke="#7a5a3a" stroke-width="1.2"/><path d="M571 418 l11 3 l-11 4 Z" fill="#d9434a"/>
          <ellipse cx="572" cy="474" rx="34" ry="3.6" fill="${P.lagon[1]}" opacity=".5"/></g>` : ""}
        ${deco.has("coquillages_deco") ? `<g>${[0, 1, 2, 3].map(i => {
          const x = 692 + i * 26, y = 476;
          return i === 0 ? `<path d="M${x - 9} ${y} C${x - 10} ${y - 12} ${x + 10} ${y - 12} ${x + 9} ${y} Z" fill="${nuit ? "#7a6a64" : "#f4b8a0"}"/><path d="M${x} ${y} L${x} ${y - 10} M${x} ${y} L${x - 5} ${y - 9} M${x} ${y} L${x + 5} ${y - 9} M${x} ${y} L${x - 8} ${y - 5} M${x} ${y} L${x + 8} ${y - 5}" stroke="#c97f68" stroke-width="1"/>`
            : i === 1 ? `<path d="M${x - 8} ${y} C${x - 10} ${y - 8} ${x} ${y - 13} ${x + 8} ${y - 7} C${x + 6} ${y - 2} ${x + 2} ${y + 1} ${x - 8} ${y} Z" fill="${nuit ? "#7a7064" : "#f2dcc0"}" stroke="#b9987a"/><path d="M${x - 2} ${y - 3} q4 -6 8 -4" stroke="#c9a888" fill="none"/>`
              : i === 2 ? `<ellipse cx="${x}" cy="${y - 3.4}" rx="8" ry="5" fill="${nuit ? "#5a4a3a" : "#a06a3a"}"/><ellipse cx="${x - 2}" cy="${y - 5}" rx="4" ry="1.6" fill="#fff" opacity=".4"/>${[[-4, -2], [1, -1.4], [4, -4]].map(([u, v]) => `<circle cx="${x + u}" cy="${y + v}" r="1" fill="#f2dcc0"/>`).join("")}`
                : `<path d="M${x - 7} ${y} C${x - 7} ${y - 9} ${x + 7} ${y - 9} ${x + 7} ${y} Z" fill="${nuit ? "#6a6064" : "#ffd6e0"}" stroke="#d8a0b0"/>`;
        }).join("")}</g>` : ""}
        ${deco.has("bouee") ? `<g><ellipse cx="950" cy="384" rx="34" ry="5" fill="none" stroke="#fff" stroke-opacity=".35" stroke-width="1.5"/><ellipse cx="950" cy="386" rx="46" ry="7" fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="1.2"/>
          <defs><radialGradient id="phbd-bo" cx=".5" cy=".42" r=".55"><stop offset=".5" stop-color="#000" stop-opacity=".3"/><stop offset=".7" stop-color="#000" stop-opacity="0"/><stop offset=".86" stop-color="#fff" stop-opacity=".25"/><stop offset="1" stop-color="#000" stop-opacity=".25"/></radialGradient></defs>
          <path d="M928 372 a22 14 0 1 0 44 0 a22 14 0 1 0 -44 0 Z M940 372 a10 6 0 1 1 20 0 a10 6 0 1 1 -20 0 Z" fill="${nuit ? "#7a3a3a" : "#e5484d"}" fill-rule="evenodd"/>
          <path d="M944 359 l-4 8 M956 359 l4 8 M944 385 l-4 -8 M956 385 l4 -8" stroke="${nuit ? "#9a9590" : "#f6f1ea"}" stroke-width="7"/>
          <path d="M928 372 a22 14 0 1 0 44 0 a22 14 0 1 0 -44 0 Z M940 372 a10 6 0 1 1 20 0 a10 6 0 1 1 -20 0 Z" fill="url(#phbd-bo)" fill-rule="evenodd"/></g>` : ""}
        ${deco.has("tiki") ? `<g>${ombre(404, 392, 18, 3.4, .22)}${portee(404, 390, long * .5, 8, .18)}
          <defs><linearGradient id="phbd-ti" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${nuit ? "#2a1e14" : "#5a3d22"}"/><stop offset=".5" stop-color="${nuit ? "#4a3624" : "#9a6a3a"}"/><stop offset="1" stop-color="${nuit ? "#20160e" : "#4a3018"}"/></linearGradient></defs>
          <path d="M393 392 V354 C393 347 397 344 404 344 C411 344 415 347 415 354 V392 Z" fill="url(#phbd-ti)" stroke="#2a1a0c" stroke-width="1"/>
          <path d="M395.6 358 h5.4 M407 358 h5.4" stroke="#2a1a0c" stroke-width="2.4" stroke-linecap="round"/>
          <ellipse cx="398.6" cy="362.6" rx="3" ry="2.4" fill="${nuit ? "#8a806a" : "#f2e2c0"}"/><ellipse cx="409.4" cy="362.6" rx="3" ry="2.4" fill="${nuit ? "#8a806a" : "#f2e2c0"}"/>
          <circle cx="398.6" cy="362.6" r="1.2" fill="#1a1008"/><circle cx="409.4" cy="362.6" r="1.2" fill="#1a1008"/>
          <path d="M402.4 365.6 l1.6 4.6 l1.6 -4.6" fill="none" stroke="#2a1a0c" stroke-width="1.2"/>
          <rect x="396.6" y="373.4" width="14.8" height="5.6" rx="2" fill="#2a1a0c"/><path d="M398 376.2 h12" stroke="${nuit ? "#8a806a" : "#f2e2c0"}" stroke-width="1.4" stroke-dasharray="1.8 1"/>
          <path d="M393 384 h22 M396 389 h16" stroke="#2a1a0c" stroke-width="1" opacity=".7"/><path d="M396 350 q8 -4 16 0" stroke="#fff" stroke-width="1.2" opacity="${nuit ? .05 : .2}" fill="none"/></g>` : ""}
        ${deco.has("phare") ? `<g><ellipse cx="54" cy="332" rx="34" ry="5" fill="#fff" opacity=".3"/>
          <path d="M26 334 C30 318 44 314 56 315 C70 316 80 322 82 334 Z" fill="${P.rocher[2]}"/><path d="M34 324 C42 318 54 318 62 320" stroke="${P.rocher[0]}" stroke-width="3" fill="none" opacity=".5" stroke-linecap="round"/>
          <defs><linearGradient id="phbd-ph" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${nuit ? "#8a8e94" : "#ffffff"}"/><stop offset="1" stop-color="${nuit ? "#4a4e54" : "#b9bec4"}"/></linearGradient></defs>
          <path d="M45 318 L48 272 H62 L65 318 Z" fill="url(#phbd-ph)" stroke="#6d757c" stroke-width="1"/>
          <path d="M46.6 300 L47.4 288 H62.6 L63.4 300 Z M45.6 314 L46 308 H64 L64.4 314 Z" fill="${nuit ? "#6a2a2a" : "#d9434a"}"/>
          <rect x="47.6" y="262" width="14.8" height="10" rx="1" fill="${nuit ? "#ffe9a0" : "#dfe8ee"}" stroke="#3a3f44" stroke-width="1.2"/>
          <path d="M46 262 L55 254 L64 262 Z" fill="#3a3f44"/><rect x="45.6" y="271.4" width="18.8" height="2" fill="#3a3f44"/>
          ${nuit ? `<path d="M62 267 L170 244 L170 292 Z" fill="#ffe9a0" opacity=".16"/><circle cx="55" cy="267" r="26" fill="url(#phbd-halo)"/>` : `<path d="M50 264 l2 6" stroke="#fff" stroke-width="1.4" opacity=".6"/>`}</g>` : ""}
        ${deco.has("coffre") ? `<g>${ombre(760, 444, 30, 4, .22)}
          <defs><linearGradient id="phbd-cf" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${nuit ? "#4a2e14" : "#9a5e2a"}"/><stop offset="1" stop-color="${nuit ? "#2a1808" : "#5a3010"}"/></linearGradient>
            <linearGradient id="phbd-or" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#fff4b8"/><stop offset=".4" stop-color="#f1c84a"/><stop offset="1" stop-color="#a8741a"/></linearGradient></defs>
          <path d="M738 424 C736 410 744 404 760 404 C776 404 784 410 782 424 Z" fill="url(#phbd-cf)" stroke="#3a1e08" stroke-width="1" transform="rotate(-18 738 424)"/>
          <rect x="738" y="424" width="44" height="20" rx="2" fill="url(#phbd-cf)" stroke="#3a1e08" stroke-width="1"/>
          ${[[744, 423], [750, 421], [756, 422], [762, 420], [768, 422], [774, 421], [753, 418], [765, 417]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3.2" fill="url(#phbd-or)" stroke="#8a5a12" stroke-width=".6"/>`).join("")}
          <path d="M738 424 H782 M749 424 V444 M771 424 V444" stroke="url(#phbd-or)" stroke-width="2.4"/><rect x="757" y="428" width="6" height="7" rx="1.2" fill="url(#phbd-or)" stroke="#7a4e10" stroke-width=".6"/>
          <path d="M732 446 C744 440 776 440 788 446 C778 450 742 450 732 446 Z" fill="${P.sable[1]}"/>
          ${nuit ? "" : `<path d="M753 414 l1 -3 l1 3 l3 1 l-3 1 l-1 3 l-1 -3 l-3 -1 Z M770 416 l.7 -2 l.7 2 l2 .7 l-2 .7 l-.7 2 l-.7 -2 l-2 -.7 Z" fill="#fff"/>`}</g>` : ""}
        ${deco.has("benitier") ? `<g><ellipse cx="72" cy="476" rx="40" ry="6" fill="#fff" opacity=".25"/>
          <defs><linearGradient id="phbd-bn" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${nuit ? "#8a8676" : "#f6f2e8"}"/><stop offset="1" stop-color="${nuit ? "#4a4638" : "#a89a7c"}"/></linearGradient>
            <linearGradient id="phbd-mt" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3fb6a8"/><stop offset=".5" stop-color="#2a6fb0"/><stop offset="1" stop-color="#6a3fa0"/></linearGradient>
            <radialGradient id="phbd-pg" cx=".35" cy=".3" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset=".6" stop-color="#f4eef6"/><stop offset="1" stop-color="#c8bcd0"/></radialGradient></defs>
          <path d="M40 470 C41 452 56 444 72 444 C88 444 103 452 104 470 C94 466 84 466 72 468 C60 466 50 466 40 470 Z" fill="url(#phbd-bn)" stroke="#7a6c50" stroke-width="1"/>
          <path d="M46 456 q4 -3 7 2 q4 -5 9 0 q5 -5 10 0 q5 -5 10 0 q5 -5 9 0 q3 -4 7 -2" stroke="#a89878" stroke-width="1.2" fill="none"/>
          <path d="M44 470 C54 467 90 467 100 470 C92 476 52 476 44 470 Z" fill="url(#phbd-mt)" opacity="${nuit ? .5 : .9}"/>
          <circle cx="72" cy="466" r="7" fill="url(#phbd-pg)"/><circle cx="69.6" cy="463.6" r="2" fill="#fff"/>
          ${nuit ? `<circle cx="72" cy="466" r="16" fill="#f4eef6" opacity=".15"/>` : `<path d="M80 458 l1 -3 l1 3 l3 1 l-3 1 l-1 3 l-1 -3 l-3 -1 Z" fill="#fff"/>`}</g>` : ""}
        ${e.veto ? `<g><ellipse cx="822" cy="322" rx="70" ry="6" fill="#fff" opacity=".25"/>
          <path d="M758 300 C780 304 860 304 884 300 L872 320 C846 324 794 324 770 320 Z" fill="${nuit ? "#4a3424" : "#9a6436"}"/><path d="M764 306 h114 M768 313 h106" stroke="#000" stroke-opacity=".2" stroke-width="1.2"/>
          <path d="M758 300 C780 304 860 304 884 300" stroke="${nuit ? "#6a4a32" : "#c48a52"}" stroke-width="2.4" fill="none"/>
          <path d="M804 300 C804 284 820 276 836 278 C850 280 858 290 856 300 Z" fill="${nuit ? "#3c4a2a" : "#6f7d3a"}"/>
          <path d="M812 298 l8 -14 l12 -2 l10 6 l4 10 M820 284 l2 14 M832 282 l2 16 M842 288 l-2 10" stroke="${nuit ? "#2a3420" : "#4a5426"}" stroke-width="1.4" fill="none"/>
          <path d="M854 294 C862 290 868 290 872 294 C872 298 866 300 858 299 Z" fill="${nuit ? "#5a6a3e" : "#9aa868"}"/><circle cx="867" cy="293" r="1" fill="#1a1a1a"/>
          <path d="M860 289 C862 283 870 283 872 288 Z" fill="#fff"/><path d="M866 284 v3.4 M864.3 285.7 h3.4" stroke="#e2464f" stroke-width="1.2"/>
          <path d="M808 299 q-10 2 -14 -2 M850 300 q8 4 14 2" stroke="${nuit ? "#5a6a3e" : "#9aa868"}" stroke-width="3.4" stroke-linecap="round" fill="none"/></g>` : ""}
      </svg>
      <svg class="phb-l phb-palmes${jourSec ? " vent" : ""}" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        ${N.couronne([222, 200], { palmes: P.palmes, sec: P.sec, noix: P.noix }, "phbd-cr")}
      </svg>
      ${decembre ? `<div class="phb-l phb-guirlande${nuit ? " nuit" : ""}" aria-hidden="true">${[[12.2, 37.6], [14.6, 34.6], [17.4, 33.8], [20.2, 35.4], [22.8, 38.6], [25.2, 36.4], [27.8, 33.2], [30.2, 35], [32.8, 40]].map(([x, y], i) =>
        `<i style="left:${x}%;top:${y}%;--k:${["#ff5a5a", "#ffd34d", "#6fe07a", "#5ab4ff"][i % 4]};animation-delay:-${i * .4}s"></i>`).join("")}</div>` : ""}
      ${jourSec && ombres ? `<div class="phb-l phb-chaleur" aria-hidden="true">${[0, 1, 2].map(i => `<i style="left:${61 + i * 3.4}%;animation-delay:-${i * .9}s"></i>`).join("")}</div>` : ""}
      <div class="phb-l phb-crabes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-crabe" style="left:${22 + i * 44}%;top:${85 - i * 4}%;--d:${7 + i * 3}s;--r:-${i * 2}s">${N.crabe("phbd-cb" + i)}</div>`).join("")}</div>
      ${jourSec && (P.sa === "printemps" || P.sa === "ete") ? `<div class="phb-l phb-papillons" aria-hidden="true">${[0, 1].map(i => `<div class="phb-papillon" style="left:${30 + i * 30}%;top:${58 - i * 8}%;--d:${11 + i * 4}s;--r:-${i * 3}s">${N.papillon(i === 1)}</div>`).join("")}</div>` : ""}
      ${nuit && met !== "pluie" && P.sa !== "hiver" ? `<div class="phb-l phb-lucioles" aria-hidden="true">${Array.from({ length: 7 }, (_, i) =>
        `<i style="left:${18 + (i * 37) % 60}%;top:${55 + (i * 13) % 28}%;--d:${5 + i % 3 * 2}s;animation-delay:-${i * 1.1}s"></i>`).join("")}</div>` : ""}
      ${met === "pluie" ? `<div class="phb-l phb-brume" aria-hidden="true"></div><div class="phb-l phb-pluie" aria-hidden="true"><svg viewBox="0 0 1000 1000" preserveAspectRatio="none">${gouttes()}</svg></div>` : ""}
      <div class="phb-l phb-nuit" style="opacity:${nuit ? (lumiere ? .2 : .34) : ph === "coucher" ? .1 : ph === "aube" ? .08 : 0}" aria-hidden="true"></div>
      ${absent() ? `<div class="phb-l phb-pancarte" role="status"><div>${e.veto
        ? `<b>Philibert se repose chez le vétérinaire</b><span>retour dans ${fmtH(e.veto.reste_s)} · la tortue s'occupe bien de lui</span>`
        : `<b>Philibert est en pension chez la voisine</b><span>sur l'île d'à côté, tout est en pause</span><button class="phb-b phb-prim" data-phb="revenir">Le faire revenir</button>`}</div></div>` : ""}`;
  }

  // Position de Philibert sur l'île (en % de la scène : gauche du dessin, bas des pattes)
  function place(e, r) {
    if (r === "bain_mer") return { x: 82, y: 86, pose: "nage" };
    if (r === "bain_flaque") return { x: 34.5, y: 90, pose: "nage" };
    if (e.position === "palmier") return { x: 14.6, y: 43, pose: "dort", rot: -8 };
    if (e.position === "rocher") return { x: 57, y: 75.6, pose: "plat" };
    return { x: flaneX, y: 87, pose: e.dort ? "dort" : "debout" };
  }

  function rendreScene() {
    const sc = dlg.querySelector(".phb-scene");
    if (!sc || !e) return;
    const cle = [e.ciel.phase, e.ciel.meteo, e.ciel.saison, e.lumiere, e.lampe.possede, e.lampe.allumee, (e.deco || []).join(), e.niveau, Math.round(e.ciel.heure * 2),
      e.veto ? Math.round(e.veto.reste_s / 600) : ""].join("|");
    if (cle !== cleScene) {
      sc.querySelector(".phb-decor").innerHTML = decor(e);
      cleScene = cle;
      const P = palette(e);           // bandes de part et d'autre de la scène (écran large) : même ciel et même mer
      sc.parentElement.style.background = `linear-gradient(${P.c[0]}, ${P.c[1]} 29%, ${P.c[2]} 48.5%, ${melange(P.mer[0], P.c[2], .35)} 50%, ${P.mer[0]} 54%, ${P.mer[1]})`;
    }
    const perso = sc.querySelector(".phb-perso");
    perso.hidden = absent();
    sc.querySelector(".phb-crottes").innerHTML = absent() ? "" : Array.from({ length: e.crottes }, (_, i) =>
      `<button class="phb-crotte" style="left:${[44, 58, 39, 66][i]}%;top:${[92, 94, 85, 89][i]}%" data-phb="nettoyer" aria-label="Ramasser la crotte">
       <svg viewBox="0 0 20 16"><ellipse cx="10" cy="14.6" rx="8" ry="1.2" fill="#3b2a12" opacity=".2"/>
       <path d="M2.4 13.6 C1.6 11.4 3.4 9.6 6.4 9.8 C8.6 8.4 11.6 8.6 13 10.2 C14.4 11.6 13.6 14.2 11 14.6 L5 14.8 C3.8 14.8 2.8 14.4 2.4 13.6 Z" fill="#5e4026"/>
       <path d="M4 11.6 C6 10.4 9 10.2 11.4 11" stroke="#7a5634" stroke-width=".8" fill="none"/>
       <path d="M12.6 10.6 C14.2 9 17.6 9.4 18.2 11.6 C18.6 13.4 16.8 14.6 14.6 14.4 C13 14.2 12.2 12.4 12.6 10.6 Z" fill="#f3efe2" stroke="#cfc8b2" stroke-width=".5"/>
       <ellipse cx="15.4" cy="11.4" rx="1.4" ry=".6" fill="#fff"/></svg></button>`).join("");
    if (absent()) return;
    const p = place(e, reaction);
    perso.style.setProperty("--x", p.x);
    perso.style.setProperty("--y", p.y);
    perso.style.setProperty("--rot", (p.rot || 0) + "deg");
    const h = e.humeur === "appel" ? "calme" : e.humeur;
    const html = D.svg({ stade: e.stade, variante: e.variante, humeur: e.dort ? "dort" : reaction === "refus" ? "grognon" : h, pose: p.pose,
      portes: e.portes, mue: e.mue, ventre: e.ventre_rond, malade: !!e.malade, froid: e.jauges.chaleur < 35, label: e.titre, fendu: e.stade === "oeuf" && e.age_jours > .004, uid: "i" });
    const box = perso.querySelector(".phb-flip");
    if (box.dataset.html !== html) { box.innerHTML = html; box.dataset.html = html; }
    perso.classList.toggle("plat", p.pose === "plat");
    perso.classList.toggle("nage", p.pose === "nage");
    perso.classList.toggle("dort", p.pose === "dort");
    perso.classList.toggle("malade", !!e.malade);
    perso.classList.toggle("froid", e.jauges.chaleur < 35 && !e.malade);
  }

  // ---- petits effets (cœurs, gouttes, miettes, étoiles, coquillages) qui partent de sa tête ----
  function effet(type, n = 6) {
    if (reduit() || document.body.classList.contains("gamemode") || !e || absent()) return;
    const box = dlg.querySelector(".phb-effets");
    if (!box) return;
    const p = place(e, reaction), g = dlg.querySelector(".phb-perso").classList.contains("gauche");
    const x = p.x + (g ? 3 : 14), y = p.y - 12;
    const F = { coeur: ico("coeur"), etoile: ico("etoile"), goutte: ico("goutte"), coquillage: icone("coquillage"), miette: "", note: ico("bulle") };
    for (let i = 0; i < n; i++) {
      const s = document.createElement("span");
      s.className = "phb-fx phb-fx-" + type;
      s.innerHTML = F[type] || "";
      const a = (i / n) * Math.PI * 2;
      s.style.left = x + "%"; s.style.top = y + "%";
      s.style.setProperty("--dx", (type === "coeur" || type === "etoile" ? (Math.random() - .5) * 60 : Math.cos(a) * (24 + Math.random() * 20)).toFixed(0) + "px");
      s.style.setProperty("--dy", (type === "miette" ? 18 + Math.random() * 14 : type === "goutte" ? -20 - Math.random() * 30 : -40 - Math.random() * 40).toFixed(0) + "px");
      s.style.animationDelay = (i * .06).toFixed(2) + "s";
      box.appendChild(s);
      setTimeout(() => s.remove(), 1900);
    }
  }
  function effetAliment(id) {
    if (reduit() || !e || absent()) return;
    const box = dlg.querySelector(".phb-effets");
    const p = place(e, ""), g = dlg.querySelector(".phb-perso").classList.contains("gauche");
    const s = document.createElement("span");
    s.className = "phb-fx phb-fx-aliment";
    s.innerHTML = icone(id);
    s.style.left = (p.x + (g ? 1 : 16)) + "%"; s.style.top = (p.y - 24) + "%";
    box.appendChild(s);
    setTimeout(() => s.remove(), 1200);
  }

  // Petite flânerie sur la plage pendant que la fenêtre est ouverte (rien quand l'onglet est caché / mode jeu)
  function flaner() {
    clearTimeout(flanerT);
    if (!dlg.open) return;
    flanerT = setTimeout(flaner, 4000 + Math.random() * 5000);
    if (!e || document.hidden || document.body.classList.contains("gamemode") || reduit()) return;
    if (e.position !== "plage" || e.dort || e.stade === "oeuf" || reaction || feuille === "jeu" || absent()) return;
    const perso = dlg.querySelector(".phb-perso");
    const r = Math.random();
    if (r < .5) {
      const lent = e.malade || e.jauges.chaleur < 35;
      const cible = 38 + Math.random() * 26, duree = Math.abs(cible - flaneX) * (lent ? .7 : .42);   // ≈ rythme des pattes
      // demi-tour d'abord s'il change de sens (0,3 s), puis il part dans la direction où il regarde
      const tourne = perso.classList.contains("gauche") !== (cible < flaneX);
      perso.classList.toggle("gauche", cible < flaneX);
      const partir = () => {
        perso.classList.add("marche");
        perso.style.transitionDuration = duree.toFixed(1) + "s";
        flaneX = cible;
        rendreScene();
        setTimeout(() => { perso.classList.remove("marche"); perso.style.transitionDuration = ""; }, duree * 1000 + 100);
      };
      if (tourne) setTimeout(partir, 340); else partir();
    } else if (r < .7) anim("hoche", 1500);
    else if (r < .85) anim("fanon", 1400);
    else anim("regarde", 1600);
  }
  function anim(c, ms) {
    const p = dlg.querySelector(".phb-perso");
    if (!p) return;
    p.classList.add(c);
    setTimeout(() => p.classList.remove(c), ms);
  }

  // ---- en-tête, jauges, paroles, soins ----
  function medaillon(e) {
    return `<span class="phb-medaillon" aria-hidden="true">${e.stade === "oeuf" ? D.svg({ stade: "oeuf", uid: "m" })
      : D.svg({ stade: e.stade, variante: e.variante, humeur: e.dort ? "dort" : "joyeux", portes: e.portes, malade: !!e.malade, label: "", uid: "m", leger: true })}</span>`;
  }
  function tete() {
    const met = e.ciel.phase === "nuit" ? (e.ciel.meteo === "pluie" ? "pluie" : e.ciel.meteo === "nuages" ? "nuage" : "lune") : ICO_METEO[e.ciel.meteo];
    const metTxt = { aube: "Aube", jour: "Jour", coucher: "Coucher de soleil", nuit: "Nuit" }[e.ciel.phase] + " · " +
      (e.ciel.phase === "nuit" ? { soleil: "étoilée", nuages: "nuageuse", pluie: "pluie", arc: "étoilée" } : { soleil: "soleil", nuages: "nuageux", pluie: "pluie", arc: "arc-en-ciel" })[e.ciel.meteo];
    return `${medaillon(e)}
      <div class="phb-titres"><h2 id="phb-titre">${esc(e.titre)}</h2>
        <div class="phb-puces">${e.stade === "oeuf" ? `<span>Œuf</span>` : `<span>${esc(e.stade_nom)}</span><span>${age(e.age_jours)}</span><span>${poids(e.poids_g)}${e.ventre_rond ? " · ventre rond" : ""}</span>`}</div></div>
      <div class="phb-ciel-info"><span class="phb-puce" title="Météo de l'île">${ico(met)}${metTxt}</span>
        <span class="phb-puce" title="${esc(e.ciel.saison_texte || "")}">${ico(ICO_SAISON[e.ciel.saison] || "fleur")}${esc(e.ciel.saison_nom || "")}</span></div>
      <button class="phb-b phb-fermer phb-amb" data-phb="ambiance" aria-pressed="${!!(e.reglages.sons && e.reglages.ambiance !== false)}"
        aria-label="${e.reglages.sons && e.reglages.ambiance !== false ? "Couper les bruits de l'île" : "Écouter les bruits de l'île"}" title="Bruits de l'île (vagues, pluie, vent, oiseaux…)">${ico(e.reglages.sons && e.reglages.ambiance !== false ? "son" : "muet")}</button>
      <span class="phb-coq" role="img" aria-label="${e.coquillages} coquillages">${icone("coquillage")}<b>${e.coquillages}</b></span>
      <button class="phb-b phb-fermer" data-phb="fermer" aria-label="Fermer l'île de Philibert">${ico("fermer")}</button>`;
  }
  const niveauJauge = v => v >= 60 ? "haut" : v >= 30 ? "moyen" : "bas";
  function blocJauges() {
    return `<div class="phb-jauges" role="list" aria-label="Jauges de Philibert">${JAUGES.map(([k, n, ic, c]) => {
      const v = e.jauges[k];
      return `<div class="phb-jauge" role="listitem" data-niveau="${niveauJauge(v)}" style="--c:${c}"><span class="phb-j-ic">${ico(ic)}</span>
        <span class="phb-j-nom">${n}</span><b>${v}</b>
        <span class="phb-j-barre" role="progressbar" aria-label="${n}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><i style="width:${v}%"></i></span></div>`;
    }).join("")}</div>`;
  }
  function parole() {
    if (message) return message;
    if (e.niveau === "oeuf") return "L'œuf est bien au chaud dans le sable. Il va bientôt éclore… (les œufs d'iguane incubent dans le sable chaud)";
    if (e.niveau === "veto") return `La tortue vétérinaire prend soin de lui sur l'île d'à côté. Pendant ce temps, ses jauges ne baissent pas. Retour dans ${fmtH(e.veto.reste_s)}.`;
    if (e.niveau === "pension") return "Philibert est chez la voisine : tout est en pause (ses jauges et son âge). Fais-le revenir quand tu veux.";
    if (e.dort) return e.sieste ? "Petite sieste sur le sable chaud…" : "Chut… Philibert dort en haut de son palmier.";
    if (e.malade) return `Il ne se sent pas bien : il a ${e.malade.texte}. Un remède, du repos et de la chaleur l'aideront.`;
    if (e.appel && e.appel.type === "caprice" && e.jauges.bonheur <= 30) return "Philibert te regarde avec insistance… a-t-il vraiment besoin de quelque chose ?";
    const b = e.besoins.filter(x => x.id !== "ventre");
    if (b.length) return b[0].texte;
    if (e.jauges.chaleur < 35) return "Brrr… il fait frisquet pour un lézard à sang froid.";
    if (e.humeur === "joyeux") return "Philibert hoche la tête : tout va bien sur son île !";
    return "Philibert prend le temps de vivre, entre le sable et la mer.";
  }
  function blocEtat() {
    const b = e.besoins;
    const ev = e.evenement;
    const etat = absent() || e.niveau === "oeuf" ? "" : e.malade ? `<span class="phb-pastille malade">${ico("soin")}Malade</span>`
      : e.niveau === "fatigue" ? `<span class="phb-pastille fatigue">${ico("lune")}${e.grognon ? "Grognon" : "Pas au mieux"}</span>` : `<span class="phb-pastille forme">${ico("coeur")}En forme</span>`;
    const appel = e.appel && (e.appel.type !== "caprice" || e.jauges.bonheur <= 30) ? `<span class="phb-pastille appel" title="${e.appel.type === "caprice" ? "Il réclame de l'attention… mais a-t-il vraiment besoin de quelque chose ?" : "Il a besoin de toi"}">${ico("bulle")}Il t'appelle</span>` : "";
    return `<div class="phb-parole" role="status"><p>${esc(parole())}</p></div>
      <div class="phb-besoins">${etat}${appel}${e.dort ? `<span class="phb-pastille dort">${ico("lune")}${e.sieste ? "Sieste" : "Il dort"}</span>` : ""}
        ${b.map(x => `<span class="phb-besoin">${ico(ICO_BESOIN[x.id] || "bulle")}${esc(x.texte)}</span>`).join("")}</div>
      ${ev ? `<div class="phb-evt"><span class="phb-evt-txt"><b>Sur l'île :</b> ${esc(ev.texte)}</span> ${Object.entries(ev.choix).map(([k, t]) => `<button class="phb-b" data-phb="evenement" data-choix="${k}">${esc(t)}</button>`).join("")}</div>` : ""}`;
  }
  function tuile(act, ic, txt, c, opts = {}) {
    return `<button class="phb-tuile" style="--c:${c}" data-phb="${act}"${opts.off ? " disabled" : ""}${opts.titre ? ` title="${esc(opts.titre)}"` : ""}${opts.pressed != null ? ` aria-pressed="${opts.pressed}"` : ""}>
      <span class="phb-tuile-ic">${ico(ic)}</span><span class="phb-tuile-txt">${txt}</span></button>`;
  }
  function boutons() {
    const off = ["oeuf", "veto", "pension"].includes(e.niveau);
    const o = { off };
    return `<div class="phb-actions" role="toolbar" aria-label="Soins">
        ${tuile("f-nourrir", "nourrir", "Nourrir", "#3a9e4a", { ...o, titre: "Repas de verdure, fleurs, friandises" })}
        ${tuile("chauffer", "soleil", "Chauffer", "#e8731a", { ...o, titre: nuitHeure() ? "La nuit, c'est la lampe chauffante" : "Au soleil sur le rocher chaud" })}
        ${e.lampe.possede ? tuile("lampe", "flamme", e.lampe.allumee ? "Lampe allumée" : "Lampe éteinte", "#c4552a", { ...o, pressed: e.lampe.allumee, titre: "Lampe chauffante (sans lumière)" }) : ""}
        ${nuitHeure() || !e.lumiere ? tuile("lumiere", e.lumiere ? "lune" : "ampoule", e.lumiere ? "Éteindre" : "Rallumer", "#3b5a9a", { ...o, pressed: !e.lumiere, titre: "La nuit, il dort mieux dans le noir" }) : ""}
        ${tuile("f-bain", "goutte", "Bain", "#2a86cc", o)}
        ${tuile("nettoyer", "balai", "Nettoyer", "#8a6a3d", o)}
        ${tuile("soigner", "soin", `Soigner${e.inventaire.remede ? ` <small>×${e.inventaire.remede}</small>` : ""}`, "#d4483b", { ...o, titre: "Donner un remède (il agit mieux au chaud)" })}
        ${tuile("caresser", "main", "Caresser", "#e0507a", o)}
        ${tuile("f-jouer", "de", "Jouer", "#7356cf", { ...o, titre: "Mini-jeux : bonheur et coquillages" })}
        ${tuile("feliciter", "etoile", "Féliciter", "#d69a0b", { ...o, titre: "Juste après une bonne action" })}
        ${tuile("gronder", "bulle", "Gronder", "#5f717a", { ...o, titre: "Doucement : pour un caprice, pas pour un vrai besoin" })}
      </div>
      <div class="phb-actions phb-actions-2" role="toolbar" aria-label="Île">
        ${tuile("ramasser", "coquillage", `Ramasser${e.ramasser_dans_s ? ` <small>${fmtH(e.ramasser_dans_s)}</small>` : ""}`, "#c9785f", { off, titre: e.ramasser_dans_s ? "La mer en rapporte dans " + fmtH(e.ramasser_dans_s) : "Ramasser des coquillages sur la plage" })}
        ${tuile("f-boutique", "panier", "Boutique", "#0d6470")}
        ${tuile("f-garde", "chapeau", "Garde-robe", "#a8812f")}
        ${tuile("f-carnet", "livre", "Carnet", "#6a5a38")}
        ${tuile("f-reglages", "reglages", "Réglages", "#5f717a")}
      </div>`;
  }

  // ---- panneaux ----
  const titre = (ic, t, petit = "") => `<h3>${ico(ic)}<span>${t}${petit ? ` <small>${petit}</small>` : ""}</span></h3>`;
  function feuilleNourrir() {
    const groupes = [["Repas du quotidien", ["verdure", "legume"]], ["Fleurs", ["fleur"]], ["Friandises — à limiter", ["friandise"]]];
    return `${titre("nourrir", "Nourrir Philibert", "· 100 % végétal")}
      ${groupes.map(([t, cats]) => `<div class="phb-groupe">${t}</div><div class="phb-grille">${Object.entries(cat.aliments).filter(([, a]) => cats.includes(a.cat)).map(([id, a]) => {
        const n = a.prix ? (e.inventaire[id] || 0) : "∞";
        return `<button class="phb-carte" data-phb="nourrir" data-aliment="${id}" ${a.prix && !n ? "disabled" : ""} title="${esc(a.texte)}">
          <span class="phb-ic">${icone(id)}</span><span>${esc(a.nom)}</span><small>${a.prix ? `×${n}` : "gratuit"}</small></button>`;
      }).join("")}</div>`).join("")}
      <p class="phb-astuce">${ico("fleur")}<span>Le savais-tu ? Un iguane vert ne mange que des plantes. Il en manque ? Passe à la <button class="phb-lien" data-phb="f-boutique">boutique</button>.</span></p>`;
  }
  function feuilleBain() {
    return `${titre("goutte", "Le bain")}<div class="phb-grille phb-grille-2">
      <button class="phb-carte" data-phb="bain" data-lieu="flaque"><span class="phb-ic phb-ic-ico" style="--c:#2a86cc">${ico("goutte")}</span><span>Bain tiède dans la flaque</span><small>propreté, aide la mue</small></button>
      <button class="phb-carte" data-phb="bain" data-lieu="mer"><span class="phb-ic phb-ic-ico" style="--c:#0f8fb0">${ico("vent")}</span><span>Nager dans la mer</span><small>bonheur, mais l'eau rafraîchit</small></button></div>`;
  }
  function feuilleJouer() {
    const J = [["feuilles", "nourrir", "#3a9e4a", "Attrape les feuilles et les fleurs qui tombent du palmier, évite les insectes (30 s)"],
      ["course", "drapeau", "#e8731a", "Cours jusqu'au rocher chaud : saute les crabes, attrape les rayons de soleil, évite l'ombre des nuages (30 s au plus)"],
      ["devin", "loupe", "#7356cf", "Devine de quel côté il va tourner la tête (5 manches)"], ["rythme", "coeur", "#e0507a", "Répète ses hochements de tête, petits et grands"]];
    return `${titre("de", "Jouer avec Philibert")}<div class="phb-grille phb-grille-2">${J.map(([id, ic, c, t]) => `<button class="phb-carte phb-carte-jeu" data-phb="jeu" data-jeu="${id}">
      <span class="phb-ic phb-ic-ico" style="--c:${c}">${ico(ic)}</span><span>${esc(cat.jeux[id] || id)}</span><small>${esc(t)}</small></button>`).join("")}</div>
      <p class="phb-astuce">${ico("coquillage")}<span>Encore ${e.jeux_restants} coquillages à gagner aujourd'hui aux jeux. Bien au chaud, il joue mieux !</span></p>`;
  }
  function feuilleBoutique() {
    const O = cat.objets, A = cat.aliments;
    const onglets = { nourriture: "Nourriture", soins: "Soins et équipement", accessoires: "Accessoires", deco: "Déco de l'île" };
    let items;
    if (boutiqueOnglet === "nourriture") items = Object.entries(A).filter(([, a]) => a.prix).map(([id, a]) => {
      const promo = id === e.promo;
      return [id, a.nom, promo ? Math.max(1, a.prix - 1) : a.prix, a.texte, `en réserve : ${e.inventaire[id] || 0}`, false, promo];
    });
    else {
      const t = { soins: ["soin", "equipement"], accessoires: ["accessoire"], deco: ["deco"] }[boutiqueOnglet];
      items = Object.entries(O).filter(([, o]) => t.includes(o.type)).map(([id, o]) => {
        const a = id === "lampe" ? e.lampe.possede : (e.accessoires.includes(id) || e.deco.includes(id));
        return [id, o.nom, o.prix, o.texte, id === "remede" ? `en réserve : ${e.inventaire.remede || 0}` : a ? "déjà à toi" : "", a, false, o.rarete || "commun"];
      });
    }
    return `${titre("panier", "Boutique de l'île", `· tu as ${e.coquillages} coquillage${e.coquillages > 1 ? "s" : ""}`)}
      <div class="phb-onglets" role="tablist">${Object.entries(onglets).map(([k, t]) => `<button class="phb-b${k === boutiqueOnglet ? " phb-on" : ""}" role="tab" aria-selected="${k === boutiqueOnglet}" data-phb="boutique-onglet" data-o="${k}">${t}</button>`).join("")}</div>
      <div class="phb-grille">${items.map(([id, nom, prix, texte, info, possede, promo, rarete = "commun"]) => `<div class="phb-carte phb-article${promo ? " promo" : ""} r-${rarete}">
        ${promo ? `<span class="phb-ruban">de saison · −1</span>` : rarete !== "commun" ? `<span class="phb-ruban phb-rare">${ico("etoile")}${esc((cat.raretes || {})[rarete] || rarete)}</span>` : ""}
        <span class="phb-ic">${icone(id)}</span><span>${esc(nom)}</span><small>${esc(texte)}</small>${info ? `<small class="phb-info">${esc(info)}</small>` : ""}
        <button class="phb-b phb-prim" data-phb="acheter" data-article="${id}" ${possede ? "disabled" : ""} aria-label="Acheter ${esc(nom)} pour ${prix} coquillages">${possede ? "✔ À toi" : `<span class="phb-ic-mini">${icone("coquillage")}</span>${prix}`}</button></div>`).join("")}</div>
      ${["accessoires", "deco"].includes(boutiqueOnglet) ? `<p class="phb-astuce">${ico("etoile")}<span>Les pièces <b>rares</b>, <b>très rares</b> et <b>légendaires</b> sont faites à la main par les artisans de l'île voisine, en un seul exemplaire : elles coûtent cher, mais les soins (remède, nourriture) restent toujours bon marché.</span></p>` : ""}
      ${boutiqueOnglet === "nourriture" ? `<p class="phb-astuce">${ico("nourrir")}<span>Pas d'insectes, de viande ni de croquettes ici : Philibert est herbivore. Le trèfle de l'île est toujours gratuit.</span></p>` : ""}`;
  }
  function feuilleGarde() {
    const slots = { tete: "Tête", yeux: "Yeux", cou: "Cou" };
    const parSlot = s => e.accessoires.filter(a => cat.objets[a].emplacement === s);
    return `${titre("chapeau", "Garde-robe")}<div class="phb-garde"><div class="phb-apercu">${D.svg({ stade: e.stade === "oeuf" ? "bebe" : e.stade, variante: e.variante, humeur: "joyeux", portes: e.portes, label: "Aperçu de Philibert", uid: "g" })}</div>
      <div>${Object.entries(slots).map(([s, n]) => `<div class="phb-groupe">${n}</div><div class="phb-ligne">${parSlot(s).map(a => `<button class="phb-b${e.portes[s] === a ? " phb-on" : ""}" data-phb="${e.portes[s] === a ? "retirer" : "porter"}" data-article="${a}" data-emplacement="${s}" aria-pressed="${e.portes[s] === a}">
        <span class="phb-ic-mini">${icone(a)}</span>${esc(cat.objets[a].nom)}${cat.objets[a].rarete && cat.objets[a].rarete !== "commun" ? `<small class="phb-r-puce r-${cat.objets[a].rarete}">${esc((cat.raretes || {})[cat.objets[a].rarete] || "")}</small>` : ""}</button>`).join("") || `<small class="phb-gris">Rien pour l'instant (voir la boutique).</small>`}</div>`).join("")}</div></div>`;
  }
  function portrait(x) {
    return `<div class="phb-portrait">${D.svg({ stade: x.stade, variante: x.variante, portes: x.portes, humeur: "joyeux", label: x.titre, uid: "a" })}</div>`;
  }
  function feuilleCarnet() {
    const c = carnetDonnees;
    const onglets = { historique: "Historique", album: "Album", stats: "Statistiques", succes: "Succès", cartes: "Cartes postales", faits: "Le savais-tu ?" };
    let corps = `<p class="phb-gris">Chargement…</p>`;
    if (c) {
      if (carnetOnglet === "historique") corps = `<ol class="phb-histo">${c.historique.map(h => `<li><time>${new Date(h.t * 1000).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</time> ${esc(h.texte)}</li>`).join("")}</ol>`;
      else if (carnetOnglet === "album") {
        const et = c.etapes || [], al = c.album || [];
        corps = `<div class="phb-groupe">Les étapes de ${esc(c.titre)}</div>
          ${et.length ? `<div class="phb-frise">${et.map(x => `<figure class="phb-photo">${portrait(x)}<figcaption><b>${esc(cat.stades[x.stade] || x.stade)}${x.variante ? " · " + esc(cat.variantes[x.variante] || "") : ""}</b><small>${date(x.t)} · ${age(x.age_jours)}</small></figcaption></figure>`).join("")}</div>`
            : `<p class="phb-gris">Encore un œuf : la première photo sera prise à l'éclosion.</p>`}
          <div class="phb-groupe">Les Philibert d'avant</div>
          ${al.length ? `<div class="phb-grille phb-grille-album">${al.map(x => `<div class="phb-carte phb-ancien">${portrait(x)}<span>${esc(x.titre)}</span>
            <small>${date(x.eclos || x.ne)} → ${date(x.fin)} · ${age(x.age_jours)}</small>
            <small>${x.repas} repas · ${x.jeux} parties · ${x.mues} mue${x.mues > 1 ? "s" : ""} · ${x.succes} succès${x.sejours_veto ? ` · ${x.sejours_veto} séjour${x.sejours_veto > 1 ? "s" : ""} chez la tortue` : ""}</small>
            <small class="phb-info">Il vit maintenant sur une île voisine.</small></div>`).join("")}</div>`
            : `<p class="phb-gris">Personne pour l'instant : quand tu recommences avec un nouvel œuf, Philibert part vivre sur une île voisine et garde sa place ici.</p>`}`;
      } else if (carnetOnglet === "stats") {
        const s = c.stats, L = [["Âge", age(c.age_jours)], ["Né le", new Date(c.ne * 1000).toLocaleDateString("fr-FR")], ["Repas", s.repas], ["dont verdure et légumes", s.verdure], ["Fleurs", s.fleurs],
          ["Friandises", s.friandises], ["Verdures goûtées", `${c.gouts.length} / 6`], ["Refus (aliments pas pour lui)", s.refus], ["Bains (dont mer)", `${s.bains} (${s.bains_mer})`], ["Séances au soleil", s.soleil],
          ["Parties jouées", s.jeux], ["Caresses", s.caresses], ["Mues", s.mues], ["Maladies (guéries à la maison)", `${s.maladies} (${s.gueris})`], ["Séjours chez le vétérinaire", s.sejours_veto],
          ["Nuits dans le noir", s.nuits_eteintes], ["Saisons vécues", `${(c.saisons_vues || []).length} / 4`], ["Coquillages gagnés", s.coquillages_gagnes],
          ["Records : feuilles · course · devin · hochements", `${s.meilleur_feuilles} · ${s.meilleur_course || 0} · ${s.meilleur_devin}/5 · ${s.meilleur_rythme}`]];
        corps = `<table class="phb-tbl">${L.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${esc(v)}</td></tr>`).join("")}</table>`;
      } else if (carnetOnglet === "succes") {
        const n = Object.values(c.succes).filter(s => s.quand).length;
        corps = `<p class="phb-gris">${n} succès sur ${Object.keys(c.succes).length}</p><div class="phb-grille">${Object.entries(c.succes).map(([, s]) => `<div class="phb-carte phb-succes${s.quand ? " ok" : ""}">
          <span class="phb-ic phb-ic-ico" style="--c:${s.quand ? "#d69a0b" : "#9aa6ab"}">${ico(s.quand ? "etoile" : "loupe")}</span><span>${esc(s.nom)}</span><small>${esc(s.texte)}${s.gain ? ` · +${s.gain} coquillages` : ""}</small>${s.quand ? `<small class="phb-info">${new Date(s.quand * 1000).toLocaleDateString("fr-FR")}</small>` : ""}</div>`).join("")}</div>`;
      } else if (carnetOnglet === "cartes") corps = c.cartes.length ? c.cartes.map(carteHtml).join("") : `<p class="phb-gris">Aucune carte postale : Philibert n'est jamais allé chez la tortue vétérinaire.</p>`;
      else corps = `<p class="phb-gris">${c.faits.length} fiche${c.faits.length > 1 ? "s" : ""} sur ${c.faits_total} — on en débloque en s'occupant de lui.</p>
        <ul class="phb-faits">${c.faits.map(f => `<li>${ico("fleur")}<span>${esc(f.texte)}</span></li>`).join("")}</ul>`;
    }
    return `${titre("livre", "Carnet de " + esc(c ? c.titre : "Philibert"))}
      <div class="phb-onglets" role="tablist">${Object.entries(onglets).map(([k, t]) => `<button class="phb-b${k === carnetOnglet ? " phb-on" : ""}" role="tab" aria-selected="${k === carnetOnglet}" data-phb="carnet-onglet" data-o="${k}">${t}</button>`).join("")}</div>${corps}`;
  }
  function carteHtml(c) {
    const u = "phbp" + (++nIco);
    // carte postale : la tortue vétérinaire (tortue verte, carapace à écailles) sur sa plage, au soleil
    const ecailles = [[54, 49, 60, 44, 67, 44, 70, 49, 64, 52, 57, 52], [44, 52, 50, 47, 54, 49, 57, 52, 52, 56, 46, 56], [70, 49, 74, 46, 79, 49, 78, 54, 73, 55, 64, 52],
      [46, 56, 52, 56, 57, 52, 64, 52, 62, 58, 50, 59], [64, 52, 73, 55, 76, 58, 70, 61, 62, 58, 64, 52]];
    return `<div class="phb-postale"><div class="phb-postale-img" aria-hidden="true"><svg viewBox="0 0 120 80"><defs>
        <linearGradient id="${u}c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3f86cf"/><stop offset="1" stop-color="#cfe8f3"/></linearGradient>
        <linearGradient id="${u}m" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f7fb0"/><stop offset=".5" stop-color="#2fc4c4"/><stop offset="1" stop-color="#9fe8de"/></linearGradient>
        <linearGradient id="${u}s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f4e6c2"/><stop offset="1" stop-color="#d9bf88"/></linearGradient>
        <radialGradient id="${u}t" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#9a8a4a"/><stop offset=".6" stop-color="#6b5e2e"/><stop offset="1" stop-color="#3e3618"/></radialGradient>
        <radialGradient id="${u}p" cx=".4" cy=".3" r=".8"><stop offset="0" stop-color="#b9c08a"/><stop offset="1" stop-color="#7a8450"/></radialGradient>
        <radialGradient id="${u}o"><stop offset="0" stop-color="#fffbe8"/><stop offset=".4" stop-color="#ffe9a0" stop-opacity=".6"/><stop offset="1" stop-color="#ffe9a0" stop-opacity="0"/></radialGradient></defs>
      <rect width="120" height="44" fill="url(#${u}c)"/><circle cx="96" cy="16" r="13" fill="url(#${u}o)"/><circle cx="96" cy="16" r="4.2" fill="#fffdf2"/>
      <path d="M14 20 C20 16 30 17 32 21 C36 19 42 21 40 24 L12 24 C9 23 10 20 14 20 Z" fill="#fff" opacity=".9"/>
      <rect y="42" width="120" height="16" fill="url(#${u}m)"/><path d="M0 47 h120 M0 52 h120" stroke="#fff" stroke-opacity=".25" stroke-width=".5" stroke-dasharray="6 9 3 12"/>
      <path d="M0 62 C30 54 90 54 120 60 V80 H0 Z" fill="url(#${u}s)"/><path d="M0 62 C30 54 90 54 120 60" stroke="#fff" stroke-width="1.6" fill="none" opacity=".85" stroke-dasharray="9 2 4 2"/>
      <path d="M12 74 C12 60 10 46 4 34" stroke="#7a6650" stroke-width="2.6" fill="none"/>
      ${[[-40, 22], [-10, 24], [20, 22], [-80, 20], [50, 18]].map(([an, l]) => { const r = an * Math.PI / 180; return `<path d="M4 34 Q${(4 + Math.cos(r) * l * .6).toFixed(1)} ${(34 + Math.sin(r) * l * .6 - 6).toFixed(1)} ${(4 + Math.cos(r) * l).toFixed(1)} ${(34 + Math.sin(r) * l + 6).toFixed(1)}" stroke="#3f7d32" stroke-width="3.4" fill="none" stroke-linecap="round" stroke-dasharray="2 1"/>`; }).join("")}
      <ellipse cx="62" cy="66" rx="30" ry="3.4" fill="#3b2a12" opacity=".2"/>
      <path d="M44 60 C38 64 34 68 36 70 C40 70 46 66 49 62 Z M76 60 C84 62 90 66 89 69 C85 70 79 66 74 62 Z" fill="url(#${u}p)" stroke="#5a6236" stroke-width=".6"/>
      <path d="M42 58 C42 48 52 42 62 42 C72 42 81 48 81 57 C81 61 72 63 62 63 C51 63 42 62 42 58 Z" fill="url(#${u}t)" stroke="#2e2810" stroke-width=".7"/>
      ${ecailles.map(q => `<path d="M${q[0]} ${q[1]} L${q[2]} ${q[3]} L${q[4]} ${q[5]} L${q[6]} ${q[7]} L${q[8]} ${q[9]} L${q[10]} ${q[11]} Z" fill="none" stroke="#c9b26a" stroke-width=".6" opacity=".7"/>`).join("")}
      <path d="M48 46 C54 43 62 42 68 43" stroke="#fff" stroke-width="1" fill="none" opacity=".3"/><path d="M42 59 C50 62 72 62 81 58" stroke="#d8cfa0" stroke-width="1.4" fill="none"/>
      <path d="M80 56 C84 50 92 49 96 52 C99 54 98 58 94 59 C90 60 85 60 80 59 Z" fill="url(#${u}p)" stroke="#5a6236" stroke-width=".6"/>
      <path d="M86 51 l2 2 l3 -1 l1 3 M88 56 l3 -.4" stroke="#5a6236" stroke-width=".5" fill="none" opacity=".7"/>
      <circle cx="92" cy="54" r="1.3" fill="#1a1610"/><circle cx="92.4" cy="53.6" r=".4" fill="#fff"/><path d="M94 57.6 q2 -.4 3.4 -1.6" stroke="#3e3a22" stroke-width=".6" fill="none"/>
      <path d="M85 50.6 C85.4 46 93 45.4 95 50.2 Z" fill="#fbfbf6" stroke="#c9c9c0" stroke-width=".5"/><path d="M90 46.6 v3 M88.5 48.1 h3" stroke="#e2464f" stroke-width="1.1"/>
      ${[[24, 70, 0], [104, 72, 1], [32, 76, 2]].map(([x, y, k]) => k === 1 ? `<circle cx="${x}" cy="${y}" r="1.6" fill="#f2dcc0"/>` : `<path d="M${x - 2.4} ${y} C${x - 2.4} ${y - 3} ${x + 2.4} ${y - 3} ${x + 2.4} ${y} Z" fill="#f4b8a0"/>`).join("")}</svg></div>
      <div><b>Carte postale de la tortue vétérinaire</b> <small>· ${new Date(c.t * 1000).toLocaleDateString("fr-FR")} · séjour de ${c.duree_h} h</small>
      <p>« Bonjour ! Philibert s'est bien reposé chez moi. ${esc(c.texte)} »</p><p class="phb-conseil"><b>Mon conseil :</b> ${esc(c.conseil)}</p>
      <small>${c.cout ? `Consultation : ${c.cout} coquillages.` : "Consultation offerte."} Il revient en pleine forme !</small></div></div>`;
  }
  function feuilleReglages() {
    const r = e.reglages;
    const chk = (k, t) => `<label class="phb-chk"><input type="checkbox" data-phb-r="${k}" ${r[k] ? "checked" : ""}> <span>${t}</span></label>`;
    return `${titre("reglages", "Réglages de Philibert")}
      ${chk("visible", "Le voir se promener en haut de la page")}
      ${chk("sons", "Petits sons (seulement dans son île)")}
      ${chk("ambiance", "Bruits de l'île selon la météo : vagues, pluie, vent, oiseaux, grenouilles la nuit (discrets, avec les petits sons)")}
      <label class="phb-chk"><span>Couleurs de l'interface</span> <select data-phb-r="theme"><option value="auto"${r.theme === "auto" || !r.theme ? " selected" : ""}>Automatique (selon le thème du panel et la nuit sur l'île)</option>
        <option value="clair"${r.theme === "clair" ? " selected" : ""}>Clair</option><option value="sombre"${r.theme === "sombre" ? " selected" : ""}>Sombre</option></select></label>
      ${chk("notif_windows", "Notification Windows s'il tombe malade ou part chez le vétérinaire (jamais en mode jeu)")}
      ${chk("discord", "Me prévenir aussi sur Discord (si le bot de NEXUS est configuré)")}
      <label class="phb-chk"><span>Vitesse du temps</span> <select data-phb-r="vitesse"><option value="normale"${r.vitesse === "normale" ? " selected" : ""}>Normale</option>
        <option value="lente"${r.vitesse === "lente" ? " selected" : ""}>Lente (deux fois moins vite)</option></select></label>
      <div class="phb-groupe">Mode vacances</div>
      <p class="phb-gris">La voisine de l'île le prend en pension : jauges, âge et maladie sont en pause jusqu'à son retour.</p>
      ${e.vacances ? `<button class="phb-b phb-prim" data-phb="revenir">Le faire revenir</button>` : `<button class="phb-b" data-phb="vacances" ${e.niveau === "veto" || e.niveau === "oeuf" ? "disabled" : ""}>Partir en pension chez la voisine</button>`}
      <div class="phb-groupe">Recommencer</div>
      <p class="phb-gris">Philibert part vivre sur une île voisine (il garde sa place dans l'album du carnet) et un nouvel œuf apparaît.</p>
      <button class="phb-b phb-danger" data-phb="recommencer">Recommencer avec un nouvel œuf…</button>`;
  }

  function rendreFeuille() {
    const f = dlg.querySelector(".phb-feuille");
    if (!f) return;
    if (!feuille || !cat) { f.hidden = true; f.innerHTML = ""; return; }
    if (feuille === "jeu") return;                        // géré par js/philibert-jeux.js
    const html = { nourrir: feuilleNourrir, bain: feuilleBain, jouer: feuilleJouer, boutique: feuilleBoutique, garde: feuilleGarde, carnet: feuilleCarnet,
      reglages: feuilleReglages, carte: () => carteHtml(e.carte) + `<button class="phb-b phb-prim" data-phb="carte-lue">Merci, docteur Tortue !</button>` }[feuille]();
    f.hidden = false;
    f.className = "phb-feuille phb-f-" + feuille;
    const msg = message && ["boutique", "garde", "reglages"].includes(feuille) ? `<p class="phb-dit" role="status">${esc(message)}</p>` : "";
    f.innerHTML = `<button class="phb-b phb-fermer-f" data-phb="fermer-feuille" aria-label="Fermer ce panneau">${ico("fermer")}</button>${msg}${html}`;
  }

  function rendre() {
    if (!e) return;
    const t = dlg.querySelector(".phb-tete-ile");
    if (!t) return;
    dlg.dataset.phase = e.ciel.phase;
    dlg.toggleAttribute("data-nuit", e.ciel.phase === "nuit");
    dlg.toggleAttribute("data-sombre", interfaceSombre());
    Ambiance.maj();
    dlg.toggleAttribute("data-lumiere", !!e.lumiere);
    t.innerHTML = tete();
    dlg.querySelector(".phb-bas").innerHTML = `${e.niveau === "oeuf" || absent() ? "" : blocJauges()}<div class="phb-etat">${blocEtat()}</div>${boutons()}`;
    rendreScene();
    if (feuille && feuille !== "jeu") rendreFeuille();
    if (e.carte && !feuille) { feuille = "carte"; rendreFeuille(); }
    nouveautes();
  }
  // Succès et fiches « Le savais-tu ? » débloqués : un petit bandeau, puis marqués comme vus
  let vuEnvoye = false;
  function nouveautes() {
    if (!e.nouveau || !e.nouveau.length || vuEnvoye) return;
    const box = dlg.querySelector(".phb-bandeaux");
    box.innerHTML = e.nouveau.map(n => `<div class="phb-bandeau">${n.type === "succes" ? `${ico("etoile")}<span><b>Succès :</b> ${esc(n.nom)} — ${esc(n.texte)}</span>` : `${ico("fleur")}<span><b>Le savais-tu ?</b> ${esc(n.texte)}</span>`}</div>`).join("");
    son("joie");
    effet("etoile", 6);
    vuEnvoye = true;
    setTimeout(() => { box.innerHTML = ""; vuEnvoye = false; }, 9000);
    api("/api/philibert/action", { action: "vu" }).then(r => { e.nouveau = []; diffuser(r.etat); }).catch(() => {});
  }

  function diffuser(nv) {
    e = nv;
    dispatchEvent(new CustomEvent("philibert:etat", { detail: nv }));
  }
  function appliquer(nv) { diffuser(nv); if (dlg.open) rendre(); }
  function dire(m) {
    message = m || "";
    clearTimeout(messageT);
    if (message) messageT = setTimeout(() => { message = ""; if (dlg.open && e) { const p = dlg.querySelector(".phb-parole p"); if (p) p.textContent = parole(); } }, 15000);
  }

  async function action(nom, params = {}) {
    try {
      const r = await api("/api/philibert/action", { action: nom, ...params });
      dire(r.message);
      appliquer(r.etat);
      if (r.reaction) jouerReaction(r.reaction);
      return r;
    } catch (x) {
      dire(x.message);
      son("non");
      if (dlg.open) rendre();
      return null;
    }
  }
  function jouerReaction(r) {
    clearTimeout(reactionT);
    const s = { mange_verdure: "croc", mange_legume: "croc", mange_fleur: "croc", mange_friandise: "croc", bain_mer: "plouf", bain_flaque: "plouf", coquillage: "ding", achat: "ding",
      refus: "non", gueri: "joie", fier: "pop", caresse: "pop", repu: "non", non: "non", joue: "joie", bonjour: "joie" }[r];
    if (s) son(s);
    const avant = reaction;
    reaction = ["bain_mer", "bain_flaque", "refus"].includes(r) ? r : "";
    if (reaction !== avant) rendreScene();
    const p = dlg.querySelector(".phb-perso");
    if (!p) return;
    const cls = r.startsWith("mange") ? "mange" : { refus: "refus", caresse: "fanon", fier: "hoche", gueri: "hoche", bonjour: "hoche", triste: "triste", repu: "refus", calme: "hoche", joue: "saute" }[r];
    if (cls) { p.classList.remove(cls); void p.offsetWidth; p.classList.add(cls); setTimeout(() => p.classList.remove(cls), 1600); }
    if (r.startsWith("mange")) { effetAliment(dernierAliment); setTimeout(() => effet("miette", 7), 450); }
    else if (r.startsWith("bain")) setTimeout(() => effet("goutte", 9), 900);
    else if (r === "caresse" || r === "joue" || r === "bonjour") effet("coeur", 5);
    else if (r === "fier" || r === "gueri") effet("etoile", r === "gueri" ? 8 : 4);
    else if (r === "coquillage" || r === "achat") effet("coquillage", 4);
    reactionT = setTimeout(() => { reaction = ""; rendreScene(); }, r.startsWith("bain") ? 3500 : 1600);
  }

  async function charger() {
    try { appliquer(await api("/api/philibert")); } catch (x) { dire("NEXUS ne répond pas : " + x.message); }
  }

  // ---- ouverture ----
  async function ouvrir(f) {
    if (!dlg.innerHTML) {
      dlg.innerHTML = `<div class="phb-ile">
        <div class="phb-tete-ile"></div>
        <div class="phb-scene-zone"><div class="phb-scene"><div class="phb-decor"></div><div class="phb-crottes"></div>
          <button class="phb-perso phb-anim" data-phb="caresser" aria-label="Caresser Philibert"><span class="phb-flip"></span></button>
          <div class="phb-effets" aria-hidden="true"></div></div>
          <div class="phb-bandeaux" aria-live="polite"></div></div>
        <div class="phb-feuille" hidden></div>
        <div class="phb-bas"></div></div>`;
    }
    if (!dlg.open) dlg.showModal();
    if (!cat) { try { cat = await api("/api/philibert/catalogue"); } catch (x) { /* réessayé à la prochaine ouverture */ } }
    dire("");
    e = (window.nxPhilibert && window.nxPhilibert.etat()) || e;
    if (e) rendre();
    await charger();
    clearInterval(pollT);
    pollT = setInterval(() => { if (!document.hidden && dlg.open && feuille !== "jeu") charger(); }, 30000);
    flaner();
    if (f && typeof f === "string") ouvrirFeuille(f);
  }
  dlg.addEventListener("close", () => { Ambiance.maj(); clearInterval(pollT); clearTimeout(flanerT); feuille = null; if (window.PhilibertJeux) window.PhilibertJeux.arreter(); rendreFeuille(); });
  dlg.addEventListener("cancel", ev => {                              // Échap : ferme d'abord le panneau ouvert
    if (feuille && feuille !== "carte") { ev.preventDefault(); fermerFeuille(); }
  });
  function fermerFeuille() {
    if (feuille === "jeu" && window.PhilibertJeux) window.PhilibertJeux.arreter();
    feuille = null;
    rendreFeuille();
    const b = dlg.querySelector(".phb-actions .phb-tuile");
    if (b) b.focus();
  }
  async function ouvrirFeuille(f) {
    feuille = f;
    dire("");
    if (f === "carnet") { carnetDonnees = null; rendreFeuille(); try { carnetDonnees = await api("/api/philibert/carnet"); } catch (x) { dire(x.message); } }
    rendreFeuille();
    const prem = dlg.querySelector(".phb-feuille button:not(.phb-fermer-f), .phb-feuille input");
    if (prem) prem.focus();
  }

  dlg.addEventListener("click", async ev => {
    if (ev.target === dlg) { dlg.close(); return; }
    const b = ev.target.closest("[data-phb]");
    if (!b || b.disabled) return;
    const a = b.dataset.phb;
    if (a === "fermer") return dlg.close();
    if (a === "fermer-feuille") return fermerFeuille();
    if (a.startsWith("f-")) return ouvrirFeuille(a.slice(2));
    if (a === "boutique-onglet") { boutiqueOnglet = b.dataset.o; return rendreFeuille(); }
    if (a === "carnet-onglet") { carnetOnglet = b.dataset.o; return rendreFeuille(); }
    if (a === "nourrir") { feuille = null; rendreFeuille(); dernierAliment = b.dataset.aliment; await action("nourrir", { aliment: b.dataset.aliment }); return; }
    if (a === "bain") { feuille = null; rendreFeuille(); await action("bain", { lieu: b.dataset.lieu }); return; }
    if (a === "lampe") return action("lampe", { on: !e.lampe.allumee });
    if (a === "ambiance") return action("reglages", e.reglages.sons ? { ambiance: e.reglages.ambiance === false } : { sons: true, ambiance: true });
    if (a === "lumiere") return action("lumiere", { on: !e.lumiere });
    if (a === "acheter") { await action("acheter", { article: b.dataset.article }); return; }
    if (a === "porter") return action("porter", { article: b.dataset.article });
    if (a === "retirer") return action("retirer", { emplacement: b.dataset.emplacement });
    if (a === "evenement") return action("evenement", { choix: b.dataset.choix });
    if (a === "revenir") { await action("vacances", { on: false }); return; }
    if (a === "vacances") { if (confirm("Envoyer Philibert en pension chez la voisine ? Tout sera en pause jusqu'à son retour.")) { await action("vacances", { on: true }); fermerFeuille(); } return; }
    if (a === "recommencer") {
      if (!confirm("Recommencer avec un nouvel œuf ?\nPhilibert partira vivre sur une île voisine (il restera dans l'album du carnet).")) return;
      if (!confirm("Vraiment sûr ? Cette action ne peut pas être annulée.")) return;
      await action("recommencer", { confirmer: "NOUVEL OEUF" });
      fermerFeuille();
      return;
    }
    if (a === "carte-lue") { feuille = null; await action("carte_lue"); rendreFeuille(); return; }
    if (a === "jeu") { if (window.PhilibertJeux) { feuille = "jeu"; window.PhilibertJeux.lancer(b.dataset.jeu, dlg.querySelector(".phb-feuille"), { etat: () => e, fin: finJeu }); } return; }
    if (a === "caresser" && (["veto", "pension", "oeuf"].includes(e && e.niveau))) return;
    action(a);
  });
  dlg.addEventListener("change", ev => {
    const i = ev.target.closest("[data-phb-r]");
    if (!i) return;
    action("reglages", { [i.dataset.phbR]: i.type === "checkbox" ? i.checked : i.value });
    if (i.dataset.phbR === "notif_windows" && i.checked && "Notification" in window && Notification.permission === "default") Notification.requestPermission();
  });
  function finJeu(r) {
    if (window.PhilibertJeux) window.PhilibertJeux.arreter();
    if (feuille !== "jeu") return;                    // panneau fermé entre-temps
    feuille = "jouer";
    if (r && r.etat) { dire(r.message); son("ding"); appliquer(r.etat); effet("coquillage", 4); }
    rendreFeuille();
  }
  window.PhilibertIle = { ambiance: Ambiance, ouvrir, appliquer, action, icone, fermer: () => dlg.close() };
})();
