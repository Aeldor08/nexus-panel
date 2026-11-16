"use strict";
/* Dessin de Philibert, l'iguane vert de NEXUS (SVG original, vu de profil, tourné vers la droite).
   PhilibertDessin.svg({ stade, variante, humeur, pose, portes, mue, ventre, malade, froid }) → chaîne SVG.
   Les animations (pattes, queue, clignement, hochement, fanon) sont en CSS (philibert.css) sur les classes
   .phb-patte, .phb-queue, .phb-paupiere, .phb-tete, .phb-fanon : rien n'est animé ici en JavaScript.
   Détails d'iguane vert : grande écaille ronde sur la joue, fanon sous le menton, crête dorsale, queue rayée,
   iris doré, petit « troisième œil » sur le dessus de la tête. */
(() => {
  const PALETTES = {
    insulaire: { corps: "#4fae4f", fonce: "#2f7a37", ventre: "#a9d77a", crete: "#79c56a", fanon: "#c6e39a", bande: "#2a6a30", joue: "#d5e8b5" },
    royal: { corps: "#4fae4f", fonce: "#2f7a37", ventre: "#b4dc7f", crete: "#e7b93a", fanon: "#cfe6a0", bande: "#2a6a30", joue: "#e9e0a8" },
    gourmand: { corps: "#5cb550", fonce: "#357f37", ventre: "#c0e08a", crete: "#82c96d", fanon: "#d0e8a6", bande: "#2e6f31", joue: "#dcebbd" },
    nageur: { corps: "#3fa88c", fonce: "#21705f", ventre: "#9ed9bd", crete: "#5cc6dc", fanon: "#b9e6cf", bande: "#1f5f80", joue: "#cdeadf" },
    convalescent: { corps: "#63b25a", fonce: "#3b7f3c", ventre: "#b6dc8c", crete: "#8acb78", fanon: "#d2e8ad", bande: "#33703a", joue: "#dbebc2" },
  };
  const MALADE = { corps: "#a9c79b", fonce: "#7f9e73", ventre: "#d3e3c0", crete: "#b9d3a8", fanon: "#dfead0", bande: "#87a57c", joue: "#e4eedb" };
  const FROID = { corps: "#3b7f45", fonce: "#245535", ventre: "#86b073", crete: "#5a9a5e", fanon: "#a6c88e", bande: "#1e4a2c", joue: "#bcd3a8" };
  const SAGE = { corps: "#6f9f62", fonce: "#4a7444", ventre: "#c3d8a6", fanon: "#e4ecd6", joue: "#e2e9cf" };

  function couleurs(o) {
    let c = { ...(PALETTES[o.variante] || PALETTES.insulaire) };
    if (o.stade === "sage") c = { ...c, ...SAGE, crete: o.variante === "royal" ? "#e7b93a" : o.variante === "nageur" ? "#7fc3cf" : "#9dbb8a" };
    if (o.malade) c = { ...c, ...MALADE };
    else if (o.froid) c = { ...c, ...FROID };
    return c;
  }

  function crete(stade, c) {
    const taille = stade === "bebe" ? .55 : stade === "juvenile" ? .8 : 1;
    let d = "";
    for (let x = 50; x <= 90; x += 3.3) {
      const y = 30.2 + Math.pow((x - 68) / 22, 2) * 2.2 - (x > 84 ? (x - 84) * .35 : 0);
      const h = (1.8 + 2.6 * Math.sin(Math.PI * (x - 46) / 48)) * taille;
      d += `M${(x - 1.5).toFixed(1)} ${(y + .6).toFixed(1)} L${(x + .3).toFixed(1)} ${(y - h).toFixed(1)} L${(x + 1.5).toFixed(1)} ${(y + .6).toFixed(1)} Z`;
    }
    return `<path class="phb-crete" d="${d}" fill="${c.crete}" stroke="${c.fonce}" stroke-width=".4" stroke-linejoin="round"/>`;
  }

  function patte(cls, d, orteils, coul, epais) {
    return `<g class="phb-patte ${cls}"><path d="${d}" fill="none" stroke="${coul}" stroke-width="${epais}" stroke-linecap="round" stroke-linejoin="round"/>` +
      `<path d="${orteils}" fill="none" stroke="${coul}" stroke-width="1" stroke-linecap="round"/></g>`;
  }

  function accessoires(portes, c) {
    const p = portes || {};
    let tete = "", yeux = "", cou = "";
    if (p.tete === "chapeau") tete = `<g class="phb-acc"><path d="M94.5 26.4 C94.6 20.4 107.4 20.4 107.5 26.4 Z" fill="#e9c768" stroke="#a8812f" stroke-width=".5"/>
      <rect x="94.7" y="24.2" width="12.6" height="1.7" fill="#d9434f"/><ellipse cx="101" cy="26.6" rx="10.5" ry="2.1" fill="#f0d27b" stroke="#a8812f" stroke-width=".5"/>
      <path d="M92 26.8 h18" stroke="#c9a24a" stroke-width=".35" stroke-dasharray="1 1"/></g>`;
    if (p.tete === "couronne") tete = `<g class="phb-acc">${[[94.6, 27], [100.6, 25.6], [106.6, 27.2]].map(([x, y], i) =>
      `<g transform="translate(${x} ${y})">${[0, 72, 144, 216, 288].map(a => `<ellipse rx="1.5" ry="2.4" transform="rotate(${a}) translate(0 -1.6)" fill="${i === 1 ? "#ff6b8b" : "#ff4f6d"}"/>`).join("")}
      <circle r="1" fill="#ffd34d"/></g>`).join("")}</g>`;
    if (p.yeux === "lunettes") yeux = `<g class="phb-acc"><path d="M93 30 L97.6 30.4" stroke="#1b2330" stroke-width=".9"/>
      <circle cx="101.2" cy="31" r="3.7" fill="#1d2a3a" stroke="#0f141b" stroke-width=".7"/><path d="M99.4 29.6 q1 -1 2.4 -.9" stroke="#9fc7ff" stroke-width=".6" fill="none" opacity=".8"/></g>`;
    if (p.cou === "collier") cou = `<g class="phb-acc">${[[86.6, 36.8, "#ff7ab6"], [87.6, 40.4, "#ffd34d"], [89.8, 43.4, "#7fd0ff"], [93.2, 45.2, "#ff7ab6"], [96.8, 45.6, "#ffd34d"]].map(([x, y, f]) =>
      `<circle cx="${x}" cy="${y}" r="1.9" fill="${f}" stroke="#fff" stroke-width=".4"/><circle cx="${x}" cy="${y}" r=".6" fill="#fff6c2"/>`).join("")}</g>`;
    if (p.cou === "foulard") cou = `<g class="phb-acc"><path d="M85.2 36 L97 41.2 L88.6 48.2 Z" fill="#e2464f" stroke="#a52a33" stroke-width=".5"/>
      <circle cx="89" cy="40" r=".7" fill="#fff"/><circle cx="91.6" cy="43" r=".7" fill="#fff"/><circle cx="88.6" cy="45" r=".6" fill="#fff"/><circle cx="93.6" cy="40.8" r=".6" fill="#fff"/></g>`;
    void c;
    return { tete, yeux, cou };
  }

  function oeuf(o) {
    const fendu = o.fendu ? `<path d="M57 38 l3 2.5 l2.6 -3 l2.4 3.4 l2.8 -2.6 l2.6 2.2" fill="none" stroke="#8a7a55" stroke-width=".8" stroke-linejoin="round"/>` : "";
    return `<svg class="phb-svg phb-oeuf" viewBox="0 0 128 64" role="img" aria-label="${o.label || "L'œuf de Philibert"}">
      <ellipse cx="64" cy="58" rx="26" ry="4.5" fill="#e6c98b" opacity=".9"/>
      <g class="phb-oeuf-corps"><ellipse cx="64" cy="43" rx="11" ry="14" fill="#f6eed8" stroke="#c9b98f" stroke-width=".8"/>
      <ellipse cx="60" cy="38" rx="2.2" ry="1.4" fill="#d9cba3"/><ellipse cx="68" cy="47" rx="1.8" ry="1.2" fill="#d9cba3"/><ellipse cx="66" cy="35" rx="1.1" ry=".8" fill="#d9cba3"/>
      <ellipse cx="59" cy="40" rx="2.6" ry="4.4" fill="#fff" opacity=".45"/>${fendu}</g>
      <path d="M36 58 C44 52 52 54 56 56 M72 56 C78 53 86 52 92 58" stroke="#d8b774" stroke-width="1.2" fill="none"/></svg>`;
  }

  function svg(o = {}) {
    if (o.stade === "oeuf") return oeuf(o);
    const c = couleurs(o);
    const h = o.humeur || "calme";
    const gourmand = o.variante === "gourmand" || o.ventre;
    const sage = o.stade === "sage";
    const echelle = { bebe: "translate(64 57) scale(.66) translate(-64 -57)", juvenile: "translate(64 57) scale(.84) translate(-64 -57)" }[o.stade] || "";
    const teteEch = { bebe: "translate(86 36) scale(1.28) translate(-86 -36)", juvenile: "translate(86 36) scale(1.1) translate(-86 -36)" }[o.stade] || "";
    const queueEch = { bebe: "translate(44 41) scale(.72 1) translate(-44 -41)", juvenile: "translate(44 41) scale(.88 1) translate(-44 -41)" }[o.stade] || "";
    const bas = gourmand ? "C82 47 75 51.5 62 51.5 C49 51.5 40 48.5 40 41" : "C82 45 74 47.6 62 47.6 C50 47.6 40 46 40 41";
    const acc = accessoires(o.portes, c);
    const dort = h === "dort";
    const yeux = dort
      ? `<path d="M97.8 31.4 Q101.2 33.2 104.6 31.4" fill="none" stroke="${c.fonce}" stroke-width="1" stroke-linecap="round"/>`
      : `<circle cx="101.2" cy="31" r="3" fill="#f6edbd"/><circle cx="101.4" cy="31" r="2.3" fill="#d4a017"/>
         <ellipse cx="101.6" cy="31" rx=".8" ry="1.6" fill="#1b1b1b"/><circle cx="102.2" cy="30.1" r=".6" fill="#fff"/>
         ${h === "malade" || h === "froid" ? `<path d="M97.7 31 A3.5 3.5 0 0 1 104.7 31 Z" fill="${c.corps}"/>` : ""}
         <ellipse class="phb-paupiere" cx="101.2" cy="31" rx="3.5" ry="3.5" fill="${c.corps}"/>`;
    const sourcil = h === "grognon" ? `<path d="M97.4 27.6 L104.6 29.3" stroke="${c.fonce}" stroke-width="1.3" stroke-linecap="round"/>`
      : sage ? `<path d="M97.2 28 q3.4 -2.2 7.6 -.2" stroke="#f3f1e6" stroke-width="1.1" fill="none" stroke-linecap="round"/>`
        : `<path d="M97.6 28 q3.4 -1.6 7 0" stroke="${c.fonce}" stroke-width=".7" fill="none" stroke-linecap="round"/>`;
    const bouche = h === "joyeux" ? "M99.6 36.8 Q106.6 40.4 113.4 35.8" : (h === "grognon" || h === "malade") ? "M99.6 38.4 Q106.6 36.4 113.4 37" : "M99.6 37.4 Q106.6 38.8 113.4 36.2";
    const joues = h === "joyeux" || gourmand ? `<ellipse cx="106.6" cy="35.6" rx="2" ry="1.2" fill="#ff8fa3" opacity="${gourmand ? .45 : .35}"/>` : "";
    const fanonD = sage ? "M87.6 39.2 C88.4 49 95 53.5 100.6 48.6 C102.6 46 103.4 42.6 103 39.4 Z" : "M88 39.5 C89 46.4 94 50.2 99.2 47.2 C101.2 45.4 102 42.4 102 39.6 Z";
    const mue = o.mue ? `<g class="phb-mue" fill="#f4f1e4" opacity=".85" stroke="#d8d2bd" stroke-width=".3">
      <path d="M54 33 l4 -1.5 l2 3 l-3 2.4 l-3.4 -1 Z"/><path d="M70 40 l5 -1 l1 3 l-4 1.6 Z"/><path d="M26 44 l4 -1 l.6 2.6 l-3.6 .8 Z"/><path d="M80 34 l3 -.6 l.4 2 l-2.8 .6 Z"/></g>` : "";
    const royal = o.variante === "royal" ? `<path class="phb-collerette" d="M87.6 26 L84.4 29.2 L88.8 30.4 L83.4 33.6 L88.4 35 L83.2 38.2 L88.2 39.4 L84.2 42.6 L89.4 42.4 Z"
      fill="#f2c443" stroke="#b8861a" stroke-width=".5" stroke-linejoin="round"/>` : "";
    const pansement = o.variante === "convalescent" ? `<g transform="rotate(-14 99 25.5)"><rect x="94.4" y="23.8" width="9.4" height="3.4" rx="1.2" fill="#f3d9b5" stroke="#c9a77b" stroke-width=".4"/>
      <circle cx="97" cy="25.5" r=".35" fill="#c9a77b"/><circle cx="99.1" cy="25.5" r=".35" fill="#c9a77b"/><circle cx="101.2" cy="25.5" r=".35" fill="#c9a77b"/></g>` : "";
    const pose = o.pose || "debout";
    return `<svg class="phb-svg phb-${o.stade || "bebe"} phb-h-${h} phb-pose-${pose}" viewBox="0 0 128 64" role="img" aria-label="${o.label || "Philibert"}">
      <ellipse class="phb-ombre" cx="62" cy="57.4" rx="${pose === "nage" ? 0 : 42}" ry="2.4" fill="#000" opacity=".16"/>
      <g transform="${echelle}"><g class="phb-corps-tout">
        <g class="phb-queue"><g transform="${queueEch}">
          <path d="M44.5 37 C32 38 22 44 12 49 C8 51 4 52.2 1 52.4 C5 52.9 10 52.4 14.4 51.4 C24 48.6 34 46.4 44.5 45.6 Z" fill="${c.corps}" stroke="${c.fonce}" stroke-width=".6"/>
          <path d="M35 39.6 l-1.8 6.6 M27.6 42.6 l-1.6 5.4 M20.4 46.2 l-1.3 4 M13.8 49.4 l-.9 2.4" stroke="${c.bande}" stroke-width="1.7" stroke-linecap="round" opacity=".55"/>
        </g></g>
        ${patte("phb-p-ar-loin", "M46.5 42 L42.6 50 L46.4 54.6", "M46.4 54.6 l3 .4 M46.4 54.6 l2.2 1.6 M46.4 54.6 l-.6 1.8", c.fonce, 3.6)}
        ${patte("phb-p-av-loin", "M75 41.6 L77 49.6 L81.4 54.2", "M81.4 54.2 l3 .2 M81.4 54.2 l2.4 1.6 M81.4 54.2 l-.4 1.8", c.fonce, 3.4)}
        ${crete(o.stade, c)}
        <path d="M40 41 C40 33 52 28.6 66 29 C76 29.4 84 30 88.4 33 L88.4 39 ${bas} Z" fill="${c.corps}" stroke="${c.fonce}" stroke-width=".7"/>
        <path d="M45 44.4 C54 ${gourmand ? 51 : 47.8} 72 ${gourmand ? 51.4 : 48.2} 85.4 41.6 C80 ${gourmand ? 49.6 : 46.8} 71 ${gourmand ? 51 : 47.4} 62 ${gourmand ? 51 : 47.4} C53 ${gourmand ? 51 : 47.4} 47.4 46.6 45 44.4 Z" fill="${c.ventre}" opacity=".9"/>
        <path d="M56.4 30.6 q-1.4 8 .8 16.4 M66.6 29.6 q-1 9 .8 17.6 M76 30.4 q-.6 7.6 .8 15.2" stroke="${c.bande}" stroke-width="1.6" fill="none" opacity=".22"/>
        ${mue}
        ${patte("phb-p-ar", "M51 43.2 L47.6 51.2 L52.6 55.2", "M52.6 55.2 l3.2 .3 M52.6 55.2 l2.4 1.8 M52.6 55.2 l-.6 2", c.corps, 4.4)}
        ${patte("phb-p-av", "M80 43 L82 51 L86.8 55.2", "M86.8 55.2 l3.2 .2 M86.8 55.2 l2.6 1.7 M86.8 55.2 l-.4 2", c.corps, 4.2)}
        ${royal}
        <g class="phb-tete"><g transform="${teteEch}">
          <path class="phb-fanon" d="${fanonD}" fill="${c.fanon}" stroke="${c.fonce}" stroke-width=".55"/>
          <path d="M90 41 q2 3.6 4.4 4.6 M93.6 40.8 q1.6 3.4 3.6 4.4" stroke="${c.fonce}" stroke-width=".35" fill="none" opacity=".5"/>
          <path d="M84 31.4 C90 26 100 25.2 107.4 28 C112.4 30 115.2 33 114.4 36 C112.6 39.2 104 40.2 96 40.2 C90 40.8 86 40.4 84 38.4 Z" fill="${c.corps}" stroke="${c.fonce}" stroke-width=".7"/>
          <circle cx="91.6" cy="35.4" r="3.1" fill="${c.joue}" stroke="${c.fonce}" stroke-width=".5"/>
          <circle cx="91" cy="34.8" r=".9" fill="#fff" opacity=".45"/>
          <circle cx="98.4" cy="26.4" r=".6" fill="${c.fonce}" opacity=".7"/>
          <circle cx="111.6" cy="31.6" r=".75" fill="${c.fonce}"/>
          <path d="${bouche}" fill="none" stroke="${c.fonce}" stroke-width=".85" stroke-linecap="round"/>
          ${joues}${yeux}${sourcil}${pansement}${acc.yeux}${acc.tete}
        </g></g>
        <g transform="${teteEch}">${acc.cou}</g>
      </g></g></svg>`;
  }

  window.PhilibertDessin = { svg, couleurs };
})();
