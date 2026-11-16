"use strict";
/* L'île de Philibert (fenêtre ouverte par un clic sur l'iguane du haut, ou depuis ⚙ Réglages).
   Une île au milieu de la mer : plage, palmier (il y dort), rocher chaud, flaque, mer turquoise et vagues, crabes,
   mouettes, ciel qui suit l'heure réelle (aube, jour, coucher, nuit étoilée) et la météo de l'île (nuages, pluie,
   arc-en-ciel). En dessous : ses jauges, « ce qui ne va pas », et les soins. Feuilles : nourrir, bain, jouer,
   boutique, garde-robe, carnet, réglages ; carte postale de la tortue vétérinaire à son retour.
   Tout est calculé par le serveur (philibert.py) : la page n'envoie que des intentions.
   Décor en couches HTML : seules les couches animées (vagues, nuages, pluie, crabes, mouettes) bougent, par
   transform (rien en JavaScript). Animations coupées en mode jeu et avec « réduire les animations ». */
(() => {
  const D = window.PhilibertDessin;
  if (!D) return;
  const dlg = document.createElement("dialog");
  dlg.className = "phb-dlg";
  dlg.setAttribute("aria-labelledby", "phb-titre");
  document.body.appendChild(dlg);
  let e = null, cat = null, cleScene = "", feuille = null, message = "", reaction = "", reactionT = 0, pollT = 0, flanerT = 0, flaneX = 50;
  let carnetOnglet = "historique", boutiqueOnglet = "nourriture", carnetDonnees = null;

  const JAUGES = [
    ["faim", "Faim", "🍃"], ["bonheur", "Bonheur", "♥"], ["energie", "Énergie", "⚡"],
    ["proprete", "Propreté", "✧"], ["sante", "Santé", "✚"], ["chaleur", "Chaleur", "☀"],
  ];
  const fmtH = s => { const h = Math.floor(s / 3600), m = Math.round(s % 3600 / 60); return h ? `${h} h ${String(m).padStart(2, "0")}` : `${m} min`; };
  const age = j => j < 1 ? `${Math.max(0, Math.round(j * 24))} h` : `${j.toFixed(j < 10 ? 1 : 0).replace(".", ",")} jour${j >= 2 ? "s" : ""}`;
  const poids = g => g >= 1000 ? `${(g / 1000).toFixed(2).replace(".", ",")} kg` : `${g} g`;

  // ---- sons (synthèse très courte, seulement après un geste, si les sons sont activés) ----
  let ctxAudio = null;
  function son(type) {
    if (!e || !e.reglages.sons) return;
    try {
      ctxAudio = ctxAudio || new (window.AudioContext || window.webkitAudioContext)();
      const t = ctxAudio.currentTime, o = ctxAudio.createOscillator(), g = ctxAudio.createGain();
      const notes = { croc: [520, 380, "square", .05], plouf: [420, 140, "sine", .25], ding: [880, 1320, "sine", .18], pop: [600, 700, "triangle", .06],
        non: [300, 220, "sawtooth", .12], joie: [660, 990, "sine", .2] }[type] || [600, 600, "sine", .05];
      o.type = notes[2];
      o.frequency.setValueAtTime(notes[0], t);
      o.frequency.exponentialRampToValueAtTime(notes[1], t + notes[3]);
      g.gain.setValueAtTime(.0001, t);
      g.gain.exponentialRampToValueAtTime(.08, t + .01);
      g.gain.exponentialRampToValueAtTime(.0001, t + notes[3] + .05);
      o.connect(g).connect(ctxAudio.destination);
      o.start(t); o.stop(t + notes[3] + .08);
    } catch (x) { /* pas de son : tant pis */ }
  }
  window.PhilibertSon = son;

  // ---- icônes dessinées (aliments, objets) ----
  function icone(id) {
    const a = cat && cat.aliments[id];
    const feuille = (c, d) => `<svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 27 C5 12 14 4 28 4 C28 18 20 27 5 27Z" fill="${c}" stroke="${d}" stroke-width="1.2"/><path d="M6 26 C12 18 18 12 25 7" stroke="${d}" stroke-width="1.2" fill="none"/></svg>`;
    const fleur = (c, m) => `<svg viewBox="0 0 32 32" aria-hidden="true">${[0, 72, 144, 216, 288].map(r => `<ellipse cx="16" cy="9" rx="5" ry="7" fill="${c}" transform="rotate(${r} 16 16)"/>`).join("")}<circle cx="16" cy="16" r="4" fill="${m}"/></svg>`;
    const fruit = (c, f) => `<svg viewBox="0 0 32 32" aria-hidden="true"><ellipse cx="16" cy="18" rx="10" ry="${f ? 8 : 10}" fill="${c}" stroke="rgba(0,0,0,.25)"/><path d="M16 8 q2 -4 6 -4" stroke="#6b4b2a" stroke-width="2" fill="none"/><ellipse cx="20" cy="6" rx="4" ry="2" fill="#5cae4f"/><ellipse cx="12" cy="14" rx="3" ry="2" fill="#fff" opacity=".35"/></svg>`;
    const M = {
      trefle: `<svg viewBox="0 0 32 32" aria-hidden="true">${[[16, 10], [10, 18], [22, 18]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="6" fill="#6cc24a" stroke="#3f8a2e"/>`).join("")}<path d="M16 18 v11" stroke="#3f8a2e" stroke-width="2"/></svg>`,
      feuilles_pissenlit: feuille("#7cc85a", "#3f8a2e"), feuilles_murier: feuille("#4fae4f", "#2f7a37"), chou_vert: feuille("#9ad47a", "#4f8f3a"),
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
    };
    return M[id] || (a ? feuille("#7cc85a", "#3f8a2e") : "");
  }

  // ---- décor ----
  const CIELS = {
    aube: ["#6f86cf", "#f4b0a6", "#ffd9a0"], jour: ["#3aa6ea", "#7fcaf2", "#c6ecfb"], coucher: ["#3f3f8c", "#d9688a", "#ffb36b"], nuit: ["#081431", "#13285a", "#24407a"],
  };
  function ciel(ph, met) {
    let c = CIELS[ph];
    if (met === "pluie") c = ph === "nuit" ? ["#0b1424", "#1a2638", "#2a384d"] : ["#6c7f90", "#93a5b4", "#b9c6d0"];
    else if (met === "nuages" && ph === "jour") c = ["#5d9fd0", "#9ccbeb", "#d2e8f5"];
    return c;
  }
  function astre(e) {
    const h = e.ciel.heure, ph = e.ciel.phase;
    if (ph === "nuit") {
      const k = ((h + 24 - 21) % 24) / 9;                  // 21 h → 6 h
      const x = 120 + k * 760, y = 150 - Math.sin(Math.PI * k) * 110;
      return `<g><circle cx="${x}" cy="${y}" r="22" fill="#f4f1d6"/><circle cx="${x + 9}" cy="${y - 5}" r="19" fill="${ciel("nuit", e.ciel.meteo)[0]}"/></g>`;
    }
    const k = Math.min(1, Math.max(0, (h - 6) / 15));
    const x = 90 + k * 820, y = 230 - Math.sin(Math.PI * k) * 180;
    const c = ph === "jour" ? "#ffe066" : "#ffb347";
    return `<g class="phb-soleil"><circle cx="${x}" cy="${y}" r="54" fill="${c}" opacity=".22"/><circle cx="${x}" cy="${y}" r="30" fill="${c}"/></g>`;
  }
  function etoiles() {
    let s = "";
    for (let i = 0; i < 46; i++) {
      const x = (i * 379 + 97) % 1000, y = 8 + (i * i * 53 + i * 29) % 215, r = i % 5 === 0 ? 1.8 : 1.1;
      s += `<circle cx="${x}" cy="${y}" r="${r}" fill="#fff"/>`;
    }
    return s;
  }
  // gouttes de pluie : deux moitiés identiques (la couche descend d'une moitié, en boucle, sans saut)
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
  const nuage = (c) => `<svg viewBox="0 0 200 80" aria-hidden="true"><path d="M30 70 C10 70 2 56 10 44 C14 36 26 32 36 36 C40 18 58 8 80 12 C96 4 122 8 130 26 C148 20 170 28 172 46 C190 48 198 62 188 70 Z" fill="${c}"/></svg>`;

  const couleurMer = (ph, met) => ph === "nuit" ? ["#173e66", "#0a2240"] : met === "pluie" ? ["#4b8f9e", "#2a6275"] : ph === "coucher" ? ["#4c8fb8", "#244e72"] : ["#3fd0d4", "#0f8fb0"];
  function decor(e) {
    const ph = e.ciel.phase, met = e.ciel.meteo, nuit = ph === "nuit";
    const c = ciel(ph, met);
    const mer = couleurMer(ph, met);
    const nbNuages = met === "pluie" ? 6 : met === "nuages" ? 5 : 2;
    const coulNuage = met === "pluie" ? "#8a97a3" : nuit ? "#3b4f72" : "#ffffff";
    const deco = new Set(e.deco || []);
    const lumiere = e.lumiere, lampe = e.lampe.possede, lampeOn = e.lampe.possede && e.lampe.allumee;
    const absent = ["veto", "pension"].includes(e.niveau);
    return `
      <div class="phb-l phb-l-ciel" style="background:linear-gradient(${c[0]}, ${c[1]} 55%, ${c[2]})"></div>
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        ${nuit && met !== "pluie" ? etoiles() : ""}${met === "pluie" ? "" : astre(e)}
        ${met === "arc" ? `<g fill="none" stroke-width="10" opacity=".55">${["#ff5a5a", "#ffa94d", "#ffe066", "#69db7c", "#4dabf7", "#9775fa"].map((k, i) => `<path d="M${180 + i * 10} 262 A${330 - i * 10} ${250 - i * 10} 0 0 1 ${820 - i * 10} 262" stroke="${k}"/>`).join("")}</g>` : ""}
        <path d="M770 252 C800 236 860 234 900 252 Z" fill="${nuit ? "#1f3b2e" : "#7fb069"}" opacity=".85"/>
        <rect x="836" y="232" width="18" height="14" fill="${nuit ? "#3b3326" : "#e9d3a4"}"/><path d="M832 233 L845 223 L858 233 Z" fill="${nuit ? "#4a2c22" : "#c0573e"}"/>
        ${nuit ? `<rect x="842" y="237" width="5" height="5" fill="#ffd27a"/>` : ""}
      </svg>
      <div class="phb-l phb-nuages" aria-hidden="true">${Array.from({ length: nbNuages }, (_, i) =>
        `<div class="phb-nuage" style="top:${4 + (i * 37) % 30}%;--d:${70 + i * 23}s;--r:-${(i * 41) % 70}s;width:${16 + (i * 7) % 10}%;opacity:${nuit ? .55 : .92}">${nuage(coulNuage)}</div>`).join("")}</div>
      ${!nuit && met !== "pluie" ? `<div class="phb-l phb-mouettes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-mouette" style="top:${12 + i * 9}%;--d:${26 + i * 9}s;--r:-${i * 11}s">
        <svg viewBox="0 0 40 16"><path class="phb-aile" d="M2 10 Q11 0 20 9 Q29 0 38 10" fill="none" stroke="#2f3a44" stroke-width="2.4" stroke-linecap="round"/></svg></div>`).join("")}</div>` : ""}
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <defs><linearGradient id="phb-mer" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${mer[0]}"/><stop offset="1" stop-color="${mer[1]}"/></linearGradient></defs>
        <rect x="0" y="250" width="1000" height="250" fill="url(#phb-mer)"/>
        <path d="M0 252 H1000" stroke="#fff" stroke-opacity=".35" stroke-width="2"/>
      </svg>
      <div class="phb-l phb-vagues" aria-hidden="true">
        ${[0, 1, 2].map(i => `<div class="phb-vague" style="top:${56 + i * 11}%;--d:${9 + i * 4}s;opacity:${.5 - i * .1}"><svg viewBox="0 0 400 20" preserveAspectRatio="none"><path d="M0 10 Q25 0 50 10 T100 10 T150 10 T200 10 T250 10 T300 10 T350 10 T400 10" fill="none" stroke="#fff" stroke-width="2.4"/></svg></div>`).join("")}
      </div>
      <svg class="phb-l" viewBox="0 0 1000 500" preserveAspectRatio="none" aria-hidden="true">
        <path d="M96 500 C130 384 262 336 500 330 C738 336 870 384 906 500 Z" fill="#9fdbe0" opacity=".55"/>
        <path d="M112 500 C150 392 270 346 500 341 C730 346 852 392 890 500 Z" fill="${nuit ? "#8c7a58" : "#f1d79a"}"/>
        <path d="M200 470 q20 -6 40 0 M560 476 q24 -6 48 0 M700 452 q16 -5 32 0 M330 445 q14 -4 28 0" stroke="${nuit ? "#76664a" : "#dcbc78"}" stroke-width="3" fill="none" stroke-linecap="round"/>
        <ellipse cx="420" cy="440" rx="58" ry="13" fill="${nuit ? "#2d5b78" : "#8fd6ea"}" stroke="${nuit ? "#5c7f8f" : "#d8f3f8"}" stroke-width="3"/>
        <path d="M590 410 C588 380 612 362 650 362 C690 362 714 380 712 410 Z" fill="${nuit ? "#5b5550" : "#a79a8e"}"/>
        <path d="M600 396 C610 374 640 368 664 372" stroke="${nuit ? "#79716a" : "#c9beb2"}" stroke-width="5" fill="none" stroke-linecap="round"/>
        ${!nuit && ["soleil", "arc"].includes(met) ? `<path d="M610 356 q6 -10 0 -20 M650 352 q6 -10 0 -20 M690 356 q6 -10 0 -20" stroke="#ff9f43" stroke-width="2.4" fill="none" opacity=".55" class="phb-chaleur"/>` : ""}
        <path d="M262 420 C258 360 246 290 222 196" stroke="#8a5a2b" stroke-width="16" fill="none" stroke-linecap="round"/>
        <path d="M262 420 C258 360 246 290 222 196" stroke="#a87442" stroke-width="16" fill="none" stroke-dasharray="4 14" stroke-linecap="round"/>
        <g class="phb-palmes" fill="${nuit ? "#2d5a33" : "#3f9a46"}" stroke="${nuit ? "#1f3f24" : "#2b6f31"}" stroke-width="2">
          <path d="M222 196 C180 170 130 176 96 206 C140 192 180 196 222 200 Z"/><path d="M222 196 C200 150 160 134 120 140 C164 152 196 170 222 200 Z"/>
          <path d="M222 196 C240 150 280 136 322 146 C280 156 246 174 222 200 Z"/><path d="M222 196 C270 176 318 184 350 214 C304 200 262 198 222 202 Z"/>
          <path d="M222 196 C222 160 236 130 262 112 C246 140 236 166 226 200 Z"/></g>
        <circle cx="214" cy="206" r="9" fill="#7a5530"/><circle cx="230" cy="208" r="9" fill="#6b4a29"/>
        <path d="M330 430 V370" stroke="#6b4a29" stroke-width="5"/>
        <g class="phb-lanterne"><rect x="319" y="352" width="22" height="22" rx="4" fill="${lumiere ? "#ffd27a" : "#5a5040"}" stroke="#6b4a29" stroke-width="3"/>
          ${lumiere && nuit ? `<circle cx="330" cy="363" r="40" fill="#ffd27a" opacity=".22"/>` : ""}</g>
        ${lampe ? `<g><path d="M178 432 V262 L196 246" stroke="#555c63" stroke-width="5" fill="none"/><path d="M186 236 L210 228 L206 254 Z" fill="#c45a2a" stroke="#8a3d1a" stroke-width="2"/>
          ${lampeOn ? `<circle cx="204" cy="240" r="7" fill="#ff8a3d"/><path d="M206 236 L250 186 L232 232 Z" fill="#ff9248" opacity=".25"/><circle cx="222" cy="206" r="34" fill="#ff9248" opacity=".14"/>` : `<circle cx="204" cy="240" r="6" fill="#6b4a3a"/>`}</g>` : ""}
        ${deco.has("hamac") ? `<path d="M342 300 V430" stroke="#6b4a29" stroke-width="6"/><path d="M250 298 C270 346 320 348 340 302" stroke="#e0894a" stroke-width="10" fill="none" stroke-linecap="round"/><path d="M256 304 C274 340 316 342 336 306" stroke="#f2b27a" stroke-width="3" fill="none" stroke-dasharray="6 6"/>` : ""}
        ${deco.has("parasol") ? `<path d="M470 438 V346" stroke="#8a5a2b" stroke-width="4"/><path d="M412 352 C420 312 520 312 528 352 Z" fill="#ff6b6b"/><path d="M444 352 C448 320 492 320 496 352 Z" fill="#fff"/>` : ""}
        ${deco.has("chateau") ? `<path d="M548 470 V446 h10 v8 h8 v-16 h12 v16 h8 v-8 h10 v24 Z" fill="#e6c98b" stroke="#b8924e" stroke-width="2"/><path d="M572 438 V424 l12 4 l-12 4" fill="#e2464f"/>` : ""}
        ${deco.has("coquillages_deco") ? `<g stroke="#c99a84" stroke-width="1.5">${[690, 716, 742, 768].map((x, i) => `<path d="M${x} 474 C${x} 462 ${x + 16} 462 ${x + 16} 474 Z" fill="${["#ffd5c2", "#ffe9a8", "#fff", "#ffc9d6"][i]}"/>`).join("")}</g>` : ""}
        ${deco.has("bouee") ? `<g class="phb-flotte"><circle cx="950" cy="372" r="22" fill="#ff5252"/><circle cx="950" cy="372" r="10" fill="${mer[0]}"/><path d="M950 350 v10 M950 384 v10 M928 372 h10 M962 372 h10" stroke="#fff" stroke-width="6"/></g>` : ""}
        ${e.veto ? `<g class="phb-barque"><path d="M760 300 h120 l-16 22 h-88 Z" fill="#a0612f" stroke="#6b3e1a" stroke-width="3"/>
          <ellipse cx="830" cy="290" rx="24" ry="15" fill="#6aa84f" stroke="#3f7a2e" stroke-width="3"/><circle cx="858" cy="286" r="8" fill="#9ccc65" stroke="#3f7a2e" stroke-width="2"/>
          <rect x="852" y="272" width="14" height="7" rx="2" fill="#fff" stroke="#c0392b"/><path d="M859 273 v5 M856.5 275.5 h5" stroke="#e2464f" stroke-width="1.6"/></g>` : ""}
      </svg>
      <div class="phb-l phb-crabes" aria-hidden="true">${[0, 1].map(i => `<div class="phb-crabe" style="left:${22 + i * 44}%;top:${86 - i * 4}%;--d:${7 + i * 3}s;--r:-${i * 2}s">
        <svg viewBox="0 0 40 24"><g stroke="#b9381f" stroke-width="2" stroke-linecap="round"><path d="M8 16 l-6 5 M12 18 l-4 5 M32 16 l6 5 M28 18 l4 5"/></g>
        <ellipse cx="20" cy="14" rx="12" ry="7" fill="#ff6a3d" stroke="#b9381f" stroke-width="1.5"/><circle cx="16" cy="6" r="2.4" fill="#fff" stroke="#b9381f"/><circle cx="24" cy="6" r="2.4" fill="#fff" stroke="#b9381f"/>
        <circle cx="16" cy="6" r="1" fill="#222"/><circle cx="24" cy="6" r="1" fill="#222"/><path d="M6 10 q-4 -6 2 -8 M34 10 q4 -6 -2 -8" stroke="#ff6a3d" stroke-width="3" fill="none"/></svg></div>`).join("")}</div>
      ${met === "pluie" ? `<div class="phb-l phb-pluie" aria-hidden="true"><svg viewBox="0 0 1000 1000" preserveAspectRatio="none">${gouttes()}</svg></div>` : ""}
      <div class="phb-l phb-nuit" style="opacity:${nuit ? (lumiere ? .38 : .58) : ph === "coucher" ? .14 : ph === "aube" ? .1 : 0}" aria-hidden="true"></div>
      ${absent ? `<div class="phb-l phb-pancarte" role="status"><div>${e.veto
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
    const cle = [e.ciel.phase, e.ciel.meteo, e.lumiere, e.lampe.possede, e.lampe.allumee, (e.deco || []).join(), e.niveau, e.veto ? Math.round(e.veto.reste_s / 600) : ""].join("|");
    if (cle !== cleScene) {
      sc.querySelector(".phb-decor").innerHTML = decor(e);
      cleScene = cle;
      // bandes de part et d'autre de la scène (écran large) : même ciel et même mer
      const c = ciel(e.ciel.phase, e.ciel.meteo), m = couleurMer(e.ciel.phase, e.ciel.meteo);
      sc.parentElement.style.background = `linear-gradient(${c[0]}, ${c[1]} 27%, ${c[2]} 50%, ${m[0]} 50%, ${m[1]})`;
    }
    const perso = sc.querySelector(".phb-perso");
    const absent = ["veto", "pension"].includes(e.niveau);
    perso.hidden = absent;
    // crottes (cliquables : on les ramasse)
    sc.querySelector(".phb-crottes").innerHTML = absent ? "" : Array.from({ length: e.crottes }, (_, i) =>
      `<button class="phb-crotte" style="left:${[44, 58, 39, 66][i]}%;top:${[92, 94, 85, 89][i]}%" data-phb="nettoyer" aria-label="Ramasser la crotte">
       <svg viewBox="0 0 20 16"><path d="M3 15 C1 15 1 12 4 11 C3 9 5 7 8 8 C8 5 11 3 13 5 C15 4 17 7 15 9 C18 10 19 15 16 15 Z" fill="#8a5a33" stroke="#5e3b1e"/></svg></button>`).join("");
    if (absent) return;
    const p = place(e, reaction);
    perso.style.left = p.x + "%";
    perso.style.top = p.y + "%";
    perso.style.setProperty("--rot", (p.rot || 0) + "deg");
    const h = e.humeur === "appel" ? "calme" : e.humeur;
    const html = D.svg({ stade: e.stade, variante: e.variante, humeur: e.dort ? "dort" : reaction === "refus" ? "grognon" : h, pose: p.pose,
      portes: e.portes, mue: e.mue, ventre: e.ventre_rond, malade: !!e.malade, froid: e.jauges.chaleur < 35, label: e.titre, fendu: e.stade === "oeuf" && e.age_jours > .004 });
    const box = perso.querySelector(".phb-flip");
    if (box.dataset.html !== html) { box.innerHTML = html; box.dataset.html = html; }
    perso.classList.toggle("plat", p.pose === "plat");
    perso.classList.toggle("nage", p.pose === "nage");
    perso.classList.toggle("malade", !!e.malade);
    perso.classList.toggle("froid", e.jauges.chaleur < 35 && !e.malade);
  }

  // Petite flânerie sur la plage pendant que la fenêtre est ouverte (rien quand l'onglet est caché / mode jeu)
  function flaner() {
    clearTimeout(flanerT);
    if (!dlg.open) return;
    flanerT = setTimeout(flaner, 4000 + Math.random() * 5000);
    if (!e || document.hidden || document.body.classList.contains("gamemode") || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    if (e.position !== "plage" || e.dort || e.stade === "oeuf" || reaction || feuille === "jeu" || ["veto", "pension"].includes(e.niveau)) return;
    const perso = dlg.querySelector(".phb-perso");
    const r = Math.random();
    if (r < .5) {
      const lent = e.malade || e.jauges.chaleur < 35;
      const cible = 38 + Math.random() * 26, duree = Math.abs(cible - flaneX) * (lent ? .5 : .22);
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

  // ---- panneau du bas ----
  function niveauJauge(v) { return v >= 60 ? "haut" : v >= 30 ? "moyen" : "bas"; }
  function blocJauges() {
    return `<div class="phb-jauges" role="list" aria-label="Jauges de Philibert">${JAUGES.map(([k, n, ic]) => {
      const v = e.jauges[k];
      return `<div class="phb-jauge" role="listitem" data-niveau="${niveauJauge(v)}"><span class="phb-j-ic" aria-hidden="true">${ic}</span>
        <span class="phb-j-nom">${n}</span><span class="phb-j-barre" role="progressbar" aria-label="${n}" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${v}"><i style="width:${v}%"></i></span>
        <b>${v}</b></div>`;
    }).join("")}</div>`;
  }
  function blocEtat() {
    if (e.niveau === "oeuf") return `<p class="phb-dit">L'œuf est bien au chaud dans le sable. Il va bientôt éclore… (les œufs d'iguane incubent dans le sable chaud)</p>`;
    if (e.niveau === "veto") return `<p class="phb-dit">La tortue vétérinaire prend soin de lui sur l'île d'à côté. Pendant ce temps, ses jauges ne baissent pas. Retour dans ${fmtH(e.veto.reste_s)}.</p>`;
    if (e.niveau === "pension") return `<p class="phb-dit">Philibert est chez la voisine : tout est en pause (ses jauges et son âge). Fais-le revenir quand tu veux.</p>`;
    const b = e.besoins;
    const ev = e.evenement;
    const etat = e.malade ? `<span class="phb-pastille malade">Malade</span>` : e.niveau === "fatigue" ? `<span class="phb-pastille fatigue">${e.grognon ? "Grognon" : "Pas au mieux"}</span>` : `<span class="phb-pastille forme">En forme</span>`;
    const appel = e.appel ? `<span class="phb-pastille appel" title="${e.appel.type === "caprice" ? "Il réclame de l'attention… mais a-t-il vraiment besoin de quelque chose ?" : "Il a besoin de toi"}">! Il t'appelle</span>` : "";
    return `${message ? `<p class="phb-dit" role="status">${esc(message)}</p>` : ""}
      <div class="phb-besoins">${etat}${appel}${e.dort ? `<span class="phb-pastille dort">${e.sieste ? "Sieste" : "Il dort"}</span>` : ""}
        ${b.length ? `<ul>${b.map(x => `<li>${esc(x.texte)}</li>`).join("")}</ul>` : `<span class="phb-ok">Rien ne lui manque pour l'instant.</span>`}</div>
      ${ev ? `<div class="phb-evt"><b>Sur l'île :</b> ${esc(ev.texte)} ${Object.entries(ev.choix).map(([k, t]) => `<button class="phb-b" data-phb="evenement" data-choix="${k}">${esc(t)}</button>`).join("")}</div>` : ""}`;
  }
  function boutons() {
    const nuit = e.ciel.heure >= 21 || e.ciel.heure < 7;
    const off = ["oeuf", "veto", "pension"].includes(e.niveau);
    const dis = off ? " disabled" : "";
    const B = (act, txt, titre, extra = "") => `<button class="phb-b" data-phb="${act}"${dis}${titre ? ` title="${esc(titre)}"` : ""} ${extra}>${txt}</button>`;
    return `<div class="phb-actions" role="toolbar" aria-label="Soins">
        ${B("f-nourrir", "🍃 Nourrir", "Repas de verdure, fleurs, friandises")}
        ${B("chauffer", "☀ Chauffer", nuit ? "La nuit, c'est la lampe chauffante" : "Au soleil sur le rocher chaud")}
        ${e.lampe.possede ? B("lampe", e.lampe.allumee ? "🔥 Lampe : allumée" : "🔥 Lampe : éteinte", "Lampe chauffante (sans lumière)", `aria-pressed="${e.lampe.allumee}"`) : ""}
        ${nuit || !e.lumiere ? B("lumiere", e.lumiere ? "💡 Éteindre la lumière" : "💡 Rallumer", "La nuit, il dort mieux dans le noir", `aria-pressed="${!e.lumiere}"`) : ""}
        ${B("f-bain", "💧 Bain", "Bain tiède dans la flaque, ou nager dans la mer")}
        ${B("nettoyer", "🧹 Nettoyer", "Ramasser ses crottes")}
        ${B("soigner", `✚ Soigner${e.inventaire.remede ? ` (${e.inventaire.remede})` : ""}`, "Donner un remède (il agit mieux au chaud)")}
        ${B("caresser", "✋ Caresser", "")}
        ${B("f-jouer", "🎲 Jouer", "Mini-jeux : bonheur et coquillages")}
        ${B("feliciter", "👍 Féliciter", "Juste après une bonne action")}
        ${B("gronder", "☝ Gronder (doucement)", "Pour un caprice, pas pour un vrai besoin")}
      </div>
      <div class="phb-actions phb-actions-2" role="toolbar" aria-label="Île">
        <button class="phb-b" data-phb="ramasser"${off ? " disabled" : ""} title="${e.ramasser_dans_s ? "La mer en rapporte dans " + fmtH(e.ramasser_dans_s) : "Ramasser des coquillages sur la plage"}">🐚 Ramasser${e.ramasser_dans_s ? ` <small>(${fmtH(e.ramasser_dans_s)})</small>` : ""}</button>
        <button class="phb-b" data-phb="f-boutique">🛒 Boutique</button>
        <button class="phb-b" data-phb="f-garde">🎩 Garde-robe</button>
        <button class="phb-b" data-phb="f-carnet">📖 Carnet</button>
        <button class="phb-b" data-phb="f-reglages">⚙ Réglages</button>
      </div>`;
  }

  // ---- feuilles (panneaux) ----
  function feuilleNourrir() {
    const groupes = [["Repas du quotidien", ["verdure", "legume"]], ["Fleurs", ["fleur"]], ["Friandises — à limiter", ["friandise"]]];
    return `<h3>Nourrir Philibert <small>· 100 % végétal</small></h3>
      ${groupes.map(([t, cats]) => `<div class="phb-groupe">${t}</div><div class="phb-grille">${Object.entries(cat.aliments).filter(([, a]) => cats.includes(a.cat)).map(([id, a]) => {
        const n = a.prix ? (e.inventaire[id] || 0) : "∞";
        return `<button class="phb-carte" data-phb="nourrir" data-aliment="${id}" ${a.prix && !n ? "disabled" : ""} title="${esc(a.texte)}">
          <span class="phb-ic">${icone(id)}</span><span>${esc(a.nom)}</span><small>${a.prix ? `×${n}` : "gratuit"}</small></button>`;
      }).join("")}</div>`).join("")}
      <p class="phb-astuce">Le savais-tu ? Un iguane vert ne mange que des plantes. Il en manque ? Passe à la <button class="phb-lien" data-phb="f-boutique">boutique</button>.</p>`;
  }
  function feuilleBain() {
    return `<h3>Le bain</h3><div class="phb-grille phb-grille-2">
      <button class="phb-carte" data-phb="bain" data-lieu="flaque"><span class="phb-ic">💧</span><span>Bain tiède dans la flaque</span><small>propreté, aide la mue</small></button>
      <button class="phb-carte" data-phb="bain" data-lieu="mer"><span class="phb-ic">🌊</span><span>Nager dans la mer</span><small>bonheur, mais l'eau rafraîchit</small></button></div>`;
  }
  function feuilleJouer() {
    const J = [["feuilles", "🍃", "Attrape les feuilles et les fleurs qui tombent du palmier, évite les insectes (30 s)"],
      ["devin", "↔", "Devine de quel côté il va tourner la tête (5 manches)"], ["rythme", "♪", "Répète ses hochements de tête, petits et grands"]];
    return `<h3>Jouer avec Philibert</h3><div class="phb-grille phb-grille-3">${J.map(([id, ic, t]) => `<button class="phb-carte" data-phb="jeu" data-jeu="${id}">
      <span class="phb-ic phb-ic-txt">${ic}</span><span>${esc(cat.jeux[id])}</span><small>${esc(t)}</small></button>`).join("")}</div>
      <p class="phb-astuce">Encore ${e.jeux_restants} coquillages à gagner aujourd'hui aux jeux. Bien au chaud, il joue mieux !</p>`;
  }
  function feuilleBoutique() {
    const O = cat.objets, A = cat.aliments;
    const onglets = { nourriture: "Nourriture", soins: "Soins et équipement", accessoires: "Accessoires", deco: "Déco de l'île" };
    let items;
    if (boutiqueOnglet === "nourriture") items = Object.entries(A).filter(([, a]) => a.prix).map(([id, a]) => [id, a.nom, a.prix, a.texte, `en réserve : ${e.inventaire[id] || 0}`, false]);
    else {
      const t = { soins: ["soin", "equipement"], accessoires: ["accessoire"], deco: ["deco"] }[boutiqueOnglet];
      items = Object.entries(O).filter(([, o]) => t.includes(o.type)).map(([id, o]) => {
        const a = id === "lampe" ? e.lampe.possede : (e.accessoires.includes(id) || e.deco.includes(id));
        return [id, o.nom, o.prix, o.texte, id === "remede" ? `en réserve : ${e.inventaire.remede || 0}` : a ? "déjà à toi" : "", a];
      });
    }
    return `<h3>Boutique de l'île <small>· tu as ${e.coquillages} coquillage${e.coquillages > 1 ? "s" : ""}</small></h3>
      <div class="phb-onglets" role="tablist">${Object.entries(onglets).map(([k, t]) => `<button class="phb-b${k === boutiqueOnglet ? " phb-on" : ""}" role="tab" aria-selected="${k === boutiqueOnglet}" data-phb="boutique-onglet" data-o="${k}">${t}</button>`).join("")}</div>
      <div class="phb-grille">${items.map(([id, nom, prix, texte, info, possede]) => `<div class="phb-carte phb-article">
        <span class="phb-ic">${icone(id)}</span><span>${esc(nom)}</span><small>${esc(texte)}</small>${info ? `<small class="phb-info">${esc(info)}</small>` : ""}
        <button class="phb-b phb-prim" data-phb="acheter" data-article="${id}" ${possede ? "disabled" : ""} aria-label="Acheter ${esc(nom)} pour ${prix} coquillages">${possede ? "✔" : `🐚 ${prix}`}</button></div>`).join("")}</div>
      ${boutiqueOnglet === "nourriture" ? `<p class="phb-astuce">Pas d'insectes, de viande ni de croquettes ici : Philibert est herbivore. Le trèfle de l'île est toujours gratuit.</p>` : ""}`;
  }
  function feuilleGarde() {
    const slots = { tete: "Tête", yeux: "Yeux", cou: "Cou" };
    const parSlot = s => e.accessoires.filter(a => cat.objets[a].emplacement === s);
    return `<h3>Garde-robe</h3><div class="phb-garde"><div class="phb-apercu">${D.svg({ stade: e.stade === "oeuf" ? "bebe" : e.stade, variante: e.variante, humeur: "joyeux", portes: e.portes, label: "Aperçu de Philibert" })}</div>
      <div>${Object.entries(slots).map(([s, n]) => `<div class="phb-groupe">${n}</div><div class="phb-ligne">${parSlot(s).map(a => `<button class="phb-b${e.portes[s] === a ? " phb-on" : ""}" data-phb="${e.portes[s] === a ? "retirer" : "porter"}" data-article="${a}" data-emplacement="${s}" aria-pressed="${e.portes[s] === a}">
        <span class="phb-ic-mini">${icone(a)}</span>${esc(cat.objets[a].nom)}</button>`).join("") || `<small class="phb-gris">Rien pour l'instant (voir la boutique).</small>`}</div>`).join("")}</div></div>`;
  }
  function feuilleCarnet() {
    const c = carnetDonnees;
    const onglets = { historique: "Historique", stats: "Statistiques", succes: "Succès", cartes: "Cartes postales", faits: "Le savais-tu ?" };
    let corps = `<p class="phb-gris">Chargement…</p>`;
    if (c) {
      if (carnetOnglet === "historique") corps = `<ol class="phb-histo">${c.historique.map(h => `<li><time>${new Date(h.t * 1000).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" })}</time> ${esc(h.texte)}</li>`).join("")}</ol>`;
      else if (carnetOnglet === "stats") {
        const s = c.stats, L = [["Âge", age(c.age_jours)], ["Né le", new Date(c.ne * 1000).toLocaleDateString("fr-FR")], ["Repas", s.repas], ["dont verdure et légumes", s.verdure], ["Fleurs", s.fleurs],
          ["Friandises", s.friandises], ["Verdures goûtées", `${c.gouts.length} / 6`], ["Refus (aliments pas pour lui)", s.refus], ["Bains (dont mer)", `${s.bains} (${s.bains_mer})`], ["Séances au soleil", s.soleil],
          ["Parties jouées", s.jeux], ["Caresses", s.caresses], ["Mues", s.mues], ["Maladies (guéries à la maison)", `${s.maladies} (${s.gueris})`], ["Séjours chez le vétérinaire", s.sejours_veto],
          ["Nuits dans le noir", s.nuits_eteintes], ["Coquillages gagnés", s.coquillages_gagnes], ["Records : feuilles · devin · hochements", `${s.meilleur_feuilles} · ${s.meilleur_devin}/5 · ${s.meilleur_rythme}`]];
        corps = `<table class="phb-tbl">${L.map(([k, v]) => `<tr><th scope="row">${esc(k)}</th><td>${esc(v)}</td></tr>`).join("")}</table>`;
      } else if (carnetOnglet === "succes") corps = `<div class="phb-grille">${Object.entries(c.succes).map(([, s]) => `<div class="phb-carte phb-succes${s.quand ? " ok" : ""}">
        <span class="phb-ic phb-ic-txt">${s.quand ? "🏆" : "🔒"}</span><span>${esc(s.nom)}</span><small>${esc(s.texte)}${s.gain ? ` · +${s.gain} 🐚` : ""}</small>${s.quand ? `<small class="phb-info">${new Date(s.quand * 1000).toLocaleDateString("fr-FR")}</small>` : ""}</div>`).join("")}</div>`;
      else if (carnetOnglet === "cartes") corps = c.cartes.length ? c.cartes.map(carteHtml).join("") : `<p class="phb-gris">Aucune carte postale : Philibert n'est jamais allé chez la tortue vétérinaire. 🎉</p>`;
      else corps = `<p class="phb-gris">${c.faits.length} fiche${c.faits.length > 1 ? "s" : ""} sur ${c.faits_total} — on en débloque en s'occupant de lui.</p>
        <ul class="phb-faits">${c.faits.map(f => `<li>💡 ${esc(f.texte)}</li>`).join("")}</ul>`;
    }
    return `<h3>Carnet de ${esc(c ? c.titre : "Philibert")}</h3>
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
    return `<h3>Réglages de Philibert</h3>
      ${chk("visible", "Le voir se promener en haut de la page")}
      ${chk("sons", "Petits sons (seulement dans son île)")}
      ${chk("notif_windows", "Notification Windows s'il tombe malade ou part chez le vétérinaire (jamais en mode jeu)")}
      ${chk("discord", "Me prévenir aussi sur Discord (si le bot de NEXUS est configuré)")}
      <label class="phb-chk"><span>Vitesse du temps</span> <select data-phb-r="vitesse"><option value="normale"${r.vitesse === "normale" ? " selected" : ""}>Normale</option>
        <option value="lente"${r.vitesse === "lente" ? " selected" : ""}>Lente (deux fois moins vite)</option></select></label>
      <div class="phb-groupe">Mode vacances</div>
      <p class="phb-gris">La voisine de l'île le prend en pension : jauges, âge et maladie sont en pause jusqu'à son retour.</p>
      ${e.vacances ? `<button class="phb-b phb-prim" data-phb="revenir">Le faire revenir</button>` : `<button class="phb-b" data-phb="vacances" ${e.niveau === "veto" || e.niveau === "oeuf" ? "disabled" : ""}>🧳 Partir en pension chez la voisine</button>`}
      <div class="phb-groupe">Recommencer</div>
      <p class="phb-gris">Philibert part vivre sur une île voisine et un nouvel œuf apparaît. Son carnet repart de zéro.</p>
      <button class="phb-b phb-danger" data-phb="recommencer">🥚 Recommencer avec un nouvel œuf…</button>`;
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
    f.innerHTML = `<button class="phb-b phb-fermer-f" data-phb="fermer-feuille" aria-label="Fermer ce panneau">✕</button>${msg}${html}`;
  }

  function rendre() {
    if (!e) return;
    const t = dlg.querySelector(".phb-tete-ile");
    if (!t) return;
    t.querySelector("#phb-titre").textContent = e.titre;
    t.querySelector(".phb-sous").textContent = e.stade === "oeuf" ? "Œuf" : `${e.stade_nom} · ${age(e.age_jours)} · ${poids(e.poids_g)}${e.ventre_rond ? " (ventre rond)" : ""}`;
    t.querySelector(".phb-coq").textContent = `🐚 ${e.coquillages}`;
    t.querySelector(".phb-coq").setAttribute("aria-label", `${e.coquillages} coquillages`);
    t.querySelector(".phb-meteo").textContent = { aube: "Aube", jour: "Jour", coucher: "Coucher de soleil", nuit: "Nuit" }[e.ciel.phase] + " · " +
      (e.ciel.phase === "nuit" ? { soleil: "ciel étoilé", nuages: "nuageux", pluie: "pluie", arc: "ciel étoilé" } : { soleil: "soleil", nuages: "nuageux", pluie: "pluie", arc: "arc-en-ciel" })[e.ciel.meteo];
    dlg.querySelector(".phb-bas").innerHTML = `${e.niveau === "oeuf" || ["veto", "pension"].includes(e.niveau) ? "" : blocJauges()}<div class="phb-etat">${blocEtat()}</div>${boutons()}`;
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
    box.innerHTML = e.nouveau.map(n => `<div class="phb-bandeau">${n.type === "succes" ? `🏆 <b>Succès :</b> ${esc(n.nom)} — ${esc(n.texte)}` : `💡 <b>Le savais-tu ?</b> ${esc(n.texte)}`}</div>`).join("");
    son("joie");
    vuEnvoye = true;
    setTimeout(() => { box.innerHTML = ""; vuEnvoye = false; }, 9000);
    api("/api/philibert/action", { action: "vu" }).then(r => { e.nouveau = []; diffuser(r.etat); }).catch(() => {});
  }

  function diffuser(nv) {
    e = nv;
    dispatchEvent(new CustomEvent("philibert:etat", { detail: nv }));
  }
  function appliquer(nv) { diffuser(nv); if (dlg.open) rendre(); }

  async function action(nom, params = {}) {
    try {
      const r = await api("/api/philibert/action", { action: nom, ...params });
      message = r.message || "";
      if (r.reaction) jouerReaction(r.reaction);
      appliquer(r.etat);
      return r;
    } catch (x) {
      message = x.message;
      son("non");
      if (dlg.open) rendre();
      return null;
    }
  }
  function jouerReaction(r) {
    clearTimeout(reactionT);
    const s = { mange_verdure: "croc", mange_legume: "croc", mange_fleur: "croc", mange_friandise: "croc", bain_mer: "plouf", bain_flaque: "plouf", coquillage: "ding", achat: "ding",
      refus: "non", gueri: "joie", fier: "pop", caresse: "pop", repu: "non", non: "non" }[r];
    if (s) son(s);
    reaction = ["bain_mer", "bain_flaque", "refus"].includes(r) ? r : "";
    const p = dlg.querySelector(".phb-perso");
    if (!p) return;
    const cls = r.startsWith("mange") ? "mange" : { refus: "refus", caresse: "fanon", fier: "hoche", gueri: "hoche", bonjour: "hoche", triste: "triste", repu: "refus", calme: "hoche" }[r];
    if (cls) { p.classList.add(cls); setTimeout(() => p.classList.remove(cls), 1600); }
    reactionT = setTimeout(() => { reaction = ""; rendreScene(); }, r.startsWith("bain") ? 3500 : 1600);
  }

  async function charger() {
    try { appliquer(await api("/api/philibert")); } catch (x) { message = "NEXUS ne répond pas : " + x.message; }
  }

  // ---- ouverture ----
  async function ouvrir() {
    if (!dlg.innerHTML) {
      dlg.innerHTML = `<div class="phb-ile">
        <div class="phb-tete-ile"><div class="phb-titres"><h2 id="phb-titre">Philibert</h2><span class="phb-sous"></span></div>
          <span class="phb-meteo"></span><span class="phb-coq" role="img"></span>
          <button class="phb-b phb-fermer" data-phb="fermer" aria-label="Fermer l'île de Philibert">✕</button></div>
        <div class="phb-scene-zone"><div class="phb-scene"><div class="phb-decor"></div><div class="phb-crottes"></div>
          <button class="phb-perso phb-anim" data-phb="caresser" aria-label="Caresser Philibert"><span class="phb-flip"></span></button>
          <div class="phb-bandeaux" aria-live="polite"></div></div>
          <div class="phb-feuille" hidden></div></div>
        <div class="phb-bas" aria-live="polite"></div></div>`;
    }
    if (!dlg.open) dlg.showModal();
    if (!cat) { try { cat = await api("/api/philibert/catalogue"); } catch (x) { /* réessayé à la prochaine ouverture */ } }
    message = "";
    e = (window.nxPhilibert && window.nxPhilibert.etat()) || e;
    if (e) rendre();
    await charger();
    clearInterval(pollT);
    pollT = setInterval(() => { if (!document.hidden && dlg.open && feuille !== "jeu") charger(); }, 30000);
    flaner();
  }
  dlg.addEventListener("close", () => { clearInterval(pollT); clearTimeout(flanerT); feuille = null; if (window.PhilibertJeux) window.PhilibertJeux.arreter(); rendreFeuille(); });
  dlg.addEventListener("cancel", ev => {                              // Échap : ferme d'abord le panneau ouvert
    if (feuille && feuille !== "carte") { ev.preventDefault(); fermerFeuille(); }
  });
  function fermerFeuille() {
    if (feuille === "jeu" && window.PhilibertJeux) window.PhilibertJeux.arreter();
    feuille = null;
    rendreFeuille();
    const b = dlg.querySelector(".phb-actions .phb-b");
    if (b) b.focus();
  }
  async function ouvrirFeuille(f) {
    feuille = f;
    message = "";
    if (f === "carnet") { carnetDonnees = null; rendreFeuille(); try { carnetDonnees = await api("/api/philibert/carnet"); } catch (x) { message = x.message; } }
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
    if (a === "nourrir") { feuille = null; rendreFeuille(); await action("nourrir", { aliment: b.dataset.aliment }); return; }
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
      if (!confirm("Recommencer avec un nouvel œuf ?\nPhilibert partira vivre sur une île voisine, et son carnet repartira de zéro.")) return;
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
    if (r && r.etat) { message = r.message; son("ding"); appliquer(r.etat); }
    rendreFeuille();
  }
  window.PhilibertIle = { ouvrir, appliquer, action, icone, fermer: () => dlg.close() };
})();
