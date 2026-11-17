"use strict";
/* Éléments de nature de l'île de Philibert (SVG originaux, d'après des observations réelles), partagés par l'île
   (philibert-ile.js) et les mini-jeux (philibert-jeux.js) :
   - cocotier : stipe courbe, gris-brun, annelé par les cicatrices des palmes tombées (plus serrées en haut),
     base renflée et racines ; palmes pennées (une nervure, des dizaines de folioles étroites qui retombent en V),
     une vieille palme sèche qui pend, grappe de noix vertes et brunes ;
   - nuages cumulus : sommet bombé et éclairé, base plate et plus sombre ; plus petits et plus plats vers l'horizon ;
   - oiseaux : goéland (ailes grises au bout noir, en « M ») et frégate (longues ailes coudées, queue fourchue) ;
   - crabe fantôme (Ocypode) : carapace carrée couleur sable, yeux noirs au bout de longs pédoncules, pinces blanches
     inégales, pattes fines ; papillons (julia orange, soufré jaune) ;
   - rocher volcanique à facettes (lumière du côté du soleil), lichens ; noix de coco tombée ;
   - feuille, fleur d'hibiscus et scarabée pour la « pluie de feuilles ».
   Chaque fonction rend un fragment SVG (dans les coordonnées données) ou un <svg> complet ; « id » préfixe les
   identifiants de dégradés (un préfixe unique par endroit de la page). */
