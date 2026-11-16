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
  const D = window.PhilibertDessin, I = window.PhilibertIcones;
  if (!D || !I) return;
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

  // ---- icônes dessinées des aliments et objets ----
  function icone(id) {
    const feuilleI = (c, d) => `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 27 C5 12 14 4 28 4 C28 18 20 27 5 27Z" fill="${c}" stroke="${d}" stroke-width="1.2"/><path d="M6 26 C12 18 18 12 25 7" stroke="${d}" stroke-width="1.2" fill="none"/></svg>`;
    const fleur = (c, m) => `<svg viewBox="0 0 32 32" aria-hidden="true">${[0, 72, 144, 216, 288].map(r => `<ellipse cx="16" cy="9" rx="5" ry="7" fill="${c}" transform="rotate(${r} 16 16)"/>`).join("")}<circle cx="16" cy="16" r="4" fill="${m}"/></svg>`;
    const fruit = (c, f) => `<svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="18" rx="10" ry="${f ? 8 : 10}" fill="${c}" stroke="rgba(0,0,0,.25)"/><path d="M16 8 q2 -4 6 -4" stroke="#6b4b2a" stroke-width="2" fill="none"/><ellipse cx="20" cy="6" rx="4" ry="2" fill="#5cae4f"/><ellipse cx="12" cy="14" rx="3" ry="2" fill="#fff" opacity=".35"/></svg>`;
    const M = {
      trefle: `<svg viewBox="0 0 32 32" aria-hidden="true">${[[16, 10], [10, 18], [22, 18]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="6" fill="#6cc24a" stroke="#3f8a2e"/>`).join("")}<path d="M16 18 v11" stroke="#3f8a2e" stroke-width="2"/></svg>`,
      feuilles_pissenlit: feuilleI("#7cc85a", "#3f8a2e"), feuilles_murier: feuilleI("#4fae4f", "#2f7a37"), chou_vert: feuilleI("#9ad47a", "#4f8f3a"),
      courge: fruit("#f5a83b", true), haricots: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 24 C10 10 18 6 26 6" stroke="#5aa84a" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M8 27 C14 16 20 12 27 11" stroke="#7cc85a" stroke-width="4" fill="none" stroke-linecap="round"/></svg>`,
      hibiscus: fleur("#ff4f6d", "#ffd34d"), fleur_pissenlit: fleur("#ffd23f", "#f0a500"),
      mangue: fruit("#ffb23e"), papaye: fruit("#ff8a3d"), figue: fruit("#8e4d8f"), banane: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M6 10 C8 22 18 28 28 22 C20 24 12 20 10 9 Z" fill="#ffd84a" stroke="#c9a120"/></svg>`,
      remede: `<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="10" y="6" width="12" height="22" rx="3" fill="#e8f4ff" stroke="#6b8fb0"/><rect x="11" y="3" width="10" height="5" rx="1" fill="#6b8fb0"/><path d="M16 13 v9 M11.5 17.5 h9" stroke="#e2464f" stroke-width="3"/></svg>`,
      lampe: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M8 6 h16 l-3 9 h-10 Z" fill="#c45a2a"/><circle cx="16" cy="17" r="4" fill="#ff9248"/><path d="M16 21 v8 M10 29 h12" stroke="#555" stroke-width="2"/></svg>`,
      chapeau: `<svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="21" rx="14" ry="4" fill="#f0d27b" stroke="#a8812f"/><path d="M8 21 C8 9 24 9 24 21 Z" fill="#e9c768" stroke="#a8812f"/><rect x="8.4" y="16" width="15.2" height="2.6" fill="#d9434f"/></svg>`,
      couronne: fleur("#ff6b8b", "#ffd34d"), lunettes: `<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="9" cy="17" r="6" fill="#1d2a3a"/><circle cx="23" cy="17" r="6" fill="#1d2a3a"/><path d="M15 16 h2" stroke="#1d2a3a" stroke-width="2"/></svg>`,
      collier: `<svg viewBox="0 0 32 32" aria-hidden="true">${[[6, 12, "#ff7ab6"], [9, 20, "#ffd34d"], [16, 25, "#7fd0ff"], [23, 20, "#ff7ab6"], [26, 12, "#ffd34d"]].map(([x, y, c]) => `<circle cx="${x}" cy="${y}" r="4" fill="${c}" stroke="#fff"/>`).join("")}</svg>`,
      foulard: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 8 L28 8 L16 28 Z" fill="#e2464f" stroke="#a52a33"/><circle cx="12" cy="13" r="1.4" fill="#fff"/><circle cx="20" cy="13" r="1.4" fill="#fff"/><circle cx="16" cy="19" r="1.4" fill="#fff"/></svg>`,
      hamac: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M3 8 C8 24 24 24 29 8" stroke="#d98c4a" stroke-width="5" fill="none"/><path d="M3 8 v20 M29 8 v20" stroke="#8a5a2b" stroke-width="2"/></svg>`,
      chateau: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 28 V14 h5 v4 h4 v-8 h6 v8 h4 v-4 h5 v14 Z" fill="#e6c98b" stroke="#b8924e"/><path d="M16 10 V3 l5 2 l-5 2" fill="#e2464f" stroke="#a52a33"/></svg>`,
      coquillages_deco: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M4 26 C4 16 14 14 16 26 Z" fill="#ffd5c2" stroke="#d89c84"/><path d="M16 26 C18 12 30 14 28 26 Z" fill="#ffe9a8" stroke="#d6b45a"/></svg>`,
      parasol: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M3 14 C5 4 27 4 29 14 Z" fill="#ff6b6b"/><path d="M10 14 C11 6 21 6 22 14 Z" fill="#fff"/><path d="M16 12 v18" stroke="#8a5a2b" stroke-width="2"/></svg>`,
      bouee: `<svg viewBox="0 0 32 32" aria-hidden="true"><circle cx="16" cy="16" r="12" fill="#ff5252"/><circle cx="16" cy="16" r="6" fill="#bfe9f2"/><path d="M16 4 v6 M16 22 v6 M4 16 h6 M22 16 h6" stroke="#fff" stroke-width="4"/></svg>`,
      coquillage: `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 20C5 12 10 6 16 6s11 6 11 14l-4 5H9z" fill="#ffd9c4" stroke="#d6907a" stroke-width="1.4"/><path d="M16 25V8M12 25l-2-14M20 25l2-14" stroke="#d6907a" stroke-width="1.3" fill="none"/></svg>`,
    };
    return M[id] || feuilleI("#7cc85a", "#3f8a2e");
  }

  // ---- couleurs : phase du jour, météo et saison ----
  function palette(e) {
    const ph = e.ciel.phase, met = e.ciel.meteo, sa = e.ciel.saison || "printemps", nuit = ph === "nuit";
    const CIELS = { aube: ["#6f86cf", "#f4b0a6", "#ffd9a0"], jour: ["#3aa6ea", "#7fcaf2", "#c6ecfb"], coucher: ["#3f3f8c", "#d9688a", "#ffb36b"], nuit: ["#081431", "#13285a", "#24407a"] };
    let c = CIELS[ph];
    if (ph === "jour") c = { ete: ["#2b9be8", "#6cc3f4", "#c4effd"], hiver: ["#6aa2cc", "#a1c6e1", "#dce9f2"], automne: ["#4b94cf", "#8ac0e6", "#cfe5f3"] }[sa] || c;
    if (met === "pluie") c = nuit ? ["#0b1424", "#1a2638", "#2a384d"] : ["#6c7f90", "#93a5b4", "#b9c6d0"];
    else if (met === "nuages" && ph === "jour") c = ["#5d9fd0", "#9ccbeb", "#d2e8f5"];
    const mer = nuit ? ["#173e66", "#0a2240"] : met === "pluie" ? ["#4b8f9e", "#2a6275"] : ph === "coucher" ? ["#4c8fb8", "#244e72"]
      : { ete: ["#35d4d2", "#0a8bb0"], hiver: ["#4fb2bb", "#1a6b88"], automne: ["#3fb8bf", "#147c99"] }[sa] || ["#3fd0d4", "#0f8fb0"];
    const sable = nuit ? "#8c7a58" : { ete: "#f5d995", hiver: "#e8d6aa", automne: "#e6cc8c" }[sa] || "#f1d79a";
    const palme = nuit ? ["#3f7d48", "#2a5a31"] : { hiver: ["#3a8c4a", "#285f31"], automne: ["#33893f", "#22602b"], ete: ["#47a54a", "#2c7330"] }[sa] || ["#3f9a46", "#2b6f31"];
    return { c, mer, sable, palme, nuit, ph, met, sa };
  }

  function etoiles() {
    let s = "";
    for (let i = 0; i < 42; i++) {
      const x = (i * 379 + 97) % 1000 / 10, y = (8 + (i * i * 53 + i * 29) % 215) / 5, g = i % 6 === 0;
      s += `<i class="phb-etoile${g ? " g" : ""}" style="left:${x}%;top:${y}%;animation-delay:-${(i * .37) % 4}s"></i>`;
    }
    return `<div class="phb-l phb-etoiles" aria-hidden="true">${s}</div>`;
  }
  function astre(e, P) {
    const h = e.ciel.heure;
    if (P.nuit) {
      const k = ((h + 24 - 21) % 24) / 9;
      return `<div class="phb-astre phb-lune" style="left:${12 + k * 76}%;top:${30 - Math.sin(Math.PI * k) * 22}%" aria-hidden="true">
        <svg viewBox="0 0 60 60"><circle cx="30" cy="30" r="26" fill="#f4f1d6" opacity=".12"/><circle cx="30" cy="30" r="15" fill="#f4f1d6"/>
        <circle cx="25" cy="27" r="3" fill="#e2ddb8"/><circle cx="34" cy="35" r="2" fill="#e2ddb8"/><circle cx="38" cy="25" r="13" fill="${P.c[0]}"/></svg></div>`;
    }
    const k = Math.min(1, Math.max(0, (h - 6) / 15));
    const coul = P.ph === "jour" ? "#ffe066" : "#ffb347";
    return `<div class="phb-astre phb-soleil" style="left:${9 + k * 82}%;top:${46 - Math.sin(Math.PI * k) * 36}%" aria-hidden="true">
      <svg class="phb-rayons" viewBox="0 0 60 60"><g stroke="${coul}" stroke-width="2.2" stroke-linecap="round" opacity=".7">${Array.from({ length: 12 }, (_, i) =>
        `<path d="M30 4 v6" transform="rotate(${i * 30} 30 30)"/>`).join("")}</g></svg>
      <svg viewBox="0 0 60 60"><circle cx="30" cy="30" r="24" fill="${coul}" opacity=".22"/><circle cx="30" cy="30" r="14" fill="${coul}"/><circle cx="26" cy="26" r="5" fill="#fff" opacity=".35"/></svg></div>`;
  }
  let gouttesHtml = "";
  function gouttes() {
    if (gouttesHtml) return gouttesHtml;
    let d = "";
    for (let i = 0; i < 150; i++) {
      const x = (i * 613 + 41) % 1000, y = (i * i * 37 + i * 11) % 500;
      for (const dy of [0, 500]) d += `M${x} ${y + dy} l-5 22 `;
    }
    return (gouttesHtml = `<path d="${d}" stroke="#dcecff" stroke-opacity=".6" stroke-width="1.6" stroke-linecap="round" vector-effect="non-scaling-stroke"/>`);
  }
  const nuage = c => `<svg viewBox="0 0 200 80" aria-hidden="true"><path d="M30 70 C10 70 2 56 10 44 C14 36 26 32 36 36 C40 18 58 8 80 12 C96 4 122 8 130 26 C148 20 170 28 172 46 C190 48 198 62 188 70 Z" fill="${c}"/><path d="M40 64 C60 60 130 60 178 64" stroke="#000" stroke-opacity=".05" stroke-width="6" fill="none"/></svg>`;

  // décor au sol selon la saison (dans le calque de l'île)
  function solSaison(P) {
    if (P.sa === "printemps") return `<g><path d="M128 432 C122 402 150 388 170 396 C186 382 214 392 210 418 C220 426 214 440 200 440 L136 440 Z" fill="${P.nuit ? "#2f5a34" : "#4ba552"}"/>
      ${[[146, 404], [170, 398], [194, 408], [158, 420], [186, 424]].map(([x, y], i) => `<g transform="translate(${x} ${y})">${[0, 72, 144, 216, 288].map(a => `<ellipse rx="3.4" ry="5" transform="rotate(${a}) translate(0 -3.6)" fill="${i % 2 ? "#ff5a7a" : "#ff8fa8"}"/>`).join("")}<circle r="2" fill="#ffd34d"/></g>`).join("")}
      ${[[420, 470], [520, 478], [660, 466], [740, 472]].map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="3" fill="${i % 2 ? "#ffd23f" : "#fff"}"/><circle cx="${x}" cy="${y}" r="1.2" fill="#f0a500"/>`).join("")}</g>`;
    if (P.sa === "ete") return `<g>${[[612, 468, 1], [372, 474, .7]].map(([x, y, k]) => `<g transform="translate(${x} ${y}) scale(${k})"><path d="M0 -12 L3.5 -4 L12 -3.7 L5.5 2 L7.5 10.5 L0 6 L-7.5 10.5 L-5.5 2 L-12 -3.7 L-3.5 -4 Z" fill="#ff8a3d" stroke="#d35f1c" stroke-width="1.4" stroke-linejoin="round"/><circle r="1.4" fill="#ffd2a8"/></g>`).join("")}</g>`;
    if (P.sa === "automne") return `<g><circle cx="300" cy="428" r="9" fill="#7a5530"/><circle cx="318" cy="433" r="8" fill="#6b4a29"/><circle cx="296" cy="425" r="2" fill="#a8835a"/>
      <path d="M500 458 C540 444 580 446 610 456" stroke="#b58a3c" stroke-width="5" fill="none" stroke-linecap="round"/><path d="M512 455 l-4 -9 M530 450 l-3 -10 M548 448 l-1 -10 M566 449 l1 -10 M584 451 l3 -9" stroke="#c9a04e" stroke-width="3" stroke-linecap="round"/></g>`;
    return `<g><path d="M520 470 l60 -6" stroke="#9a7a52" stroke-width="7" stroke-linecap="round"/><path d="M540 466 l30 -10" stroke="#8a6b45" stroke-width="5" stroke-linecap="round"/></g>`;
  }

  function decor(e) {
    const P = palette(e), { ph, met, nuit } = P;
    const nbNuages = met === "pluie" ? 6 : met === "nuages" ? 5 : 2;
    const coulNuage = met === "pluie" ? "#8a97a3" : nuit ? "#3b4f72" : "#ffffff";
    const deco = new Set(e.deco || []);
    const lumiere = e.lumiere, lampe = e.lampe.possede, lampeOn = e.lampe.possede && e.lampe.allumee;
    const jourSec = !nuit && met !== "pluie";
    const decembre = new Date().getMonth() === 11;
    return `
      <div class="phb-l phb-l-ciel" style="background:linear-gradient(${P.c[0]}, ${P.c[1]} 55%, ${P.c[2]})"></div>
      ${nuit && met !== "pluie" ? etoiles() : ""}${met === "pluie" ? "" : astre(e, P)}
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        ${met === "arc" ? `<g fill="none" stroke-width="10" opacity=".5">${["#ff5a5a", "#ffa94d", "#ffe066", "#69db7c", "#4dabf7", "#9775fa"].map((k, i) => `<path d="M${180 + i * 10} 262 A${330 - i * 10} ${250 - i * 10} 0 0 1 ${820 - i * 10} 262" stroke="${k}"/>`).join("")}</g>` : ""}
        <path d="M770 252 C800 236 860 234 900 252 Z" fill="${nuit ? "#1f3b2e" : "#7fb069"}" opacity=".85"/>
        <rect x="836" y="232" width="18" height="14" fill="${nuit ? "#3b3326" : "#e9d3a4"}"/><path d="M832 233 L845 223 L858 233 Z" fill="${nuit ? "#4a2c22" : "#c0573e"}"/>
        ${nuit ? `<rect x="842" y="237" width="5" height="5" fill="#ffd27a"/>` : ""}
      </svg>
      <div class="phb-l phb-nuages" aria-hidden="true">${Array.from({ length: nbNuages }, (_, i) =>
        `<div class="phb-nuage" style="top:${4 + (i * 37) % 30}%;--d:${70 + i * 23}s;--r:-${(i * 41) % 70}s;width:${16 + (i * 7) % 10}%;opacity:${nuit ? .55 : .94}">${nuage(coulNuage)}</div>`).join("")}</div>
      ${jourSec ? `<div class="phb-l phb-mouettes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-mouette" style="top:${12 + i * 9}%;--d:${26 + i * 9}s;--r:-${i * 11}s">
        <svg viewBox="0 0 40 16"><path d="M2 10 Q11 0 20 9 Q29 0 38 10" fill="none" stroke="#2f3a44" stroke-width="2.4" stroke-linecap="round"/></svg></div>`).join("")}</div>` : ""}
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="phb-mer" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${P.mer[0]}"/><stop offset="1" stop-color="${P.mer[1]}"/></linearGradient></defs>
        <rect x="0" y="250" width="1000" height="250" fill="url(#phb-mer)"/>
        <path d="M0 252 H1000" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
        ${!nuit && met !== "pluie" ? `<path d="M380 262 h240 M420 274 h160 M450 286 h100" stroke="#fff" stroke-opacity=".18" stroke-width="3" stroke-linecap="round"/>` : ""}
      </svg>
      ${!nuit && met !== "pluie" ? `<div class="phb-l phb-reflets" aria-hidden="true">${Array.from({ length: 12 }, (_, i) =>
        `<i style="left:${(i * 83 + 7) % 96}%;top:${54 + (i * 29) % 40}%;animation-delay:-${(i * .7) % 3.4}s"></i>`).join("")}</div>` : ""}
      <div class="phb-l phb-vagues" aria-hidden="true">
        ${[0, 1, 2].map(i => `<div class="phb-vague" style="top:${56 + i * 11}%;--d:${(P.sa === "hiver" ? 7 : 9) + i * 4}s;opacity:${.5 - i * .1}"><svg viewBox="0 0 400 20" preserveAspectRatio="none"><path d="M0 10 Q25 0 50 10 T100 10 T150 10 T200 10 T250 10 T300 10 T350 10 T400 10" fill="none" stroke="#fff" stroke-width="2.4"/></svg></div>`).join("")}
      </div>
      <svg class="phb-l phb-ecume" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <path d="M92 500 C126 382 262 332 500 326 C738 332 874 382 910 500 Z" fill="#d9f6f6" opacity=".55"/>
      </svg>
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <path d="M104 500 C140 386 266 340 500 335 C734 340 860 386 898 500 Z" fill="#a6e2e4" opacity=".7"/>
        <path d="M112 500 C150 392 270 346 500 341 C730 346 852 392 890 500 Z" fill="${P.sable}"/>
        <path d="M150 470 C200 420 330 385 500 381 C670 385 800 420 850 470" stroke="#fff" stroke-opacity=".18" stroke-width="10" fill="none"/>
        <path d="M200 470 q20 -6 40 0 M560 476 q24 -6 48 0 M700 452 q16 -5 32 0 M330 445 q14 -4 28 0" stroke="#000" stroke-opacity=".07" stroke-width="3" fill="none" stroke-linecap="round"/>
        <ellipse cx="420" cy="440" rx="${P.sa === "automne" ? 70 : 58}" ry="${P.sa === "automne" ? 15 : 13}" fill="${nuit ? "#2d5b78" : "#8fd6ea"}" stroke="${nuit ? "#5c7f8f" : "#d8f3f8"}" stroke-width="3"/>
        <ellipse cx="404" cy="436" rx="16" ry="3" fill="#fff" opacity="${nuit ? .1 : .45}"/>
        <path d="M590 410 C588 380 612 362 650 362 C690 362 714 380 712 410 Z" fill="${nuit ? "#5b5550" : "#a79a8e"}"/>
        <path d="M596 408 C600 396 612 390 626 390" stroke="#000" stroke-opacity=".1" stroke-width="6" fill="none" stroke-linecap="round"/>
        <path d="M600 396 C610 374 640 368 664 372" stroke="${nuit ? "#79716a" : "#cbc0b4"}" stroke-width="5" fill="none" stroke-linecap="round"/>
        <ellipse cx="650" cy="412" rx="64" ry="5" fill="#000" opacity=".08"/>
        ${solSaison(P)}
        <path d="M262 420 C258 360 246 290 222 196" stroke="#8a5a2b" stroke-width="16" fill="none" stroke-linecap="round"/>
        <path d="M262 420 C258 360 246 290 222 196" stroke="#a87442" stroke-width="16" fill="none" stroke-dasharray="4 14" stroke-linecap="round"/>
        <path d="M258 420 C254 360 243 292 220 200" stroke="#000" stroke-opacity=".12" stroke-width="4" fill="none"/>
        <ellipse cx="262" cy="424" rx="34" ry="5" fill="#000" opacity=".08"/>
        <path d="M330 430 V370" stroke="#6b4a29" stroke-width="5"/>
        <g><rect x="319" y="352" width="22" height="22" rx="4" fill="${lumiere ? "#ffd27a" : "#5a5040"}" stroke="#6b4a29" stroke-width="3"/>
          ${lumiere && nuit ? `<circle cx="330" cy="363" r="40" fill="#ffd27a" opacity=".22"/>` : ""}</g>
        ${lampe ? `<g><path d="M178 432 V262 L196 246" stroke="#555c63" stroke-width="5" fill="none"/><path d="M186 236 L210 228 L206 254 Z" fill="#c45a2a" stroke="#8a3d1a" stroke-width="2"/>
          ${lampeOn ? `<circle cx="204" cy="240" r="7" fill="#ff8a3d"/><path d="M206 236 L250 186 L232 232 Z" fill="#ff9248" opacity=".25"/><circle cx="222" cy="206" r="34" fill="#ff9248" opacity=".14"/>` : `<circle cx="204" cy="240" r="6" fill="#6b4a3a"/>`}</g>` : ""}
        ${deco.has("hamac") ? `<path d="M342 300 V430" stroke="#6b4a29" stroke-width="6"/><path d="M250 298 C270 346 320 348 340 302" stroke="#e0894a" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M256 304 C274 340 316 342 336 306" stroke="#f2b27a" stroke-width="3" fill="none" stroke-dasharray="6 6"/>` : ""}
        ${deco.has("parasol") ? `<path d="M470 438 V346" stroke="#8a5a2b" stroke-width="4"/><path d="M412 352 C420 312 520 312 528 352 Z" fill="#ff6b6b"/><path d="M444 352 C448 320 492 320 496 352 Z" fill="#fff"/><ellipse cx="470" cy="440" rx="40" ry="5" fill="#000" opacity=".08"/>` : ""}
        ${deco.has("chateau") ? `<path d="M548 470 V446 h10 v8 h8 v-16 h12 v16 h8 v-8 h10 v24 Z" fill="#e6c98b" stroke="#b8924e" stroke-width="2"/><path d="M572 438 V424 l12 4 l-12 4" fill="#e2464f"/>` : ""}
        ${deco.has("coquillages_deco") ? `<g stroke="#c99a84" stroke-width="1.5">${[690, 716, 742, 768].map((x, i) => `<path d="M${x} 474 C${x} 462 ${x + 16} 462 ${x + 16} 474 Z" fill="${["#ffd5c2", "#ffe9a8", "#fff", "#ffc9d6"][i]}"/>`).join("")}</g>` : ""}
        ${deco.has("bouee") ? `<g><circle cx="950" cy="372" r="22" fill="#ff5252"/><circle cx="950" cy="372" r="10" fill="${P.mer[0]}"/><path d="M950 350 v10 M950 384 v10 M928 372 h10 M962 372 h10" stroke="#fff" stroke-width="6"/></g>` : ""}
        ${e.veto ? `<g><path d="M760 300 h120 l-16 22 h-88 Z" fill="#a0612f" stroke="#6b3e1a" stroke-width="3"/>
          <ellipse cx="830" cy="290" rx="24" ry="15" fill="#6aa84f" stroke="#3f7a2e" stroke-width="3"/><circle cx="858" cy="286" r="8" fill="#9ccc65" stroke="#3f7a2e" stroke-width="2"/>
          <rect x="852" y="272" width="14" height="7" rx="2" fill="#fff" stroke="#c0392b"/><path d="M859 273 v5 M856.5 275.5 h5" stroke="#e2464f" stroke-width="1.6"/></g>` : ""}
      </svg>
      <svg class="phb-l phb-palmes${!nuit && met !== "pluie" ? " vent" : ""}" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <g fill="${P.palme[0]}" stroke="${P.palme[1]}" stroke-width="2">
          <path d="M222 196 C180 170 130 176 96 206 C140 192 180 196 222 200 Z"/><path d="M222 196 C200 150 160 134 120 140 C164 152 196 170 222 200 Z"/>
          <path d="M222 196 C240 150 280 136 322 146 C280 156 246 174 222 200 Z"/><path d="M222 196 C270 176 318 184 350 214 C304 200 262 198 222 202 Z"/>
          <path d="M222 196 C222 160 236 130 262 112 C246 140 236 166 226 200 Z"/></g>
        <g fill="none" stroke="#fff" stroke-opacity=".18" stroke-width="2"><path d="M218 196 C190 180 150 180 116 198"/><path d="M226 194 C250 166 280 154 312 152"/></g>
        <circle cx="214" cy="206" r="9" fill="#7a5530"/><circle cx="230" cy="208" r="9" fill="#6b4a29"/><circle cx="211" cy="203" r="2.4" fill="#a8835a"/>
      </svg>
      ${decembre ? `<div class="phb-l phb-guirlande${nuit ? " nuit" : ""}" aria-hidden="true">${[[12.2, 37.6], [14.6, 34.6], [17.4, 33.8], [20.2, 35.4], [22.8, 38.6], [25.2, 36.4], [27.8, 33.2], [30.2, 35], [32.8, 40]].map(([x, y], i) =>
        `<i style="left:${x}%;top:${y}%;--k:${["#ff5a5a", "#ffd34d", "#6fe07a", "#5ab4ff"][i % 4]};animation-delay:-${i * .4}s"></i>`).join("")}</div>` : ""}
      <div class="phb-l phb-crabes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-crabe" style="left:${22 + i * 44}%;top:${86 - i * 4}%;--d:${7 + i * 3}s;--r:-${i * 2}s">
        <svg viewBox="0 0 40 24"><g stroke="#b9381f" stroke-width="2" stroke-linecap="round"><path d="M8 16 l-6 5 M12 18 l-4 5 M32 16 l6 5 M28 18 l4 5"/></g>
        <ellipse cx="20" cy="14" rx="12" ry="7" fill="#ff6a3d" stroke="#b9381f" stroke-width="1.5"/><ellipse cx="17" cy="11" rx="5" ry="2" fill="#fff" opacity=".3"/><circle cx="16" cy="6" r="2.4" fill="#fff" stroke="#b9381f"/><circle cx="24" cy="6" r="2.4" fill="#fff" stroke="#b9381f"/>
        <circle cx="16" cy="6" r="1" fill="#222"/><circle cx="24" cy="6" r="1" fill="#222"/><path d="M6 10 q-4 -6 2 -8 M34 10 q4 -6 -2 -8" stroke="#ff6a3d" stroke-width="3" fill="none"/></svg></div>`).join("")}</div>
      ${jourSec && (P.sa === "printemps" || P.sa === "ete") ? `<div class="phb-l phb-papillons" aria-hidden="true">${[0, 1].map(i => `<div class="phb-papillon" style="left:${30 + i * 30}%;top:${58 - i * 8}%;--d:${11 + i * 4}s;--r:-${i * 3}s">
        <svg viewBox="0 0 24 18"><g class="phb-ailes"><path d="M12 9 C8 1 1 2 2 8 C3 12 9 11 12 9 Z M12 9 C16 1 23 2 22 8 C21 12 15 11 12 9 Z" fill="${i ? "#ffb347" : "#ff7ab6"}"/><path d="M12 9 C9 13 5 16 6 12 M12 9 C15 13 19 16 18 12" fill="${i ? "#ffd27a" : "#ffb0d4"}"/></g><path d="M12 4 v10" stroke="#3b2a1a" stroke-width="1.4" stroke-linecap="round"/></svg></div>`).join("")}</div>` : ""}
      ${nuit && met !== "pluie" && P.sa !== "hiver" ? `<div class="phb-l phb-lucioles" aria-hidden="true">${Array.from({ length: 7 }, (_, i) =>
        `<i style="left:${18 + (i * 37) % 60}%;top:${55 + (i * 13) % 28}%;--d:${5 + i % 3 * 2}s;animation-delay:-${i * 1.1}s"></i>`).join("")}</div>` : ""}
      ${met === "pluie" ? `<div class="phb-l phb-pluie" aria-hidden="true"><svg viewBox="0 0 1000 1000" preserveAspectRatio="none">${gouttes()}</svg></div>` : ""}
      <div class="phb-l phb-nuit" style="opacity:${nuit ? (lumiere ? .36 : .56) : ph === "coucher" ? .14 : ph === "aube" ? .1 : 0}" aria-hidden="true"></div>
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
      sc.parentElement.style.background = `linear-gradient(${P.c[0]}, ${P.c[1]} 27%, ${P.c[2]} 50%, ${P.mer[0]} 50%, ${P.mer[1]})`;
    }
    const perso = sc.querySelector(".phb-perso");
    perso.hidden = absent();
    sc.querySelector(".phb-crottes").innerHTML = absent() ? "" : Array.from({ length: e.crottes }, (_, i) =>
      `<button class="phb-crotte" style="left:${[44, 58, 39, 66][i]}%;top:${[92, 94, 85, 89][i]}%" data-phb="nettoyer" aria-label="Ramasser la crotte">
       <svg viewBox="0 0 20 16"><path d="M3 15 C1 15 1 12 4 11 C3 9 5 7 8 8 C8 5 11 3 13 5 C15 4 17 7 15 9 C18 10 19 15 16 15 Z" fill="#8a5a33" stroke="#5e3b1e"/></svg></button>`).join("");
    if (absent()) return;
    const p = place(e, reaction);
    perso.style.setProperty("--x", p.x);
    perso.style.setProperty("--y", p.y);
    perso.style.setProperty("--rot", (p.rot || 0) + "deg");
    const h = e.humeur === "appel" ? "calme" : e.humeur;
    const html = D.svg({ stade: e.stade, variante: e.variante, humeur: e.dort ? "dort" : reaction === "refus" ? "grognon" : h, pose: p.pose,
      portes: e.portes, mue: e.mue, ventre: e.ventre_rond, malade: !!e.malade, froid: e.jauges.chaleur < 35, label: e.titre, fendu: e.stade === "oeuf" && e.age_jours > .004 });
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
      perso.classList.toggle("gauche", cible < flaneX);
      perso.classList.add("marche");
      perso.style.transitionDuration = duree.toFixed(1) + "s";
      flaneX = cible;
      rendreScene();
      setTimeout(() => { perso.classList.remove("marche"); perso.style.transitionDuration = ""; }, duree * 1000 + 100);
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
    return `<span class="phb-medaillon" aria-hidden="true">${e.stade === "oeuf" ? D.svg({ stade: "oeuf" })
      : D.svg({ stade: e.stade, variante: e.variante, humeur: e.dort ? "dort" : "joyeux", portes: e.portes, malade: !!e.malade, label: "" })}</span>`;
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
    if (e.appel && e.appel.type === "caprice") return "Philibert te regarde avec insistance… a-t-il vraiment besoin de quelque chose ?";
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
    const appel = e.appel ? `<span class="phb-pastille appel" title="${e.appel.type === "caprice" ? "Il réclame de l'attention… mais a-t-il vraiment besoin de quelque chose ?" : "Il a besoin de toi"}">${ico("bulle")}Il t'appelle</span>` : "";
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
        return [id, o.nom, o.prix, o.texte, id === "remede" ? `en réserve : ${e.inventaire.remede || 0}` : a ? "déjà à toi" : "", a, false];
      });
    }
    return `${titre("panier", "Boutique de l'île", `· tu as ${e.coquillages} coquillage${e.coquillages > 1 ? "s" : ""}`)}
      <div class="phb-onglets" role="tablist">${Object.entries(onglets).map(([k, t]) => `<button class="phb-b${k === boutiqueOnglet ? " phb-on" : ""}" role="tab" aria-selected="${k === boutiqueOnglet}" data-phb="boutique-onglet" data-o="${k}">${t}</button>`).join("")}</div>
      <div class="phb-grille">${items.map(([id, nom, prix, texte, info, possede, promo]) => `<div class="phb-carte phb-article${promo ? " promo" : ""}">
        ${promo ? `<span class="phb-ruban">de saison · −1</span>` : ""}
        <span class="phb-ic">${icone(id)}</span><span>${esc(nom)}</span><small>${esc(texte)}</small>${info ? `<small class="phb-info">${esc(info)}</small>` : ""}
        <button class="phb-b phb-prim" data-phb="acheter" data-article="${id}" ${possede ? "disabled" : ""} aria-label="Acheter ${esc(nom)} pour ${prix} coquillages">${possede ? "✔ À toi" : `<span class="phb-ic-mini">${icone("coquillage")}</span>${prix}`}</button></div>`).join("")}</div>
      ${boutiqueOnglet === "nourriture" ? `<p class="phb-astuce">${ico("nourrir")}<span>Pas d'insectes, de viande ni de croquettes ici : Philibert est herbivore. Le trèfle de l'île est toujours gratuit.</span></p>` : ""}`;
  }
  function feuilleGarde() {
    const slots = { tete: "Tête", yeux: "Yeux", cou: "Cou" };
    const parSlot = s => e.accessoires.filter(a => cat.objets[a].emplacement === s);
    return `${titre("chapeau", "Garde-robe")}<div class="phb-garde"><div class="phb-apercu">${D.svg({ stade: e.stade === "oeuf" ? "bebe" : e.stade, variante: e.variante, humeur: "joyeux", portes: e.portes, label: "Aperçu de Philibert" })}</div>
      <div>${Object.entries(slots).map(([s, n]) => `<div class="phb-groupe">${n}</div><div class="phb-ligne">${parSlot(s).map(a => `<button class="phb-b${e.portes[s] === a ? " phb-on" : ""}" data-phb="${e.portes[s] === a ? "retirer" : "porter"}" data-article="${a}" data-emplacement="${s}" aria-pressed="${e.portes[s] === a}">
        <span class="phb-ic-mini">${icone(a)}</span>${esc(cat.objets[a].nom)}</button>`).join("") || `<small class="phb-gris">Rien pour l'instant (voir la boutique).</small>`}</div>`).join("")}</div></div>`;
  }
  function portrait(x) {
    return `<div class="phb-portrait">${D.svg({ stade: x.stade, variante: x.variante, portes: x.portes, humeur: "joyeux", label: x.titre })}</div>`;
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
    return `<div class="phb-postale"><div class="phb-postale-img" aria-hidden="true"><svg viewBox="0 0 120 80"><rect width="120" height="80" fill="#bfe9f2"/><path d="M0 52 H120 V80 H0Z" fill="#3fc1c9"/>
      <path d="M20 80 C30 58 90 58 100 80Z" fill="#f1d79a"/><ellipse cx="60" cy="56" rx="20" ry="12" fill="#6aa84f" stroke="#3f7a2e" stroke-width="2"/><circle cx="84" cy="52" r="7" fill="#9ccc65" stroke="#3f7a2e" stroke-width="2"/>
      <circle cx="86" cy="50" r="1.2" fill="#222"/><rect x="78" y="40" width="12" height="6" rx="2" fill="#fff" stroke="#c0392b"/><path d="M84 41 v4 M82 43 h4" stroke="#e2464f" stroke-width="1.4"/>
      <circle cx="98" cy="18" r="9" fill="#ffe066"/></svg></div>
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
          <div class="phb-effets" aria-hidden="true"></div>
          <div class="phb-bandeaux" aria-live="polite"></div></div></div>
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
  dlg.addEventListener("close", () => { clearInterval(pollT); clearTimeout(flanerT); feuille = null; if (window.PhilibertJeux) window.PhilibertJeux.arreter(); rendreFeuille(); });
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
  window.PhilibertIle = { ouvrir, appliquer, action, icone, fermer: () => dlg.close() };
})();
