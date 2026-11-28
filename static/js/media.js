"use strict";
// ===== Onglet Média : Spotify, YouTube (navigateur) et tout lecteur compatible Windows =====
(() => {
  const root = $("tab-media");
  root.innerHTML = `
    <div class="card c-media">
      <h2>Lecture en cours <small id="m-sub"></small></h2>
      <div id="m-body"></div>
    </div>
    <div class="section-title" id="m-others-title" hidden>Autres sources</div>
    <div class="sessions" id="m-sessions"></div>
    <p class="hint">Fonctionne avec Spotify, Deezer, Apple Music, Tidal, VLC… ; dans tous les navigateurs (Opera GX, Chrome,
      Edge, Firefox, Brave, Vivaldi, Arc…) avec YouTube, Deezer, SoundCloud, Twitch… ; et tout lecteur qui apparaît dans le
      panneau multimédia de Windows (touches média du clavier). Lancez une lecture et elle s'affiche ici.</p>`;

  let state = null, selected = null, lastCoverKey = {};

  const coverUrl = s => s.cover ? `/api/media/cover?source=${encodeURIComponent(s.source)}&v=${s.cover}` : null;
  const appClass = s => s.app === "Spotify" || s.site === "Spotify" ? "spotify" : s.app === "Deezer" || s.site === "Deezer" ? "deezer"
    : s.is_browser ? "browser" : "";

  function pick() {
    if (!state || !state.sessions.length) return null;
    return state.sessions.find(s => s.source === selected) || state.sessions[0];
  }

  function renderMain() {
    const body = $("m-body");
    const s = pick();
    if (!state || !state.available) {
      body.innerHTML = `<div class="empty">Contrôles multimédias Windows indisponibles${state && state.error ? " — " + esc(state.error) : ""}</div>`;
      return;
    }
    if (!s) {
      $("m-sub").textContent = "";
      body.innerHTML = `<div class="empty">Rien en lecture. Lancez Spotify ou une vidéo YouTube.</div>`;
      return;
    }
    $("m-sub").textContent = s.status === "playing" ? "▶ en lecture" : s.status === "paused" ? "❚❚ en pause" : s.status;
    // Construction unique du lecteur, puis mises à jour ciblées (évite de recharger l'image)
    if (!$("m-title") || body.dataset.source !== s.source) {
      body.dataset.source = s.source;
      body.innerHTML = `
        <div class="player">
          <div class="cover" id="m-cover"><span class="ph">♪</span></div>
          <div>
            <span class="track-app" id="m-app"></span>
            <div class="track-title" id="m-title"></div>
            <div class="track-artist" id="m-artist"></div>
            <div class="progress">
              <div class="bar" id="m-bar" role="slider" aria-label="Position de lecture" tabindex="0"><i id="m-fill"></i></div>
              <div class="times"><span id="m-pos"></span><span id="m-dur"></span></div>
            </div>
            <div class="controls">
              <button class="ctl" id="m-prev" aria-label="Précédent">⏮</button>
              <button class="ctl main" id="m-play" aria-label="Lecture / pause">▶</button>
              <button class="ctl" id="m-next" aria-label="Suivant">⏭</button>
            </div>
            <div class="m-vol" id="m-vol"></div>
          </div>
        </div>`;
      lastCoverKey[s.source] = null;
      $("m-prev").onclick = () => control("prev");
      $("m-next").onclick = () => control("next");
      $("m-play").onclick = () => control("toggle");
      $("m-bar").onclick = ev => {
        const cur = pick();
        if (!cur || !cur.can_seek) return;
        const r = $("m-bar").getBoundingClientRect();
        control("seek", Math.max(0, Math.min(1, (ev.clientX - r.left) / r.width)) * cur.duration);
      };
      $("m-bar").onkeydown = ev => {
        const cur = pick();
        if (!cur || !cur.can_seek) return;
        if (ev.key === "ArrowRight") control("seek", Math.min(cur.duration, posNow(cur) + 10));
        if (ev.key === "ArrowLeft") control("seek", Math.max(0, posNow(cur) - 10));
      };
    }
    const app = $("m-app");
    app.textContent = s.app + (s.is_browser ? (s.site ? " · " + s.site : " · navigateur") : "");
    app.className = "track-app " + appClass(s);
    $("m-title").textContent = s.title || "Sans titre";
    $("m-artist").textContent = [s.artist, s.album].filter(Boolean).join(" — ");
    const url = coverUrl(s);
    if (lastCoverKey[s.source] !== url) {
      lastCoverKey[s.source] = url;
      const box = $("m-cover");
      box.classList.remove("square");
      // Image entière (jamais rognée) par-dessus une copie floutée qui remplit le cadre
      box.innerHTML = url ? `<img class="bg" src="${url}" alt="" aria-hidden="true"><img class="fg" src="${url}" alt="">`
                          : `<span class="ph">♪</span>`;
      const fg = box.querySelector("img.fg");
      if (fg) fg.onload = () => box.classList.toggle("square", Math.abs(fg.naturalWidth / fg.naturalHeight - 1) < .15);
    }
    $("m-cover").classList.toggle("glow", s.status === "playing");
    $("m-body").classList.toggle("m-attente", !!(attente && attente.source === s.source));   // ⏭ / ⏮ : en attente de la piste
    const pos = posNow(s), pct = s.duration ? pos / s.duration * 100 : 0;
    $("m-fill").style.width = pct + "%";
    nxNiveau($("m-bar"), pct, 101, 101, 101);                        // progression : toujours « bas » (pas d'alerte)
    $("m-bar").classList.toggle("noseek", !s.can_seek);
    $("m-bar").setAttribute("aria-valuenow", Math.round(pct));
    $("m-pos").textContent = s.duration ? fmtDur(pos) : "";
    $("m-dur").textContent = s.duration ? fmtDur(s.duration) : "";
    $("m-play").textContent = s.status === "playing" ? "❚❚" : "▶";
    $("m-play").disabled = !s.can_play_pause;
    $("m-prev").disabled = !s.can_prev;
    $("m-next").disabled = !s.can_next;
    if (window.renderMediaVolume) window.renderMediaVolume(s);   // curseur de volume (mixer.js)
  }

  function renderOthers() {
    const s = pick();
    const others = state && state.sessions.length > 1 ? state.sessions : [];
    $("m-others-title").hidden = !others.length;
    $("m-sessions").innerHTML = others.map(o => {
      const url = coverUrl(o);
      return `<button class="session${s && o.source === s.source ? " sel" : ""}" data-src="${esc(o.source)}">
        ${url ? `<img src="${url}" alt="">` : `<span class="mini-ph"></span>`}
        <span class="meta"><div>${esc(o.title || "Sans titre")}</div>
        <div><small>${esc(o.app)} · ${o.status === "playing" ? "▶ en lecture" : "en pause"}</small></div></span></button>`;
    }).join("");
  }
  $("m-sessions").addEventListener("click", ev => {
    const b = ev.target.closest(".session");
    if (b) { selected = b.dataset.src; renderMain(); renderOthers(); }
  });

  // Mini-lecteur dans la barre d'onglets (visible sur tous les onglets)
  function renderNowPlaying() {
    const np = $("np");
    const s = state && state.sessions.find(x => x.status === "playing");
    np.hidden = !s;
    if (s) np.innerHTML = `<span class="eq">♪</span><span class="t">${esc(s.title)}${s.artist ? " — " + esc(s.artist) : ""}</span>`;
  }
  $("np").addEventListener("click", () => { location.hash = "#media"; });

  // ---- Réactivité ----
  // 1. Le serveur répond DÈS QUE l'état visible change (piste, lecture / pause, source) : /api/media?sig=…&attendre=…
  //    (sinon au bout de 3 s dans l'onglet, 15 s ailleurs, pour recaler la position).
  // 2. Entre deux réponses, la position avance ici (extrapolée), la barre de progression reste fluide.
  // 3. Les boutons réagissent au clic, sans attendre l'application : ⏯ bascule tout de suite ; ⏭ / ⏮ estompent
  //    le titre jusqu'à l'arrivée de la nouvelle piste. L'état réel remplace l'affichage dès qu'il arrive.
  let sig = "", fetchedAt = 0, attente = null;                  // attente : { source, title, until } après ⏭ / ⏮
  // voulu : { source, status, until } après ⏯. L'appli met quelques centaines de ms à basculer : une lecture faite
  // entre-temps (encore l'ancien état) ne doit pas refaire basculer le bouton (aller-retour ❚❚ → ▶ → ❚❚).
  // On garde l'état demandé jusqu'à ce que le serveur le confirme, 2,5 s au plus (refus, autre appareil…).
  let voulu = null;
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const posNow = s => !s ? 0 : s.status !== "playing" ? s.position
    : Math.min(s.duration || Infinity, s.position + (performance.now() - fetchedAt) / 1000);

  async function control(action, position) {
    const s = pick();
    if (!s) return;
    if (action === "toggle") {
      s.position = posNow(s); fetchedAt = performance.now(); s.status = s.status === "playing" ? "paused" : "playing";
      voulu = { source: s.source, status: s.status, until: performance.now() + 2500 };
      if (s.status === "playing" && window.nxMixer) setTimeout(() => window.nxMixer.relire(), 400);   // volume de l'appli
    }
    else if (action === "seek") { s.position = position; fetchedAt = performance.now(); }
    else attente = { source: s.source, title: s.title, until: performance.now() + 3000 };
    renderMain(); renderNowPlaying();
    try {
      const r = await api("/api/media/control", { source: s.source, action, position });
      if (!r.ok) { toast("Commande refusée par l'application", true); attente = null; voulu = null; }
    } catch (e) { toast("Erreur : " + e.message, true); attente = null; voulu = null; }
    refresh(0).catch(() => {});                                   // état réel tout de suite
  }

  function apply(st) {
    const avant = state;
    state = st; sig = st.sig || ""; fetchedAt = performance.now();
    if (voulu) {
      const s = state.sessions.find(x => x.source === voulu.source);
      if (!s || s.status === voulu.status || performance.now() > voulu.until) voulu = null;   // confirmé (ou abandon)
      else s.status = voulu.status;                                // pas encore suivi : on garde l'état demandé
    }
    // une source qui (re)passe en lecture : son volume peut apparaître dans le mélangeur, on le relit sans attendre
    if (window.nxMixer && state.sessions.some(x => x.status === "playing" &&
        !(avant && avant.sessions.some(y => y.source === x.source && y.status === "playing")))) window.nxMixer.relire();
    window.mediaState = state;        // réutilisé par le sommaire
    if (selected && !state.sessions.some(s => s.source === selected)) selected = null;
    if (attente) {
      const s = state.sessions.find(x => x.source === attente.source);
      if (!s || s.title !== attente.title || performance.now() > attente.until) attente = null;
    }
    renderNowPlaying();
    if (Tabs.current === "media") { renderMain(); renderOthers(); }
  }
  async function refresh(attendre = 0) {
    apply(await api(`/api/media?sig=${encodeURIComponent(attendre ? sig : "")}&attendre=${attendre}`));
  }
  // une seule boucle d'écoute, en continu (en pause quand la page est cachée)
  (async function ecoute() {
    for (;;) {
      if (document.hidden) { await sleep(800); continue; }
      const t0 = performance.now(), avant = sig;
      try {
        await refresh(Tabs.current === "media" ? 3 : 15);
        // réponse immédiate SANS changement (serveur qui n'attend pas, ex. pas encore redémarré) : pas de rafale
        if (sig === avant && performance.now() - t0 < 400) await sleep(1000);
      } catch (e) { await sleep(2000); }
    }
  })();
  // position et temps qui avancent entre deux réponses (onglet Média seulement)
  setInterval(() => {
    if (Tabs.current !== "media" || document.hidden || !$("m-fill")) return;
    const s = pick();
    if (!s || s.status !== "playing" || !s.duration) return;
    const p = posNow(s), pct = p / s.duration * 100;
    $("m-fill").style.width = pct + "%";
    $("m-pos").textContent = fmtDur(p);
    $("m-bar").setAttribute("aria-valuenow", Math.round(pct));
  }, 250);
  Tabs.register("media", { show() { refresh(0).catch(() => {}); }, hide() {} });
})();