(() => {
  const r1 = n => Math.round(n * 10) / 10;
  const pt = p => `${r1(p[0])} ${r1(p[1])}`;
  const unit = d => { const L = Math.hypot(d[0], d[1]) || 1; return [d[0] / L, d[1] / L]; };
  const bz = (s, t) => { const u = 1 - t; return [0, 1].map(k => u * u * u * s[0][k] + 3 * u * u * t * s[1][k] + 3 * u * t * t * s[2][k] + t * t * t * s[3][k]); };
  const bzd = (s, t) => { const u = 1 - t; return [0, 1].map(k => 3 * u * u * (s[1][k] - s[0][k]) + 6 * u * t * (s[2][k] - s[1][k]) + 3 * t * t * (s[3][k] - s[2][k])); };
  const qz = (a, k, b, t) => { const u = 1 - t; return [u * u * a[0] + 2 * u * t * k[0] + t * t * b[0], u * u * a[1] + 2 * u * t * k[1] + t * t * b[1]]; };
  const qzd = (a, k, b, t) => [2 * (1 - t) * (k[0] - a[0]) + 2 * t * (b[0] - k[0]), 2 * (1 - t) * (k[1] - a[1]) + 2 * t * (b[1] - k[1])];
  function alea(graine) {
    let s = (graine >>> 0) || 1;
    return () => { s = (s + 0x6D2B79F5) >>> 0; let t = s; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
  }
  const svgDoc = (vb, corps, attrs = "") => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${vb}" ${attrs}>${corps}</svg>`;

  // ------------------------------------------------------------------ cocotier
  // stipe : base [x,y] → cime, deux points de contrôle ; w0 largeur au pied, w1 sous la couronne ; lum : +1 soleil à droite
  function stipe(o) {
    const s = [o.base, o.c1, o.c2, o.cime], n = 30, G = [], D = [];
    const larg = t => (o.w1 + (o.w0 - o.w1) * Math.pow(1 - t, 1.7) + (t < .07 ? o.w0 * .55 * Math.pow(1 - t / .07, 2) : 0)) / 2;
    const cote = (t, k) => { const c = bz(s, t), d = unit(bzd(s, t)), w = larg(t) * k; return [c[0] + d[1] * w, c[1] - d[0] * w]; };
    for (let i = 0; i <= n; i++) { const t = i / n; G.push(cote(t, 1)); D.push(cote(t, -1)); }
    const contour = `M${G.map(pt).join(" L")} L${D.slice().reverse().map(pt).join(" L")} Z`;
    let anneaux = "", reflets = "";
    const N = o.anneaux || 30;
    for (let k = 1; k < N; k++) {
      const t = .05 + .93 * Math.pow(k / N, .82), c = bz(s, t), d = unit(bzd(s, t));
      const a = cote(t, 1), b = cote(t, -1), bas = [c[0] - d[0] * 2.2, c[1] - d[1] * 2.2];
      anneaux += `M${pt(a)} Q${pt(bas)} ${pt(b)} `;
      const a2 = cote(t - .012, .9), b2 = cote(t - .012, -.9), bas2 = [c[0] - d[0] * 3.6, c[1] - d[1] * 3.6];
      reflets += `M${pt(a2)} Q${pt(bas2)} ${pt(b2)} `;
    }
    let fibres = "";
    for (const k of [-.55, -.2, .25, .6]) { const P = []; for (let i = 2; i <= n - 1; i += 2) P.push(cote(i / n, k)); fibres += `M${P.map(pt).join(" L")} `; }
    const L = o.lum > 0;
    const id = o.id;
    const racines = [[-1, 18, 6], [-.6, 12, 8], [.5, 14, 7], [1, 20, 5], [0, 4, 9]].map(([dx, l, y]) =>
      `M${r1(o.base[0] + dx * o.w0 * .3)} ${r1(o.base[1] - 2)} q${r1(dx * l * .5)} ${r1(y * .4)} ${r1(dx * l)} ${y}`).join(" ");
    return `<defs><linearGradient id="${id}-st" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stop-color="${L ? o.coul[0] : o.coul[2]}"/><stop offset=".32" stop-color="${L ? o.coul[1] : o.coul[2]}"/>
        <stop offset=".62" stop-color="${L ? o.coul[2] : o.coul[1]}"/><stop offset="1" stop-color="${L ? o.coul[1] : o.coul[0]}"/></linearGradient></defs>
      <path d="${racines}" stroke="${o.coul[0]}" stroke-width="4" stroke-linecap="round" fill="none" opacity=".85"/>
      <path d="${contour}" fill="url(#${id}-st)"/>
      <path d="${fibres}" stroke="${o.coul[0]}" stroke-width=".8" fill="none" opacity=".25"/>
      <path d="${reflets}" stroke="${o.clair}" stroke-width="1.1" fill="none" opacity=".28"/>
      <path d="${anneaux}" stroke="${o.coul[0]}" stroke-width="1.5" fill="none" opacity=".55" stroke-linecap="round"/>`;
  }
  // palme : depuis la cime C, angle (degrés, 0 = droite, -90 = haut), longueur, retombée ; couleurs [claire, foncée, nervure]
  function palme(C, ang, L, droop, coul, o = {}) {
    const a = ang * Math.PI / 180, dir = [Math.cos(a), Math.sin(a)];
    const T = [C[0] + dir[0] * L, C[1] + dir[1] * L + L * droop];
    const K = [C[0] + dir[0] * L * .55, C[1] + dir[1] * L * .55 - L * .1];
    const n = o.n || 24, rnd = alea(o.graine || Math.round(ang * 7 + L));
    let dA = "", dB = "";
    for (let i = 2; i <= n; i++) {
      const s = i / n, p = qz(C, K, T, s), d = unit(qzd(C, K, T, s));
      for (const side of [-1, 1]) {
        if (o.sec && rnd() < .3) continue;
        const nrm = [-d[1] * side, d[0] * side];
        const dl = unit([nrm[0] * .78 + d[0] * .5, nrm[1] * .78 + d[1] * .5 + (o.sec ? 1.1 : .7)]);
        const len = L * (o.court || .3) * Math.pow(Math.sin(Math.PI * (s * .86 + .1)), .7) * (1 - s * .2) * (.85 + rnd() * .3);
        const tip = [p[0] + dl[0] * len, p[1] + dl[1] * len + len * .1];
        const mid = [p[0] + dl[0] * len * .5, p[1] + dl[1] * len * .5 + len * .1];
        const pp = [-dl[1], dl[0]], w = 1.2 + len * .055;
        const seg = `M${pt(p)} Q${pt([mid[0] + pp[0] * w, mid[1] + pp[1] * w])} ${pt(tip)} Q${pt([mid[0] - pp[0] * w * .6, mid[1] - pp[1] * w * .6])} ${pt(p)} Z `;
        if ((side < 0) === (dir[0] >= 0)) dA += seg; else dB += seg;
      }
    }
    return `<path d="${dB}" fill="${coul[1]}"/><path d="${dA}" fill="${coul[0]}"/>
      <path d="M${pt(C)} Q${pt(K)} ${pt(T)}" stroke="${coul[2]}" stroke-width="${o.epais || 2.2}" fill="none" stroke-linecap="round"/>`;
  }
  // couronne complète : palmes du fond (sombres), palme sèche, noix, palmes de devant
  function couronne(C, P, id) {
    const f = P.palmes, k = P.echelle || 1;
    const fond = [[-100, 92, .28], [-58, 108, .36], [-132, 104, .36], [-18, 118, .55], [-166, 116, .55]];
    const devant = [[-78, 100, .3], [-38, 124, .55], [-146, 122, .55], [6, 128, .62], [-188, 122, .7], [-8, 104, .95], [-172, 98, .95]];
    const coul = (x, ombre) => ombre ? [f[1], f[3], f[4]] : [f[0], f[1], f[2]];
    const g = (L, sc) => L.map(([a, l, d], i) => palme(C, a, l * k, d, coul(0, sc), { graine: i * 31 + (sc ? 7 : 3) })).join("");
    const seche = palme([C[0] + 2, C[1] + 6], 104, 70 * k, .05, [P.sec[0], P.sec[1], P.sec[1]], { sec: true, court: .22, n: 16, graine: 5 });
    const noix = [[-8, 10, 9, 1], [8, 12, 9, 0], [0, 17, 8.4, 1], [-15, 16, 7.8, 0], [14, 5, 7.6, 1]].map(([dx, dy, r, brun], i) =>
      `<circle cx="${C[0] + dx}" cy="${C[1] + dy}" r="${r}" fill="url(#${id}-${brun ? "nb" : "nv"})"/>${i % 2 ? "" : `<ellipse cx="${C[0] + dx - r * .3}" cy="${C[1] + dy - r * .35}" rx="${r * .32}" ry="${r * .22}" fill="#fff" opacity=".22"/>`}`).join("");
    return `<defs><radialGradient id="${id}-nb" cx=".38" cy=".32" r=".7"><stop offset="0" stop-color="${P.noix[0]}"/><stop offset="1" stop-color="${P.noix[1]}"/></radialGradient>
        <radialGradient id="${id}-nv" cx=".38" cy=".32" r=".7"><stop offset="0" stop-color="${P.noix[2]}"/><stop offset="1" stop-color="${P.noix[3]}"/></radialGradient></defs>
      ${g(fond, true)}${seche}
      <path d="M${C[0] - 9} ${C[1] + 4} q9 -9 18 0 q-2 7 -9 9 q-7 -2 -9 -9 Z" fill="${P.sec[1]}"/>
      ${noix}${g(devant, false)}`;
  }
  // petit cocotier lointain (île voisine, mini-jeux) : peu de folioles
  function cocotierLoin(x, y, h, coul, penche = -.12) {
    const cime = [x + h * penche * 2, y - h];
    return `<path d="M${x} ${y} Q${x + h * penche * .4} ${y - h * .5} ${pt(cime)}" stroke="${coul[1]}" stroke-width="${r1(h * .055 + .6)}" fill="none" stroke-linecap="round"/>
      ${[[-150, .5, .45], [-110, .45, .35], [-60, .45, .35], [-25, .5, .45], [-85, .38, .3]].map(([a, l, d]) => palme(cime, a, h * l, d, [coul[0], coul[0], coul[0]], { n: 9, court: .28, epais: 1 })).join("")}`;
  }

  // ------------------------------------------------------------------ nuages (svg complet, viewBox 240 × 100)
  function nuage(id, graine, c) {
    // un cumulus = un massif de « choux-fleurs » : grosses bulles au centre, petites bulles qui débordent en haut,
    // chacune ombrée (dessus éclairé, dessous gris), le tout posé sur une base plate et adouci par un léger flou
    const r = alea(graine), puffs = [];
    const n = 9 + Math.floor(r() * 4), base = 84;
    for (let i = 0; i < n; i++) {
      const t = i / (n - 1), x = 24 + t * 192 + (r() - .5) * 16;
      const rad = (12 + 24 * Math.pow(Math.sin(Math.PI * (t * .9 + .05)), 1.4) + r() * 9) * (c.plat ? .72 : 1);
      puffs.push([Math.min(232 - rad, Math.max(rad + 8, x)), base - rad * (.5 + r() * .3), rad, 0]);   // (dans le cadre : pas de bord coupé net)
    }
    for (let i = 0; i < 7; i++) {                      // petites bulles du sommet (texture « chou-fleur »)
      const p = puffs[2 + Math.floor(r() * (n - 4))];
      const a = -Math.PI / 2 + (r() - .5) * 1.8, rr = p[2] * (.32 + r() * .22);
      puffs.push([Math.min(232 - rr, Math.max(rr + 8, p[0] + Math.cos(a) * p[2] * .78)), Math.max(rr + 6, p[1] + Math.sin(a) * p[2] * .78), rr, 1]);
    }
    puffs.sort((a, b) => a[3] - b[3] || b[2] - a[2]);
    const forme = puffs.map(([x, y, rr]) => `M${r1(x - rr)} ${r1(y)} a${r1(rr)} ${r1(rr)} 0 1 0 ${r1(2 * rr)} 0 a${r1(rr)} ${r1(rr)} 0 1 0 ${r1(-2 * rr)} 0 Z`).join(" ");
    return `<svg viewBox="0 0 240 100" aria-hidden="true"><defs>
        <clipPath id="${id}-p"><path d="${forme}"/></clipPath>
        <linearGradient id="${id}-g" gradientUnits="userSpaceOnUse" x1="0" y1="8" x2="0" y2="${base}"><stop offset="0" stop-color="${c.haut}"/><stop offset=".55" stop-color="${c.milieu}"/><stop offset="1" stop-color="${c.bas}"/></linearGradient>
        <radialGradient id="${id}-h" cx=".42" cy=".3" r=".55"><stop offset="0" stop-color="${c.haut}" stop-opacity=".9"/><stop offset="1" stop-color="${c.haut}" stop-opacity="0"/></radialGradient>
        <linearGradient id="${id}-b" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${c.bas}" stop-opacity="0"/><stop offset="1" stop-color="${c.bas}" stop-opacity=".85"/></linearGradient>
        <clipPath id="${id}-c"><rect x="0" y="0" width="240" height="${base + 2}"/></clipPath>
        <filter id="${id}-f" x="-10%" y="-10%" width="120%" height="120%"><feGaussianBlur stdDeviation="${c.flou || 1.4}"/></filter></defs>
      <g filter="url(#${id}-f)" clip-path="url(#${id}-c)">
        <path d="${forme}" fill="url(#${id}-g)"/>
        ${puffs.filter(q => q[1] < base - 18).map(([x, y, rr]) => `<circle cx="${r1(x - rr * .15)}" cy="${r1(y - rr * .25)}" r="${r1(rr * .7)}" fill="url(#${id}-h)" opacity=".55"/>`).join("")}
        <rect x="0" y="${base - 22}" width="240" height="24" fill="url(#${id}-b)" clip-path="url(#${id}-p)"/></g></svg>`;
  }

  // ------------------------------------------------------------------ oiseaux (svg complets)
  // goéland vu de côté, en vol : tête blanche ronde, bec jaune à tache rouge, œil noir ; ailes en deux parties (bras et
  // main) pour que l'aile se plie au poignet quand elle bat ; bouts d'ailes noirs à petits « miroirs » blancs.
  // Animations CSS (philibert.css) : .g-aile-p (aile proche), .g-aile-l (aile lointaine), .g-main (pliage), .g-corps.
  const goeland = (id = "go") => `<svg viewBox="0 0 64 40" aria-hidden="true"><defs>
      <linearGradient id="${id}-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d4dbe2"/><stop offset="1" stop-color="#a7b2bd"/></linearGradient>
      <radialGradient id="${id}-c" cx=".4" cy=".35" r=".7"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#d6dde3"/></radialGradient></defs>
    <g class="g-aile-l"><path d="M30 20 C26 14 22 9 18 7 L22 18 Z" fill="#98a4b0"/>
      <g class="g-main"><path d="M18 7 C14 5 9 5 5 7 C10 9 15 12 22 18 Z" fill="#8e9aa6"/><path d="M5 7 C8 6.4 11 6.6 13 7.4 L11 9.2 C9 8.4 7 7.8 5 7 Z" fill="#26292d"/></g></g>
    <g class="g-corps"><path d="M18 22 C22 17.6 34 17 42 19.4 C46 20.6 47.6 22 46.4 23.4 C40 26 26 26.4 18 24 L10 25.6 L13.4 22.2 Z" fill="url(#${id}-c)"/>
      <path d="M10 25.6 L13.4 22.2 L18 22.6 L16 25 Z" fill="#2c3034"/>
      <path d="M20 24 C27 25.6 38 25.2 45 23" stroke="#c4ccd3" stroke-width=".8" fill="none"/>
      <circle cx="45.4" cy="19.6" r="4.2" fill="url(#${id}-c)"/><circle cx="46.8" cy="18.8" r=".9" fill="#1a1c1e"/><circle cx="47.1" cy="18.5" r=".3" fill="#fff"/>
      <path d="M49.2 19.6 L55.6 20.4 L49.4 21.8 Z" fill="#f2c12e"/><circle cx="53.4" cy="20.9" r=".55" fill="#d8402a"/>
      <path d="M30 24.6 l-1.4 3 M33 24.8 l-.8 3" stroke="#e8a08a" stroke-width=".9" stroke-linecap="round"/></g>
    <g class="g-aile-p"><path d="M28 21 C25 14 22 8 17 4.4 L22 19.6 Z" fill="url(#${id}-a)" stroke="#8994a0" stroke-width=".4"/>
      <g class="g-main"><path d="M17 4.4 C12 2.2 6 2 1 4.4 C7 6.4 14 11 22 19.6 Z" fill="url(#${id}-a)" stroke="#8994a0" stroke-width=".4"/>
        <path d="M1 4.4 C4.4 3.2 8.4 3 11.6 3.8 L9.6 6.8 C6.6 5.6 4 4.8 1 4.4 Z" fill="#202326"/>
        <circle cx="4.6" cy="4.4" r=".55" fill="#fff"/><circle cx="7.6" cy="4.6" r=".5" fill="#fff"/></g>
      <path d="M20 19 C22 15 24 12 26 9" stroke="#fff" stroke-width=".7" fill="none" opacity=".5"/></g></svg>`;
  const fregate = () => `<svg viewBox="0 0 70 26" aria-hidden="true"><path d="M35 12 C30 9 25 9.6 20 11.6 C14 13.8 8 13.4 1 10.4 C7 15 14 16.4 21 15 C26 14 31 13.6 35 14 C39 13.6 44 14 49 15 C56 16.4 63 15 69 10.4 C62 13.4 56 13.8 50 11.6 C45 9.6 40 9 35 12 Z" fill="#20242a"/>
      <path d="M35 13 l-1.6 9 l1.6 -3.2 l1.6 3.2 Z" fill="#20242a"/><path d="M35 11.4 l3.4 -.2 l2.2 .6" stroke="#20242a" stroke-width="1.2" fill="none"/></svg>`;

  // ------------------------------------------------------------------ crabe fantôme (svg complet, viewBox 48 × 30)
  // crabe fantôme mignon et réaliste : carapace carrée couleur sable, gros yeux noirs au bout de pédoncules,
  // une grosse pince blanche et une petite, pattes fines à articulations. Animations CSS (philibert.css) :
  // .c-pattes-a / .c-pattes-b (paires qui trottinent en alternance), .c-pince (il l'agite de temps en temps),
  // .c-yeux (les pédoncules se redressent), .c-corps (petit rebond).
  function crabe(id) {
    const patte = (x, y, a, b) => `M${x} ${y} L${a[0]} ${a[1]} L${b[0]} ${b[1]}`;
    const A = [patte(15, 17, [8, 12.6], [3.2, 24.6]), patte(16, 19.6, [9.6, 20.4], [7.6, 28]), patte(33, 18, [41, 16.6], [44, 27.4]), patte(31.6, 20.4, [36, 23.4], [36.4, 28.6])].join(" ");
    const B = [patte(15, 18.4, [7, 16.6], [4.2, 27.4]), patte(17.6, 20.4, [13, 23.4], [12.4, 28.6]), patte(33, 16, [40, 12.6], [44.8, 24.6]), patte(32, 19.6, [38.4, 20.4], [40.4, 28])].join(" ");
    const pattes = (d, cls) => `<g class="${cls}" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="${d}" stroke="#b59f7a" stroke-width="1.8"/><path d="${d}" stroke="#ece0c6" stroke-width=".6" opacity=".7"/></g>`;
    return `<svg viewBox="0 0 48 32" aria-hidden="true"><defs>
        <radialGradient id="${id}-c" cx=".42" cy=".3" r=".8"><stop offset="0" stop-color="#f6ecd4"/><stop offset=".6" stop-color="#dfcba2"/><stop offset="1" stop-color="#b9a37a"/></radialGradient>
        <radialGradient id="${id}-o"><stop offset="0" stop-color="#3b2a12" stop-opacity=".35"/><stop offset="1" stop-color="#3b2a12" stop-opacity="0"/></radialGradient>
        <radialGradient id="${id}-p" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#e2d8c4"/></radialGradient></defs>
      <ellipse cx="24" cy="29.4" rx="19" ry="2.4" fill="url(#${id}-o)"/>
      ${pattes(A, "c-pattes-a")}${pattes(B, "c-pattes-b")}
      <g class="c-corps">
        <g class="c-yeux"><path d="M20.4 9.4 L19.2 3.6 M27.6 9.4 L28.8 3.6" stroke="#cbb68e" stroke-width="1.6" stroke-linecap="round"/>
          <ellipse cx="19" cy="3.4" rx="1.6" ry="2.5" fill="#1c1914"/><ellipse cx="29" cy="3.4" rx="1.6" ry="2.5" fill="#1c1914"/>
          <circle cx="18.5" cy="2.5" r=".6" fill="#fff"/><circle cx="28.5" cy="2.5" r=".6" fill="#fff"/></g>
        <path d="M13.4 15.4 C13.2 10.4 18 8 24 8 C30 8 34.8 10.4 34.6 15.4 C34.4 19.6 30 21.6 24 21.6 C18 21.6 13.6 19.6 13.4 15.4 Z" fill="url(#${id}-c)" stroke="#a99068" stroke-width=".5"/>
        <path d="M18 11.8 q6 -2.2 12 0" stroke="#b39d77" stroke-width=".5" fill="none" opacity=".7"/><ellipse cx="21" cy="11.4" rx="4" ry="1.6" fill="#fff" opacity=".35"/>
        <path d="M21.4 17 q2.6 1.6 5.2 0" stroke="#8a7656" stroke-width=".6" fill="none" stroke-linecap="round"/>
        <path d="M14.4 14 C12 13 9.6 13.2 8.6 14.6 C7.8 16 9 17.4 11 17.2 C12.4 17 13.6 16.4 14.6 16 Z" fill="url(#${id}-p)" stroke="#b9a37a" stroke-width=".5"/>
        <g class="c-pince"><path d="M33.6 13.6 C37 11.8 40 11.2 42.4 12.6 C44.6 14 44.4 16.8 42 17.4 C39.6 18 36.4 16.6 33.8 16.2 Z" fill="url(#${id}-p)" stroke="#b9a37a" stroke-width=".5"/>
          <path d="M42.2 12.6 l3.4 -2 M42.6 17.2 l3 .6" stroke="#efe7d6" stroke-width="1.5" stroke-linecap="round"/><path d="M42.2 12.6 l3.4 -2 M42.6 17.2 l3 .6" stroke="#b9a37a" stroke-width=".4" stroke-linecap="round"/></g>
      </g></svg>`;
  }
  // papillons : julia (orange) ou soufré (jaune) ; ailes dans .phb-ailes (battement CSS)
  function papillon(jaune) {
    const [a, b, bord] = jaune ? ["#f7d84a", "#f0c02a", "#c99512"] : ["#f2802a", "#e7641c", "#5a2a10"];
    return `<svg viewBox="0 0 30 22" aria-hidden="true"><g class="phb-ailes">
      <path d="M15 10 C12 3 6 .6 2.4 2.4 C.8 4.6 3.6 9 8 10.6 C10.6 11.4 13 11 15 10 Z M15 10 C18 3 24 .6 27.6 2.4 C29.2 4.6 26.4 9 22 10.6 C19.4 11.4 17 11 15 10 Z" fill="${a}" stroke="${bord}" stroke-width=".7"/>
      <path d="M15 11 C12 13 8.6 16.6 9 19 C10.8 20.4 13.6 17 15 12.6 Z M15 11 C18 13 21.4 16.6 21 19 C19.2 20.4 16.4 17 15 12.6 Z" fill="${b}" stroke="${bord}" stroke-width=".6"/>
      ${jaune ? `<circle cx="9" cy="5.6" r=".9" fill="#c99512"/><circle cx="21" cy="5.6" r=".9" fill="#c99512"/>` : `<path d="M4 3.6 C6 6 9 6.4 11 6 M26 3.6 C24 6 21 6.4 19 6" stroke="#5a2a10" stroke-width="1" fill="none"/>`}</g>
      <path d="M15 4.6 V17" stroke="#2c2116" stroke-width="1.3" stroke-linecap="round"/><path d="M14.6 4.8 l-2 -3.6 M15.4 4.8 l2 -3.6" stroke="#2c2116" stroke-width=".45"/></svg>`;
  }

  // ------------------------------------------------------------------ rocher (fragment) : x,y = coin bas gauche, l × h ; lum : +1 soleil à droite
  function rocher(id, x, y, l, h, o = {}) {
    const P = (u, v) => pt([x + u * l, y - v * h]);
    const C = o.coul || ["#c7bcb0", "#9a8d80", "#6e635a", "#4d443d"];
    const L = (o.lum || 1) > 0;
    const facette = (pts, f, op) => `<path d="M${pts.map(([u, v]) => P(u, v)).join(" L")} Z" fill="${f}" opacity="${op}"/>`;
    return `<defs><linearGradient id="${id}-r" x1="${L ? 1 : 0}" y1="0" x2="${L ? 0 : 1}" y2="1">
        <stop offset="0" stop-color="${C[0]}"/><stop offset=".45" stop-color="${C[1]}"/><stop offset="1" stop-color="${C[2]}"/></linearGradient>
        <pattern id="${id}-t" width="14" height="12" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r="1" fill="#000" opacity=".12"/><circle cx="10" cy="8" r=".8" fill="#000" opacity=".1"/>
          <circle cx="8" cy="2" r=".7" fill="#fff" opacity=".1"/><circle cx="2" cy="9" r=".6" fill="#fff" opacity=".12"/></pattern></defs>
      <path d="M${P(0, 0)} C${P(-.03, .3)} ${P(.05, .62)} ${P(.16, .8)} C${P(.3, .98)} ${P(.52, 1.02)} ${P(.68, .95)} C${P(.86, .86)} ${P(1, .6)} ${P(1.03, .3)} C${P(1.05, .14)} ${P(1.02, .05)} ${P(1, 0)} Z" fill="url(#${id}-r)"/>
      ${facette([[.14, .78], [.34, .96], [.6, .98], [.56, .7], [.3, .6]], L ? C[0] : C[1], .55)}
      ${facette([[.56, .7], [.6, .98], [.82, .88], [.97, .55], [.74, .48]], L ? "#fff" : C[3], L ? .12 : .25)}
      ${facette([[.74, .48], [.97, .55], [1.02, .2], [1, 0], [.7, 0], [.68, .26]], C[3], L ? .2 : .1)}
      ${facette([[0, 0], [-.02, .3], [.06, .58], [.3, .6], [.28, .3], [.24, 0]], C[3], L ? .12 : .02)}
      <path d="M${P(0, 0)} C${P(-.03, .3)} ${P(.05, .62)} ${P(.16, .8)} C${P(.3, .98)} ${P(.52, 1.02)} ${P(.68, .95)} C${P(.86, .86)} ${P(1, .6)} ${P(1.03, .3)} C${P(1.05, .14)} ${P(1.02, .05)} ${P(1, 0)} Z" fill="url(#${id}-t)"/>
      <path d="M${P(.42, .98)} L${P(.46, .74)} L${P(.4, .56)} M${P(.46, .74)} L${P(.56, .66)} M${P(.8, .5)} L${P(.84, .3)} L${P(.8, .1)}" stroke="${C[3]}" stroke-width="1.2" fill="none" opacity=".6" stroke-linecap="round"/>
      ${o.lichen === false ? "" : `<g fill="#c8c98a" opacity=".55"><ellipse cx="${r1(x + .3 * l)}" cy="${r1(y - .82 * h)}" rx="${r1(l * .05)}" ry="${r1(h * .05)}"/><ellipse cx="${r1(x + .38 * l)}" cy="${r1(y - .88 * h)}" rx="${r1(l * .03)}" ry="${r1(h * .035)}"/><ellipse cx="${r1(x + .1 * l)}" cy="${r1(y - .4 * h)}" rx="${r1(l * .035)}" ry="${r1(h * .04)}"/></g>`}`;
  }
  // noix de coco tombée (fragment, centre x,y, rayon r) : bourre fibreuse brune
  function coco(id, x, y, r) {
    return `<defs><radialGradient id="${id}-k" cx=".36" cy=".3" r=".75"><stop offset="0" stop-color="#a77c4a"/><stop offset=".6" stop-color="#7a5430"/><stop offset="1" stop-color="#4c321b"/></radialGradient></defs>
      <ellipse cx="${x}" cy="${r1(y + r * .92)}" rx="${r1(r * 1.1)}" ry="${r1(r * .22)}" fill="#3b2a12" opacity=".25"/>
      <path d="M${r1(x - r)} ${y} C${r1(x - r)} ${r1(y - r * 1.2)} ${r1(x + r)} ${r1(y - r * 1.2)} ${r1(x + r)} ${y} C${r1(x + r)} ${r1(y + r * .9)} ${r1(x - r)} ${r1(y + r * .9)} ${r1(x - r)} ${y} Z" fill="url(#${id}-k)"/>
      <path d="M${r1(x - r * .6)} ${r1(y - r * .5)} q${r1(r * .3)} ${r1(r * .9)} ${r1(r * .1)} ${r1(r * 1.2)} M${r1(x)} ${r1(y - r * .85)} q${r1(r * .2)} ${r1(r * .9)} 0 ${r1(r * 1.6)} M${r1(x + r * .55)} ${r1(y - r * .55)} q${r1(-r * .2)} ${r1(r * .8)} ${r1(r * .05)} ${r1(r * 1.2)}" stroke="#3e2915" stroke-width="${r1(r * .08 + .3)}" fill="none" opacity=".45"/>
      <ellipse cx="${r1(x - r * .35)}" cy="${r1(y - r * .45)}" rx="${r1(r * .28)}" ry="${r1(r * .16)}" fill="#e6c79a" opacity=".3"/>`;
  }

  // ------------------------------------------------------------------ pluie de feuilles (svg complets, viewBox 40 × 40)
  const feuilleTombee = (vert = 0) => {
    const [a, b, n] = [["#6cae45", "#3f7d2c", "#c9e09a"], ["#8dbb4a", "#56862c", "#e0eba8"], ["#4f9a3e", "#2f6a28", "#b7d89a"]][vert % 3];
    return `<svg viewBox="0 0 40 40"><defs><linearGradient id="ft${vert}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="${a}"/><stop offset="1" stop-color="${b}"/></linearGradient></defs>
      <path d="M6 34 C4 20 12 7 34 5 C34 22 24 34 6 34 Z" fill="url(#ft${vert})" stroke="${b}" stroke-width=".8"/>
      <path d="M6 34 C14 26 22 17 31 8 M12 28 l-1 -6 M16 24 l-.4 -7 M21 19 l.4 -7 M26 14 l.8 -5 M12 28 l6 .4 M16 24 l7 .2 M21 19 l7 0 M26 14 l5 -.4" stroke="${n}" stroke-width=".9" fill="none" opacity=".75" stroke-linecap="round"/>
      <path d="M6 34 l-3 3" stroke="${b}" stroke-width="1.6" stroke-linecap="round"/></svg>`;
  };
  const hibiscus = () => `<svg viewBox="0 0 40 40"><defs><radialGradient id="hbs" cx=".5" cy=".5" r=".55"><stop offset="0" stop-color="#7d0f2a"/><stop offset=".25" stop-color="#c8243f"/><stop offset=".8" stop-color="#ee4a5c"/><stop offset="1" stop-color="#ff8a8a"/></radialGradient></defs>
      ${[0, 72, 144, 216, 288].map(a => `<path d="M20 20 C12 17 10 6 16 3.4 C19 2.2 21 2.2 24 3.4 C30 6 28 17 20 20 Z" transform="rotate(${a} 20 20)" fill="url(#hbs)" stroke="#a3162f" stroke-width=".6"/>
        <path d="M20 19 C19 13 19 8 20 5" transform="rotate(${a} 20 20)" stroke="#8d1028" stroke-width=".5" fill="none" opacity=".5"/>`).join("")}
      <path d="M20 20 L30 9" stroke="#f3c94a" stroke-width="1.4" stroke-linecap="round"/>${[[30, 9], [28.6, 8], [31, 10.6], [29.6, 11]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1" fill="#ffd54a"/>`).join("")}
      <circle cx="31.4" cy="8.4" r="1.2" fill="#e8483f"/></svg>`;
  const scarabee = () => `<svg viewBox="0 0 40 40"><defs><linearGradient id="scb" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#2c3d1c"/><stop offset=".45" stop-color="#5a6e2c"/><stop offset="1" stop-color="#1f2a14"/></linearGradient></defs>
      <g stroke="#1e1a12" stroke-width="1.3" fill="none" stroke-linecap="round"><path d="M14 16 l-6 -4 l-2 -5 M13 21 l-7 0 l-3 3 M14 26 l-5 5 l0 4 M26 16 l6 -4 l2 -5 M27 21 l7 0 l3 3 M26 26 l5 5 l0 4"/><path d="M17 9 q-3 -4 -6 -4 M23 9 q3 -4 6 -4" stroke-width=".9"/></g>
      <ellipse cx="20" cy="11" rx="4.6" ry="3.4" fill="#26301a"/><path d="M12 16 C12 13 28 13 28 16 L28 27 C28 34 12 34 12 27 Z" fill="url(#scb)"/>
      <path d="M20 14.6 V33" stroke="#151c0e" stroke-width=".9"/><ellipse cx="16" cy="19" rx="1.6" ry="4" fill="#fff" opacity=".2"/></svg>`;

  window.PhilibertNature = { alea, stipe, palme, couronne, cocotierLoin, nuage, goeland, fregate, crabe, papillon, rocher, coco, feuilleTombee, hibiscus, scarabee, svgDoc, bz, qz };
})();
