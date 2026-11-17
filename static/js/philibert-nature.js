"use strict";
/* Éléments de nature de l'île de Philibert (SVG originaux, d'après des observations réelles), partagés par l'île
   (philibert-ile.js) et les mini-jeux (philibert-jeux.js) :
   - cocotier : stipe courbe, gris-brun, annelé par les cicatrices des palmes tombées (plus serrées en haut),
     base renflée et racines ; palmes pennées (une nervure, des dizaines de folioles étroites qui retombent en V),
     une vieille palme sèche qui pend, grappe de noix vertes et brunes ;
   - nuages cumulus : sommet bombé et éclairé, base plate et plus sombre ; plus petits et plus plats vers l'horizon ;
   - oiseaux : goéland argenté en vol (bras et main de l'aile articulés pour un vrai battement) et posé (il marche),
     frégate (longues ailes coudées, queue fourchue) ;
   - crabes de plage : crabe fantôme (Ocypode) couleur sable aux grands yeux sur pédoncules, et crabe violoniste (Uca)
     à l'énorme pince orange ; papillons (julia orange, soufré jaune) ;
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
  // ------------------------------------------------------------------ goéland (d'après des photos de goélands argentés)
  // Adulte : tête blanche, bec jaune épais à tache rouge (gonys), œil jaune pâle cerclé d'orange, manteau gris perle,
  // bouts d'ailes noirs avec « miroirs » blancs, bord de fuite blanc, queue blanche carrée, pattes roses.
  // En vol (viewBox 80 × 44, il va vers la droite) : chaque aile a deux parties, le bras (.g-bras, articulé à l'épaule)
  // et la main (.g-main, articulée au poignet) : en remontant, la main se replie au poignet ; en descendant, l'aile
  // s'étend en entier (battement réel). .g-pattes-vol : pattes sorties pour se poser. Animations : philibert.css.
  const goeland = (id = "go") => `<svg viewBox="0 0 80 44" aria-hidden="true"><defs>
      <linearGradient id="${id}-a" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#cfd7de"/><stop offset="1" stop-color="#97a3af"/></linearGradient>
      <linearGradient id="${id}-l" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a3aeb9"/><stop offset="1" stop-color="#7d8995"/></linearGradient>
      <linearGradient id="${id}-c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".7" stop-color="#f1f4f6"/><stop offset="1" stop-color="#cfd7de"/></linearGradient>
      <linearGradient id="${id}-b" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f0c437"/><stop offset="1" stop-color="#e3ad1f"/></linearGradient></defs>
    <g class="g-tout">
    <g class="g-aile g-loin" style="transform-origin:40px 21px"><path d="M41 21.4 C38.6 17 36 13.4 34 11 L31.4 13.6 C33.6 16.6 35.6 19.4 37.4 22.6 Z" fill="url(#${id}-l)"/>
      <g class="g-main" style="transform-origin:34px 11px"><path d="M34 11 C29 8.6 22 7 15.6 7.2 C20 9 25.6 11.6 31.4 13.6 Z" fill="url(#${id}-l)"/>
        <path d="M15.6 7.2 C19.6 6.9 22.8 7.4 25 8.2 L23.2 10.2 C20.6 8.9 18 7.9 15.6 7.2 Z" fill="#1e2125"/></g></g>
    <path d="M17 23 L9.4 22.4 C8.8 23.8 8.8 25.4 9.6 26.8 L17 26.4 Z" fill="#f4f6f8" stroke="#c9d1d8" stroke-width=".4"/>
    <g class="g-pattes-vol" style="opacity:0"><path d="M30 27.6 L28.4 35.6 M33.4 27.8 L33 35.8" stroke="#e9978f" stroke-width="1.3" stroke-linecap="round"/>
      <path d="M28.4 35.6 l-2.4 1.4 h4.6 Z M33 35.8 l-2.2 1.4 h4.6 Z" fill="#e9978f"/></g>
    <path d="M15 23.2 C22 19.8 37 18.6 47.6 19.8 C53 20.6 55.6 22.8 55.2 25.4 C54.6 28.6 47 30.8 37 30.8 C27 30.8 19 28.4 15 26.4 Z" fill="url(#${id}-c)"/>
    <path d="M18 22.6 C26 20.6 38 20 46 21 C40 22.6 28 23.4 18 24 Z" fill="#aab4be"/>
    <path d="M17.6 27 l-3.4 .9 l3.6 .7 Z" fill="#ee9f97"/>
    <circle cx="54.4" cy="20.6" r="5.2" fill="url(#${id}-c)"/>
    <path d="M58.6 19.8 C62 19.4 66 19.8 69.4 20.6 C69.6 21.3 69 21.9 68 22.1 L66.8 22.4 C66.2 23.4 65 23.6 64 23.2 L58.8 22.4 Z" fill="url(#${id}-b)" stroke="#c8941a" stroke-width=".35"/>
    <path d="M59 21.3 L67.8 21.3" stroke="#a87a14" stroke-width=".35"/><circle cx="65.4" cy="22.6" r=".85" fill="#d9362a"/>
    <circle cx="56.4" cy="19.2" r="1.15" fill="#f3e9a8" stroke="#e2552f" stroke-width=".5"/><circle cx="56.6" cy="19.2" r=".45" fill="#111"/>
    <g class="g-aile g-proche" style="transform-origin:38px 22px"><path d="M39.6 22.4 C36.4 17 33 12 30 8.6 L26.4 12.4 C29.4 16 31.6 19.6 33 24 Z" fill="url(#${id}-a)" stroke="#8d99a5" stroke-width=".3"/>
      <path d="M26.6 12.6 C29.4 16 31.6 19.6 33 24" stroke="#fff" stroke-width=".9" fill="none" opacity=".85"/><path d="M39 21.6 C36 16.8 33 12.4 30.4 9.2" stroke="#fff" stroke-width=".6" fill="none" opacity=".7"/>
      <g class="g-main" style="transform-origin:30px 8.6px"><path d="M30 8.6 C24 5.6 15 3.6 6 3.8 C11.6 6.4 18.6 9.6 26.4 12.4 Z" fill="url(#${id}-a)" stroke="#8d99a5" stroke-width=".3"/>
        <path d="M6 3.8 C10.6 3.6 14.4 4 17.4 4.8 L15.2 7.8 C12 6.2 9 5 6 3.8 Z" fill="#1d2024"/>
        <ellipse cx="9.4" cy="4.4" rx=".9" ry=".55" fill="#fff"/><ellipse cx="12.8" cy="5" rx=".8" ry=".5" fill="#fff"/>
        <path d="M11 6.2 l1.6 -.7 M14 7.4 l1.6 -.7 M17.2 8.8 l1.4 -.6" stroke="#1d2024" stroke-width=".35"/></g></g>
    </g></svg>`;
  // Goéland posé, de profil (viewBox 56 × 48, tourné vers la droite) : ailes repliées (pointes noires croisées
  // au-delà de la queue, croissant blanc des tertiaires), pattes roses palmées. .g-jambe-a / .g-jambe-b : la marche ;
  // .g-tete : hochement de tête en marchant, coup d'œil autour de lui.
  const goelandPose = (id = "gp") => `<svg viewBox="0 0 56 48" aria-hidden="true"><defs>
      <linearGradient id="${id}-a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#bcc6cf"/><stop offset="1" stop-color="#97a3af"/></linearGradient>
      <linearGradient id="${id}-c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset=".75" stop-color="#f1f4f6"/><stop offset="1" stop-color="#d3dae0"/></linearGradient>
      <radialGradient id="${id}-o"><stop offset="0" stop-color="#3b2a12" stop-opacity=".3"/><stop offset="1" stop-color="#3b2a12" stop-opacity="0"/></radialGradient></defs>
    <ellipse cx="27" cy="43.4" rx="15" ry="2.2" fill="url(#${id}-o)"/>
    <g class="g-jambe-a" style="transform-origin:24px 32px"><path d="M24 32 L23.2 41.6" stroke="#e69790" stroke-width="1.4" stroke-linecap="round"/><path d="M23.2 41.4 l-2.8 1.8 h6.2 Z" fill="#e69790"/></g>
    <g class="g-buste">
      <path d="M18 25 C12 26 7 27.6 2.6 29.2 C7 29.6 12 29.2 17 28.4 Z" fill="#1d2024"/><circle cx="5" cy="28.9" r=".7" fill="#fff"/><circle cx="8.4" cy="28.5" r=".6" fill="#fff"/>
      <path d="M18 27 L8.6 29 L9.4 30.4 L18 30 Z" fill="#f4f6f8"/>
      <path d="M14 26 C16 21 24 18.6 32 19 C38 19.4 41 22.6 40.6 27 C40 31.6 34 34 26 34 C20 34 15 31 14 26 Z" fill="url(#${id}-c)"/>
      <path d="M15 25.6 C18 21 26 19 33 19.6 C36 20 37.4 22.4 35.8 24.6 C32 28 24 29.4 17.6 28.6 C15.8 28.2 14.8 27 15 25.6 Z" fill="url(#${id}-a)"/>
      <path d="M18 28.2 C24 28.8 30 27.6 34.6 24.8" stroke="#fff" stroke-width=".8" fill="none" opacity=".9"/>
      <path d="M20 23.4 C24 22 28 21.6 32 22" stroke="#d6dde3" stroke-width=".5" fill="none" opacity=".8"/>
      <g class="g-tete" style="transform-origin:36px 21px">
        <path d="M33 21 C34 16 36 12 40 11.6 C44 11.4 46 13.6 45.6 16.6 C45.2 19 42.6 20.6 40 21.4 C37 22.4 34.6 23 33 21 Z" fill="url(#${id}-c)"/>
        <path d="M45.2 13.8 C48 13.4 51 13.6 53.6 14.4 C53.8 15 53.3 15.5 52.5 15.6 L51.6 15.8 C51.1 16.7 50.2 16.9 49.4 16.6 L45.2 16.2 Z" fill="#eebf2f" stroke="#c8941a" stroke-width=".35"/>
        <path d="M45.4 15 L52.4 15" stroke="#a87a14" stroke-width=".35"/><circle cx="50.5" cy="16" r=".7" fill="#d9362a"/>
        <circle cx="43" cy="13.6" r="1.05" fill="#f3e9a8" stroke="#e2552f" stroke-width=".45"/><circle cx="43.2" cy="13.6" r=".42" fill="#111"/></g>
    </g>
    <g class="g-jambe-b" style="transform-origin:28px 32px"><path d="M28 32 L28.8 41.6" stroke="#ee9f97" stroke-width="1.4" stroke-linecap="round"/><path d="M28.8 41.4 l-2.6 1.8 h6.2 Z" fill="#ee9f97"/></g>
    </svg>`;
  const fregate = () => `<svg viewBox="0 0 70 26" aria-hidden="true"><path d="M35 12 C30 9 25 9.6 20 11.6 C14 13.8 8 13.4 1 10.4 C7 15 14 16.4 21 15 C26 14 31 13.6 35 14 C39 13.6 44 14 49 15 C56 16.4 63 15 69 10.4 C62 13.4 56 13.8 50 11.6 C45 9.6 40 9 35 12 Z" fill="#20242a"/>
      <path d="M35 13 l-1.6 9 l1.6 -3.2 l1.6 3.2 Z" fill="#20242a"/><path d="M35 11.4 l3.4 -.2 l2.2 .6" stroke="#20242a" stroke-width="1.2" fill="none"/></svg>`;

  // ------------------------------------------------------------------ crabes de plage (svg complets, viewBox 48 × 32, sable à y = 29.6)
  // Vus de face, comme on les voit filer sur le sable. Chaque patte a trois articles (méros, carpe, propode + dactyle)
  // et tourne autour de sa base : deux groupes (.c-pa, .c-pb) alternent quand il court de côté. .c-yeux : les
  // pédoncules se dressent ; .c-pince : la pince s'agite ; .c-tout s'enfonce sous la ligne du sable (découpe) quand il
  // s'enfouit ; .c-trou : le trou et le petit tas de sable ; .c-grain : les grains projetés.
  function pattesCrabe(bases, genoux, chevilles, bouts, coul) {
    let out = "";
    for (const cote of [1, -1]) {
      bases.forEach((b, i) => {
        const X = p => (cote === 1 ? p[0] : 48 - p[0]);
        const pts = [b, genoux[i], chevilles[i], bouts[i]].map(p => `${r1(X(p))} ${r1(p[1])}`);
        const d = `M${pts[0]} L${pts[1]} L${pts[2]} L${pts[3]}`;
        const groupe = (i % 2 === 0) === (cote === 1) ? "c-pa" : "c-pb";
        out += `<g class="c-p ${groupe}" style="transform-origin:${r1(X(b))}px ${r1(b[1])}px"><path d="${d}" stroke="${coul[0]}" stroke-width="${coul[2] || 2}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="${d}" stroke="${coul[1]}" stroke-width="${(coul[2] || 2) - .75}" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
          <circle cx="${pts[1].split(" ")[0]}" cy="${pts[1].split(" ")[1]}" r=".75" fill="${coul[0]}"/><circle cx="${pts[2].split(" ")[0]}" cy="${pts[2].split(" ")[1]}" r=".6" fill="${coul[0]}"/></g>`;
      });
    }
    return out;
  }
  const solCrabe = (id, coul) => `<radialGradient id="${id}-o"><stop offset="0" stop-color="#3b2a12" stop-opacity=".32"/><stop offset="1" stop-color="#3b2a12" stop-opacity="0"/></radialGradient>
      <clipPath id="${id}-s"><rect x="-30" y="-30" width="110" height="59.6"/></clipPath>`;
  const trouCrabe = (id, sable) => `<ellipse cx="24" cy="29.8" rx="18" ry="2.2" fill="url(#${id}-o)" class="c-ombre"/>
      <g class="c-trou" style="opacity:0"><ellipse cx="24" cy="29.6" rx="7.5" ry="1.6" fill="#6e5a3a"/><path d="M14 29.8 C16 27.4 19 26.8 21 28.2 M34 29.8 C32 27.4 29 26.8 27 28.2" stroke="${sable}" stroke-width="2.4" fill="none" stroke-linecap="round"/></g>
      <g class="c-grain" style="opacity:0"><circle cx="13" cy="27" r=".9" fill="${sable}"/><circle cx="35" cy="26" r=".8" fill="${sable}"/><circle cx="10" cy="24.6" r=".6" fill="${sable}"/><circle cx="38" cy="24.4" r=".7" fill="${sable}"/></g>`;

  // Crabe fantôme (Ocypode) : carapace presque carrée couleur sable, granuleuse, rainure en H ; très longs pédoncules
  // aux gros yeux sombres (la cornée occupe tout le bout) ; pinces blanches inégales ; pattes longues et fines, les
  // plus rapides de la plage. Il court de côté, s'arrête net, dresse les yeux, agite la pince et s'enfouit.
  function crabe(id) {
    const P = pattesCrabe([[33.6, 13.2], [34.2, 15.4], [34, 17.8], [32.8, 20]], [[38.6, 8.2], [42.6, 10.4], [45, 14.6], [41.4, 19.8]],
      [[41.6, 17.6], [46.2, 19.6], [48.6, 24], [43.4, 26.4]], [[40.2, 29.4], [45, 29.4], [49.4, 29.5], [42.6, 29.5]], ["#9f8560", "#e2d1ac"]);
    let grains = "";
    const r = alea(7);
    for (let i = 0; i < 22; i++) grains += `<circle cx="${r1(15.5 + r() * 17)}" cy="${r1(11.4 + r() * 9.6)}" r="${r1(.2 + r() * .3)}" fill="${r() < .5 ? "#c4ad84" : "#fff8ea"}" opacity=".8"/>`;
    return `<svg viewBox="0 0 48 32" aria-hidden="true"><defs>${solCrabe(id)}
        <radialGradient id="${id}-c" cx=".45" cy=".3" r=".8"><stop offset="0" stop-color="#f8efda"/><stop offset=".6" stop-color="#e2cfa6"/><stop offset="1" stop-color="#bba27a"/></radialGradient>
        <radialGradient id="${id}-p" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#ffffff"/><stop offset="1" stop-color="#e3d8c2"/></radialGradient>
        <radialGradient id="${id}-y" cx=".35" cy=".3" r=".8"><stop offset="0" stop-color="#4a4438"/><stop offset="1" stop-color="#14120e"/></radialGradient></defs>
      ${trouCrabe(id, "#dcc79c")}
      <g clip-path="url(#${id}-s)"><g class="c-tout">
        ${P}
        <g class="c-yeux" style="transform-origin:24px 11px"><path d="M18.4 11 L16.4 4.8 M29.6 11 L31.6 4.8" stroke="#cfb98f" stroke-width="1.7" stroke-linecap="round"/>
          <ellipse cx="16.1" cy="4.2" rx="1.9" ry="2.9" fill="url(#${id}-y)" transform="rotate(-16 16.1 4.2)"/><ellipse cx="31.9" cy="4.2" rx="1.9" ry="2.9" fill="url(#${id}-y)" transform="rotate(16 31.9 4.2)"/>
          <circle cx="15.5" cy="3.1" r=".55" fill="#fff"/><circle cx="31.3" cy="3.1" r=".55" fill="#fff"/></g>
        <path d="M14.5 10.6 L33.5 10.6 C34.8 10.6 35.4 11.7 35 13 L33.6 19 C33 21 31 22 28.5 22 L19.5 22 C17 22 15 21 14.4 19 L13 13 C12.6 11.7 13.2 10.6 14.5 10.6 Z" fill="url(#${id}-c)" stroke="#a48b63" stroke-width=".5"/>
        ${grains}
        <path d="M20.6 12.6 C21.6 15 21.6 17 20.8 19 M27.4 12.6 C26.4 15 26.4 17 27.2 19 M21.2 15.8 L26.8 15.8" stroke="#b49c74" stroke-width=".5" fill="none" opacity=".75"/>
        <path d="M15.6 11.6 L32.4 11.6" stroke="#fff" stroke-width=".6" opacity=".5"/>
        <path d="M14.6 15.4 C12.6 15.2 11 16 10.4 17.4 C10 18.8 11.2 19.8 12.8 19.4 C14 19 14.8 18 15.2 17.2 Z" fill="url(#${id}-p)" stroke="#bba27a" stroke-width=".5"/>
        <path d="M10.6 17.2 l-1.6 1.6" stroke="#e8dfcd" stroke-width="1.1" stroke-linecap="round"/>
        <g class="c-pince" style="transform-origin:33px 16px"><path d="M33.2 15.2 C36.4 13.6 39.8 13.4 41.8 15 C43.6 16.6 43 19.6 40.6 20.2 C38.2 20.8 35.4 19.4 33.4 18.4 Z" fill="url(#${id}-p)" stroke="#bba27a" stroke-width=".5"/>
          <path d="M41.6 15.2 l2.6 -1.4 M41.4 19.6 l2.8 .2" stroke="#f4eee2" stroke-width="1.5" stroke-linecap="round"/><path d="M41.6 15.2 l2.6 -1.4 M41.4 19.6 l2.8 .2" stroke="#bba27a" stroke-width=".4" stroke-linecap="round"/>
          <path d="M35.4 15.4 C37 14.8 38.6 14.8 40 15.4" stroke="#fff" stroke-width=".6" fill="none" opacity=".8"/></g>
      </g></g></svg>`;
  }
  // Crabe violoniste (Uca) : petite carapace trapézoïdale bleu-vert tachetée, pédoncules très fins, et chez le mâle
  // une pince énorme (orange, doigts blancs) qu'il lève et rabaisse pour faire signe ; l'autre pince est minuscule.
  function violoniste(id) {
    const P = pattesCrabe([[31.4, 14.8], [31.8, 16.6], [31.4, 18.4], [30.4, 20]], [[35.4, 11.6], [38.6, 13], [40.6, 16.4], [37.4, 20.2]],
      [[37.6, 19.4], [41.4, 21.2], [43.4, 25], [39.2, 26.8]], [[36.4, 29.4], [40.6, 29.4], [44.2, 29.5], [38.6, 29.5]], ["#6e4434", "#c48a6c", 1.6]);
    let taches = "";
    const r = alea(23);
    for (let i = 0; i < 14; i++) taches += `<circle cx="${r1(18.5 + r() * 11)}" cy="${r1(13.6 + r() * 6.8)}" r="${r1(.3 + r() * .45)}" fill="#a8e0e4" opacity=".75"/>`;
    return `<svg viewBox="0 0 48 32" aria-hidden="true"><defs>${solCrabe(id)}
        <linearGradient id="${id}-c" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#5d9bb4"/><stop offset="1" stop-color="#2c5a70"/></linearGradient>
        <linearGradient id="${id}-p" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#f7b56c"/><stop offset=".6" stop-color="#ec7a33"/><stop offset="1" stop-color="#c85a22"/></linearGradient></defs>
      ${trouCrabe(id, "#cdb38a")}
      <g clip-path="url(#${id}-s)"><g class="c-tout">
        ${P}
        <g class="c-yeux" style="transform-origin:24px 13px"><path d="M20.4 13 L19.2 4 M27.6 13 L28.8 4" stroke="#3e6f84" stroke-width=".9" stroke-linecap="round"/>
          <ellipse cx="19.1" cy="3.6" rx="1" ry="1.6" fill="#1c2226"/><ellipse cx="28.9" cy="3.6" rx="1" ry="1.6" fill="#1c2226"/>
          <circle cx="18.8" cy="3" r=".35" fill="#fff"/><circle cx="28.6" cy="3" r=".35" fill="#fff"/></g>
        <path d="M17 12.6 L31 12.6 C32.4 12.6 32.8 13.7 32.3 14.9 L30.4 19.6 C29.8 21 28.4 21.6 26.8 21.6 L21.2 21.6 C19.6 21.6 18.2 21 17.6 19.6 L15.7 14.9 C15.2 13.7 15.6 12.6 17 12.6 Z" fill="url(#${id}-c)" stroke="#23485a" stroke-width=".5"/>
        ${taches}<path d="M17.6 13.6 L30.4 13.6" stroke="#cfeef0" stroke-width=".5" opacity=".6"/>
        <path d="M17 17.4 C15.6 17.2 14.6 17.8 14.4 18.8 C14.4 19.8 15.4 20.2 16.4 19.8 L17.6 19 Z" fill="#e9d6c4" stroke="#9a7a62" stroke-width=".4"/>
        <g class="c-pince" style="transform-origin:31.6px 16.8px">
          <path d="M31.2 15.6 C32.8 14.6 34.4 13.6 35.8 12.4 L37.6 14.6 C36 15.8 34 17.2 31.8 18.2 Z" fill="#d9773a" stroke="#9c4e20" stroke-width=".4"/>
          <path d="M35.2 11.8 C35.4 8.6 38.6 6.8 42 7.2 C45.4 7.6 47 9.8 46.4 12.6 C45.8 15.2 43.4 16.4 40.6 16.4 C37.6 16.4 35.2 14.6 35.2 11.8 Z" fill="url(#${id}-p)" stroke="#9c4e20" stroke-width=".5"/>
          <path d="M44.6 13.6 C46.4 16.4 47 20.2 46.2 24 C45.9 25.2 45.2 25.4 45 24.4 C45 21 44.2 18 42.6 15.8 Z" fill="#fbf4ea" stroke="#b49a80" stroke-width=".4"/>
          <path d="M41.2 16.4 C42 19.4 42.2 22.4 41.6 25.4 C41.4 26.4 40.6 26.4 40.6 25.4 C40.6 22.4 40 19.8 38.8 17.4 Z" fill="#f2e8da" stroke="#b49a80" stroke-width=".4"/>
          <path d="M45.4 18 l-.8 .2 M45.6 20.4 l-.8 .2 M41.6 19.6 l.7 .1 M41.8 22 l.7 .1" stroke="#c9b49c" stroke-width=".35"/>
          <path d="M37.6 9.6 C39 8 41.6 7.8 43.4 8.4" stroke="#fde2bf" stroke-width=".8" fill="none" opacity=".85"/>
          <circle cx="39.4" cy="11.6" r=".55" fill="#c85a22" opacity=".55"/><circle cx="42" cy="12.8" r=".5" fill="#c85a22" opacity=".55"/><circle cx="40.4" cy="14.2" r=".45" fill="#c85a22" opacity=".55"/></g>
      </g></g></svg>`;
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

  window.PhilibertNature = { alea, stipe, palme, couronne, cocotierLoin, nuage, goeland, goelandPose, fregate, crabe, violoniste, papillon, rocher, coco, feuilleTombee, hibiscus, scarabee, svgDoc, bz, qz };
})();
