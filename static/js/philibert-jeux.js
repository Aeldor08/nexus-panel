"use strict";
/* Les quatre mini-jeux de Philibert (dans un panneau de son île). Le serveur ouvre la partie (jeton à usage unique),
   tire les côtés et les suites, vérifie la durée et calcule la récompense : la page ne fait qu'afficher.
   1. Pluie de feuilles (30 s) : déplacer Philibert (souris, doigt, flèches) pour attraper feuilles et fleurs ;
      les insectes, il les refuse (−1). Dessin sur un canevas avec nxImage (60 i/s max), en pause onglet caché.
   2. Gauche ou droite ? : deviner de quel côté il tourne la tête (5 manches).
   3. Le hochement : répéter ses suites de petits et grands hochements de tête (mémoire et rythme).
   4. Course au rocher chaud (30 s au plus) : il court vers le rocher ; sauter (Espace, ↑, clic ou doigt) par-dessus
      les crabes et les noix de coco ; les rayons de soleil le réchauffent (il court plus vite), l'ombre des nuages le
      refroidit (sang froid !). Il part avec sa vraie chaleur du moment. Canevas + nxImage, en pause onglet caché. */
(() => {
  const D = window.PhilibertDessin;
  let actif = null;          // { arreter() }

  const api2 = (etape, corps) => api("/api/philibert/jeu/" + etape, corps);
  function arreter() { if (actif) { try { actif.arreter(); } catch (x) {} actif = null; } }
  const son = t => window.PhilibertSon && window.PhilibertSon(t);

  const ico = n => (window.PhilibertIcones ? window.PhilibertIcones.ico(n) : "");
  const ICONES = { "Pluie de feuilles": "nourrir", "Gauche ou droite ?": "loupe", "Le hochement": "coeur", "Course au rocher chaud": "drapeau" };
  function entete(box, titre, aide) {
    box.hidden = false;
    box.className = "phb-feuille phb-f-jeu";
    box.innerHTML = `<button class="phb-b phb-fermer-f" data-phb="fermer-feuille" aria-label="Quitter le jeu">${ico("fermer") || "✕"}</button>
      <h3>${ico(ICONES[titre] || "de")}<span>${esc(titre)}</span></h3><p class="phb-gris">${aide}</p><div class="phb-jeu"></div>`;
    return box.querySelector(".phb-jeu");
  }
  function finir(r, ctx, zone) {
    if (r && r.message) zone.insertAdjacentHTML("beforeend", `<p class="phb-dit" role="status">${esc(r.message)}</p>`);
    setTimeout(() => ctx.fin(r), 2200);
  }
  const dessin = (e, extra = {}) => D.svg({ stade: e.stade, variante: e.variante, humeur: "joyeux", portes: e.portes, label: "Philibert", ...extra });

  // ---------------------------------------------------------------- 1. Pluie de feuilles
  async function feuilles(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Pluie de feuilles", "Attrape les feuilles (+1) et les fleurs (+2) qui tombent du palmier. Les insectes, il n'en mange pas : évite-les ! Souris, doigt ou flèches ← →.");
    let partie;
    try { partie = await api2("debut", { jeu: "feuilles" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Score : <b data-score>0</b></span><span>Temps : <b data-temps>30</b> s</span><span data-msg aria-live="polite"></span></div>
      <canvas class="phb-canevas" tabindex="0" aria-label="Zone de jeu : déplace Philibert avec les flèches gauche et droite"></canvas>`;
    const cv = zone.querySelector("canvas"), g = cv.getContext("2d");
    const img = new Image();
    img.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(dessin(e).replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" '));
    let W = 0, Hh = 0, dpr = 1;
    function taille() {
      dpr = window.devicePixelRatio || 1;
      W = cv.clientWidth; Hh = cv.clientHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(Hh * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    taille();
    let px = W / 2, vise = px, score = 0, insectes = 0, reste = 30, compte = 3, objets = [], prochain = 0, dernier = 0, fini = false, msgT = 0, touches = {};
    const msg = t => { const m = zone.querySelector("[data-msg]"); m.textContent = t; clearTimeout(msgT); msgT = setTimeout(() => { m.textContent = ""; }, 1400); };
    const bouger = ev => { const r = cv.getBoundingClientRect(); vise = Math.max(40, Math.min(W - 40, (ev.clientX - r.left))); };
    cv.addEventListener("pointermove", bouger);
    cv.addEventListener("pointerdown", ev => { bouger(ev); cv.focus(); });
    const kd = ev => { if (ev.key === "ArrowLeft" || ev.key === "ArrowRight") { touches[ev.key] = true; ev.preventDefault(); } };
    const ku = ev => { delete touches[ev.key]; };
    cv.addEventListener("keydown", kd); cv.addEventListener("keyup", ku);
    addEventListener("resize", taille);
    cv.focus();

    function nouvel() {
      const r = Math.random();
      const type = r < .58 ? "feuille" : r < .76 ? "fleur" : "insecte";
      objets.push({ type, x: 20 + Math.random() * (W - 40), y: -20, v: 110 + Math.random() * 90, a: Math.random() * 6, va: (Math.random() - .5) * 3 });
    }
    function dessinerObjet(o) {
      g.save(); g.translate(o.x, o.y); g.rotate(o.a);
      if (o.type === "feuille") {
        g.fillStyle = "#5cb84a"; g.strokeStyle = "#2f7a37"; g.lineWidth = 1.5;
        g.beginPath(); g.ellipse(0, 0, 13, 6, 0, 0, Math.PI * 2); g.fill(); g.stroke();
        g.beginPath(); g.moveTo(-12, 0); g.lineTo(12, 0); g.stroke();
      } else if (o.type === "fleur") {
        g.fillStyle = "#ff5a7a";
        for (let i = 0; i < 5; i++) { g.rotate(Math.PI * 2 / 5); g.beginPath(); g.ellipse(0, -6, 4, 6.5, 0, 0, Math.PI * 2); g.fill(); }
        g.fillStyle = "#ffd34d"; g.beginPath(); g.arc(0, 0, 3.6, 0, Math.PI * 2); g.fill();
      } else {
        g.rotate(-o.a);
        g.strokeStyle = "#3b2a1a"; g.lineWidth = 1.6;
        for (const s of [-1, 1]) for (const k of [-5, 0, 5]) { g.beginPath(); g.moveTo(k, 0); g.lineTo(k + s * 3, s * 9); g.stroke(); }
        g.fillStyle = "#5a3d22"; g.beginPath(); g.ellipse(0, 0, 11, 5.5, 0, 0, Math.PI * 2); g.fill();
        g.beginPath(); g.moveTo(10, -2); g.quadraticCurveTo(20, -12, 24, -8); g.stroke();
      }
      g.restore();
    }
    function image(now) {
      if (fini || !zone.isConnected) return;
      if (document.hidden) { dernier = 0; nxImage(image); return; }            // onglet caché : la partie attend
      const dt = dernier ? Math.min(.1, (now - dernier) / 1000) : 0;
      dernier = now;
      if (compte > 0) { compte -= dt; }
      else {
        reste -= dt;
        prochain -= dt;
        if (prochain <= 0) { nouvel(); prochain = .5 + Math.random() * .35; }
      }
      if (touches.ArrowLeft) vise = Math.max(40, vise - 420 * dt);
      if (touches.ArrowRight) vise = Math.min(W - 40, vise + 420 * dt);
      px += (vise - px) * Math.min(1, dt * 12);
      const py = Hh - 40;
      for (const o of objets) { o.y += o.v * dt; o.a += o.va * dt; }
      objets = objets.filter(o => {
        if (o.y > py - 18 && o.y < py + 10 && Math.abs(o.x - px) < 38) {
          if (o.type === "insecte") { insectes++; score = Math.max(0, score - 1); msg("Beurk ! Il refuse les insectes."); son("non"); }
          else { score += o.type === "fleur" ? 2 : 1; son("croc"); }
          return false;
        }
        return o.y < Hh + 30;
      });
      // dessin
      g.clearRect(0, 0, W, Hh);
      const ciel = g.createLinearGradient(0, 0, 0, Hh);
      ciel.addColorStop(0, "#8fd3f4"); ciel.addColorStop(.75, "#d9f3fb"); ciel.addColorStop(.76, "#f1d79a"); ciel.addColorStop(1, "#e6c47e");
      g.fillStyle = ciel; g.fillRect(0, 0, W, Hh);
      g.fillStyle = "#3f9a46";
      for (let x = -20; x < W + 40; x += 90) { g.beginPath(); g.ellipse(x, 0, 70, 22, .25, 0, Math.PI * 2); g.fill(); }
      objets.forEach(dessinerObjet);
      if (img.complete) g.drawImage(img, px - 48, py - 34, 96, 48);
      zone.querySelector("[data-score]").textContent = score;
      zone.querySelector("[data-temps]").textContent = compte > 0 ? "…" : Math.max(0, Math.ceil(reste));
      if (compte > 0) {
        g.fillStyle = "rgba(20, 40, 50, .75)"; g.font = "bold 46px Trebuchet MS, sans-serif"; g.textAlign = "center";
        g.fillText(String(Math.ceil(compte)), W / 2, Hh / 2);
      }
      if (reste <= 0) { fin(); return; }
      nxImage(image);
    }
    async function fin() {
      fini = true;
      removeEventListener("resize", taille);
      let r = null;
      try { r = await api2("fin", { jeton: partie.jeton, score, insectes }); } catch (x) { r = { message: x.message }; }
      finir(r, ctx, zone);
    }
    actif = { arreter() { fini = true; removeEventListener("resize", taille); } };
    nxImage(image);
  }

  // ---------------------------------------------------------------- 2. Gauche ou droite ?
  async function devin(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Gauche ou droite ?", "De quel côté Philibert va-t-il tourner la tête ? 5 manches. Flèches ← → au clavier.");
    let partie;
    try { partie = await api2("debut", { jeu: "devin" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Manche <b data-m>1</b> / 5</span><span>Score : <b data-s>0</b></span></div>
      <div class="phb-devin"><div class="phb-devin-perso phb-anim">${dessin(e, { humeur: "calme" })}</div></div>
      <p class="phb-dit" data-r aria-live="polite">Fais ton choix !</p>
      <div class="phb-ligne phb-centre"><button class="phb-b phb-prim" data-d="gauche">◀ Gauche</button><button class="phb-b phb-prim" data-d="droite">Droite ▶</button></div>`;
    let occupe = false, fini = false;
    const perso = zone.querySelector(".phb-devin-perso");
    async function choisir(c) {
      if (occupe || fini) return;
      occupe = true;
      let r;
      try { r = await api2("coup", { jeton: partie.jeton, choix: c }); } catch (x) { zone.querySelector("[data-r]").textContent = x.message; occupe = false; return; }
      perso.classList.toggle("gauche", r.cote === "gauche");
      perso.classList.add("hoche");
      setTimeout(() => perso.classList.remove("hoche"), 700);
      zone.querySelector("[data-r]").textContent = (r.bon ? "Bien vu ! " : "Raté… ") + `Il a tourné la tête à ${r.cote}.`;
      son(r.bon ? "ding" : "pop");
      zone.querySelector("[data-s]").textContent = r.score;
      if (r.fini) {
        fini = true;
        let f = null;
        try { f = await api2("fin", { jeton: partie.jeton }); } catch (x) { f = { message: x.message }; }
        finir(f, ctx, zone);
      } else {
        zone.querySelector("[data-m]").textContent = r.manche + 1;
        setTimeout(() => { occupe = false; zone.querySelector("[data-r]").textContent = "Et maintenant ?"; }, 900);
      }
    }
    zone.addEventListener("click", ev => { const b = ev.target.closest("[data-d]"); if (b) choisir(b.dataset.d); });
    const kd = ev => { if (ev.key === "ArrowLeft") { ev.preventDefault(); choisir("gauche"); } if (ev.key === "ArrowRight") { ev.preventDefault(); choisir("droite"); } };
    document.addEventListener("keydown", kd);
    zone.querySelector("[data-d]").focus();
    actif = { arreter() { fini = true; document.removeEventListener("keydown", kd); } };
  }

  // ---------------------------------------------------------------- 3. Le hochement
  async function rythme(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Le hochement", "Les iguanes « parlent » en hochant la tête. Regarde Philibert, puis répète : petit hochement (← ou 1) ou grand hochement (→ ou 2).");
    let partie;
    try { partie = await api2("debut", { jeu: "rythme" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Suite de <b data-n>3</b></span><span data-etat aria-live="polite">Regarde bien…</span></div>
      <div class="phb-devin"><div class="phb-devin-perso phb-anim">${dessin(e, { humeur: "calme" })}</div></div>
      <div class="phb-suite" aria-hidden="true"></div>
      <div class="phb-ligne phb-centre"><button class="phb-b phb-prim" data-h="petit" disabled>• Petit hochement</button><button class="phb-b phb-prim" data-h="grand" disabled>● Grand hochement</button></div>`;
    const perso = zone.querySelector(".phb-devin-perso"), chips = zone.querySelector(".phb-suite");
    let suite = partie.suite, rep = [], ecoute = false, fini = false, timers = [];
    const dire = t => { zone.querySelector("[data-etat]").textContent = t; };
    const boutons = on => zone.querySelectorAll("[data-h]").forEach(b => { b.disabled = !on; });
    function montrer() {
      ecoute = false; rep = []; boutons(false);
      zone.querySelector("[data-n]").textContent = suite.length;
      dire("Regarde bien…");
      chips.innerHTML = suite.map(() => `<i class="phb-chip"></i>`).join("");
      let t = 600;
      suite.forEach((s, i) => {
        timers.push(setTimeout(() => {
          if (fini) return;
          perso.classList.remove("hoche-petit", "hoche-grand"); void perso.offsetWidth;
          perso.classList.add("hoche-" + s);
          chips.children[i].className = "phb-chip vu " + s;
          son(s === "petit" ? "pop" : "croc");
        }, t));
        t += s === "petit" ? 600 : 1000;
      });
      timers.push(setTimeout(() => {
        if (fini) return;
        perso.classList.remove("hoche-petit", "hoche-grand");
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
      perso.classList.remove("hoche-petit", "hoche-grand"); void perso.offsetWidth; perso.classList.add("hoche-" + h);
      if (rep.length < suite.length) return;
      ecoute = false; boutons(false);
      let r;
      try { r = await api2("coup", { jeton: partie.jeton, reponse: rep }); } catch (x) { dire(x.message); return; }
      if (r.bon && !r.fini) { son("ding"); dire("Bravo ! Une de plus…"); suite = r.suite; timers.push(setTimeout(montrer, 1100)); return; }
      fini = true;
      dire(r.bon ? "Parfait, jusqu'au bout !" : "Oups, ce n'était pas tout à fait ça.");
      let f = null;
      try { f = await api2("fin", { jeton: partie.jeton }); } catch (x) { f = { message: x.message }; }
      finir(f, ctx, zone);
    }
    zone.addEventListener("click", ev => { const b = ev.target.closest("[data-h]"); if (b && !b.disabled) taper(b.dataset.h); });
    const kd = ev => {
      if (ev.key === "ArrowLeft" || ev.key === "1") { ev.preventDefault(); taper("petit"); }
      if (ev.key === "ArrowRight" || ev.key === "2") { ev.preventDefault(); taper("grand"); }
    };
    document.addEventListener("keydown", kd);
    actif = { arreter() { fini = true; timers.forEach(clearTimeout); document.removeEventListener("keydown", kd); } };
    montrer();
  }

  // ---------------------------------------------------------------- 4. Course au rocher chaud
  async function course(box, ctx) {
    const e = ctx.etat();
    const zone = entete(box, "Course au rocher chaud", "Philibert court jusqu'au rocher chaud. Saute par-dessus les crabes et les noix de coco (Espace, ↑, clic ou doigt). Les rayons de soleil le réchauffent : plus il a chaud, plus il court vite. L'ombre des nuages le refroidit.");
    let partie;
    try { partie = await api2("debut", { jeu: "course" }); } catch (x) { zone.innerHTML = `<p class="phb-dit">${esc(x.message)}</p>`; return; }
    zone.innerHTML = `<div class="phb-jeu-infos"><span>Rayons : <b data-score>0</b></span><span>Temps : <b data-temps>30</b> s</span><span data-msg aria-live="polite"></span></div>
      <canvas class="phb-canevas course" tabindex="0" aria-label="Course : appuie sur Espace ou flèche haut pour sauter"></canvas>`;
    const cv = zone.querySelector("canvas"), g = cv.getContext("2d");
    // tirage reproductible à partir de la graine du serveur (mulberry32)
    let graine = partie.graine >>> 0;
    const alea = () => { graine = (graine + 0x6D2B79F5) >>> 0; let t = graine; t = Math.imul(t ^ (t >>> 15), t | 1); t ^= t + Math.imul(t ^ (t >>> 7), t | 61); return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
    const image = svg => { const i = new Image(); i.src = "data:image/svg+xml;charset=utf-8," + encodeURIComponent(svg.replace("<svg ", '<svg xmlns="http://www.w3.org/2000/svg" ')); return i; };
    const pose = j => image(D.svg({ stade: e.stade, variante: e.variante, humeur: "joyeux", portes: e.portes, label: "", jambes: j }));
    const IMG = [pose({ av: -20, arl: -20, ar: 18, avl: 18, gar: -28, gavl: -28 }), pose({ av: 18, arl: 18, ar: -20, avl: -20, gav: -28, garl: -28 }),
      pose({ av: 24, ar: 26, avl: 24, arl: 26, gav: -40, gar: -40, gavl: -40, garl: -40 })];
    let W = 0, Hh = 0;
    function taille() {
      const dpr = window.devicePixelRatio || 1;
      W = cv.clientWidth; Hh = cv.clientHeight;
      cv.width = Math.round(W * dpr); cv.height = Math.round(Hh * dpr);
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
    }
    taille();
    const BUT = 5600, LIMITE = 30;
    // parcours : obstacles, rayons et ombres de nuages répartis sur la distance
    const obstacles = [], rayons = [], ombres = [];
    for (let x = 700; x < BUT - 500; x += 380 + alea() * 420) obstacles.push({ x, type: alea() < .6 ? "crabe" : "coco", touche: false });
    for (let x = 420; x < BUT - 300; x += 170 + alea() * 260) rayons.push({ x, h: alea() < .45 ? 95 : 30, pris: false });
    for (let x = 1300; x < BUT - 700; x += 1100 + alea() * 900) ombres.push({ x, l: 260 + alea() * 200 });
    let dist = 0, chaleur = Math.max(20, Math.min(100, e.jauges.chaleur)), score = 0, temps = 0, compte = 3, dernier = 0, fini = false, arrive = false;
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
      const ciel = g.createLinearGradient(0, 0, 0, Hh);
      ciel.addColorStop(0, "#7fcaf2"); ciel.addColorStop(.5, "#cfefff"); ciel.addColorStop(.52, "#3fd0d4"); ciel.addColorStop(.64, "#1aa4bd");
      ciel.addColorStop(.65, "#f1d79a"); ciel.addColorStop(1, "#e2c27c");
      g.fillStyle = ciel; g.fillRect(0, 0, W, Hh);
      // vagues qui défilent lentement (profondeur)
      g.strokeStyle = "rgba(255,255,255,.45)"; g.lineWidth = 2;
      for (let r = 0; r < 2; r++) { g.beginPath(); for (let x = -40; x < W + 40; x += 40) { const xx = x - (dist * (.15 + r * .1)) % 40; g.moveTo(xx, Hh * (.56 + r * .04)); g.quadraticCurveTo(xx + 10, Hh * (.55 + r * .04), xx + 20, Hh * (.56 + r * .04)); } g.stroke(); }
      // palmiers lointains
      for (let i = 0; i < 4; i++) {
        const x = ((i * 380 - dist * .3) % (W + 380) + W + 380) % (W + 380) - 120;
        g.strokeStyle = "#8a5a2b"; g.lineWidth = 6; g.beginPath(); g.moveTo(x, sol + 4); g.quadraticCurveTo(x - 6, sol - 60, x - 18, sol - 100); g.stroke();
        g.fillStyle = "#3f9a46"; for (let k = 0; k < 5; k++) { g.beginPath(); g.ellipse(x - 18 + Math.cos(k * 1.3) * 22, sol - 104 + Math.sin(k * 1.3) * 6, 26, 8, k * .7, 0, Math.PI * 2); g.fill(); }
      }
      // sable : petites stries qui défilent
      g.strokeStyle = "rgba(150,110,50,.25)"; g.lineWidth = 2;
      for (let x = -60; x < W + 60; x += 60) { const xx = x - dist % 60; g.beginPath(); g.moveTo(xx, sol + 18); g.lineTo(xx + 18, sol + 18); g.stroke(); }
      // ombres de nuages
      for (const o of ombres) {
        const ox = px + (o.x - dist);
        if (ox + o.l < -50 || ox > W + 50) continue;
        g.fillStyle = "rgba(40,60,80,.22)"; g.beginPath(); g.ellipse(ox + o.l / 2, sol + 6, o.l / 2, 12, 0, 0, Math.PI * 2); g.fill();
        g.fillStyle = "rgba(255,255,255,.92)"; for (const [dx, dy, r] of [[.25, 0, 26], [.5, -10, 34], [.75, 0, 26]]) { g.beginPath(); g.arc(ox + o.l * dx, 40 + dy, r, 0, Math.PI * 2); g.fill(); }
      }
      // rocher chaud (arrivée)
      const rx = px + (BUT - dist) + 40;
      if (rx < W + 200) {
        g.fillStyle = "#a79a8e"; g.beginPath(); g.ellipse(rx + 60, sol + 2, 80, 46, 0, Math.PI, 0); g.fill();
        g.strokeStyle = "rgba(255,159,67,.7)"; g.lineWidth = 3;
        for (let k = 0; k < 3; k++) { g.beginPath(); g.moveTo(rx + 30 + k * 30, sol - 52); g.quadraticCurveTo(rx + 36 + k * 30, sol - 62, rx + 30 + k * 30, sol - 72); g.stroke(); }
      }
      // rayons de soleil
      for (const r of rayons) {
        if (r.pris) continue;
        const x = px + (r.x - dist); if (x < -30 || x > W + 30) continue;
        const yy = sol - r.h - 20;
        g.fillStyle = "rgba(255,210,60,.3)"; g.beginPath(); g.arc(x, yy, 14, 0, Math.PI * 2); g.fill();
        g.fillStyle = "#ffc83d"; g.beginPath(); g.arc(x, yy, 7, 0, Math.PI * 2); g.fill();
        g.strokeStyle = "#ffb020"; g.lineWidth = 2;
        for (let k = 0; k < 8; k++) { const a = k * Math.PI / 4 + temps * 2; g.beginPath(); g.moveTo(x + Math.cos(a) * 9, yy + Math.sin(a) * 9); g.lineTo(x + Math.cos(a) * 13, yy + Math.sin(a) * 13); g.stroke(); }
      }
      // obstacles
      for (const o of obstacles) {
        const x = px + (o.x - dist); if (x < -40 || x > W + 40) continue;
        if (o.type === "crabe") {
          const b = Math.sin(temps * 14 + o.x) * 2;
          g.fillStyle = "#ff6a3d"; g.beginPath(); g.ellipse(x, sol - 10 + b, 15, 9, 0, 0, Math.PI * 2); g.fill();
          g.strokeStyle = "#b9381f"; g.lineWidth = 2.4;
          for (const s of [-1, 1]) { g.beginPath(); g.moveTo(x + s * 10, sol - 6 + b); g.lineTo(x + s * 17, sol + 1); g.stroke(); g.beginPath(); g.arc(x + s * 14, sol - 20 + b, 4, 0, Math.PI * 2); g.stroke(); }
          g.fillStyle = "#fff"; g.beginPath(); g.arc(x - 4, sol - 20 + b, 2.6, 0, 7); g.arc(x + 4, sol - 20 + b, 2.6, 0, 7); g.fill();
          g.fillStyle = "#222"; g.beginPath(); g.arc(x - 4, sol - 20 + b, 1.1, 0, 7); g.arc(x + 4, sol - 20 + b, 1.1, 0, 7); g.fill();
        } else {
          g.fillStyle = "#7a5530"; g.beginPath(); g.arc(x, sol - 12, 13, 0, Math.PI * 2); g.fill();
          g.fillStyle = "#a8835a"; g.beginPath(); g.arc(x - 4, sol - 16, 3, 0, Math.PI * 2); g.fill();
        }
      }
      // Philibert (3 images : deux pas et le saut)
      const im = y < 0 ? IMG[2] : IMG[Math.floor(pas) % 2];
      g.fillStyle = "rgba(0,0,0,.15)"; g.beginPath(); g.ellipse(px, sol + 2, 40 * (1 + y / 300), 5, 0, 0, Math.PI * 2); g.fill();
      if (im.complete) { g.save(); if (trebuche > 0) { g.translate(px, sol + y); g.rotate(-.12); g.translate(-px, -(sol + y)); } g.drawImage(im, px - 56, sol - 50 + y, 112, 56); g.restore(); }
      // barres : progression vers le rocher, chaleur
      g.fillStyle = "rgba(255,255,255,.85)"; g.fillRect(12, 10, W - 24, 10); g.fillStyle = "#0d6470"; g.fillRect(12, 10, (W - 24) * Math.min(1, dist / BUT), 10);
      g.fillStyle = "#a79a8e"; g.beginPath(); g.arc(W - 12, 15, 7, 0, Math.PI * 2); g.fill();
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
        const v = (150 + 105 * chaleur / 100) * (trebuche > 0 ? .45 : 1);
        dist += v * dt;
        pas += dt * v / 34;
        trebuche = Math.max(0, trebuche - dt);
        vy += 1600 * dt; y = Math.min(0, y + vy * dt); if (y === 0) vy = 0;
        chaleur = Math.max(0, chaleur - 1.4 * dt);
        if (ombres.some(o => dist > o.x && dist < o.x + o.l)) chaleur = Math.max(0, chaleur - 14 * dt);
        for (const r of rayons) if (!r.pris && Math.abs(r.x - dist - px) < 26 && Math.abs(-r.h - y) < 42) { r.pris = true; score++; chaleur = Math.min(100, chaleur + 8); son("ding"); }
        for (const o of obstacles) if (!o.touche && Math.abs(o.x - dist) < 22 && y > -26) { o.touche = true; trebuche = .8; score = Math.max(0, score - 1); msg(o.type === "crabe" ? "Oups, un crabe !" : "Aïe, une noix de coco !"); son("non"); }
        if (dist >= BUT) { arrive = true; finPartie(); return; }
        if (temps >= LIMITE) { finPartie(); return; }
      }
      dessiner();
      zone.querySelector("[data-score]").textContent = score;
      zone.querySelector("[data-temps]").textContent = compte > 0 ? "…" : Math.max(0, Math.ceil(LIMITE - temps));
      nxImage(tour);
    }
    async function finPartie() {
      fini = true;
      removeEventListener("resize", taille);
      dessiner();
      msg(arrive ? "Arrivé ! Il s'étale sur le rocher chaud." : "Presque… le rocher était tout proche.");
      let r = null;
      try { r = await api2("fin", { jeton: partie.jeton, score, arrivee: arrive }); } catch (x) { r = { message: x.message }; }
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
