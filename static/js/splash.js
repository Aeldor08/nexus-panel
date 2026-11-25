const NX_RGB = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const NEON = NX_RGB("--neon-rgb") || "0, 255, 156", MAG = NX_RGB("--mag-rgb") || "255, 43, 214",
      NEON3 = NX_RGB("--neon3-rgb") || "200, 255, 225", BG_RGB = NX_RGB("--splash-rgb") || "2, 1, 6";
"use strict";
// ===== Page de garde NEXUS =====
// boot : logo tracé, titre brouillé, vraies vérifications
// ready : attend un clic sur NEXUS (logo ou titre) — Entrée / Espace marchent aussi
// off   : veille après IDLE_MS sans activité (écran CRT qui s'éteint) ; rallumage au moindre mouvement
// dive  : plongée dans le code au clic sur NEXUS, puis le panel apparaît
(() => {
  const sp = $("splash");
  if (!sp) return;
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const IDLE_MS = 45000;                    // durée sans activité avant la mise en veille
  const MIN_BOOT = reduce ? 600 : 2400;
  const GLYPHS = "!<>-_\\/[]{}=+*^?#%&$01ABCDEFXZ";
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  // État lisible par les profils visuels (CSS seulement) : <body data-etat="…">
  //   intro (démarrage complet) · reconnexion (retour rapide par le logo) · pret (attend le clic sur NEXUS)
  //   veille · transition (après le clic sur NEXUS) · panel (page de garde fermée)
  const ETATS = { boot: "intro", ready: "pret", off: "veille", dive: "transition", gone: "panel" };
  let quickBoot = false;
  const setState = s => {
    sp.dataset.state = s;
    document.body.dataset.etat = s === "boot" && quickBoot ? "reconnexion" : (ETATS[s] || s);
  };
  const state = () => sp.dataset.state;
  let runId = 0, fast = false, idleTimer = null, clockTimer = null, wakeGuardUntil = 0;
  window.NexusCover = true;                 // (le secours de index.html sait que le script tourne)

  // ---------------------------------------------------------------- titre brouillé
  function scramble(el, text, delay, step = 140) {
    el.classList.remove("locked");
    el.innerHTML = [...text].map(() => `<span class="ch scr"> </span>`).join("");
    const chars = [...el.querySelectorAll(".ch")];
    return new Promise(done => {
      const t0 = performance.now() + delay;
      const frame = now => {
        let locked = 0;
        chars.forEach((c, i) => {
          const lockAt = t0 + 260 + i * step;
          if (now >= lockAt || fast) { if (c.classList.contains("scr")) { c.textContent = text[i]; c.classList.remove("scr"); } locked++; }
          else if (now >= t0) c.textContent = GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
        });
        if (locked < chars.length) nxImage(frame);
        else { el.classList.add("locked"); done(); }
      };
      nxImage(frame);
    });
  }
  async function type(el, html, speed = 22) {
    const tmp = document.createElement("div"); tmp.innerHTML = html;
    const plain = tmp.textContent;
    for (let i = 1; i <= plain.length && !fast; i++) {
      el.innerHTML = esc(plain.slice(0, i)).replace(/\/\//g, "<b>//</b>") + `<span class="cur">&nbsp;</span>`;
      await sleep(speed);
    }
    el.innerHTML = html;
  }

  // ---------------------------------------------------------------- vérifications réelles
  const withTimeout = (p, ms) => Promise.race([p, sleep(ms).then(() => { throw new Error("délai"); })]);
  function checks() {
    const stats = withTimeout(api("/api/stats"), 2500);
    return [
      ["Noyau", withTimeout(api("/api/version"), 2000).then(v => [`NEXUS v${v.version}`, "ok"])],
      ["Processeur", stats.then(s => [`${s.cpu.physical_cores} cœurs / ${s.cpu.logical_cores} threads`, "ok"])],
      ["Mémoire", stats.then(s => [`${fmtBytes(s.ram.total)} · ${Math.round(s.ram.percent)} % utilisés`, "ok"])],
      ["Carte graphique", stats.then(s => s.gpu.available ? [s.gpu.devices[0].name, "ok"] : ["absente", "warn"])],
      ["Capteurs (LHM)", stats.then(s => s.lhm.available ? [`en ligne · CPU ${Math.round(s.cpu.temperature ?? 0)}°C`, "ok"] : ["hors ligne", "warn"])],
      ["Sortie audio", withTimeout(api("/api/audio"), 2500).then(a => a.device ? [a.device.name, "ok"] : ["indisponible", "warn"])],
      ["Réseau", withTimeout(api("/api/net"), 2500).then(n => {
        const cf = n.targets.find(t => t.key === "cloudflare");
        return cf && cf.last != null ? [`en ligne · ping ${Math.round(cf.last)} ms`, "ok"] : ["mesure en cours", "dim"];
      })],
      ["Mode jeu", stats.then(s => s.gamemode && s.gamemode.in_game ? [`ACTIF · ${gameLabel(s.gamemode.game)}`, "ok"] : ["en veille", "dim"])],
    ];
  }
  const TAG = { ok: " OK ", warn: "WARN", err: "FAIL", dim: " -- " };
  const logLine = (name, value, cls) => {
    $("sp-log").innerHTML += `<span class="${cls}">[${TAG[cls] || " -- "}]</span> ${esc(name)} <span class="dim">${".".repeat(Math.max(2, 20 - name.length))}</span> ${esc(value)}\n`;
  };

  function restartLogoAnimations() {
    sp.querySelectorAll(".sp-logo, .sp-logo *").forEach(e => { e.style.animation = "none"; void e.getBoundingClientRect(); e.style.animation = ""; });
  }

  // ---------------------------------------------------------------- démarrage
  // Animations déclarées par le profil visuel actif (profil.json → "animations"), lues via js/profiles.js
  async function profileAnim(maxWait = 1500) {
    const id = document.documentElement.dataset.profile;
    if (!id) return null;
    const t0 = performance.now();
    while (performance.now() - t0 < maxWait) {
      const p = window.nexusProfile;
      if (p !== undefined) return p && p.id === id ? (p.animations || null) : null;
      await sleep(50);
    }
    return null;
  }

  // ⚙ Réglages → « Jouer l'intro animée des profils » (par appareil) : décoché, la page de garde
  // démarre comme une reconnexion (état « reconnexion », pas d'attente) : aucun profil ne joue son intro.
  const profileIntroOff = () => { try { return localStorage.getItem("nexus-intro-profils") === "0"; } catch (e) { return false; } };

  async function boot(quick) {
    const id = ++runId;
    fast = !!quick;
    quickBoot = !!quick || (!!document.documentElement.dataset.profile && profileIntroOff());
    setState("boot");
    homeReady = false;
    setTimeout(prepareHome, 600);              // dès que la page de garde est affichée
    document.body.classList.add("sp-lock");
    $("sp-log").innerHTML = `<span class="dim">NEXUS BIOS 2.077 — ${quick ? "reconnexion" : "séquence de démarrage"}</span>\n`;
    $("sp-bar").style.width = "0";
    $("sp-tag").textContent = "";
    restartLogoAnimations();
    const t0 = performance.now();
    scramble($("sp-title"), "NEXUS", quick || reduce ? 0 : 450, quick ? 60 : 140);
    const list = checks();
    let version = "";
    list[0][1].then(([v]) => { version = v.replace("NEXUS ", ""); }).catch(() => {});
    sleep(quick || reduce ? 300 : 1100).then(() => type($("sp-tag"), `Centre de contrôle <b>//</b> ${esc(version || "v—")} <b>//</b> Neural link`));
    if (!quick) await sleep(reduce ? 0 : 700);
    for (let i = 0; i < list.length; i++) {
      if (id !== runId || state() === "dive" || state() === "gone") return;
      let res;
      try { res = await list[i][1]; } catch (e) { res = ["délai dépassé", "warn"]; }
      logLine(list[i][0], res[0], res[1]);
      $("sp-bar").style.width = ((i + 1) / list.length * 100) + "%";
      if (!fast) await sleep(reduce ? 0 : 150);
    }
    if (!fast) {
      // Intro d'un profil : la page de garde reste au moins sa durée (un clic ou une touche la passe)
      const anim = quick || reduce || profileIntroOff() ? null : await profileAnim();
      const total = Math.max(MIN_BOOT, (anim && anim.intro_ms) || 0);
      while (!fast && performance.now() - t0 < total && id === runId && state() === "boot") await sleep(100);
    }
    if (id !== runId || state() !== "boot") return;
    $("sp-log").innerHTML += `<span class="ok">&gt; accès autorisé — clique sur NEXUS pour te connecter.</span>\n`;
    ready();
  }

  // ---------------------------------------------------------------- prêt / veille
  function ready() {
    setState("ready");
    armIdle();
  }
  function armIdle() {
    clearTimeout(idleTimer);
    idleTimer = setTimeout(() => { if (state() === "ready") powerOff(); }, IDLE_MS);
  }
  function standbyClock() {
    $("sp-sb-clock").textContent = new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }
  function powerOff() {
    clearTimeout(idleTimer);
    sp.classList.remove("powering-on");
    setState("off");
    standbyClock();
    clearInterval(clockTimer);
    clockTimer = setInterval(standbyClock, 10000);
  }
  function powerOn() {
    clearInterval(clockTimer);
    wakeGuardUntil = performance.now() + 500;   // le clic qui rallume n'entre pas dans le panel
    sp.classList.add("powering-on");
    restartLogoAnimations();
    setState("ready");
    setTimeout(() => sp.classList.remove("powering-on"), 950);
    armIdle();
  }

  // ---------------------------------------------------------------- plongée : pluie de code (« matrice »)
  // Chronologie (DIVE_MS = 4 s) :
  //   0 → 0,9 s   fondu enchaîné : la page de garde recule et floute, la pluie apparaît par-dessus
  //   0,9 → 3 s   pluie de code sur 3 profondeurs ; le mot NEXUS se forme dans la pluie (dès 1,2 s)
  //   3 → 4 s     ouverture : un trou aux bords doux s'agrandit depuis le centre et dévoile le sommaire
  const DIVE_MS = 4000, FADE_IN = .9 / 4, REVEAL_AT = 3 / 4;
  const ease = x => x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2;   // easeInOutCubic
  const KANA = "ｦｱｳｴｵｶｷｹｺｻｼｽｾｿﾀﾂﾃﾅﾆﾇﾈﾊﾋﾎﾏﾐﾑﾒﾓﾔﾕﾗﾘﾜ0123456789ABCDEF:=+*<>";
  const glyph = () => KANA[Math.floor(Math.random() * KANA.length)];

  function dive() {
    return new Promise(resolve => {
      const view = $("sp-dive"), vctx = view.getContext("2d");
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      const W = innerWidth, H = innerHeight;
      view.width = W * dpr; view.height = H * dpr;
      vctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      // La pluie est dessinée sur un calque à part (traînées), puis composée sur l'écran
      const rain = document.createElement("canvas");
      rain.width = W * dpr; rain.height = H * dpr;
      const ctx = rain.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.fillStyle = `rgb(${BG_RGB})`; ctx.fillRect(0, 0, W, H);

      // Le recul de la page de garde part du logo
      const lr = sp.querySelector(".sp-logo").getBoundingClientRect();
      $("sp-screen").style.transformOrigin = `${lr.left + lr.width / 2}px ${lr.top + lr.height / 2}px`;

      // 3 profondeurs : loin (petit, lent, magenta pâle), milieu (cyan), près (grand, rapide, cyan vif)
      const LAYERS = [
        { size: 11, speed: [9, 16], color: `rgba(${MAG},.55)`, head: "rgba(255,170,240,.8)" },
        { size: 16, speed: [13, 22], color: `rgba(${NEON},.75)`, head: `rgba(${NEON3},.95)` },
        { size: 24, speed: [16, 28], color: `rgb(${NEON})`, head: "#ffffff" },
      ];
      const cols = [];
      LAYERS.forEach((L, li) => {
        const n = Math.ceil(W / L.size);
        for (let i = 0; i < n; i++) {
          if (li === 0 || Math.random() < (li === 1 ? .7 : .45)) {
            cols.push({ L, x: i * L.size + L.size / 2, row: -Math.random() * (H / L.size) * .8,
                        speed: L.speed[0] + Math.random() * (L.speed[1] - L.speed[0]), last: -1 });
          }
        }
      });

      // Masque du mot NEXUS (cellules de la grille « près » qui tombent dans les lettres)
      const mask = document.createElement("canvas");
      mask.width = W; mask.height = H;
      const mctx = mask.getContext("2d");
      const fs = Math.min(W * .19, H * .34);
      mctx.font = `700 ${fs}px Bahnschrift, "Arial Narrow", sans-serif`;
      mctx.textAlign = "center"; mctx.textBaseline = "middle";
      mctx.fillStyle = "#fff";
      mctx.fillText("NEXUS", W / 2, H / 2);
      const md = mctx.getImageData(0, 0, W, H).data;
      const CELL = 14, wordCells = [];
      for (let y = CELL / 2; y < H; y += CELL)
        for (let x = CELL / 2; x < W; x += CELL)
          if (md[(Math.floor(y) * W + Math.floor(x)) * 4 + 3] > 128) wordCells.push([x, y]);

      const start = performance.now();
      let last = start, revealed = false;
      const maxR = Math.hypot(W, H) / 2 + 80;

      const frame = now => {
        const t = Math.min(1, (now - start) / DIVE_MS);
        const dt = Math.min(.05, (now - last) / 1000);
        last = now;

        // Traînées : voile sombre proportionnel au temps écoulé (même rendu à 60 ou 144 Hz)
        ctx.fillStyle = `rgba(${BG_RGB},${1 - Math.pow(.935, dt * 60)})`;
        ctx.fillRect(0, 0, W, H);
        ctx.textAlign = "center"; ctx.textBaseline = "top";

        // Colonnes de code
        const slow = t > REVEAL_AT ? 1 - .6 * ease((t - REVEAL_AT) / (1 - REVEAL_AT)) : 1;   // ralentit à la fin
        for (const c of cols) {
          c.row += c.speed * dt * slow;
          const r = Math.floor(c.row);
          if (r !== c.last) {
            ctx.font = `${c.L.size}px "MS Gothic", Consolas, monospace`;
            if (c.last >= 0) { ctx.fillStyle = Math.random() < .05 ? "#fcee0a" : c.L.color; ctx.fillText(glyph(), c.x, c.last * c.L.size); }
            ctx.fillStyle = c.L.head;
            ctx.fillText(glyph(), c.x, r * c.L.size);
            c.last = r;
          }
          if (c.row * c.L.size > H + 40 && Math.random() < .08) { c.row = -Math.random() * 12; c.last = -1; }
        }

        // Le mot NEXUS se forme dans la pluie (1,2 s → 3 s), puis s'estompe pendant l'ouverture
        const wIn = Math.min(1, Math.max(0, (t - .3) / .35));
        const wOut = t > REVEAL_AT ? 1 - ease((t - REVEAL_AT) / (1 - REVEAL_AT)) : 1;
        const w = wIn * wOut;
        if (w > 0 && wordCells.length) {
          ctx.font = `700 ${CELL + 2}px "MS Gothic", Consolas, monospace`;
          ctx.textBaseline = "middle";
          const n = Math.floor(wordCells.length * .09 * w) + 1;
          for (let k = 0; k < n; k++) {
            const [x, y] = wordCells[Math.floor(Math.random() * wordCells.length)];
            ctx.fillStyle = Math.random() < .25 ? `rgba(255,255,255,${w})` : `rgba(${NEON},${w})`;
            ctx.fillText(glyph(), x, y);
          }
        }

        // Composition à l'écran : fond toujours opaque, la pluie apparaît en fondu…
        vctx.globalCompositeOperation = "source-over";
        vctx.globalAlpha = 1;
        vctx.fillStyle = `rgb(${BG_RGB})`; vctx.fillRect(0, 0, W, H);
        vctx.globalAlpha = ease(Math.min(1, t / FADE_IN));
        vctx.drawImage(rain, 0, 0, W, H);
        // Lueur du mot (halo doux au centre pendant qu'il est visible)
        if (w > 0) {
          const g = vctx.createRadialGradient(W / 2, H / 2, 0, W / 2, H / 2, fs * 1.6);
          g.addColorStop(0, `rgba(${NEON},${.10 * w})`); g.addColorStop(1, `rgba(${NEON},0)`);
          vctx.fillStyle = g; vctx.fillRect(0, 0, W, H);
        }
        vctx.globalAlpha = 1;

        // …et ouverture finale : un trou aux bords doux s'agrandit et dévoile le sommaire
        if (t > REVEAL_AT) {
          if (!revealed) { revealed = true; cascadeHome(); }
          const p = ease((t - REVEAL_AT) / (1 - REVEAL_AT));
          const r = p * maxR, soft = 140;
          vctx.globalCompositeOperation = "destination-out";
          const hole = vctx.createRadialGradient(W / 2, H / 2, Math.max(0, r - soft), W / 2, H / 2, r + 1);
          hole.addColorStop(0, "rgba(0,0,0,1)"); hole.addColorStop(1, "rgba(0,0,0,0)");
          vctx.fillStyle = hole;
          vctx.beginPath(); vctx.arc(W / 2, H / 2, r + 1, 0, Math.PI * 2); vctx.fill();
          if (r > soft) { vctx.beginPath(); vctx.arc(W / 2, H / 2, Math.max(0, r - soft), 0, Math.PI * 2); vctx.fill(); }
          // Anneau néon sur le bord de l'ouverture
          vctx.globalCompositeOperation = "source-over";
          vctx.strokeStyle = `rgba(${NEON},${.55 * (1 - p)})`;
          vctx.lineWidth = 2; vctx.shadowColor = `rgb(${NEON})`; vctx.shadowBlur = 18;
          vctx.beginPath(); vctx.arc(W / 2, H / 2, Math.max(1, r - soft * .5), 0, Math.PI * 2); vctx.stroke();
          vctx.shadowBlur = 0;
        }

        if (t < 1) nxImage(frame);
        else resolve();
      };
      nxImage(frame);
    });
  }

  // Les tuiles du sommaire apparaissent en cascade pendant l'ouverture
  function cascadeHome() {
    document.querySelectorAll("#tab-accueil .home-hero, #tab-accueil .home-tile").forEach((el, i) => {
      el.classList.remove("cascade"); void el.offsetWidth;
      el.style.animationDelay = (i * 70) + "ms";
      el.classList.add("cascade");
      setTimeout(() => { el.classList.remove("cascade"); el.style.animationDelay = ""; }, 1400 + i * 70);
    });
  }

  async function enter() {
    if (state() === "dive" || state() === "gone") return;
    clearTimeout(idleTimer); clearInterval(clockTimer);
    runId++;                                     // arrête un démarrage en cours
    try { sessionStorage.setItem("nexus-intro", "1"); } catch (e) {}
    if (location.hash.slice(1).split("/")[0] !== "accueil") location.hash = "#accueil";
    if (reduce) {                                // animations réduites : simple fondu
      setState("dive");
      sp.classList.add("sp-fade");
      cascadeHome();
      await sleep(450);
      finish();
      return;
    }
    // Transition d'un profil : le profil anime (CSS), le panel garde la minuterie et la navigation.
    // Fin en CHEVAUCHEMENT : vers 60 % de l'animation, la page de garde s'efface en fondu (ease-in-out) pendant
    // que le sommaire, déjà prêt dessous, se révèle en cascade. Puis l'état « arrivee » dure encore un instant
    // sur le sommaire (les profils y prolongent leur effet : feuilles, souffle chaud, étoiles…).
    const p = window.nexusProfile, anim = p && p.id === document.documentElement.dataset.profile ? p.animations : null;
    if (anim && anim.remplace_transition) {
      const ms = Math.min(5000, Math.max(300, anim.transition_ms || 2000));
      // Fin de transition : « fondu » (simple), « cercle » (ouverture en rond depuis le logo, comme la pluie de
      // code du thème par défaut) ou « tele » (vieille télé qui s'allume). Réglages peut imposer l'une d'elles.
      // Le cercle part plus tôt (45 %) et s'ouvre lentement : il disperse l'animation du profil, encore en cours.
      const ouv = ouverture(anim.ouverture);
      const fadeAt = Math.round(ms * (ouv === "cercle" ? .45 : .6));
      const fadeMs = ouv === "tele" ? TELE_MS : ouv === "cercle" ? Math.max(1100, ms - fadeAt + 650) : ms - fadeAt + 350;
      sp.dataset.transition = "profil";
      setState("dive");                          // (le verrou de défilement reste jusqu'à la fin : pas de bande à droite)
      setTimeout(() => {
        if (state() !== "dive") return;
        sp.style.setProperty("--sp-fondu", fadeMs + "ms");
        if (ouv === "cercle") iris(fadeMs);
        else if (ouv === "tele") tele();
        else sp.classList.add("sp-fondu");
        document.body.dataset.etat = "arrivee";
        cascadeHome();
      }, fadeAt);
      await sleep(fadeAt + fadeMs);
      finish();
      document.body.dataset.etat = "arrivee";
      setTimeout(() => { if (document.body.dataset.etat === "arrivee") document.body.dataset.etat = "panel"; }, 1100);
      return;
    }
    setState("dive");
    await dive();
    finish();
  }
  // ---- Fins de transition des profils ----
  const TELE_MS = 1150;
  const ouverture = choix => {
    if (document.body.classList.contains("gamemode")) return "fondu";   // animations coupées : pas d'écran noir figé
    // choix de ⚙ Réglages, retenu PAR PROFIL visuel (nexus-ouverture-profils = { id: choix }) ; à défaut,
    // l'ancien réglage commun (nexus-ouverture, avant 3.21) ; sinon celui du profil (profil.json)
    let pref = null;
    try {
      const id = document.documentElement.dataset.profile || "";
      const map = JSON.parse(localStorage.getItem("nexus-ouverture-profils") || "{}") || {};
      pref = Object.prototype.hasOwnProperty.call(map, id) ? map[id] : localStorage.getItem("nexus-ouverture");
    } catch (e) {}
    const v = pref === "cercle" || pref === "tele" || pref === "fondu" ? pref : choix;
    return v === "cercle" || v === "tele" ? v : "fondu";
  };
  // Ouverture en rond : un trou aux bords doux part du logo et s'agrandit (masque CSS animé, propriété --sp-r),
  // un anneau lumineux aux couleurs du profil (--sp-anneau) suit le bord ; l'animation du profil continue autour.
  function iris(dur) {
    const lr = sp.querySelector(".sp-logo, .sp-enter").getBoundingClientRect();
    const cx = lr.left + lr.width / 2, cy = lr.top + lr.height / 2;
    sp.style.setProperty("--sp-ix", Math.round(cx) + "px");
    sp.style.setProperty("--sp-iy", Math.round(cy) + "px");
    // rayon final = coin le plus éloigné du logo + bord doux : l'ouverture utilise toute sa durée, sans temps mort
    const far = Math.max(...[[0, 0], [innerWidth, 0], [0, innerHeight], [innerWidth, innerHeight]].map(([x, y]) => Math.hypot(x - cx, y - cy)));
    sp.style.setProperty("--sp-rmax", Math.round(far + 190) + "px");
    const ring = document.createElement("div");
    ring.className = "sp-anneau";
    sp.appendChild(ring);
    sp.classList.add("sp-iris");
    setTimeout(() => ring.remove(), dur + 100);
  }
  // Vieille télé qui s'allume : l'écran passe au noir, une ligne lumineuse s'étire au milieu, l'image s'ouvre
  // verticalement dans un éclair, puis se stabilise sur le sommaire (transform et opacity seulement).
  function tele() {
    const o = document.createElement("div");
    o.className = "sp-tele";
    o.setAttribute("aria-hidden", "true");
    o.innerHTML = '<i class="h"></i><i class="b"></i><i class="ligne"></i><i class="eclair"></i>';
    const teinte = getComputedStyle(sp).getPropertyValue("--sp-anneau").trim();   // lueur aux couleurs du profil
    if (teinte) o.style.setProperty("--sp-anneau", teinte);
    document.body.appendChild(o);
    setTimeout(() => sp.classList.add("sp-cache"), 260);          // la page de garde disparaît sous le noir
    setTimeout(() => o.remove(), TELE_MS + 150);
  }
  function finish() {
    setState("gone");
    document.body.classList.remove("sp-lock");
    sp.classList.remove("sp-fade", "sp-fondu", "sp-iris", "sp-cache");
    ["--sp-fondu", "--sp-ix", "--sp-iy", "--sp-rmax"].forEach(v => sp.style.removeProperty(v));
    sp.querySelectorAll(".sp-anneau").forEach(e => e.remove());
    delete sp.dataset.transition;
    $("sp-screen").style.transformOrigin = "";
  }

  // Sommaire préparé à l'avance (sous la page de garde) : ses données et ses images sont prêtes au clic
  let homeReady = false;
  function prepareHome() {
    if (homeReady || state() === "gone") return;
    homeReady = true;
    if (location.hash.slice(1).split("/")[0] !== "accueil") location.hash = "#accueil";
  }

  // ---------------------------------------------------------------- page de garde depuis le panel
  function showCover() {
    if (state() !== "gone") return;
    sp.classList.add("powering-on");
    setTimeout(() => sp.classList.remove("powering-on"), 950);
    boot(true);
  }

  // ---------------------------------------------------------------- événements
  ["pointerenter", "focus", "touchstart"].forEach(t => $("sp-enter").addEventListener(t, prepareHome, { passive: true }));
  $("sp-enter").addEventListener("click", ev => {
    ev.stopPropagation();
    if (performance.now() < wakeGuardUntil) return;
    if (state() === "boot" || state() === "ready") enter();
  });
  sp.addEventListener("click", () => { if (state() === "boot") fast = true; });   // clic ailleurs : accélère
  const activity = ev => {
    if (state() === "off") { if (ev.type !== "mousemove" || Math.abs(ev.movementX) + Math.abs(ev.movementY) > 2) powerOn(); return; }
    if (state() === "ready") armIdle();
  };
  ["mousemove", "mousedown", "wheel", "touchstart"].forEach(t => sp.addEventListener(t, activity, { passive: true }));
  document.addEventListener("keydown", ev => {
    if (state() === "gone" || state() === "dive") return;
    if (state() === "off") { powerOn(); ev.preventDefault(); return; }
    if ((ev.key === "Enter" || ev.key === " ") && state() !== "dive") { ev.preventDefault(); enter(); return; }
    if (state() === "boot") fast = true;
    armIdle();
  }, true);
  // Logo NEXUS de l'en-tête : retour à la page de garde
  const hdr = document.querySelector("h1 .home-link");
  if (hdr) {
    hdr.title = "Page de garde NEXUS";
    hdr.addEventListener("click", ev => { ev.preventDefault(); showCover(); });
  }
  window.replayIntro = () => { if (state() === "gone") { sp.classList.add("powering-on"); setTimeout(() => sp.classList.remove("powering-on"), 950); boot(false); } };
  window.nexusCover = { boot, ready, powerOff, powerOn, enter, showCover, state };   // (tests)

  if (state() !== "gone") boot(false); else setState("gone");
})();
