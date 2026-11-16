"use strict";
/* Dessin de Philibert, l'iguane vert de NEXUS (SVG original, vu de profil, tourné vers la droite).
   PhilibertDessin.svg({ stade, variante, humeur, pose, portes, mue, ventre, malade, froid, jambes }) → chaîne SVG.
   - Posture de lézard : pattes étalées en deux segments (épaule/hanche → coude/genou → pied à cinq doigts) ;
     elles marchent par paires en diagonale (avant proche + arrière lointain, puis l'inverse) ;
   - queue en deux parties (base + bout) pour une ondulation en S pendant la marche ;
   - détails d'iguane vert : grande écaille ronde sur la joue, fanon avec ses petites épines, crête dorsale,
     queue rayée, iris doré, « troisième œil » sur le dessus de la tête, rangées d'écailles sur le flanc.
   Les animations sont en CSS (philibert.css) sur .phb-patte, .phb-genou, .phb-queue, .phb-queue-bout,
   .phb-corps, .phb-paupiere, .phb-tete, .phb-fanon. « jambes » donne une pose fixe (images du mini-jeu de
   course, dessiné sur un canevas) : { av, ar, avl, arl } en degrés, et { gav, gar, gavl, garl } pour les genoux. */
(() => {
  const PALETTES = {
    insulaire: { corps: "#4fae4f", fonce: "#2b7034", ventre: "#acd97c", crete: "#7cc86b", fanon: "#c8e49c", bande: "#2a6a30", joue: "#d8ebb7" },
    royal: { corps: "#4fae4f", fonce: "#2b7034", ventre: "#b7de82", crete: "#e9b936", fanon: "#d0e7a2", bande: "#2a6a30", joue: "#ece2a6" },
    gourmand: { corps: "#5cb550", fonce: "#327a35", ventre: "#c3e28c", crete: "#85cb70", fanon: "#d2e9a8", bande: "#2e6f31", joue: "#ddecbf" },
    nageur: { corps: "#3da98d", fonce: "#1f6c5c", ventre: "#a1dac0", crete: "#5ec8de", fanon: "#bbe7d1", bande: "#1f5f80", joue: "#cfebe0" },
    convalescent: { corps: "#63b25a", fonce: "#377b3a", ventre: "#b9dd8e", crete: "#8ccc7a", fanon: "#d4e9af", bande: "#33703a", joue: "#dcecc3" },
  };
  const MALADE = { corps: "#a9c79b", fonce: "#7b9a70", ventre: "#d5e4c2", crete: "#bad4a9", fanon: "#e0ebd1", bande: "#87a57c", joue: "#e6efdc" };
  const FROID = { corps: "#3b7f45", fonce: "#21502f", ventre: "#88b175", crete: "#5b9b5f", fanon: "#a8c990", bande: "#1e4a2c", joue: "#bed4a9" };
  const SAGE = { corps: "#6f9f62", fonce: "#46703f", ventre: "#c5d9a8", fanon: "#e6edd8", joue: "#e4eacf" };

  function couleurs(o) {
    let c = { ...(PALETTES[o.variante] || PALETTES.insulaire) };
    if (o.stade === "sage") c = { ...c, ...SAGE, crete: o.variante === "royal" ? "#e9b936" : o.variante === "nageur" ? "#7fc3cf" : "#9dbb8a" };
    if (o.malade) c = { ...c, ...MALADE };
    else if (o.froid) c = { ...c, ...FROID };
    return c;
  }
  // couleur plus claire (k > 0) ou plus foncée (k < 0)
  function teinte(hex, k) {
    const n = parseInt(hex.slice(1), 16), v = [n >> 16, (n >> 8) & 255, n & 255];
    return "#" + v.map(x => Math.round(k > 0 ? x + (255 - x) * k : x * (1 + k)).toString(16).padStart(2, "0")).join("");
  }

  function defs(c) {
    const id = "phbg" + (c.corps + c.fonce).replace(/#/g, "");
    // (même identifiant pour la même palette : plusieurs Philibert identiques sur la page partagent le dégradé)
    return { id, html: `<defs><linearGradient id="${id}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="${teinte(c.corps, .24)}"/><stop offset=".5" stop-color="${c.corps}"/><stop offset="1" stop-color="${teinte(c.corps, -.14)}"/></linearGradient></defs>` };
  }

  function crete(stade, c) {
    const taille = stade === "bebe" ? .5 : stade === "juvenile" ? .78 : 1;
    let d = "";
    for (let x = 50; x <= 90; x += 3.1) {
      const y = 30.2 + Math.pow((x - 68) / 22, 2) * 2.2 - (x > 84 ? (x - 84) * .35 : 0);
      const h = (1.7 + 2.8 * Math.sin(Math.PI * (x - 46) / 48)) * taille;
      d += `M${(x - 1.4).toFixed(1)} ${(y + .6).toFixed(1)} Q${(x - .2).toFixed(1)} ${(y - h * .55).toFixed(1)} ${(x + .6).toFixed(1)} ${(y - h).toFixed(1)} Q${(x + .9).toFixed(1)} ${(y - h * .4).toFixed(1)} ${(x + 1.5).toFixed(1)} ${(y + .6).toFixed(1)} Z`;
    }
    return `<path class="phb-crete" d="${d}" fill="${c.crete}" stroke="${c.fonce}" stroke-width=".4" stroke-linejoin="round"/>`;
  }

  // Patte en deux segments : hanche (hx, hy) → genou (gx, gy) → pied (px, py) ; doigts longs vers l'avant
  function patte(cls, [hx, hy], [gx, gy], [px, py], coul, ongle, e1, e2, a = 0, g = 0, long = 1) {
    const d = (dx, dy) => `M${px} ${py} l${(dx * long).toFixed(1)} ${dy}`;
    return `<g class="phb-patte ${cls}"><g transform="rotate(${a} ${hx} ${hy})">
      <path d="M${hx} ${hy} L${gx} ${gy}" stroke="${coul}" stroke-width="${e1}" stroke-linecap="round"/>
      <g class="phb-genou"><g transform="rotate(${g} ${gx} ${gy})">
        <path d="M${gx} ${gy} L${px} ${py}" stroke="${coul}" stroke-width="${e2}" stroke-linecap="round"/>
        <path d="${d(3.8, .5)} ${d(3.4, 1.9)} ${d(2.2, 2.8)} ${d(.3, 2.9)} ${d(-1.9, 1.7)}" stroke="${coul}" stroke-width="1.05" stroke-linecap="round" fill="none"/>
        <path d="M${px + 3.8 * long} ${py + .5} l.7 .1 M${px + 3.4 * long} ${py + 1.9} l.6 .3 M${px + 2.2 * long} ${py + 2.8} l.4 .5" stroke="${ongle}" stroke-width=".7" stroke-linecap="round"/>
      </g></g></g></g>`;
  }

  function accessoires(portes) {
    const p = portes || {};
    let tete = "", yeux = "", cou = "";
    if (p.tete === "chapeau") tete = `<g class="phb-acc"><path d="M94.5 26.4 C94.6 20.4 107.4 20.4 107.5 26.4 Z" fill="#e9c768" stroke="#a8812f" stroke-width=".5"/>
      <path d="M96 24 q5 -1.2 10 0" stroke="#f6dc8f" stroke-width=".6" fill="none"/>
      <rect x="94.7" y="24.2" width="12.6" height="1.7" fill="#d9434f"/><ellipse cx="101" cy="26.6" rx="10.5" ry="2.1" fill="#f0d27b" stroke="#a8812f" stroke-width=".5"/>
      <path d="M92 26.8 h18" stroke="#c9a24a" stroke-width=".35" stroke-dasharray="1 1"/></g>`;
    if (p.tete === "couronne") tete = `<g class="phb-acc">${[[94.6, 27], [100.6, 25.6], [106.6, 27.2]].map(([x, y], i) =>
      `<g transform="translate(${x} ${y})">${[0, 72, 144, 216, 288].map(a => `<ellipse rx="1.5" ry="2.4" transform="rotate(${a}) translate(0 -1.6)" fill="${i === 1 ? "#ff6b8b" : "#ff4f6d"}"/>`).join("")}
      <circle r="1" fill="#ffd34d"/></g>`).join("")}</g>`;
    if (p.yeux === "lunettes") yeux = `<g class="phb-acc"><path d="M93 30 L97.4 30.4" stroke="#1b2330" stroke-width=".9"/>
      <circle cx="101.4" cy="31" r="4" fill="#1d2a3a" stroke="#0f141b" stroke-width=".7"/><path d="M99.4 29.4 q1 -1.1 2.6 -1" stroke="#9fc7ff" stroke-width=".7" fill="none" opacity=".85"/></g>`;
    if (p.cou === "collier") cou = `<g class="phb-acc">${[[86.6, 36.8, "#ff7ab6"], [87.6, 40.4, "#ffd34d"], [89.8, 43.4, "#7fd0ff"], [93.2, 45.2, "#ff7ab6"], [96.8, 45.6, "#ffd34d"]].map(([x, y, f]) =>
      `<circle cx="${x}" cy="${y}" r="1.9" fill="${f}" stroke="#fff" stroke-width=".4"/><circle cx="${x}" cy="${y}" r=".6" fill="#fff6c2"/>`).join("")}</g>`;
    if (p.cou === "foulard") cou = `<g class="phb-acc"><path d="M85.2 36 L97 41.2 L88.6 48.2 Z" fill="#e2464f" stroke="#a52a33" stroke-width=".5"/>
      <circle cx="89" cy="40" r=".7" fill="#fff"/><circle cx="91.6" cy="43" r=".7" fill="#fff"/><circle cx="88.6" cy="45" r=".6" fill="#fff"/><circle cx="93.6" cy="40.8" r=".6" fill="#fff"/></g>`;
    return { tete, yeux, cou };
  }

  function oeuf(o) {
    const fendu = o.fendu ? `<path d="M57 38 l3 2.5 l2.6 -3 l2.4 3.4 l2.8 -2.6 l2.6 2.2" fill="none" stroke="#8a7a55" stroke-width=".8" stroke-linejoin="round"/>` : "";
    return `<svg class="phb-svg phb-oeuf" viewBox="0 0 128 64" role="img" aria-label="${o.label || "L'œuf de Philibert"}">
      <defs><radialGradient id="phb-oeuf-g" cx=".38" cy=".32" r=".8"><stop offset="0" stop-color="#fffdf3"/><stop offset=".7" stop-color="#f3e9cf"/><stop offset="1" stop-color="#e0d2ad"/></radialGradient></defs>
      <ellipse cx="64" cy="58" rx="26" ry="4.5" fill="#e6c98b" opacity=".9"/>
      <g class="phb-oeuf-corps"><ellipse cx="64" cy="43" rx="11" ry="14" fill="url(#phb-oeuf-g)" stroke="#c9b98f" stroke-width=".8"/>
      <ellipse cx="60" cy="38" rx="2.2" ry="1.4" fill="#d9cba3"/><ellipse cx="68" cy="47" rx="1.8" ry="1.2" fill="#d9cba3"/><ellipse cx="66" cy="35" rx="1.1" ry=".8" fill="#d9cba3"/>
      ${fendu}</g>
      <path d="M36 58 C44 52 52 54 56 56 M72 56 C78 53 86 52 92 58" stroke="#d8b774" stroke-width="1.2" fill="none"/></svg>`;
  }

  function ecailles(c) {
    let d = "";
    for (let r = 0; r < 3; r++) for (let i = 0; i < 9; i++) {
      const x = 50 + i * 3.6 + (r % 2) * 1.8, y = 35.6 + r * 2.6 + Math.pow((x - 66) / 26, 2) * 2;
      d += `M${x.toFixed(1)} ${y.toFixed(1)} a.75 .55 0 1 0 1.5 0 a.75 .55 0 1 0 -1.5 0 `;
    }
    return `<path d="${d}" fill="${c.fonce}" opacity=".16"/>`;
  }

  function svg(o = {}) {
    if (o.stade === "oeuf") return oeuf(o);
    const c = couleurs(o);
    const g = defs(c), peau = `url(#${g.id})`;
    const h = o.humeur || "calme";
    const gourmand = o.variante === "gourmand" || o.ventre;
    const sage = o.stade === "sage";
    const J = o.jambes || {};
    const echelle = { bebe: "translate(64 57) scale(.66) translate(-64 -57)", juvenile: "translate(64 57) scale(.84) translate(-64 -57)" }[o.stade] || "";
    const teteEch = { bebe: "translate(86 36) scale(1.3) translate(-86 -36)", juvenile: "translate(86 36) scale(1.1) translate(-86 -36)" }[o.stade] || "";
    const queueEch = { bebe: "translate(44 41) scale(.72 1) translate(-44 -41)", juvenile: "translate(44 41) scale(.88 1) translate(-44 -41)" }[o.stade] || "";
    const bas = gourmand ? "C82 47 75 51.5 62 51.5 C49 51.5 40 48.5 40 41" : "C82 45 74 47.6 62 47.6 C50 47.6 40 46 40 41";
    const acc = accessoires(o.portes);
    const dort = h === "dort";
    const yeux = dort
      ? `<path d="M97.8 31.4 Q101.4 33.6 105 31.4" fill="none" stroke="${c.fonce}" stroke-width="1.05" stroke-linecap="round"/>
         <path d="M98.6 32.4 l-.6 1 M104.2 32.4 l.6 1" stroke="${c.fonce}" stroke-width=".5" stroke-linecap="round"/>`
      : `<circle cx="101.4" cy="31" r="3.4" fill="${teinte(c.fonce, -.15)}"/><circle cx="101.4" cy="31" r="3" fill="#f7efc4"/>
         <circle cx="101.6" cy="31" r="2.5" fill="#dca51c"/><circle cx="101.6" cy="31" r="2.5" fill="none" stroke="#a8770f" stroke-width=".45"/>
         <ellipse cx="101.9" cy="31" rx=".85" ry="1.75" fill="#171717"/><circle cx="102.6" cy="29.9" r=".75" fill="#fff"/><circle cx="100.6" cy="32.2" r=".35" fill="#fff" opacity=".8"/>
         ${h === "malade" || h === "froid" ? `<path d="M97.9 31 A3.5 3.5 0 0 1 104.9 31 Z" fill="${c.corps}"/>` : ""}
         <ellipse class="phb-paupiere" cx="101.4" cy="31" rx="3.6" ry="3.6" fill="${c.corps}"/>`;
    const sourcil = h === "grognon" ? `<path d="M97.4 27.4 L105 29.3" stroke="${c.fonce}" stroke-width="1.35" stroke-linecap="round"/>`
      : sage ? `<path d="M97.2 27.8 q3.6 -2.4 8 -.2" stroke="#f3f1e6" stroke-width="1.2" fill="none" stroke-linecap="round"/>`
        : `<path d="M97.4 27.9 q3.8 -1.9 7.6 .1" stroke="${c.fonce}" stroke-width=".75" fill="none" stroke-linecap="round"/>`;
    const bouche = h === "joyeux" ? "M96.4 37.6 Q106 41 113.4 35.8" : (h === "grognon" || h === "malade") ? "M96.4 38.6 Q106 36.6 113.4 37" : "M96.4 38 Q106 39.4 113.4 36.2";
    const joues = h === "joyeux" || gourmand ? `<ellipse cx="106.6" cy="35.6" rx="2.1" ry="1.25" fill="#ff8fa3" opacity="${gourmand ? .45 : .38}"/>` : "";
    const fanonD = sage ? "M87.6 39.2 C88.4 49 95 53.5 100.6 48.6 C102.6 46 103.4 42.6 103 39.4 Z" : "M88 39.5 C89 46.4 94 50.2 99.2 47.2 C101.2 45.4 102 42.4 102 39.6 Z";
    const epines = sage ? [[100.6, 48.6], [102.2, 46.4], [103, 43.6]] : [[99.2, 47.2], [100.8, 45.2], [101.7, 42.6]];
    const mue = o.mue ? `<g class="phb-mue" fill="#f4f1e4" opacity=".88" stroke="#d8d2bd" stroke-width=".3">
      <path d="M54 33 l4 -1.5 l2 3 l-3 2.4 l-3.4 -1 Z"/><path d="M70 40 l5 -1 l1 3 l-4 1.6 Z"/><path d="M26 44 l4 -1 l.6 2.6 l-3.6 .8 Z"/><path d="M80 34 l3 -.6 l.4 2 l-2.8 .6 Z"/></g>` : "";
    const royal = o.variante === "royal" ? `<path class="phb-collerette" d="M87.6 26 L84.4 29.2 L88.8 30.4 L83.4 33.6 L88.4 35 L83.2 38.2 L88.2 39.4 L84.2 42.6 L89.4 42.4 Z"
      fill="#f2c443" stroke="#b8861a" stroke-width=".5" stroke-linejoin="round"/>` : "";
    const pansement = o.variante === "convalescent" ? `<g transform="rotate(-14 99 25.5)"><rect x="94.4" y="23.8" width="9.4" height="3.4" rx="1.2" fill="#f3d9b5" stroke="#c9a77b" stroke-width=".4"/>
      <circle cx="97" cy="25.5" r=".35" fill="#c9a77b"/><circle cx="99.1" cy="25.5" r=".35" fill="#c9a77b"/><circle cx="101.2" cy="25.5" r=".35" fill="#c9a77b"/></g>` : "";
    const pose = o.pose || "debout";
    const loin = teinte(c.fonce, .12), ongle = teinte(c.fonce, -.35);
    return `<svg class="phb-svg phb-${o.stade || "bebe"} phb-h-${h} phb-pose-${pose}" viewBox="0 0 128 64" role="img" aria-label="${o.label || "Philibert"}">
      ${g.html}
      <ellipse class="phb-ombre" cx="62" cy="57.6" rx="${pose === "nage" ? 0 : 43}" ry="2.3" fill="#000" opacity=".15"/>
      <g transform="${echelle}"><g class="phb-corps-tout"><g class="phb-corps">
        <g class="phb-queue"><g transform="${queueEch}">
          <path d="M44.5 37 C36 37.8 29 41 22.4 44.4 L25 49.2 C31.4 47.4 37.6 46.2 44.5 45.6 Z" fill="${peau}" stroke="${c.fonce}" stroke-width=".6"/>
          <g class="phb-queue-bout">
            <path d="M23.6 43.8 C17.6 46.8 11 50.2 1 52.4 C6 52.9 12.4 52.2 25.8 49 Z" fill="${peau}" stroke="${c.fonce}" stroke-width=".6"/>
            <path d="M20.4 46.2 l-1.3 4 M13.8 49.4 l-.9 2.4 M8 51 l-.5 1.4" stroke="${c.bande}" stroke-width="1.6" stroke-linecap="round" opacity=".55"/>
          </g>
          <path d="M43 37.2 C36 37.8 30 40.6 23.8 43.6" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width=".8"/>
          <path d="M35 39.6 l-1.8 6.6 M27.6 42.6 l-1.6 5.4" stroke="${c.bande}" stroke-width="1.7" stroke-linecap="round" opacity=".55"/>
        </g></g>
        ${patte("phb-p-ar-loin", [46.5, 42], [42.8, 47.6], [46.2, 54], loin, ongle, 3.6, 2.9, J.arl || 0, J.garl || 0, 1.15)}
        ${patte("phb-p-av-loin", [75, 41.6], [78.6, 46.8], [78.4, 53.6], loin, ongle, 3.4, 2.7, J.avl || 0, J.gavl || 0)}
        ${crete(o.stade, c)}
        <path d="M40 41 C40 33 52 28.6 66 29 C76 29.4 84 30 88.4 33 L88.4 39 ${bas} Z" fill="${peau}" stroke="${c.fonce}" stroke-width=".7"/>
        <path d="M45 44.4 C54 ${gourmand ? 51 : 47.8} 72 ${gourmand ? 51.4 : 48.2} 85.4 41.6 C80 ${gourmand ? 49.6 : 46.8} 71 ${gourmand ? 51 : 47.4} 62 ${gourmand ? 51 : 47.4} C53 ${gourmand ? 51 : 47.4} 47.4 46.6 45 44.4 Z" fill="${c.ventre}" opacity=".92"/>
        <path d="M56.4 30.6 q-1.4 8 .8 16.4 M66.6 29.6 q-1 9 .8 17.6 M76 30.4 q-.6 7.6 .8 15.2" stroke="${c.bande}" stroke-width="1.6" fill="none" opacity=".2"/>
        ${ecailles(c)}
        <path d="M48 32.6 C56 30 70 29.4 82 31.4" fill="none" stroke="#fff" stroke-opacity=".3" stroke-width="1.4" stroke-linecap="round"/>
        ${mue}
        ${patte("phb-p-ar", [51, 43.4], [46.6, 49.4], [51.4, 55.2], c.corps, ongle, 4.6, 3.6, J.ar || 0, J.gar || 0, 1.2)}
        ${patte("phb-p-av", [80, 43], [84.4, 48.6], [84, 55.2], c.corps, ongle, 4.4, 3.4, J.av || 0, J.gav || 0)}
        ${royal}
        <g class="phb-tete"><g transform="${teteEch}">
          <path class="phb-fanon" d="${fanonD}" fill="${c.fanon}" stroke="${c.fonce}" stroke-width=".55"/>
          <path d="M90 41 q2 3.6 4.4 4.6 M93.6 40.8 q1.6 3.4 3.6 4.4" stroke="${c.fonce}" stroke-width=".35" fill="none" opacity=".5"/>
          <path d="${epines.map(([x, y]) => `M${x} ${y} l1.3 -.2 l-.7 1.1 Z`).join(" ")}" fill="${c.fanon}" stroke="${c.fonce}" stroke-width=".35" stroke-linejoin="round"/>
          <path d="M84 31.4 C90 26 100 25.2 107.4 28 C112.4 30 115.2 33 114.4 36 C112.6 39.2 104 40.2 96 40.2 C90 40.8 86 40.4 84 38.4 Z" fill="${peau}" stroke="${c.fonce}" stroke-width=".7"/>
          <path d="M90 28.4 C96 26.4 103 26.4 108.6 28.6" fill="none" stroke="#fff" stroke-opacity=".32" stroke-width="1" stroke-linecap="round"/>
          <circle cx="91.6" cy="35.4" r="3.1" fill="${c.joue}" stroke="${c.fonce}" stroke-width=".5"/>
          <circle cx="90.9" cy="34.7" r="1" fill="#fff" opacity=".5"/>
          <circle cx="98.4" cy="26.4" r=".65" fill="${c.fonce}" opacity=".7"/>
          <ellipse cx="111.8" cy="31.4" rx=".9" ry=".7" fill="${c.fonce}"/>
          <path d="${bouche}" fill="none" stroke="${c.fonce}" stroke-width=".85" stroke-linecap="round"/>
          ${joues}${yeux}${sourcil}${pansement}${acc.yeux}${acc.tete}
        </g></g>
        <g transform="${teteEch}">${acc.cou}</g>
      </g></g></g></svg>`;
  }

  window.PhilibertDessin = { svg, couleurs, teinte };
})();
