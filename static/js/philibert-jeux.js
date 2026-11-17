"use strict";
/* Les quatre mini-jeux de Philibert (dans un panneau de son île). Le serveur ouvre la partie (jeton à usage unique),
   donne les règles des paliers, tire les côtés et les suites, vérifie la durée, borne le score et calcule la
   récompense : la page applique les règles et affiche. Chaque jeu devient plus difficile au fil de la partie, montre
   son palier, et finit tout seul en cas d'échec (vies, erreurs) ; une bonne partie dure 2 à 3 minutes.
   1. Pluie de feuilles (3 min au plus) : déplacer Philibert (souris, doigt, flèches) pour attraper feuilles et
      fleurs ; un palier toutes les 20 s (plus vite, plus d'objets, plus d'insectes) ; 5 vies.
   2. Gauche ou droite ? (20 manches, 3 erreurs) : un coup d'œil le trahit souvent… de plus en plus bref.
   3. En rythme : répéter ses suites de hochements de tête ET de fanon déployé ; une nouvelle suite à chaque
      manche, plus longue (3 à 14 gestes), et tous les gestes de plus en plus rapides.
   4. Course au rocher chaud (10 étapes, 3 vies) : sauter (Espace, ↑, clic ou doigt) par-dessus les crabes et les
      noix de coco ; à chaque étape il court plus vite et les obstacles sont plus serrés ; rayons de soleil et ombres
      des nuages. Canevas + nxImage (60 i/s max), tout s'arrête onglet caché. */
