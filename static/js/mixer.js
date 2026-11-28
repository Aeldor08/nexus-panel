"use strict";
// ===== Son : volume de la source en lecture (dans le lecteur) + mélangeur par application =====
(() => {
  const card = document.createElement("div");
  card.className = "card c-mixer";
  card.style.marginTop = "18px";
  card.innerHTML = `
    <h2>Mélangeur de son <small id="mx-dev"></small></h2>
    <div class="mx-list" id="mx-master"></div>
    <div class="section-title">Applications</div>
    <div class="mx-list" id="mx-apps"></div>
    <p class="hint">Comme le mélangeur de volume de Windows : chaque appli qui joue (ou a joué) du son a sa ligne.
      Le volume d'une appli est relatif au volume général. Une appli n'apparaît qu'après avoir émis un son.</p>`;
  $("tab-media").appendChild(card);

  let state = null, pollStart = 0;

  // ---- Contrôle d'un curseur de volume (un par appli ; partagé par le mélangeur et la carte Média) ----
  // Règles :
  //  1. tenu par le pointeur (ou tout juste modifié) : l'écran garde la valeur de l'utilisateur, jamais celle
  //     du serveur (qui peut dater d'avant le dernier réglage) ;
  //  2. un seul envoi à la fois par appli : pendant qu'il part, seule la DERNIÈRE valeur demandée attend
  //     (les intermédiaires sont abandonnées) → jamais d'envois qui se doublent ni d'ancien volume appliqué après ;
  //  3. après le dernier envoi, la valeur choisie reste affichée jusqu'à ce que le serveur RENVOIE cette valeur
  //     (preuve qu'il a suivi) ; s'il ne l'a toujours pas fait au bout de 2,5 s (réglé ailleurs, échec), il fait foi.
  const CLIENT = Math.random().toString(36).slice(2, 10);   // identifie cette page pour le serveur
  const GAP_MS = 60, ATTENTE_MS = 2500;
  let seq = 0;
  const ctl = {};
  const C = key => ctl[key] || (ctl[key] = { held: false, inflight: false, pending: null, timer: 0, last: 0, value: null, doneAt: 0 });
  const owns = (key, serverPct) => {
    const c = ctl[key];
    if (!c || c.value === null) return false;
    if (c.held || c.inflight || c.pending !== null || c.timer) return true;
    // le serveur a suivi : MÊME valeur, lue par une requête partie APRÈS la confirmation du dernier envoi
    // (une valeur intermédiaire croisée en chemin, lue en retard, ne vaut pas preuve)
    if (serverPct === c.value && pollStart > c.doneAt) return false;
    return performance.now() - c.doneAt < ATTENTE_MS;
  };
  function userVolume(key, pct) {
    const c = C(key);
    c.value = pct; c.pending = pct;
    reflect(key, pct);
    pump(key);
  }
  function pump(key) {
    const c = C(key);
    if (c.inflight || c.pending === null || c.timer) return;
    const wait = GAP_MS - (performance.now() - c.last);
    if (wait > 0) { c.timer = setTimeout(() => { c.timer = 0; pump(key); }, wait); return; }
    const pct = c.pending;
    c.pending = null; c.inflight = true; c.last = performance.now();
    api("/api/audio", { target: key, volume: pct / 100, seq: ++seq, client: CLIENT })
      .catch(e => toast("Son : " + e.message, true))
      .finally(() => {
        c.inflight = false; c.doneAt = performance.now();
        if (c.pending !== null) pump(key);
      });
  }
  // Affiche une valeur sur TOUS les curseurs de cette appli (mélangeur + carte Média)
  function reflect(key, pct) {
    document.querySelectorAll(`.mx-row[data-key="${CSS.escape(key)}"]`).forEach(el => {
      const range = el.querySelector(".mx-range");
      if (Number(range.value) !== pct) range.value = pct;
      el.querySelector(".mx-val").textContent = pct + " %";
      range.style.setProperty("--pct", pct + "%");
      nxNiveau(range, pct, 101, 101, 101);           // volume : pas d'alerte
    });
  }
  // Fin de manipulation, où que le pointeur soit relâché (même hors du curseur)
  const lacher = () => { for (const c of Object.values(ctl)) if (c.held) { c.held = false; c.doneAt = Math.max(c.doneAt, performance.now()); } };
  addEventListener("pointerup", lacher, true);
  addEventListener("pointercancel", lacher, true);
  addEventListener("blur", lacher);

  // ---- Jauges de niveau fluides : lissage audio par requestAnimationFrame ----
  // Montée rapide, descente lente (pas de scintillement) ; affichage par clip-path (repeinture seule, la texture
  // de la jauge n'est jamais étirée) ; la boucle s'arrête d'elle-même quand tout est immobile.
  // Sans animation (prefers-reduced-motion) ou onglet caché : valeur appliquée directement.
  const calm = matchMedia("(prefers-reduced-motion: reduce)");
  const ATTACK_MS = 45, RELEASE_MS = 380;
  const meters = new Map();          // élément <i> -> { cur, target }
  let raf = 0, lastT = 0;
  const draw = (el, v) => { el.style.clipPath = `inset(0 ${(100 - v).toFixed(2)}% 0 0)`; };
  function setLevel(el, v) {
    let m = meters.get(el);
    if (!m) { m = { cur: v, target: v }; meters.set(el, m); draw(el, v); }
    m.target = v;
    if (calm.matches || document.hidden) { m.cur = v; draw(el, v); return; }
    if (!raf) { lastT = performance.now(); raf = 1; nxImage(step); }
  }
  function step(now) {
    const dt = Math.min(100, now - lastT); lastT = now;
    let moving = false;
    for (const [el, m] of meters) {
      if (!el.isConnected) { meters.delete(el); continue; }
      if (m.cur === m.target) continue;
      m.cur += (m.target - m.cur) * (1 - Math.exp(-dt / (m.target > m.cur ? ATTACK_MS : RELEASE_MS)));
      if (Math.abs(m.target - m.cur) < .2) m.cur = m.target; else moving = true;
      draw(el, m.cur);
    }
    if (moving) nxImage(step); else raf = 0;            // 60 images/s maximum (index.html : nxImage)
  }
  // Niveau d'un vumètre : affichage lissé + --valeur / data-niveau pour les profils (même valeur partout)
  function meterLevel(i, peak, muted) {
    const v = muted ? 0 : Math.min(100, Math.sqrt(peak || 0) * 100);
    setLevel(i, v);
    nxNiveau(i.parentElement, Math.round(v), 101, 101, 101);
  }
  // Couper / rétablir le son : envoi direct, puis relecture de l'état
  function sendMute(target, muted) {
    api("/api/audio", { target, muted }).then(() => poll.now()).catch(e => toast("Son : " + e.message, true));
  }

  // ---- Boutons − / + (téléphone) : 5 % par appui, arrondi au multiple de 5 ; appui maintenu = répétition ----
  function brancherPas(b, key, range) {
    const pas = Number(b.dataset.pas);
    const appliquer = () => {
      const cur = Number(range.value);
      const nv = Math.max(0, Math.min(100, pas > 0 ? Math.floor(cur / 5) * 5 + 5 : Math.ceil(cur / 5) * 5 - 5));
      if (nv !== cur) userVolume(key, nv);
    };
    let attente = 0, repete = 0, parPointeur = false;
    const stop = () => { clearTimeout(attente); clearInterval(repete); attente = repete = 0; };
    b.addEventListener("pointerdown", ev => {
      if (ev.button !== 0) return;
      parPointeur = true;
      appliquer();
      stop();
      attente = setTimeout(() => { repete = setInterval(appliquer, 140); }, 420);
    });
    ["pointerup", "pointerleave", "pointercancel"].forEach(n => b.addEventListener(n, stop));
    b.addEventListener("click", () => {                // clavier (Entrée / Espace) ; un toucher est déjà compté
      if (parPointeur) { parPointeur = false; return; }
      appliquer();
    });
    b.addEventListener("contextmenu", ev => ev.preventDefault());   // appui long sur téléphone : pas de menu
  }

  // ---- Une ligne de réglage (créée une fois, puis mise à jour) ----
  function row(container, key, opts) {
    let el = container.querySelector(`[data-key="${CSS.escape(key)}"]`);
    if (!el) {
      el = document.createElement("div");
      el.className = "mx-row" + (opts.master ? " master" : "");
      el.dataset.key = key;
      el.innerHTML = `
        <span class="mx-ico"></span>
        <span class="mx-name"></span>
        <span class="mx-meter" aria-hidden="true"><i></i></span>
        <button class="mx-pas mx-moins" type="button" data-pas="-5" aria-label="Baisser le volume de 5 %">−</button>
        <input type="range" min="0" max="100" step="1" class="mx-range">
        <button class="mx-pas mx-plus" type="button" data-pas="5" aria-label="Monter le volume de 5 %">+</button>
        <span class="mx-val"></span>
        <button class="mx-mute" aria-pressed="false"></button>`;
      const range = el.querySelector(".mx-range");
      range.addEventListener("pointerdown", () => { C(key).held = true; });
      range.addEventListener("input", () => userVolume(key, Number(range.value)));
      el.querySelectorAll(".mx-pas").forEach(b => brancherPas(b, key, range));
      el.querySelector(".mx-mute").addEventListener("click", () => {
        sendMute(key, el.querySelector(".mx-mute").getAttribute("aria-pressed") !== "true");
      });
      container.appendChild(el);
    }
    const ico = el.querySelector(".mx-ico");
    if (ico.dataset.set !== "1") {
      ico.dataset.set = "1";
      if (opts.icon) {
        const img = new Image();
        img.alt = "";
        img.onerror = () => { ico.textContent = opts.letter; ico.classList.add("ph"); };
        img.src = opts.icon;
        ico.appendChild(img);
      } else { ico.textContent = opts.letter; ico.classList.add("ph"); }
    }
    el.querySelector(".mx-name").innerHTML = `${esc(opts.name)}${opts.sub ? `<small>${esc(opts.sub)}</small>` : ""}`;
    const range = el.querySelector(".mx-range");
    range.setAttribute("aria-label", "Volume " + opts.name);
    // Valeur affichée : celle de l'utilisateur tant qu'il manipule (ou que le serveur n'a pas suivi), sinon le serveur
    const server = Math.round(opts.volume * 100);
    const mine = owns(key, server);
    const pct = mine ? ctl[key].value : server;
    if (!mine && ctl[key]) ctl[key].value = null;          // le serveur fait foi à nouveau (ex. réglé ailleurs)
    if (Number(range.value) !== pct) range.value = pct;     // (jamais réécrit s'il n'a pas changé)
    el.querySelector(".mx-val").textContent = pct + " %";
    range.style.setProperty("--pct", pct + "%");
    nxNiveau(range, pct, 101, 101, 101);                    // volume : pas d'alerte
    el.dataset.muted = opts.muted ? "1" : "";
    meterLevel(el.querySelector(".mx-meter i"), opts.peak, opts.muted);
    const mute = el.querySelector(".mx-mute");
    mute.setAttribute("aria-pressed", opts.muted ? "true" : "false");
    mute.textContent = opts.muted ? "🔇" : "🔊";
    mute.title = opts.muted ? "Réactiver le son" : "Couper le son";
    el.classList.toggle("muted", !!opts.muted);
    el.classList.toggle("idle", opts.active === false);
    return el;
  }

  const letter = n => (n.replace(/[^\p{L}\p{N}]/gu, "")[0] || "?").toUpperCase();

  function render() {
    if (!state) return;
    if (!state.available) {
      $("mx-master").innerHTML = `<div class="empty">Contrôle du son indisponible${state.error ? " — " + esc(state.error) : ""}</div>`;
      return;
    }
    const d = state.device;
    $("mx-dev").textContent = d ? d.name : "";
    if (d) row($("mx-master"), "master", { master: true, name: "Volume général", sub: d.name, volume: d.volume,
      muted: d.muted, peak: d.peak, letter: "♪" });
    const list = $("mx-apps"), keys = new Set(state.apps.map(a => a.key));
    const tenu = Object.values(ctl).some(c => c.held);
    list.querySelectorAll(".mx-row, .empty").forEach(r => { if (!keys.has(r.dataset.key) && !(tenu && ctl[r.dataset.key])) r.remove(); });
    state.apps.forEach((a, i) => {
      const el = row(list, a.key, {
        name: a.name, sub: a.sessions > 1 ? `${a.sessions} sessions` : (a.active ? "" : "inactif"),
        volume: a.volume, muted: a.muted, peak: a.peak, active: a.active,
        icon: a.has_icon ? `/api/audio/icon/${encodeURIComponent(a.key)}` : null,
        letter: a.key === "__system__" ? "⚙" : letter(a.name),
      });
      // Ordre du serveur (actives en premier), en ne déplaçant une ligne QUE si elle n'est pas à sa place, et
      // jamais pendant qu'un curseur est tenu : déplacer un élément arrête le glisser en cours dans le navigateur.
      if (!tenu && list.children[i] !== el) list.insertBefore(el, list.children[i] || null);
    });
    if (!state.apps.length && !list.querySelector(".empty")) list.innerHTML = `<div class="empty">Aucune application n'émet de son</div>`;
    // curseur du lecteur : mis à jour à chaque lecture du mélangeur (pas seulement quand la carte Média change),
    // sinon il restait « pas encore dans le mélangeur » plusieurs secondes après le retour du son
    const mb = $("m-body");
    if (mb && mb.dataset.source && $("m-vol")) window.renderMediaVolume({ source: mb.dataset.source });
  }

  // ---- Curseur de volume dans le lecteur (source en cours : Spotify, navigateur…) ----
  function appFor(source) {
    if (!state || !state.apps) return null;
    const low = (source || "").toLowerCase();
    return state.apps.find(a => a.key === low) ||
           state.apps.find(a => a.key !== "__system__" && low.includes(a.key.replace(/\.exe$/, "")));
  }
  window.renderMediaVolume = s => {
    const box = $("m-vol");
    if (!box) return;
    const a = appFor(s.source);
    if (!a) {
      // Windows ne liste une appli qu'une fois son son ouvert (Spotify le referme après une longue pause) : quelques
      // instants au plus, le mélangeur est relu dès que la lecture reprend
      if (box.dataset.key !== "") { box.innerHTML = `<span class="muted m-vol-attente">Volume : apparaît dès que l'appli joue du son</span>`; box.dataset.key = ""; }
      return;
    }
    if (box.dataset.key !== a.key) { box.innerHTML = ""; box.dataset.key = a.key; }
    row(box, a.key, { name: "Volume " + a.name, volume: a.volume, muted: a.muted, peak: a.peak, letter: "♪" });
  };

  // État complet (applis, volumes, muet) : 1 fois par seconde. Niveaux seuls (légers, tous dans une réponse) :
  // 10 fois par seconde, lissés à l'écran.
  const poll = poller(async () => {
    const t = performance.now();                 // instant où la requête PART (voir owns)
    state = await api("/api/audio");
    pollStart = t;
    render();
  }, 1000);
  const pollLevels = poller(async () => {
    const lv = await api("/api/audio/niveaux");
    document.querySelectorAll(".mx-row[data-key]").forEach(r => {
      const peak = r.dataset.key === "master" ? lv.master : lv.apps[r.dataset.key];
      const i = r.querySelector(".mx-meter i");
      if (i && peak != null) meterLevel(i, peak, r.dataset.muted === "1");
    });
  }, 100);
  // Relecture immédiate (la carte Média l'appelle quand une source repasse en lecture)
  window.nxMixer = { relire: () => { if (Tabs.current === "media" && !document.hidden) poll.now(); } };
  // S'ajoute au gestionnaire existant de l'onglet Média (sans le remplacer)
  const prev = Tabs.handlers.media || {};
  Tabs.register("media", {
    show() { prev.show && prev.show(); poll.start(); pollLevels.start(); },
    hide() { prev.hide && prev.hide(); poll.stop(); pollLevels.stop(); },
  });
})();
