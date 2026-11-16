"use strict";
/* Les trois mini-jeux de Philibert (dans un panneau de son île). Le serveur ouvre la partie (jeton à usage unique),
   tire les côtés et les suites, vérifie la durée et calcule la récompense : la page ne fait qu'afficher.
   1. Pluie de feuilles (30 s) : déplacer Philibert (souris, doigt, flèches) pour attraper feuilles et fleurs ;
      les insectes, il les refuse (−1). Dessin sur un canevas avec nxImage (60 i/s max), en pause onglet caché.
   2. Gauche ou droite ? : deviner de quel côté il tourne la tête (5 manches).
   3. Le hochement : répéter ses suites de petits et grands hochements de tête (mémoire et rythme). */
(() => {
  const D = window.PhilibertDessin;
  let actif = null;          // { arreter() }

  const api2 = (etape, corps) => api("/api/philibert/jeu/" + etape, corps);
  function arreter() { if (actif) { try { actif.arreter(); } catch (x) {} actif = null; } }
  const son = t => window.PhilibertSon && window.PhilibertSon(t);

  function entete(box, titre, aide) {
    box.hidden = false;
    box.innerHTML = `<button class="phb-b phb-fermer-f" data-phb="fermer-feuille" aria-label="Quitter le jeu">✕</button>
      <h3>${esc(titre)}</h3><p class="phb-gris">${aide}</p><div class="phb-jeu"></div>`;
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

  window.PhilibertJeux = {
    lancer(jeu, box, ctx) { arreter(); ({ feuilles, devin, rythme }[jeu] || feuilles)(box, ctx); },
    arreter,
  };
})();