(() => {
  const D = window.PhilibertDessin;
  let actif = null;          // { arreter() }
  let enCours = null;        // { jeton, ctx } : la partie ouverte sur le serveur, tant qu'elle n'est pas terminée

  const api2 = (etape, corps) => api("/api/philibert/jeu/" + etape, corps);
  // Quitter une partie en cours (✕, fermeture de l'île, autre jeu) = l'abandonner : le serveur la clôt, sans gain ;
  // l'énergie prise au lancement ne revient pas.
  function arreter() {
    if (actif) { try { actif.arreter(); } catch (x) {} actif = null; }
    if (enCours) { const j = enCours.jeton; enCours = null; api2("annuler", { jeton: j }).catch(() => {}); }
  }
  const ouverte = (partie, ctx, box) => {
    enCours = { jeton: partie.jeton, ctx };
    const b = box.querySelector("[data-abandon]");
    if (b) b.hidden = false;
  };
  const terminee = () => { enCours = null; };   // juste avant d'envoyer « fin »
  async function abandonner(box) {
    if (!enCours) return;
    if (!confirm("Abandonner la partie ?\nTu ne gagnes rien, et l'énergie dépensée pour la lancer (−8) ne revient pas.")) return;
    const { jeton, ctx } = enCours;
    enCours = null;
    if (actif) { try { actif.arreter(); } catch (x) {} actif = null; }
    let r;
    try { r = await api2("annuler", { jeton }); } catch (x) { r = { message: x.message }; }
    const zone = box.querySelector(".phb-jeu");
    if (zone) zone.insertAdjacentHTML("afterbegin", `<p class="phb-dit" role="status">${esc(r.message || "Partie abandonnée.")}</p>`);
    setTimeout(() => ctx.fin(r), 1200);
  }
  const son = t => window.PhilibertSon && window.PhilibertSon(t);

  const ico = n => (window.PhilibertIcones ? window.PhilibertIcones.ico(n) : "");
  const ICONES = { "Pluie de feuilles": "nourrir", "Gauche ou droite ?": "loupe", "En rythme": "coeur", "Course au rocher chaud": "drapeau" };
  const calme = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const vies = (n, max) => `<span class="phb-vies" aria-label="${n} vie${n > 1 ? "s" : ""} sur ${max}">${"♥".repeat(Math.max(0, n))}<i>${"♥".repeat(Math.max(0, max - n))}</i></span>`;
  const mmss = t => { t = Math.max(0, Math.ceil(t)); return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`; };
  // bandeau « Palier 3 ! » dessiné sur le canevas (il s'efface en 1,4 s ; sans fondu si les animations sont réduites)
  function bandeau(g, W, texte, age) {
    if (age > 1.4) return;
    const a = calme() ? 1 : Math.min(1, (1.4 - age) / .5);
    g.save(); g.globalAlpha = a; g.font = "bold 26px Trebuchet MS, sans-serif"; g.textAlign = "center";
    const l = g.measureText(texte).width + 36;
    g.fillStyle = "rgba(13, 100, 112, .88)"; g.beginPath(); g.roundRect ? g.roundRect(W / 2 - l / 2, 44, l, 40, 20) : g.rect(W / 2 - l / 2, 44, l, 40); g.fill();
    g.fillStyle = "#fff"; g.fillText(texte, W / 2, 73); g.restore();
  }
  function entete(box, titre, aide) {
    box.hidden = false;
    box.className = "phb-feuille phb-f-jeu";
    box.innerHTML = `<button class="phb-b phb-fermer-f" data-phb="fermer-feuille" aria-label="Quitter le jeu (la partie est abandonnée)">${ico("fermer") || "✕"}</button>
      <h3>${ico(ICONES[titre] || "de")}<span>${esc(titre)}</span><button class="phb-b phb-abandon" data-abandon hidden>Abandonner</button></h3>
      <p class="phb-gris">${aide}</p><div class="phb-jeu"></div>`;
    box.querySelector("[data-abandon]").addEventListener("click", () => abandonner(box));
    return box.querySelector(".phb-jeu");
  }
  function finir(r, ctx, zone) {
    if (r && r.message) zone.insertAdjacentHTML("beforeend", `<p class="phb-dit" role="status">${esc(r.message)}</p>`);
    setTimeout(() => ctx.fin(r), 2200);
  }
  const N = window.PhilibertNature;
  const imgSvg = svg => { const i = new Image(); i.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg.includes("xmlns=") ? svg : svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ')); return i; };
  const pret = i => i && i.complete && i.naturalWidth > 0;
  // fond de plage réaliste (ciel voilé à l'horizon, mer, lagon, sable grainé), peint une seule fois par taille
  function fondPlage(W, H, horizon, plage) {
    const c = document.createElement("canvas"), dpr = window.devicePixelRatio || 1;
    c.width = Math.round(W * dpr); c.height = Math.round(H * dpr);
    const g = c.getContext("2d");
    g.setTransform(dpr, 0, 0, dpr, 0, 0);
    let d = g.createLinearGradient(0, 0, 0, H * horizon);
    d.addColorStop(0, "#2a6fc0"); d.addColorStop(.6, "#5aa3dd"); d.addColorStop(1, "#d3eaf4");
    g.fillStyle = d; g.fillRect(0, 0, W, H * horizon + 1);
    d = g.createLinearGradient(0, H * horizon, 0, H * plage);
    d.addColorStop(0, "#3a86b2"); d.addColorStop(.45, "#1f8fb0"); d.addColorStop(.8, "#3fc8c6"); d.addColorStop(1, "#a6ece2");
    g.fillStyle = d; g.fillRect(0, H * horizon, W, H * (plage - horizon) + 1);
    g.strokeStyle = "rgba(255,255,255,.2)"; g.lineWidth = 1;
    for (let y = H * horizon + 3, k = 0; y < H * plage - 4; k++, y += 2.4 + k * .9) {
      g.beginPath();
      for (let x = (k * 37) % 50; x < W; x += 26 + k * 6) { g.moveTo(x, y); g.quadraticCurveTo(x + 4 + k, y - .8 - k * .1, x + 8 + k * 2, y); }
      g.stroke();
    }
    d = g.createLinearGradient(0, H * plage, 0, H);
    d.addColorStop(0, "#d9c494"); d.addColorStop(.12, "#f1e2bc"); d.addColorStop(1, "#d8bd86");
    g.fillStyle = d; g.fillRect(0, H * plage, W, H * (1 - plage) + 1);
    g.fillStyle = "rgba(255,255,255,.85)";
    for (let x = 0; x < W; x += 9) { const l = 4 + (x * 7) % 11; g.fillRect(x, H * plage - .5, l, 1.6); }
    for (let i = 0; i < W * H * (1 - plage) / 40; i++) {
      const x = (i * 977) % W, y = H * plage + 4 + ((i * 613) % Math.max(1, Math.floor(H * (1 - plage) - 4)));
      g.fillStyle = i % 2 ? "rgba(122,95,52,.28)" : "rgba(255,255,255,.4)"; g.fillRect(x, y, 1.2, 1.2);
    }
    return c;
  }
  const dessin = (e, extra = {}) => D.svg({ stade: e.stade, variante: e.variante, mutation: e.mutation, marques: e.marques, humeur: "joyeux", portes: e.portes, label: "Philibert", uid: "j", ...extra });

  // ---------------------------------------------------------------- 1. Pluie de feuilles
  async function feuilles(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Pluie de feuilles", "Attrape les feuilles (+1) et les fleurs (+2) qui tombent du palmier. Les insectes, il n'en mange pas : en attraper un coûte une vie, et 6 feuilles ratées aussi. Toutes les 20 s, un palier de plus : ça tombe plus vite, plus dru, avec plus d'insectes. Souris, doigt ou flèches ← →. Pendant la partie, la souris reste dans le cadre (Échap, Alt+Tab ou la touche Windows pour en sortir).");
    let partie;
    try { partie = await api2("debut", { jeu: "feuilles" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    ouverte(partie, ctx, box);
    const R = partie.regles, MAXT = partie.duree || R.duree_max;
    const palierDe = t => Math.min(R.palier_max, 1 + Math.floor(Math.max(0, t) / R.palier_s));
    const vitesse = p => 1 + R.vitesse_pas * (p - 1), cadence = p => 1 + R.cadence_pas * (p - 1);
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Palier <b data-palier>1</b> / ${R.palier_max}</span><span>Score : <b data-score>0</b></span><span data-vies>${vies(R.vies, R.vies)}</span><span>Ratées : <b data-ratees>0</b> / ${R.ratees_par_vie}</span><span>Temps : <b data-temps>${mmss(MAXT)}</b></span><span data-msg aria-live="polite"></span></div>
      <canvas class="phb-canevas" tabindex="0" aria-label="Zone de jeu : déplace Philibert avec les flèches gauche et droite"></canvas>`;
    const cv = zone.querySelector("canvas"), g = cv.getContext("2d");
    const img = imgSvg(dessin(e, { leger: true }));
    const IM = { feuille: [0, 1, 2].map(k => imgSvg(N.feuilleTombee(k))), fleur: imgSvg(N.hibiscus()), insecte: imgSvg(N.scarabee()),
      cime: imgSvg(`<svg viewBox="0 0 600 130">${[[40, -150, 150, .5], [150, 165, 140, .55], [250, 20, 150, .55], [330, 150, 150, .6], [450, 35, 140, .5], [560, 160, 140, .55], [600, 120, 120, .4], [0, 60, 120, .4]]
        .map(([x, a, l, d], i) => N.palme([x, -16], a, l, d, i % 2 ? ["#5f9e3e", "#3f7a30", "#a6aa52"] : ["#6aac42", "#478a33", "#b2b552"], { n: 20, graine: 11 + i })).join("")}</svg>`) };
    let W = 0, Hh = 0, dpr = 1, fond = null;
    function taille() {
      dpr = window.devicePixelRatio || 1;
      W = cv.clientWidth; Hh = cv.clientHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(Hh * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      fond = fondPlage(W, Hh, .52, .7);
    }
    taille();
    let px = W / 2, vise = px, score = 0, insectes = 0, joue = 0, compte = partie.compte || 3, objets = [], prochain = 0, dernier = 0, fini = false, msgT = 0, touches = {};
    let palier = 1, palierT = 99, nbVies = R.vies, ratees = 0, raison = "";
    const msg = t => { const m = zone.querySelector("[data-msg]"); m.textContent = t; clearTimeout(msgT); msgT = setTimeout(() => { m.textContent = ""; }, 1400); };
    // La souris reste « prisonnière » du cadre pendant la partie (Pointer Lock) : on lit ses déplacements, le curseur
    // ne peut plus sortir (Échap, Alt+Tab ou la touche Windows le libèrent, c'est le navigateur qui le garantit).
    const verrouille = () => document.pointerLockElement === cv;
    const verrouiller = () => { if (!fini && !verrouille() && cv.requestPointerLock) { try { const p = cv.requestPointerLock(); if (p && p.catch) p.catch(() => {}); } catch (x) { /* refusé : souris libre */ } } };
    const bouger = ev => {
      if (verrouille()) vise = Math.max(40, Math.min(W - 40, vise + (ev.movementX || 0)));      // souris gardée : on suit ses mouvements
      else { const r = cv.getBoundingClientRect(); vise = Math.max(40, Math.min(W - 40, (ev.clientX - r.left))); }   // doigt, ou souris libre
    };
    const libre = () => { if (!verrouille() && !fini) msg("Clique dans le cadre pour y garder la souris."); };
    cv.addEventListener("pointermove", bouger);
    cv.addEventListener("pointerdown", ev => { bouger(ev); cv.focus(); if (ev.pointerType === "mouse") verrouiller(); });
    const refus = () => { if (!fini) msg("Ce navigateur ne permet pas de garder la souris dans le cadre : elle reste libre."); };
    document.addEventListener("pointerlockchange", libre);
    document.addEventListener("pointerlockerror", refus);
    const deverrouiller = () => { document.removeEventListener("pointerlockchange", libre); document.removeEventListener("pointerlockerror", refus); if (verrouille()) document.exitPointerLock(); };
    verrouiller();
    const kd = ev => { if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") { touches[ev.key] = true; ev.preventDefault(); } };
    const ku = ev => { delete touches[ev.key]; };
    cv.addEventListener("keydown", kd); cv.addEventListener("keyup", ku);
    addEventListener("resize", taille);
    cv.focus();

    function nouvel() {
      const r = Math.random(), pi = R.insectes + R.insectes_pas * (palier - 1);
      const type = r < pi ? "insecte" : r < pi + R.fleurs ? "fleur" : "feuille";
      objets.push({ type, x: 20 + Math.random() * (W - 40), y: -20, v: (R.vitesse[0] + Math.random() * R.vitesse[1]) * vitesse(palier),
        a: Math.random() * 6, va: (Math.random() - .5) * 3, k: Math.floor(Math.random() * 3), ph: Math.random() * 6 });
    }
    const perdre = t => {
      nbVies--; zone.querySelector("[data-vies]").innerHTML = vies(nbVies, R.vies); msg(t); son("non");
      if (nbVies <= 0) raison = "Plus de vies !";
    };
    function dessinerObjet(o) {
      const ondule = !calme() && o.type === "feuille";
      g.save(); g.translate(o.x + (ondule ? Math.sin(o.y / 40 + o.ph) * 10 : 0), o.y);
      if (o.type === "insecte") { g.rotate(Math.sin(o.y / 25 + o.ph) * .25); if (pret(IM.insecte)) g.drawImage(IM.insecte, -15, -15, 30, 30); }
      else { if (!calme()) g.rotate(o.a); const im = o.type === "fleur" ? IM.fleur : IM.feuille[o.k]; if (pret(im)) g.drawImage(im, -17, -17, 34, 34); }
      g.restore();
    }
    function image(now) {
      if (fini || !zone.isConnected) return;
      if (document.hidden) { dernier = 0; nxImage(image); return; }            // onglet caché : la partie attend
      const dt = dernier ? Math.min(.1, (now - dernier) / 1000) : 0;
      dernier = now;
      if (compte > 0) { compte -= dt; }
      else {
        joue += dt; palierT += dt;
        const p = palierDe(joue);
        if (p !== palier) { palier = p; palierT = 0; zone.querySelector("[data-palier]").textContent = p; msg(`Palier ${p} : ça tombe plus vite !`); son("ding"); }
        prochain -= dt;
        if (prochain <= 0) { nouvel(); prochain = (R.cadence[0] + Math.random() * R.cadence[1]) / cadence(palier); }
      }
      const vk = 420 * (1 + .07 * (palier - 1));                                 // les flèches suivent le rythme du palier
      if (touches.ArrowLeft) vise = Math.max(40, vise - vk * dt);
      if (touches.ArrowRight) vise = Math.min(W - 40, vise + vk * dt);
      px += (vise - px) * Math.min(1, dt * 12);
      const py = Hh - 40;
      for (const o of objets) { o.y += o.v * dt; o.a += o.va * dt; }
      objets = objets.filter(o => {
        if (o.y > py - 18 && o.y < py + 10 && Math.abs(o.x - px) < 38) {
          if (o.type === "insecte") { insectes++; perdre("Beurk ! Il refuse les insectes (une vie en moins)."); }
          else { score += o.type === "fleur" ? 2 : 1; son("croc"); }
          return false;
        }
        if (o.y >= Hh + 30) {
          if (o.type !== "insecte" && ++ratees >= R.ratees_par_vie) { ratees = 0; perdre("Trop de feuilles ratées : une vie en moins."); }
          zone.querySelector("[data-ratees]").textContent = ratees;
          return false;
        }
        return true;
      });
      // dessin
      g.clearRect(0, 0, W, Hh);
      if (fond) g.drawImage(fond, 0, 0, W, Hh);
      const og = g.createRadialGradient(px, py + 12, 2, px, py + 12, 46);
      og.addColorStop(0, "rgba(59,42,18,.3)"); og.addColorStop(1, "rgba(59,42,18,0)");
      g.fillStyle = og; g.fillRect(px - 50, py + 4, 100, 16);
      if (pret(img)) g.drawImage(img, px - 48, py - 34, 96, 48);
      if (verrouille()) { g.fillStyle = "rgba(255,255,255,.85)"; g.beginPath(); g.moveTo(vise, py + 22); g.lineTo(vise - 6, py + 30); g.lineTo(vise + 6, py + 30); g.fill(); }
      objets.forEach(dessinerObjet);
      if (pret(IM.cime)) { const hc = Math.min(120, W * .2); for (let x = 0; x < W; x += hc * 600 / 130) g.drawImage(IM.cime, x, 0, hc * 600 / 130, hc); }
      if (palier > 1) bandeau(g, W, `Palier ${palier}`, palierT);
      zone.querySelector("[data-score]").textContent = score;
      zone.querySelector("[data-temps]").textContent = compte > 0 ? "…" : mmss(MAXT - joue);
      if (compte > 0) {
        g.fillStyle = "rgba(20, 40, 50, .75)"; g.font = "bold 46px Trebuchet MS, sans-serif"; g.textAlign = "center";
        g.fillText(String(Math.ceil(compte)), W / 2, Hh / 2);
      }
      if (joue >= MAXT && !raison) raison = "Fin du temps : bravo, il est rassasié !";
      if (raison) { fin(); return; }
      nxImage(image);
    }
    async function fin() {
      fini = true;
      deverrouiller();
      removeEventListener("resize", taille);
      let r = null;
      terminee();
      msg(raison);
      try { r = await api2("fin", { jeton: partie.jeton, score, insectes, palier }); } catch (x) { r = { message: x.message }; }
      finir(r, ctx, zone);
    }
    actif = { arreter() { fini = true; deverrouiller(); removeEventListener("resize", taille); } };
    nxImage(image);
  }

  // ---------------------------------------------------------------- 2. Gauche ou droite ?
  async function devin(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Gauche ou droite ?", "De quel côté Philibert va-t-il tourner la tête ? Observe-le : juste avant, il jette souvent un coup d'œil du bon côté… pas toujours ! À chaque palier (toutes les 4 manches), ce coup d'œil est plus bref. 20 manches, la partie s'arrête à la 3ᵉ erreur. Flèches ← → au clavier.");
    let partie;
    try { partie = await api2("debut", { jeu: "devin" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    ouverte(partie, ctx, box);
    const MAXM = partie.manches || 20, MAXE = partie.erreurs || 3;
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Manche <b data-m>1</b> / ${MAXM}</span><span>Palier <b data-p>1</b></span><span>Score : <b data-s>0</b></span><span data-vies>${vies(MAXE, MAXE)}</span></div>
      <div class="phb-devin"><div class="phb-devin-perso phb-anim">${dessin(e, { humeur: "calme" })}</div></div>
      <p class="phb-dit" data-r aria-live="polite">Regarde-le bien…</p>
      <div class="phb-ligne phb-centre"><button class="phb-b phb-prim" data-d="gauche" disabled>◀ Gauche</button><button class="phb-b phb-prim" data-d="droite" disabled>Droite ▶</button></div>`;
    let occupe = true, fini = false, timers = [];
    const perso = zone.querySelector(".phb-devin-perso");
    const boutons = on => zone.querySelectorAll("[data-d]").forEach(b => { b.disabled = !on; });
    // le coup d'œil : la tête se penche une fraction de seconde vers un côté (l'indice du serveur, vrai le plus souvent)
    function indice(m) {
      occupe = true; boutons(false);
      perso.classList.remove("gauche", "lorgne-gauche", "lorgne-droite");
      zone.querySelector("[data-p]").textContent = m.palier;
      zone.querySelector("[data-r]").textContent = "Regarde-le bien…";
      timers.push(setTimeout(() => {
        if (fini) return;
        perso.classList.add("lorgne-" + m.indice);
        timers.push(setTimeout(() => {
          perso.classList.remove("lorgne-gauche", "lorgne-droite");
          if (fini) return;
          occupe = false; boutons(true);
          zone.querySelector("[data-r]").textContent = "À toi : gauche ou droite ?";
        }, m.indice_ms));
      }, 700 + Math.random() * 500));
    }
    async function choisir(c) {
      if (occupe || fini) return;
      occupe = true; boutons(false);
      let r;
      try { r = await api2("coup", { jeton: partie.jeton, choix: c }); } catch (x) { zone.querySelector("[data-r]").textContent = x.message; occupe = false; boutons(true); return; }
      perso.classList.toggle("gauche", r.cote === "gauche");
      perso.classList.add("hoche");
      timers.push(setTimeout(() => perso.classList.remove("hoche"), 700));
      zone.querySelector("[data-r]").textContent = (r.bon ? "Bien vu ! " : "Raté… ") + `Il a tourné la tête à ${r.cote}.`;
      son(r.bon ? "ding" : "non");
      zone.querySelector("[data-s]").textContent = r.score;
      zone.querySelector("[data-vies]").innerHTML = vies(MAXE - r.erreurs, MAXE);
      if (r.fini) {
        fini = true;
        let f = null;
        terminee();
        try { f = await api2("fin", { jeton: partie.jeton }); } catch (x) { f = { message: x.message }; }
        finir(f, ctx, zone);
      } else {
        zone.querySelector("[data-m]").textContent = r.manche + 1;
        if (r.suivante.palier > r.palier || (r.manche % 4 === 0)) son("pop");
        timers.push(setTimeout(() => { if (!fini) indice(r.suivante); }, 1000));
      }
    }
    zone.addEventListener("click", ev => { const b = ev.target.closest("[data-d]"); if (b && !b.disabled) choisir(b.dataset.d); });
    const kd = ev => { if (ev.key === "ArrowLeft") { ev.preventDefault(); choisir("gauche"); } if (ev.key === "ArrowRight") { ev.preventDefault(); choisir("droite"); } };
    document.addEventListener("keydown", kd);
    actif = { arreter() { fini = true; timers.forEach(clearTimeout); document.removeEventListener("keydown", kd); } };
    indice(partie);
    zone.querySelector("[data-d]").focus();
  }

  // ---------------------------------------------------------------- 3. En rythme
  async function rythme(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "En rythme", "Les iguanes « parlent » avec la tête et le fanon. Regarde Philibert, puis reproduis toute sa suite, hochements de tête ET fanon : petit hochement (← ou 1), grand hochement (→ ou 2), fanon déployé (↓ ou 3). À chaque manche (un palier de plus), une nouvelle suite, un geste de plus, et ses hochements comme son fanon vont de plus en plus vite. Jusqu'à 14 gestes !");
    let partie;
    try { partie = await api2("debut", { jeu: "rythme" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    ouverte(partie, ctx, box);
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Palier <b data-p>1</b></span><span>Suite de <b data-n>3</b> / ${partie.max || 14}</span><span>Vitesse <b data-v>1</b></span><span data-etat aria-live="polite">Regarde bien…</span></div>
      <div class="phb-devin"><div class="phb-devin-perso phb-anim">${dessin(e, { humeur: "calme" })}</div></div>
      <div class="phb-suite" aria-hidden="true"></div>
      <div class="phb-ligne phb-centre"><button class="phb-b phb-prim" data-h="petit" disabled>• Petit hochement</button><button class="phb-b phb-prim" data-h="grand" disabled>● Grand hochement</button>
        <button class="phb-b phb-prim" data-h="fanon" disabled>◆ Fanon</button></div>`;
    const perso = zone.querySelector(".phb-devin-perso"), chips = zone.querySelector(".phb-suite");
    let suite = partie.suite, tempo = partie.tempo || .78, palier = partie.palier || 1, rep = [], ecoute = false, fini = false, timers = [];
    const T0 = partie.tempo || .78, DUREE = { petit: 1, grand: 1.5, fanon: 1.4 };
    const dire = t => { zone.querySelector("[data-etat]").textContent = t; };
    const boutons = on => zone.querySelectorAll("[data-h]").forEach(b => { b.disabled = !on; });
    const geste = h => {
      perso.classList.remove("hoche-petit", "hoche-grand", "fanon"); void perso.offsetWidth;
      perso.classList.add(h === "fanon" ? "fanon" : "hoche-" + h);
    };
    function montrer() {
      ecoute = false; rep = []; boutons(false);
      zone.querySelector("[data-n]").textContent = suite.length;
      zone.querySelector("[data-p]").textContent = palier;
      zone.querySelector("[data-v]").textContent = (T0 / tempo).toFixed(1).replace(".", ",") + "×";
      perso.style.setProperty("--phb-t", tempo + "s");                 // vitesse des animations de la tête et du fanon
      dire("Regarde bien…");
      chips.innerHTML = suite.map(() => `<i class="phb-chip"></i>`).join("");
      let t = 600;
      suite.forEach((h, i) => {
        timers.push(setTimeout(() => {
          if (fini) return;
          geste(h);
          chips.children[i].className = "phb-chip vu " + h;
          son(h === "petit" ? "pop" : h === "grand" ? "croc" : "saut");
        }, t));
        t += DUREE[h] * tempo * 1000;
      });
      timers.push(setTimeout(() => {
        if (fini) return;
        perso.classList.remove("hoche-petit", "hoche-grand", "fanon");
        chips.innerHTML = suite.map(() => `<i class="phb-chip"></i>`).join("");
        ecoute = true; boutons(true); dire("À toi !");
        zone.querySelector("[data-h]").focus();
      }, t + 200));
    }
    async function taper(h) {
      if (!ecoute || fini) return;
      rep.push(h);
      const c = chips.children[rep.length - 1];
      if (c) c.className = "phb-chip vu " + h;
      geste(h);
      if (rep.length < suite.length) return;
      ecoute = false; boutons(false);
      let r;
      try { r = await api2("coup", { jeton: partie.jeton, reponse: rep }); } catch (x) { dire(x.message); return; }
      if (r.bon && !r.fini) { son("ding"); dire(`Bravo ! Palier ${r.palier} : nouvelle suite, un peu plus vite…`); suite = r.suite; tempo = r.tempo || tempo; palier = r.palier || palier + 1; timers.push(setTimeout(montrer, 1100)); return; }
      fini = true;
      dire(r.bon ? "Parfait, jusqu'au bout !" : "Oups, ce n'était pas tout à fait ça.");
      let f = null;
      terminee();
      try { f = await api2("fin", { jeton: partie.jeton }); } catch (x) { f = { message: x.message }; }
      finir(f, ctx, zone);
    }
    zone.addEventListener("click", ev => { const b = ev.target.closest("[data-h]"); if (b && !b.disabled) taper(b.dataset.h); });
    const kd = ev => {
      if (ev.key === "ArrowLeft" || ev.key === "1") { ev.preventDefault(); taper("petit"); }
      if (ev.key === "ArrowRight" || ev.key === "2") { ev.preventDefault(); taper("grand"); }
      if (ev.key === "ArrowDown" || ev.key === "3") { ev.preventDefault(); taper("fanon"); }
    };
    document.addEventListener("keydown", kd);
    actif = { arreter() { fini = true; timers.forEach(clearTimeout); document.removeEventListener("keydown", kd); } };
    montrer();
  }

  // ---------------------------------------------------------------- 4. Course au rocher chaud
  async function course(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Course au rocher chaud", "Philibert court jusqu'au rocher chaud, en 10 étapes. Saute par-dessus les crabes et les noix de coco (Espace, ↑, clic ou doigt) : chaque choc coûte une vie (3 en tout). À chaque étape, il court plus vite et les obstacles sont plus serrés. Les rayons de soleil le réchauffent : plus il a chaud, plus il court vite. L'ombre des nuages le refroidit.");
    let partie;
    try { partie = await api2("debut", { jeu: "course" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    ouverte(partie, ctx, box);
    const R = partie.regles, BUT = R.etape_px * R.etapes, LIMITE = partie.duree || R.duree_max;
    const etapeDe = d => Math.min(R.etapes, 1 + Math.floor(Math.max(0, d) / R.etape_px));
    const vitesse = k => 1 + R.vitesse_pas * (k - 1), ecart = k => 1 / (1 + R.ecart_pas * (k - 1));
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Étape <b data-etape>1</b> / ${R.etapes}</span><span>Rayons : <b data-score>0</b></span><span data-vies>${vies(R.vies, R.vies)}</span><span>Temps : <b data-temps>${mmss(LIMITE)}</b></span><span data-msg aria-live="polite"></span></div>
      <canvas class="phb-canevas course" tabindex="0" aria-label="Course : appuie sur Espace ou flèche haut pour sauter"></canvas>`;
    const cv = zone.querySelector("canvas"), g = cv.getContext("2d");
    // tirage reproductible à partir de la graine du serveur (mulberry32)
    let graine = partie.graine >>> 0;
    const alea = () => { graine = (graine + 0x6D2B79F5) >>> 0; let t = graine; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const image = svg => { const i = new Image(); i.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ')); return i; };
    const IMC = { crabe: imgSvg(N.crabe("jc")), coco: imgSvg(`<svg viewBox="0 0 40 40">${N.coco("jk", 20, 22, 13)}</svg>`),
      rocher: imgSvg(`<svg viewBox="0 0 200 100">${N.rocher("jr", 16, 96, 168, 86, { lum: -1 })}</svg>`),
      palmier: imgSvg(`<svg viewBox="0 0 300 300">${N.stipe({ id: "jp", base: [170, 296], c1: [168, 230], c2: [160, 160], cime: [140, 96], w0: 16, w1: 9, lum: 1, coul: ["#5e4f40", "#8c7862", "#bca684"], clair: "#e8d6b6", anneaux: 22 })}${N.couronne([140, 96], { palmes: ["#64a640", "#438532", "#adb050", "#30652b", "#879744"], sec: ["#b89c5c", "#8a6f3e"], noix: ["#9a7344", "#5e4022", "#93a648", "#56702a"], echelle: .78 }, "jq")}</svg>`),
      nuage: imgSvg(N.nuage("jn", 7, { haut: "#ffffff", milieu: "#eef2f7", bas: "#a9b8c9" })) };
    const pose = j => image(D.svg({ stade: e.stade, variante: e.variante, mutation: e.mutation, marques: e.marques, humeur: "joyeux", portes: e.portes, label: "", jambes: j, uid: "c" }));
    const IMG = [pose({ av: -20, arl: -20, ar: 18, avl: 18, gar: -28, gavl: -28 }), pose({ av: 18, arl: 18, ar: -20, avl: -20, gav: -28, garl: -28 }),
      pose({ av: 24, ar: 26, avl: 24, arl: 26, gav: -40, gar: -40, gavl: -40, garl: -40 })];
    let W = 0, Hh = 0, fond = null;
    function taille() {
      const dpr = window.devicePixelRatio || 1;
      W = cv.clientWidth; Hh = cv.clientHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(Hh * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      fond = fondPlage(W, Hh, .46, .62);
    }
    taille();
    // parcours : obstacles (de plus en plus serrés à chaque étape, jamais moins de R.ecart_min entre deux), rayons et
    // ombres de nuages répartis sur la distance
    const obstacles = [], rayons = [], ombres = [];
    for (let x = 700; x < BUT - 500; x += Math.max(R.ecart_min, (R.ecart[0] + alea() * R.ecart[1]) * ecart(etapeDe(x)))) obstacles.push({ x, type: alea() < .6 ? "crabe" : "coco", touche: false });
    for (let x = 420; x < BUT - 300; x += R.rayon_min + alea() * 260) rayons.push({ x, h: alea() < .45 ? 95 : 30, pris: false });
    for (let x = 1300; x < BUT - 700; x += 1100 + alea() * 900) ombres.push({ x, l: 260 + alea() * 200 });
    let dist = 0, chaleur = Math.max(20, Math.min(100, e.jauges.chaleur)), score = 0, temps = 0, compte = partie.compte || 3, dernier = 0, fini = false, arrive = false;
    let etape = 1, etapeT = 99, nbVies = R.vies, raison = "";
    let y = 0, vy = 0, trebuche = 0, pas = 0, msgT = 0;
    const msg = t => { const m = zone.querySelector("[data-msg]"); m.textContent = t; clearTimeout(msgT); msgT = setTimeout(() => { m.textContent = ""; }, 1300); };
    const sauter = () => { if (compte <= 0 && !fini && y === 0) { vy = -560; son("saut"); } };
    const kd = ev => { if (ev.key === " " || ev.key === "ArrowUp" || ev.key === "Spacebar") { ev.preventDefault(); sauter(); } };
    cv.addEventListener("keydown", kd);
    cv.addEventListener("pointerdown", ev => { ev.preventDefault(); cv.focus(); sauter(); });
    addEventListener("resize", taille);
    cv.focus();

    function dessiner() {
      const sol = Hh - 40, px = W * .2;
      if (fond) g.drawImage(fond, 0, 0, W, Hh);
      // nuages (lents) et leurs ombres sur le sable
      for (const o of ombres) {
        const ox = px + (o.x - dist);
        if (ox + o.l < -80 || ox > W + 80) continue;
        const og = g.createRadialGradient(ox + o.l / 2, sol + 4, 4, ox + o.l / 2, sol + 4, o.l / 2);
        og.addColorStop(0, "rgba(30,45,60,.32)"); og.addColorStop(1, "rgba(30,45,60,0)");
        g.save(); g.translate(0, sol + 4); g.scale(1, .12); g.translate(0, -(sol + 4)); g.fillStyle = og; g.fillRect(ox - 10, sol + 4 - o.l / 2, o.l + 20, o.l); g.restore();
        if (pret(IMC.nuage)) g.drawImage(IMC.nuage, ox + o.l * .15, 4, o.l * .7, o.l * .7 * .42);
      }
      // cocotiers en arrière-plan (parallaxe)
      if (pret(IMC.palmier)) for (let i = 0; i < 3; i++) {
        const x = ((i * 460 - dist * .45) % (W + 460) + W + 460) % (W + 460) - 230, h = Math.min(Hh * .78, 230);
        g.drawImage(IMC.palmier, x, sol + 8 - h, h, h);
      }
      // traces dans le sable qui défilent
      g.strokeStyle = "rgba(120,90,45,.22)"; g.lineWidth = 1.6;
      for (let x = -60; x < W + 60; x += 46) { const xx = x - dist % 46; g.beginPath(); g.moveTo(xx, sol + 16); g.quadraticCurveTo(xx + 8, sol + 13, xx + 16, sol + 16); g.stroke(); }
      // rocher chaud (arrivée) et air qui tremble au-dessus
      const rx = px + (BUT - dist) + 40;
      if (rx < W + 220 && pret(IMC.rocher)) {
        g.drawImage(IMC.rocher, rx - 10, sol - 92, 190, 95);
        g.strokeStyle = "rgba(255,255,255,.4)"; g.lineWidth = 2;
        for (let k = 0; k < 3; k++) { const yy = sol - 100 - ((temps * 30 + k * 12) % 36); g.beginPath(); g.moveTo(rx + 50 + k * 34, yy); g.quadraticCurveTo(rx + 58 + k * 34, yy - 8, rx + 50 + k * 34, yy - 16); g.stroke(); }
      }
      // rayons de soleil : petites boules de lumière qui scintillent
      for (const r of rayons) {
        if (r.pris) continue;
        const x = px + (r.x - dist); if (x < -30 || x > W + 30) continue;
        const yy = sol - r.h - 20, k = 1 + Math.sin(temps * 6 + r.x) * .12;
        const rg = g.createRadialGradient(x, yy, 0, x, yy, 18 * k);
        rg.addColorStop(0, "rgba(255,255,240,1)"); rg.addColorStop(.25, "rgba(255,226,120,.9)"); rg.addColorStop(1, "rgba(255,190,60,0)");
        g.fillStyle = rg; g.beginPath(); g.arc(x, yy, 18 * k, 0, Math.PI * 2); g.fill();
        g.strokeStyle = "rgba(255,245,200,.8)"; g.lineWidth = 1.2;
        g.beginPath(); g.moveTo(x - 11 * k, yy); g.lineTo(x + 11 * k, yy); g.moveTo(x, yy - 11 * k); g.lineTo(x, yy + 11 * k); g.stroke();
      }
      // obstacles : crabes fantômes (qui trottinent) et noix de coco (qui roulent un peu)
      for (const o of obstacles) {
        const x = px + (o.x - dist); if (x < -40 || x > W + 40) continue;
        if (o.type === "crabe") { const b = Math.abs(Math.sin(temps * 14 + o.x)) * 2; if (pret(IMC.crabe)) g.drawImage(IMC.crabe, x - 20, sol - 24 - b, 40, 25); }
        else if (pret(IMC.coco)) { g.save(); g.translate(x, sol - 12); g.rotate(-(dist - o.x) / 40); g.drawImage(IMC.coco, -16, -18, 32, 32); g.restore(); }
      }
      // Philibert (3 images : deux pas et le saut) et son ombre
      const im = y < 0 ? IMG[2] : IMG[Math.floor(pas) % 2];
      const og = g.createRadialGradient(px, sol + 3, 2, px, sol + 3, 44 * (1 + y / 300));
      og.addColorStop(0, "rgba(59,42,18,.32)"); og.addColorStop(1, "rgba(59,42,18,0)");
      g.save(); g.translate(0, sol + 3); g.scale(1, .14); g.translate(0, -(sol + 3)); g.fillStyle = og; g.fillRect(px - 50, sol + 3 - 50, 100, 100); g.restore();
      if (pret(im)) { g.save(); if (trebuche > 0) { g.translate(px, sol + y); g.rotate(-.12); g.translate(-px, -(sol + y)); } g.drawImage(im, px - 56, sol - 50 + y, 112, 56); g.restore(); }
      // barres : progression vers le rocher, chaleur
      g.fillStyle = "rgba(255,255,255,.85)"; g.fillRect(12, 10, W - 24, 10); g.fillStyle = "#0d6470"; g.fillRect(12, 10, (W - 24) * Math.min(1, dist / BUT), 10);
      g.fillStyle = "rgba(13,100,112,.55)"; for (let k = 1; k < R.etapes; k++) g.fillRect(12 + (W - 24) * k / R.etapes - 1, 8, 2, 14);
      if (etape > 1) bandeau(g, W, `Étape ${etape} : plus vite !`, etapeT);
      g.fillStyle = "#8f8478"; g.beginPath(); g.arc(W - 12, 15, 7, 0, Math.PI * 2); g.fill();
      g.fillStyle = "rgba(255,255,255,.85)"; g.fillRect(12, 26, 120, 8); g.fillStyle = chaleur < 35 ? "#3b7fd0" : "#e8731a"; g.fillRect(12, 26, 1.2 * chaleur, 8);
      g.fillStyle = "#1f3036"; g.font = "bold 11px Segoe UI, sans-serif"; g.textAlign = "left"; g.fillText(chaleur < 35 ? "il a froid…" : "chaleur", 138, 34);
      if (compte > 0) { g.fillStyle = "rgba(20,40,50,.75)"; g.font = "bold 46px Trebuchet MS, sans-serif"; g.textAlign = "center"; g.fillText(String(Math.ceil(compte)), W / 2, Hh / 2); }
    }

    function tour(now) {
      if (fini || !zone.isConnected) return;
      if (document.hidden) { dernier = 0; nxImage(tour); return; }              // onglet caché : la course attend
      const dt = dernier ? Math.min(.05, (now - dernier) / 1000) : 0;
      dernier = now;
      if (compte > 0) compte -= dt;
      else {
        temps += dt;
        const px = 0;                                   // (coordonnées du monde : Philibert est à « dist »)
        const k = etapeDe(dist);
        if (k !== etape) { etape = k; etapeT = 0; zone.querySelector("[data-etape]").textContent = k; msg(`Étape ${k} / ${R.etapes}`); son("ding"); }
        etapeT += dt;
        const v = (R.vitesse[0] + R.vitesse[1] * chaleur / 100) * vitesse(etape) * (trebuche > 0 ? .45 : 1);
        dist += v * dt;
        pas += dt * v / 34;
        trebuche = Math.max(0, trebuche - dt);
        vy += 1600 * dt; y = Math.min(0, y + vy * dt); if (y === 0) vy = 0;
        chaleur = Math.max(0, chaleur - 1 * dt);
        if (ombres.some(o => dist > o.x && dist < o.x + o.l)) chaleur = Math.max(0, chaleur - 9 * dt);
        for (const r of rayons) if (!r.pris && Math.abs(r.x - dist - px) < 26 && Math.abs(-r.h - y) < 42) { r.pris = true; score++; chaleur = Math.min(100, chaleur + 8); son("ding"); }
        for (const o of obstacles) if (!o.touche && Math.abs(o.x - dist) < 22 && y > -26) {
          o.touche = true; trebuche = .8; nbVies--; zone.querySelector("[data-vies]").innerHTML = vies(nbVies, R.vies);
          msg(o.type === "crabe" ? "Oups, un crabe ! Une vie en moins." : "Aïe, une noix de coco ! Une vie en moins."); son("non");
          if (nbVies <= 0) raison = "Trop de chocs : il s'arrête pour souffler.";
        }
        if (dist >= BUT) { arrive = true; raison = "Arrivé ! Il s'étale sur le rocher chaud."; }
        else if (temps >= LIMITE && !raison) raison = "Le temps est écoulé : le rocher était encore loin.";
        if (raison) { finPartie(); return; }
      }
      dessiner();
      zone.querySelector("[data-score]").textContent = score;
      zone.querySelector("[data-temps]").textContent = compte > 0 ? "…" : mmss(LIMITE - temps);
      nxImage(tour);
    }
    async function finPartie() {
      fini = true;
      removeEventListener("resize", taille);
      dessiner();
      msg(raison);
      let r = null;
      terminee();
      try { r = await api2("fin", { jeton: partie.jeton, score, arrivee: arrive, palier: etape, distance: Math.round(Math.min(dist, BUT)) }); } catch (x) { r = { message: x.message }; }
      finir(r, ctx, zone);
    }
    actif = { arreter() { fini = true; removeEventListener("resize", taille); } };
    nxImage(tour);
  }


  window.PhilibertJeux = {
    lancer(jeu, box, ctx) { arreter(); ({ feuilles, devin, rythme, course }[jeu] || feuilles)(box, ctx); },
    arreter,
  };
})();
