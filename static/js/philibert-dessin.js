"use strict";
/* Dessin de Philibert, l'iguane vert de NEXUS (SVG original, vu de profil, tourné vers la droite).
   PhilibertDessin.svg({ stade, variante, humeur, pose, portes, mue, ventre, malade, froid, jambes, fendu, label, uid, leger })
   → chaîne SVG (viewBox 128 × 64, le sol à y ≈ 56).
   Dessin « naturaliste », d'après l'anatomie de l'iguane vert (Iguana iguana) :
   - tête haute aux joues fortes, grande écaille ronde et pâle sous l'oreille (écaille subtympanique), tympan,
     arcade au-dessus de l'œil, iris doré à pupille ronde, narine près du bout du museau, rangées d'écailles des lèvres,
     « troisième œil » (œil pariétal) sur le dessus du crâne, petites écailles coniques sur le cou ;
   - fanon sous la gorge, bordé de petites épines sur son bord avant (plus grand chez l'adulte et le vieux sage) ;
   - crête d'épines fines, penchées vers l'arrière, plus hautes sur la nuque, qui se prolonge sur la base de la queue ;
   - queue très longue, effilée, annelée de bandes sombres ; quelques bandes discrètes sur les flancs de l'adulte ;
   - pattes musclées en deux segments (genou vers l'avant, coude vers l'arrière, comme chez les lézards) et longs
     doigts griffus (le 4ᵉ orteil de la patte arrière est le plus long) ;
   - couleurs naturelles : dos plus sombre, flancs verts, ventre pâle ; le froid l'assombrit (un lézard fonce pour
     capter la chaleur), la maladie le pâlit ; le Royal prend les couleurs orangées de la parade des mâles.
   Le volume vient de dégradés (une source de lumière en haut) et d'une fine texture d'écailles (motif SVG),
   omise en version « leger » (le petit Philibert du haut, dessiné souvent).
   « uid » préfixe les identifiants des dégradés : un préfixe par endroit de la page (haut, île, médaillon…),
   pour qu'un dessin caché ne prive jamais un autre de ses dégradés.
   Les animations sont en CSS (philibert.css) sur .phb-patte, .phb-genou, .phb-queue, .phb-queue-bout,
   .phb-corps, .phb-paupiere, .phb-tete, .phb-fanon. « jambes » donne une pose fixe (images du mini-jeu de course) :
   { av, ar, avl, arl } en degrés pour les hanches et { gav, gar, gavl, garl } pour les genoux (négatif = patte levée). */
(() => {
  const r2 = n => Math.round(n * 100) / 100;
  const pt = p => `${r2(p[0])} ${r2(p[1])}`;
  const bz = (s, t) => { const u = 1 - t; return [0, 1].map(k => u * u * u * s[0][k] + 3 * u * u * t * s[1][k] + 3 * u * t * t * s[2][k] + t * t * t * s[3][k]); };
  const bzd = (s, t) => { const u = 1 - t; return [0, 1].map(k => 3 * u * u * (s[1][k] - s[0][k]) + 6 * u * t * (s[2][k] - s[1][k]) + 3 * t * t * (s[3][k] - s[2][k])); };
  const unit = d => { const L = Math.hypot(d[0], d[1]) || 1; return [d[0] / L, d[1] / L]; };

  // dos (sombre) · corps · clair (flancs) · ventre · crête · fanon · bandes · joue (écaille ronde) · membre (bas des pattes)
  const PALETTES = {
    insulaire: { dos: "#3b7633", corps: "#5aa443", clair: "#86c05a", ventre: "#c6da92", crete: "#8fbd5c", fanon: "#9dc66b", bande: "#263321", joue: "#d5e2ae", membre: "#468a37" },
    royal: { dos: "#46702f", corps: "#679f44", clair: "#9db452", ventre: "#d8d394", crete: "#e1892e", fanon: "#e4a248", bande: "#3a3521", joue: "#ecd59c", membre: "#a07f34" },
    gourmand: { dos: "#447a30", corps: "#66a846", clair: "#93c35e", ventre: "#d3de98", crete: "#9cc463", fanon: "#aacd72", bande: "#2f3a1e", joue: "#dde4b4", membre: "#4f8f39" },
    nageur: { dos: "#2a6a5c", corps: "#3d9c84", clair: "#68bfa3", ventre: "#b6dcc5", crete: "#78c4b2", fanon: "#88c8b1", bande: "#1c3a40", joue: "#cfe6d8", membre: "#2f7f6a" },
    convalescent: { dos: "#557f44", corps: "#77ab5a", clair: "#9cc37d", ventre: "#d1e1ac", crete: "#a7c785", fanon: "#b4d190", bande: "#435437", joue: "#dde6c1", membre: "#5f9447" },
  };
  const MALADE = { dos: "#7c8a6f", corps: "#a1b192", clair: "#bac7ac", ventre: "#dde3cf", crete: "#b4bfa5", fanon: "#c4ceb5", bande: "#6d7862", joue: "#e4e8da", membre: "#8a9a7c" };
  const FROID = { dos: "#27452a", corps: "#3d6a39", clair: "#58864c", ventre: "#93aa7a", crete: "#5d8954", fanon: "#6c945f", bande: "#18241a", joue: "#b0c096", membre: "#2f5a2e" };
  const SAGE = { dos: "#596849", corps: "#7d9166", clair: "#9fae85", ventre: "#d0d4b1", fanon: "#b2b894", bande: "#44483a", joue: "#e0dfc6", membre: "#66764f" };

  function couleurs(o) {
    let c = { ...(PALETTES[o.variante] || PALETTES.insulaire) };
    if (o.stade === "sage") c = { ...c, ...SAGE, crete: o.variante === "royal" ? "#d9923e" : o.variante === "nageur" ? "#8cbfb4" : "#a9b48e" };
    if (o.malade) c = { ...c, ...MALADE };
    else if (o.froid) c = { ...c, ...FROID };
    c.corps = c.corps || c.clair;
    c.fonce = c.dos;               // (nom d'origine, gardé pour les autres fichiers)
    return c;
  }
  // couleur plus claire (k > 0) ou plus foncée (k < 0)
  function teinte(hex, k) {
    const n = parseInt(hex.slice(1), 16), v = [n >> 16, (n >> 8) & 255, n & 255];
    return "#" + v.map(x => Math.round(k > 0 ? x + (255 - x) * k : x * (1 + k)).toString(16).padStart(2, "0")).join("");
  }
  function melange(a, b, k) {
    const A = parseInt(a.slice(1), 16), B = parseInt(b.slice(1), 16);
    return "#" + [16, 8, 0].map(s => Math.round(((A >> s) & 255) * (1 - k) + ((B >> s) & 255) * k).toString(16).padStart(2, "0")).join("");
  }
  const cle = c => { let h = 7; for (const ch of Object.values(c).join("")) h = (h * 31 + ch.charCodeAt(0)) >>> 0; return h.toString(36); };

  // ---- dégradés et motifs ----
  function defs(c, u, leger) {
    return `<defs>
      <linearGradient id="${u}-p" gradientUnits="userSpaceOnUse" x1="0" y1="29" x2="0" y2="48">
        <stop offset="0" stop-color="${c.dos}"/><stop offset=".3" stop-color="${c.corps}"/><stop offset=".64" stop-color="${c.clair}"/>
        <stop offset=".84" stop-color="${melange(c.clair, c.ventre, .55)}"/><stop offset="1" stop-color="${c.ventre}"/></linearGradient>
      <linearGradient id="${u}-q" gradientUnits="userSpaceOnUse" x1="22.6" y1="40.6" x2="26.2" y2="51.6">
        <stop offset="0" stop-color="${c.dos}"/><stop offset=".42" stop-color="${c.corps}"/><stop offset=".8" stop-color="${c.clair}"/><stop offset="1" stop-color="${melange(c.clair, c.ventre, .5)}"/></linearGradient>
      <linearGradient id="${u}-m" gradientUnits="userSpaceOnUse" x1="0" y1="41" x2="0" y2="56"><stop offset="0" stop-color="${c.clair}"/><stop offset=".42" stop-color="${c.corps}"/><stop offset="1" stop-color="${c.membre}"/></linearGradient>
      <linearGradient id="${u}-f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${teinte(c.fanon, -.12)}"/><stop offset=".55" stop-color="${c.fanon}"/><stop offset="1" stop-color="${teinte(c.fanon, .28)}"/></linearGradient>
      <radialGradient id="${u}-j" cx=".36" cy=".32" r=".8"><stop offset="0" stop-color="${teinte(c.joue, .32)}"/><stop offset=".55" stop-color="${c.joue}"/><stop offset="1" stop-color="${teinte(c.joue, -.2)}"/></radialGradient>
      <radialGradient id="${u}-i" cx=".42" cy=".38" r=".62"><stop offset="0" stop-color="#f7d873"/><stop offset=".5" stop-color="#dc9c2c"/><stop offset=".82" stop-color="#a35d18"/><stop offset="1" stop-color="#5e330e"/></radialGradient>
      <radialGradient id="${u}-o"><stop offset="0" stop-color="#2b2112" stop-opacity=".34"/><stop offset=".6" stop-color="#2b2112" stop-opacity=".16"/><stop offset="1" stop-color="#2b2112" stop-opacity="0"/></radialGradient>
      <radialGradient id="${u}-l" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".16"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>
      ${leger ? "" : `<pattern id="${u}-e" width="1.5" height="1.3" patternUnits="userSpaceOnUse">
        <circle cx=".38" cy=".38" r=".34" fill="#0b1a08" fill-opacity=".16"/><circle cx="1.13" cy="1.03" r=".34" fill="#0b1a08" fill-opacity=".16"/>
        <circle cx=".3" cy=".28" r=".15" fill="#fff" fill-opacity=".14"/><circle cx="1.05" cy=".93" r=".15" fill="#fff" fill-opacity=".14"/></pattern>`}
    </defs>`;
  }

  // ---- la queue : un tube le long de deux courbes (base et bout), avec ses anneaux sombres ----
  const Q_BASE = [[46, 39.4], [39, 39.8], [30.5, 42.4], [24, 46]];
  const Q_BOUT = [[24, 46], [17.6, 49.6], [9.6, 52.6], [1.2, 54]];
  const wBase = t => 9.6 - 4.6 * t, wBout = t => 5 * Math.pow(1 - t, 1.15) + .3 * t;
  function bord(s, w, t, cote) {
    const c = bz(s, t), d = unit(bzd(s, t)), e = w(t) / 2 * cote;
    return [c[0] - d[1] * e, c[1] + d[0] * e];             // cote = 1 : dessus (vers le haut)
  }
  function tube(s, w, t0 = 0, t1 = 1, n = 14) {
    const H = [], B = [];
    for (let i = 0; i <= n; i++) { const t = t0 + (t1 - t0) * i / n; H.push(bord(s, w, t, 1)); B.push(bord(s, w, t, -1)); }
    return { H, B, d: `M${H.map(pt).join(" L")} L${B.reverse().map(pt).join(" L")} Z`, haut: `M${H.map(pt).join(" L")}`, bas: `M${B.slice().reverse().map(pt).join(" L")}` };
  }
  function queue(c, u, o) {
    const taille = { bebe: .45, juvenile: .72, sage: 1.05 }[o.stade] || 1;
    const opB = { bebe: .22, juvenile: .38, sage: .42 }[o.stade] || .55;
    const base = tube(Q_BASE, wBase), bout = tube(Q_BOUT, wBout, 0, 1, 18);
    const anneaux = (s, w, L) => L.map(([a, b]) => tube(s, w, a, b, 4).d).join(" ");
    // épines de la crête sur la base de la queue (penchées vers le bout)
    let ep = "";
    for (const [t, h] of [[.06, 1.5], [.16, 1.3], [.27, 1.1], [.38, .9], [.5, .7], [.62, .55]]) {
      const b = bord(Q_BASE, wBase, t, .82), d = unit(bzd(Q_BASE, t)), up = [d[1], -d[0]], H = h * taille * (o.variante === "royal" ? 1.15 : 1);
      if (up[1] > 0) { up[0] = -up[0]; up[1] = -up[1]; }
      const tip = [b[0] + up[0] * H + d[0] * H * .45, b[1] + up[1] * H + d[1] * H * .45];
      ep += `M${pt([b[0] - d[0] * .7, b[1] - d[1] * .7])} L${pt(tip)} L${pt([b[0] + d[0] * .7, b[1] + d[1] * .7])} Z `;
    }
    const lum = (s, w, t0, t1) => { const P = []; for (let i = 0; i <= 8; i++) P.push(bord(s, w, t0 + (t1 - t0) * i / 8, .5)); return `M${P.map(pt).join(" L")}`; };
    const trait = `stroke="${teinte(c.dos, -.25)}" stroke-width=".5" stroke-opacity=".75" fill="none"`;
    return `<g class="phb-queue"><g transform="${o.queueEch}">
        <path d="${ep}" fill="${c.crete}" stroke="${teinte(c.dos, -.2)}" stroke-width=".3" stroke-linejoin="round"/>
        <path d="${base.d}" fill="url(#${u}-q)"/>${o.leger ? "" : `<path d="${base.d}" fill="url(#${u}-e)"/>`}
        <path d="${anneaux(Q_BASE, wBase, [[.44, .58], [.86, 1]])}" fill="${c.bande}" opacity="${opB}"/>
        <path d="${lum(Q_BASE, wBase, .05, 1)}" stroke="#fff" stroke-opacity=".2" stroke-width=".9" fill="none" stroke-linecap="round"/>
        <path d="${base.haut} ${base.bas}" ${trait}/>
        <g class="phb-queue-bout">
          <path d="${bout.d}" fill="url(#${u}-q)"/>${o.leger ? "" : `<path d="${bout.d}" fill="url(#${u}-e)"/>`}
          <path d="${anneaux(Q_BOUT, wBout, [[.1, .21], [.32, .42], [.53, .62], [.72, .8], [.88, .94]])}" fill="${c.bande}" opacity="${opB}"/>
          <path d="${lum(Q_BOUT, wBout, 0, .7)}" stroke="#fff" stroke-opacity=".18" stroke-width=".7" fill="none" stroke-linecap="round"/>
          <path d="${bout.haut} ${bout.bas}" ${trait}/>
        </g>
      </g></g>`;
  }

  // ---- crête dorsale : épines fines, plus hautes sur la nuque, penchées vers l'arrière ----
  const DOS = [[[41.6, 37], [49, 31.8], [59, 30.4], [68, 30.6]], [[68, 30.6], [76, 30.8], [82.4, 29.6], [88.6, 30.6]]];
  function crete(c, o) {
    const taille = ({ bebe: .45, juvenile: .72, sage: 1.08 }[o.stade] || 1) * (o.variante === "royal" ? 1.15 : 1);
    let d = "";
    const pas = [[0, .2, 1], [0, .32, 1], [0, .44, 1], [0, .56, 1], [0, .68, 1], [0, .8, 1], [0, .92, 1]];
    for (let i = 0; i <= 10; i++) pas.push([1, i / 10, 1]);
    for (const [k, t] of pas) {
      const b = bz(DOS[k], t), dd = unit(bzd(DOS[k], t)), up = [dd[1], -dd[0]];
      const h = (1.15 + 4.1 * Math.exp(-Math.pow((b[0] - 80) / 12.5, 2))) * taille;
      const base = [b[0] + dd[0] * .1 - up[0] * .7, b[1] - up[1] * .7];
      const tip = [b[0] + up[0] * h - dd[0] * h * .42, b[1] + up[1] * h - dd[1] * h * .42];
      const bl = [base[0] - dd[0] * .85, base[1] - dd[1] * .85], br = [base[0] + dd[0] * .85, base[1] + dd[1] * .85];
      const c1 = [bl[0] + up[0] * h * .5 + dd[0] * .2, bl[1] + up[1] * h * .5], c2 = [br[0] + up[0] * h * .45 - dd[0] * h * .25, br[1] + up[1] * h * .45];
      d += `M${pt(bl)} Q${pt(c1)} ${pt(tip)} Q${pt(c2)} ${pt(br)} Z `;
    }
    return `<path class="phb-crete" d="${d}" fill="${c.crete}" stroke="${teinte(c.dos, -.22)}" stroke-width=".3" stroke-linejoin="round"/>`;
  }

  // ---- pattes : cuisse/bras puis jambe/avant-bras (deux segments arrondis), pied à cinq doigts griffus ----
  function capsule(a, b, ra, rb) {
    const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.hypot(dx, dy) || 1, nx = -dy / L, ny = dx / L;
    const P = (p, r, s) => pt([p[0] + nx * r * s, p[1] + ny * r * s]);
    return `M${P(a, ra, 1)} L${P(b, rb, 1)} A${r2(rb)} ${r2(rb)} 0 0 0 ${P(b, rb, -1)} L${P(a, ra, -1)} A${r2(ra)} ${r2(ra)} 0 0 0 ${P(a, ra, 1)} Z`;
  }
  const DOIGTS_AR = [[2.8, 1], [4.6, 1.2], [6.2, 1.1], [7.8, .8], [-2.8, 1.2]];
  const DOIGTS_AV = [[2.2, 1], [3.4, 1.2], [4.2, 1], [3.8, .5], [-2, 1.1]];
  function patte(cls, H, G, P, o) {
    const k = o.k || 1, flex = o.arriere ? -(o.g || 0) : (o.g || 0);
    const doigts = (o.arriere ? DOIGTS_AR : DOIGTS_AV).map(([x, y]) => [x * k, y]);
    let dg = "", gr = "";
    for (const [x, y] of doigts) {
      const fin = [P[0] + x, P[1] + y], m = [P[0] + x * .5, P[1] + y * .5 - .35], dd = unit([x, y - .2]);
      dg += `M${pt(P)} Q${pt(m)} ${pt(fin)} `;
      gr += `M${pt(fin)} l${r2(dd[0] * .75)} ${r2(dd[1] * .75 + .25)} `;
    }
    const ligne = `stroke="${o.trait}" stroke-width=".35" stroke-opacity=".45"`;
    const tex = o.tex ? d => `<path d="${d}" fill="url(#${o.tex})"/>` : () => "";
    return `<g class="phb-patte ${cls}"><g transform="rotate(${o.a || 0} ${pt(H)})">
      <g class="phb-genou"><g transform="rotate(${flex} ${pt(G)})">
        <path d="${capsule(G, P, o.w[1] / 2, o.w[2] / 2)}" fill="${o.fill}" ${ligne}/>${tex(capsule(G, P, o.w[1] / 2, o.w[2] / 2))}
        <ellipse cx="${r2(P[0] + .5)}" cy="${r2(P[1] + .45)}" rx="${r2(1.5 * k)}" ry=".95" fill="${o.doigt}"/>
        <path d="${dg}" stroke="${o.doigt}" stroke-width="${r2(.95 * k)}" stroke-linecap="round" fill="none"/>
        <path d="${gr}" stroke="${o.ongle}" stroke-width=".55" stroke-linecap="round" fill="none"/>
      </g></g>
      <path d="${capsule(H, G, o.w[0] / 2, o.w[1] / 2)}" fill="${o.fill}"/>${tex(capsule(H, G, o.w[0] / 2, o.w[1] / 2))}
      ${o.lum ? `<path d="M${pt([H[0] - 1, H[1] - .6])} Q${pt([(H[0] + G[0]) / 2, (H[1] + G[1]) / 2 - 1.6])} ${pt([G[0], G[1] - 1.2])}" stroke="#fff" stroke-opacity=".2" stroke-width=".8" fill="none" stroke-linecap="round"/>` : ""}
    </g></g>`;
  }

  // ---- accessoires (dessinés comme de vrais objets : paille tressée, verres fumés, fleurs, perles, coton) ----
  function accessoires(portes, u) {
    const p = portes || {};
    let tete = "", yeux = "", cou = "";
    if (p.tete === "chapeau") tete = `<g class="phb-acc">
      <defs><linearGradient id="${u}-ch" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f3dc98"/><stop offset=".6" stop-color="#d9b866"/><stop offset="1" stop-color="#b38f43"/></linearGradient></defs>
      <path d="M94.6 26.6 C94.4 21.6 97.4 19.6 101 19.6 C104.6 19.6 107.6 21.6 107.4 26.6 Z" fill="url(#${u}-ch)" stroke="#9a7634" stroke-width=".4"/>
      <path d="M95.2 22.8 q5.8 -1.2 11.6 0 M94.8 24.6 q6.2 -1.2 12.4 0" stroke="#a8843c" stroke-width=".3" fill="none" stroke-dasharray=".7 .5"/>
      <path d="M94.7 24.9 q6.3 -1.1 12.6 0 l0 1.4 q-6.3 -1.1 -12.6 0 Z" fill="#b83a3f"/><path d="M94.8 25 q6.2 -1 12.4 0" stroke="#e06b6f" stroke-width=".3" fill="none"/>
      <ellipse cx="101" cy="26.7" rx="11" ry="2.2" fill="url(#${u}-ch)" stroke="#9a7634" stroke-width=".4"/>
      <ellipse cx="101" cy="26.7" rx="8.6" ry="1.3" fill="none" stroke="#a8843c" stroke-width=".3" stroke-dasharray=".8 .5"/>
      <path d="M91 27.2 q10 2.2 20 0" stroke="#8a6a2e" stroke-width=".35" fill="none" opacity=".6"/></g>`;
    if (p.tete === "couronne") tete = `<g class="phb-acc">
      <defs><radialGradient id="${u}-hb" cx=".5" cy=".5" r=".55"><stop offset="0" stop-color="#8e1230"/><stop offset=".3" stop-color="#d8344f"/><stop offset="1" stop-color="#ff7a8a"/></radialGradient></defs>
      <path d="M92.6 27.8 q8.4 -3.6 16.4 -.4" stroke="#4f7d34" stroke-width="1" fill="none"/>
      ${[[93.4, 27.2, .55], [97, 25.4, .6], [101, 24.8, .7], [105, 25.4, .6], [108.4, 27.2, .5]].map(([x, y, k], i) => `<g transform="translate(${x} ${y}) scale(${k})">
        ${i % 2 ? [0, 72, 144, 216, 288].map(a => `<path d="M0 0 C-2.4 -1.2 -2.2 -4.6 0 -4.8 C2.2 -4.6 2.4 -1.2 0 0 Z" transform="rotate(${a})" fill="url(#${u}-hb)" stroke="#a51f3a" stroke-width=".25"/>`).join("")
        : `<ellipse rx="2.4" ry="1.4" fill="#5d9a3e"/><path d="M-2 0 h4" stroke="#3f6e2a" stroke-width=".3"/>`}
        ${i % 2 ? `<path d="M0 0 l2.4 -2.6" stroke="#f4d24a" stroke-width=".5"/><circle cx="2.5" cy="-2.7" r=".55" fill="#ffe36a"/>` : ""}</g>`).join("")}</g>`;
    if (p.yeux === "lunettes") yeux = `<g class="phb-acc">
      <defs><linearGradient id="${u}-lu" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#3b5676"/><stop offset=".55" stop-color="#16202e"/><stop offset="1" stop-color="#0a0f16"/></linearGradient></defs>
      <path d="M90.2 31.2 L97.6 30.2" stroke="#1d1f24" stroke-width=".9" stroke-linecap="round"/>
      <path d="M97.4 28.2 C99.4 27 104 27 105.8 28.6 C106.6 31.6 105.2 34.2 101.6 34.4 C98.6 34.4 97 32.2 97.4 28.2 Z" fill="url(#${u}-lu)" stroke="#111318" stroke-width=".7"/>
      <path d="M98.8 29 q2 -1 4.6 -.4" stroke="#9fc4ef" stroke-width=".55" fill="none" opacity=".8"/><path d="M103.8 32.4 l1 -1.4" stroke="#fff" stroke-width=".4" opacity=".35"/></g>`;
    if (p.cou === "collier") cou = `<g class="phb-acc">
      <defs><radialGradient id="${u}-pe" cx=".35" cy=".3" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset=".5" stop-color="#f3e6cf"/><stop offset="1" stop-color="#c7ad86"/></radialGradient></defs>
      <path d="M86.2 33.4 C86 37.6 87.4 41.6 90 43.6 C92.6 45.4 95 45.8 96.8 45.6" stroke="#6b5435" stroke-width=".35" fill="none"/>
      ${[[86.2, 34, 1.15], [86.4, 36.6, 1.25], [87.1, 39.2, 1.3], [88.4, 41.6, 1.3], [90.4, 43.5, 1.3], [92.8, 44.9, 1.25], [95.4, 45.6, 1.15]].map(([x, y, r], i) => i % 3 === 1
        ? `<path d="M${x - r} ${y + .3} C${x - r} ${y - r * 1.2} ${x + r} ${y - r * 1.2} ${x + r} ${y + .3} Z" fill="#f2c7a8" stroke="#b9846a" stroke-width=".25"/><path d="M${x} ${y + .2} v${-r * .8} M${x - r * .5} ${y + .2} l.2 ${-r * .7} M${x + r * .5} ${y + .2} l-.2 ${-r * .7}" stroke="#b9846a" stroke-width=".2"/>`
        : `<circle cx="${x}" cy="${y}" r="${r * .85}" fill="url(#${u}-pe)" stroke="#a88f6a" stroke-width=".2"/>`).join("")}</g>`;
    if (p.cou === "foulard") cou = `<g class="phb-acc">
      <defs><linearGradient id="${u}-fo" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#d8404a"/><stop offset="1" stop-color="#93212b"/></linearGradient></defs>
      <path d="M85.2 33.4 C89.4 35.6 94 38.8 97.2 41.4 C94.6 44.4 91.6 46.8 88.6 48.6 C87 44.6 86 39 85.2 33.4 Z" fill="url(#${u}-fo)" stroke="#7d1a22" stroke-width=".4"/>
      <path d="M86.6 36 C88.6 39.6 90.8 42.6 94.2 43.2 M86.8 40.6 C88.2 43 89.6 45.2 91.4 46.4" stroke="#7d1a22" stroke-width=".35" fill="none" opacity=".55"/>
      ${[[88.4, 37.6], [91.4, 39.6], [87.8, 42.6], [90.8, 44.2], [94.2, 41.6], [88.6, 46.4]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r=".55" fill="#fff4ee" opacity=".9"/>`).join("")}
      <path d="M84.6 32.4 c-1.6 -.6 -2.6 .6 -2 1.8 c.8 1.4 2.4 .8 2.6 -.2 Z" fill="#b5303a" stroke="#7d1a22" stroke-width=".3"/></g>`;
    return { tete, yeux, cou };
  }

  // ---- l'œuf : coquille souple et un peu cabossée d'œuf de reptile, à moitié enfoui dans son nid de sable ----
  const GRAINS = [[30, 57.2], [36, 55.4], [41, 56.8], [47, 54.2], [52, 56.6], [57, 53.6], [70, 53.8], [75, 56.4], [80, 54.4], [86, 56.6], [91, 55.2], [97, 57], [44, 57.6], [66, 57.4], [83, 57.6], [61, 56.2]];
  function oeuf(o) {
    const u = (o.uid || "x") + "-oe";
    const fendu = o.fendu ? `<g fill="none" stroke="#6b5d44" stroke-width=".55" stroke-linejoin="round" stroke-linecap="round">
        <path d="M58.4 37.6 l2.2 1.8 l1.8 -2.2 l2 2.4 l2.2 -1.8 l1.6 1.4"/><path d="M62.4 37.2 l.5 -2.2 M65.4 39.8 l1.2 1.6 M59.6 39.4 l-.8 1.6"/></g>
        <path d="M60.6 39.4 l2 -2.2 l2 2.4 l-2 .6 Z" fill="#2f271c" opacity=".6"/>` : "";
    return `<svg class="phb-svg phb-oeuf" viewBox="0 0 128 64" role="img" aria-label="${o.label || "L'œuf de Philibert"}">
      <defs><radialGradient id="${u}-c" cx=".36" cy=".3" r=".85"><stop offset="0" stop-color="#fffef8"/><stop offset=".5" stop-color="#f3ebd8"/><stop offset=".84" stop-color="#ddd0b0"/><stop offset="1" stop-color="#c3b38c"/></radialGradient>
        <linearGradient id="${u}-s" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#f1dfb6"/><stop offset="1" stop-color="#d3b682"/></linearGradient>
        <radialGradient id="${u}-o"><stop offset="0" stop-color="#5a4320" stop-opacity=".3"/><stop offset="1" stop-color="#5a4320" stop-opacity="0"/></radialGradient></defs>
      <ellipse cx="64" cy="57.4" rx="44" ry="4.6" fill="url(#${u}-o)"/>
      <path d="M22 58.4 C32 50.8 47 48.4 64 48.4 C81 48.4 96 50.8 106 58.4 Z" fill="url(#${u}-s)"/>
      <ellipse cx="64" cy="51.8" rx="16" ry="3.2" fill="#a98b58" opacity=".5"/>
      <g class="phb-oeuf-corps"><g transform="rotate(-9 64 44)">
        <ellipse cx="64" cy="42.6" rx="9.2" ry="12.4" fill="url(#${u}-c)" stroke="#b9a77e" stroke-width=".45"/>
        <path d="M58.2 45.4 q2.8 1.6 5.6 .5 M66.2 36 q1.8 1.2 3.2 .4 M67.4 47.6 q1.2 -.4 1.8 -1.6" stroke="#c9ba95" stroke-width=".7" fill="none" opacity=".75" stroke-linecap="round"/>
        <g fill="#cdbf9c" opacity=".35"><ellipse cx="66.6" cy="41" rx="1.2" ry=".8"/><ellipse cx="61.4" cy="48.2" rx="1" ry=".6"/><ellipse cx="68.4" cy="33.8" rx=".7" ry=".5"/></g>
        <ellipse cx="60.6" cy="37" rx="2.4" ry="3.8" fill="#fff" opacity=".5" transform="rotate(-12 60.6 37)"/>
        ${fendu}</g></g>
      <path d="M43 58.4 C49 52.8 56 51.4 64 51.6 C72 51.4 79 52.8 85 58.4 Z" fill="url(#${u}-s)"/>
      <path d="M50 54 C56 52.4 72 52.4 78 54" stroke="#fff6dc" stroke-width=".6" fill="none" opacity=".7"/>
      <g fill="#a88a5a" opacity=".55">${GRAINS.map(([x, y], i) => `<circle cx="${x}" cy="${y}" r="${i % 3 ? .35 : .5}"/>`).join("")}</g>
      <g fill="#fff8e6" opacity=".7">${GRAINS.map(([x, y], i) => i % 2 ? `<circle cx="${x + 1.6}" cy="${y - .5}" r=".3"/>` : "").join("")}</g></svg>`;
  }

  // ---- Philibert ----
  function svg(o = {}) {
    if (o.stade === "oeuf") return oeuf(o);
    const c = couleurs(o);
    const u = (o.uid || "x") + cle(c);
    const h = o.humeur || "calme", leger = !!o.leger;
    const gourmand = o.variante === "gourmand" || o.ventre;
    const sage = o.stade === "sage", bebe = o.stade === "bebe";
    const J = o.jambes || {};
    const echelle = { bebe: "translate(64 57) scale(.66) translate(-64 -57)", juvenile: "translate(64 57) scale(.84) translate(-64 -57)" }[o.stade] || "";
    const teteEch = { bebe: "translate(86 36) scale(1.16) translate(-86 -36)", juvenile: "translate(86 36) scale(1.06) translate(-86 -36)" }[o.stade] || "";
    const queueEch = { bebe: "translate(45 40.4) scale(.78 1) translate(-45 -40.4)", juvenile: "translate(45 40.4) scale(.9 1) translate(-45 -40.4)" }[o.stade] || "";
    const acc = accessoires(o.portes, u);
    const dort = h === "dort";
    const pose = o.pose || "debout";
    const dosF = teinte(c.dos, -.22);

    // corps
    const ventreB = gourmand ? "C85 47.8 78 50.2 67 50.4 C56 50.6 47 48.8 43 44.6" : "C85 45.4 78 46.4 67 46.6 C56 46.8 47.4 46 43 43.8";
    const corpsD = `M41.6 37 C49 31.8 59 30.4 68 30.6 C76 30.8 82.4 29.6 88.6 30.6 L88.8 41.2 ${ventreB} C40.6 42.4 39.8 39.2 41.6 37 Z`;
    const opBandes = { bebe: .05, juvenile: .09 }[o.stade] || .14;
    const ecaillesVentre = (() => {
      let d = "";
      const S = gourmand ? [[[88.8, 41.2], [85, 47.8], [78, 50.2], [67, 50.4]], [[67, 50.4], [56, 50.6], [47, 48.8], [43, 44.6]]]
        : [[[88.8, 41.2], [85, 45.4], [78, 46.4], [67, 46.6]], [[67, 46.6], [56, 46.8], [47.4, 46], [43, 43.8]]];
      for (const s of S) for (let i = 1; i < 9; i++) { const p = bz(s, i / 9); d += `M${pt([p[0], p[1] - .5])} l0 -2.2 `; }
      return d;
    })();

    // tête
    const basTete = sage ? "C106 38.4 100 39.6 96 40.8 C93 42.6 89.4 43.6 86.2 42.4" : "C106 38.4 100 39.4 96 40.4 C93 41.4 89.6 42 86.6 41.4";
    const profil = `M85 30.6 C89 27.8 94 26.4 99 26.4 C104 26.4 108.6 27.6 112.4 29.6 C115 31 116.4 32.8 116 34.6 C115.6 36.2 114 37 111.6 37.4 ${basTete}`;
    const teteD = `${profil} C85.2 41 84.4 39 84.4 37 Z`;
    const fanonD = sage ? [[103, 39.2], [103, 46.6], [98.6, 52.4], [92.6, 52.6], [88.4, 52.8], [86, 48.6], [85.2, 42.6]]
      : bebe ? [[101, 39.6], [100.8, 43], [98, 46], [94.4, 46.2], [91.4, 46.4], [88.8, 44.4], [87.6, 41.8]]
        : [[103, 39.2], [102.6, 44.6], [98.6, 49.6], [93.2, 50], [89.4, 50.2], [86.8, 47.2], [85.6, 42.6]];
    const fanonPath = `M${pt(fanonD[0])} C${fanonD.slice(1, 4).map(pt).join(" ")} C${fanonD.slice(4, 7).map(pt).join(" ")} Z`;
    const avantFanon = [fanonD[0], fanonD[1], fanonD[2], fanonD[3]];
    let epines = "";
    for (let i = 1; i <= 9; i++) {
      const t = .06 + i * .085, b = bz(avantFanon, t), d = unit(bzd(avantFanon, t)), nn = [d[1], -d[0]];   // vers l'avant / le bas
      const hh = (bebe ? .7 : 1.15) * (1 - Math.abs(t - .5) * .6);
      epines += `M${pt([b[0] - d[0] * .55, b[1] - d[1] * .55])} L${pt([b[0] + nn[0] * hh + d[0] * .25, b[1] + nn[1] * hh + d[1] * .25])} L${pt([b[0] + d[0] * .55, b[1] + d[1] * .55])} Z `;
    }
    const rayures = sage || o.variante === "royal" ? `<path d="M99.6 41 q-.6 4.4 -3.2 7.6 M95.8 40.8 q-.4 4.8 -2.6 8.4 M92 41.6 q-.2 3.6 -1.4 6.4" stroke="${teinte(c.fanon, -.3)}" stroke-width=".55" fill="none" opacity=".4" stroke-linecap="round"/>` : "";

    // œil, paupières, arcade
    const lid = teinte(c.dos, .05);
    const yeux = dort
      ? `<ellipse cx="101.4" cy="30.6" rx="3.3" ry="3" fill="${lid}"/>
         <path d="M98.2 30.6 Q101.4 32.8 104.6 30.6" fill="none" stroke="${dosF}" stroke-width=".85" stroke-linecap="round"/>
         <path d="M99.2 31.5 l-.3 .8 M101.4 32.1 v.8 M103.6 31.5 l.3 .8" stroke="${dosF}" stroke-width=".4" stroke-linecap="round"/>`
      : `<ellipse cx="101.4" cy="30.6" rx="3.5" ry="3.25" fill="${lid}"/>
         <circle cx="101.5" cy="30.6" r="3.05" fill="none" stroke="${c.clair}" stroke-width=".5" stroke-dasharray=".55 .45" opacity=".55"/>
         <circle cx="101.5" cy="30.6" r="2.42" fill="url(#${u}-i)"/>
         <circle cx="101.5" cy="30.6" r="2.42" fill="none" stroke="#4a2a0a" stroke-width=".3"/>
         <path d="M99.6 29.4 q1.9 -1.4 3.9 0" stroke="#fff3c0" stroke-width=".25" fill="none" opacity=".5"/>
         <circle cx="101.65" cy="30.6" r="1.02" fill="#0c0a07"/>
         <ellipse cx="102.35" cy="29.55" rx=".62" ry=".48" fill="#fff" opacity=".92"/><circle cx="100.6" cy="31.6" r=".25" fill="#fff" opacity=".5"/>
         ${h === "malade" || h === "froid" ? `<path d="M97.9 30.6 A3.5 3.25 0 0 1 104.9 30.6 Q101.4 31.9 97.9 30.6 Z" fill="${lid}"/><path d="M98.2 30.7 Q101.4 31.9 104.6 30.7" stroke="${dosF}" stroke-width=".45" fill="none"/>` : ""}
         <ellipse class="phb-paupiere" cx="101.4" cy="30.6" rx="3.6" ry="3.35" fill="${lid}"/>`;
    const arcade = h === "grognon" ? `<path d="M97.2 27.5 Q101.4 27.1 105.8 29.7 Q101.4 28.9 97.2 27.5 Z" fill="${dosF}" stroke="${dosF}" stroke-width=".5" stroke-linejoin="round"/>`
      : sage ? `<path d="M97.2 28.3 Q101.2 25.6 105.6 27.9 Q101.4 27 97.2 28.3 Z" fill="#ecebdc" stroke="#c9c8b2" stroke-width=".3"/>`
        : `<path d="M97.4 28.3 Q101.2 25.9 105.4 27.9 Q101.4 27.2 97.4 28.3 Z" fill="${teinte(c.clair, .12)}" opacity=".85"/>`;
    const fin = h === "joyeux" ? "Q96.6 37.3 96.1 36.4" : (h === "grognon" || h === "malade") ? "Q96.8 38.3 96.2 38.8" : "Q96.8 37.8 96.2 37.3";
    const bouche = `M115.6 35.6 C110.6 36.6 103.6 37.4 97.8 37.8 ${fin}`;

    const mue = o.mue ? `<g class="phb-mue" fill="#f5f1e2" fill-opacity=".86" stroke="#d6cfb6" stroke-width=".3" stroke-linejoin="round">
      <path d="M54 33.2 l2.2 -1.4 l1.6 .8 l1.4 -.6 l.8 2.4 l-1.6 1.6 l-2.6 -.2 l-1.4 -1 Z"/><path d="M70.4 40 l2.6 -1.2 l1.6 .6 l.6 2.2 l-2.2 1.4 l-2.4 -.6 Z"/>
      <path d="M28 43.2 l2.6 -1 l1.2 1 l-.4 1.8 l-2.6 .4 Z"/><path d="M80.6 34.2 l2 -.8 l1 .8 l-.2 1.8 l-2.2 .2 Z"/>
      <path d="M56.4 32.4 l1.2 -.8 M72.2 39 l1 -.6" stroke="#fff" stroke-width=".4" fill="none"/></g>` : "";
    const pansement = o.variante === "convalescent" ? `<g transform="rotate(-14 99 25.5)"><rect x="94.4" y="23.8" width="9.4" height="3.4" rx="1.2" fill="#efd3ac" stroke="#c09c70" stroke-width=".35"/>
      <rect x="97.4" y="24.2" width="3.4" height="2.6" rx=".4" fill="#f8ead4"/>
      <circle cx="95.6" cy="25.5" r=".3" fill="#c09c70"/><circle cx="102.6" cy="25.5" r=".3" fill="#c09c70"/></g>` : "";
    const rides = sage ? `<path d="M88 41.6 q3.2 1.6 6.6 .4 M86.8 39.8 q2.6 1.4 5.4 .8 M106 34.4 q1.6 .6 3.4 .2" stroke="${dosF}" stroke-width=".4" fill="none" opacity=".45" stroke-linecap="round"/>` : "";

    const loin = teinte(c.dos, .06), doigtLoin = teinte(c.dos, -.06), ongle = "#2e2a22";
    const PA = { trait: dosF, ongle };
    return `<svg class="phb-svg phb-${o.stade || "bebe"} phb-h-${h} phb-pose-${pose}" viewBox="0 0 128 64" role="img" aria-label="${o.label || "Philibert"}">
      ${defs(c, u, leger)}
      <ellipse class="phb-ombre" cx="60" cy="56.6" rx="${pose === "nage" ? 0 : 50}" ry="3.2" fill="url(#${u}-o)"/>
      <g transform="${echelle}"><g class="phb-corps-tout"><g class="phb-corps">
        ${queue(c, u, { stade: o.stade, variante: o.variante, queueEch, leger })}
        ${patte("phb-p-ar-loin", [46.8, 41.8], [51.6, 47], [48.2, 53.6], { ...PA, w: [4.8, 3, 2.1], fill: loin, doigt: doigtLoin, arriere: true, k: .9, a: J.arl, g: J.garl })}
        ${patte("phb-p-av-loin", [75.2, 41.6], [72.2, 46.8], [75.8, 53.4], { ...PA, w: [3.6, 2.6, 1.9], fill: loin, doigt: doigtLoin, k: .9, a: J.avl, g: J.gavl })}
        ${crete(c, o)}
        <path d="${corpsD}" fill="url(#${u}-p)"/>
        ${leger ? "" : `<path d="${corpsD}" fill="url(#${u}-e)"/>`}
        <path d="M55.6 31.4 C54.6 36 55 41.4 56.4 46 M64.4 31 C63.6 36 64 41.6 65.2 46.4 M73.2 31.2 C72.4 36 72.8 41 74 45.6" stroke="${c.bande}" stroke-width="2.6" fill="none" opacity="${opBandes}"/>
        <path d="${ecaillesVentre}" stroke="${teinte(c.ventre, -.3)}" stroke-width=".3" opacity=".45"/>
        <ellipse cx="64" cy="34.6" rx="22" ry="3.4" fill="url(#${u}-l)"/>
        <path d="M47.6 33.4 C57 31 71 30.9 84.6 31.3" stroke="#fff" stroke-opacity=".22" stroke-width="1.1" fill="none" stroke-linecap="round"/>
        <path d="M86.6 33.6 C85 36.8 84.6 40.4 85.4 43.6" stroke="${dosF}" stroke-width=".5" fill="none" opacity=".35"/>
        <path d="M41.6 37 C49 31.8 59 30.4 68 30.6 C76 30.8 82.4 29.6 88.6 30.6 M88.8 41.2 ${ventreB}" stroke="${dosF}" stroke-width=".5" stroke-opacity=".8" fill="none"/>
        ${mue}
        ${patte("phb-p-ar", [51, 43.4], [56.4, 48.6], [52.4, 54.8], { ...PA, w: [5.8, 3.4, 2.3], fill: `url(#${u}-m)`, doigt: teinte(c.membre, -.08), arriere: true, lum: true, tex: leger ? "" : `${u}-e`, a: J.ar, g: J.gar })}
        ${patte("phb-p-av", [80, 43], [76.6, 48.4], [80.6, 54.8], { ...PA, w: [4.4, 3, 2.1], fill: `url(#${u}-m)`, doigt: teinte(c.membre, -.08), lum: true, tex: leger ? "" : `${u}-e`, a: J.av, g: J.gav })}
        <g class="phb-tete"><g transform="${teteEch}">
          <g class="phb-fanon"><path d="${fanonPath}" fill="url(#${u}-f)"/>${rayures}
            <path d="M${pt(fanonD[0])} C${fanonD.slice(1, 4).map(pt).join(" ")} C${fanonD.slice(4, 7).map(pt).join(" ")}" stroke="${dosF}" stroke-width=".45" fill="none" stroke-opacity=".7"/>
            <path d="${epines}" fill="${teinte(c.fanon, .2)}" stroke="${dosF}" stroke-width=".25" stroke-linejoin="round"/></g>
          <path d="${teteD}" fill="url(#${u}-p)"/>
          ${leger ? "" : `<path d="${teteD}" fill="url(#${u}-e)" opacity=".7"/>`}
          <path d="M91 28.6 C96 26.6 103 26.6 109 28.6" stroke="#fff" stroke-opacity=".26" stroke-width=".9" fill="none" stroke-linecap="round"/>
          <path d="M91.6 28.8 L94.6 27.6 L97.8 27.2 M104.6 27.2 L107.8 28 L110.6 29.2 M95 27.6 l.4 1.4 M98.6 27.2 l-.2 1.2 M106.4 27.6 l-.2 1.1 M109 28.6 l-.3 1" stroke="${dosF}" stroke-width=".3" fill="none" opacity=".4"/>
          <circle cx="95.8" cy="27.6" r=".55" fill="#d3ddc8" opacity=".85"/>
          <ellipse cx="89.8" cy="31.6" rx="1.75" ry="2.3" fill="${teinte(c.dos, -.3)}" opacity=".5"/><path d="M88.6 30.4 q1 -1 2.2 -.2" stroke="#fff" stroke-width=".3" fill="none" opacity=".35"/>
          <g fill="${teinte(c.clair, .08)}" stroke="${dosF}" stroke-width=".18" stroke-opacity=".5">
            ${[[86.3, 33.4, .36], [87.7, 34.9, .3], [86.5, 36.5, .4], [88.1, 37.9, .28], [86.8, 39.4, .34], [88.4, 40.5, .26], [85.6, 35, .26]].map(([x, y, r]) => `<circle cx="${x}" cy="${y}" r="${r}"/>`).join("")}</g>
          <ellipse cx="91.6" cy="36.4" rx="3.2" ry="2.9" fill="url(#${u}-j)" stroke="${dosF}" stroke-width=".35" stroke-opacity=".7"/>
          <ellipse cx="90.7" cy="35.3" rx=".9" ry=".55" fill="#fff" opacity=".28"/>
          <path d="M87.4 39.8 Q91 42 95.6 40.6" stroke="${dosF}" stroke-width=".45" fill="none" opacity=".3"/>
          ${rides}
          <ellipse cx="113.4" cy="31.4" rx="1.35" ry="1.05" fill="${teinte(c.clair, .15)}" opacity=".6"/><ellipse cx="113.6" cy="31.45" rx=".68" ry=".5" fill="#18200f"/>
          <path d="M114.6 35 C110 35.9 103.6 36.6 98.4 37" stroke="#fff" stroke-opacity=".3" stroke-width=".85" stroke-dasharray="1.1 .45" fill="none"/>
          <path d="M114 36.9 C110 37.6 104 38.4 98.6 38.8" stroke="#fff" stroke-opacity=".2" stroke-width=".8" stroke-dasharray="1.1 .45" fill="none"/>
          <path d="${bouche}" fill="none" stroke="${dosF}" stroke-width=".8" stroke-linecap="round"/>
          <path d="${profil}" fill="none" stroke="${dosF}" stroke-width=".5" stroke-opacity=".8"/>
          ${yeux}${arcade}${pansement}${acc.yeux}${acc.tete}
        </g></g>
        <g transform="${teteEch}">${acc.cou}</g>
      </g></g></g></svg>`;
  }

  window.PhilibertDessin = { svg, couleurs, teinte, melange };
})();
