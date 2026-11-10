// Usage : coller ce fichier dans la console d'une page du serveur de TEST, puis await testVolume("mixer") ou
// await testVolume("media", { lag: 900, setMin: 200, setMax: 900, drag: 2000 }) ; { externe: true } : volume changé ailleurs.
// Banc d'essai des curseurs de volume (mélangeur + carte Média), dans une iframe du serveur de test.
// AUCUN vrai volume n'est touché : /api/audio et /api/media sont simulés dans la page.
// Le faux serveur est volontairement méchant : état servi en retard (latence de lecture), réponses aux
// réglages lentes et dans le désordre. On glisse 20 % → 40 % (avec un petit retour à 38 %) puis on lâche.
window.testVolume = async (zone, opts = {}) => {
  const w = ms => new Promise(r => setTimeout(r, ms));
  const LAG = opts.lag ?? 600, SETMIN = opts.setMin ?? 20, SETMAX = opts.setMax ?? 300, DRAG = opts.drag ?? 2400;
  const f = document.createElement("iframe");
  f.style.cssText = "position:fixed;left:0;top:0;width:1280px;height:900px;z-index:99999;border:0;opacity:.02";
  document.body.appendChild(f);
  f.src = "/?t=" + Date.now() + "#pc";
  await new Promise(r => f.onload = r);
  const W = f.contentWindow, D = f.contentDocument;
  const o = W.DOMTokenList.prototype.toggle;
  W.DOMTokenList.prototype.toggle = function (t, fl) { if (t === "gamemode") return o.call(this, t, false); return o.call(this, t, fl); };
  D.body.classList.remove("gamemode");
  // ---- faux serveur audio ----
  const vrai = { "spotify.exe": .2, master: .5 }, hist = [];          // hist : [instant, copie de l'état]
  const snap = () => hist.push([performance.now(), { ...vrai }]);
  snap();
  const servi = () => { const t = performance.now() - LAG; let s = hist[0][1]; for (const [ti, st] of hist) if (ti <= t) s = st; return s; };
  const enVol = {}, log = { posts: [], chevauchements: 0, maxEnVol: 0 };
  const realFetch = W.fetch.bind(W);
  const json = (o, ms) => new Promise(r => setTimeout(() => r(new W.Response(JSON.stringify(o), { status: 200, headers: { "Content-Type": "application/json" } })), ms));
  W.fetch = async (url, opt = {}) => {
    const u = String(url);
    if (u.startsWith("/api/audio/niveaux")) return json({ master: .3, apps: { "spotify.exe": .4 } }, 5);
    if (u.startsWith("/api/audio/icon")) return new W.Response("", { status: 404 });
    if (u.startsWith("/api/audio") && opt.method === "POST") {
      const b = JSON.parse(opt.body), k = b.target;
      enVol[k] = (enVol[k] || 0) + 1;
      log.maxEnVol = Math.max(log.maxEnVol, enVol[k]);
      if (enVol[k] > 1) log.chevauchements++;
      const ms = SETMIN + Math.random() * (SETMAX - SETMIN);
      await w(ms);
      if ("volume" in b) vrai[k] = b.volume;
      snap();
      log.posts.push(Math.round(b.volume * 100));
      enVol[k]--;
      return json({ ok: true }, 0);
    }
    if (u.startsWith("/api/audio")) {
      const s = servi();
      return json({ available: true, error: null, device: { name: "Haut-parleurs (test)", volume: s.master, muted: false, peak: .3 },
        apps: [{ key: "spotify.exe", name: "Spotify", volume: s["spotify.exe"], muted: false, peak: .4, active: true, sessions: 1, has_icon: false },
               { key: "discord.exe", name: "Discord", volume: .8, muted: false, peak: 0, active: true, sessions: 1, has_icon: false },
               { key: "__system__", name: "Sons système", volume: 1, muted: false, peak: 0, active: false, sessions: 1, has_icon: false }] }, 25);
    }
    if (u.startsWith("/api/media")) {
      return json({ available: true, sessions: [{ source: "Spotify.exe", app: "Spotify", is_browser: false, status: "playing",
        title: "Essai", artist: "Banc d'essai", album: "", position: 30, duration: 200 }], source: "Spotify.exe", status: "playing",
        title: "Essai", artist: "Banc d'essai", position: 30, duration: 200 }, 25);
    }
    return realFetch(url, opt);
  };
  W.location.hash = "#media";
  // le curseur à tester
  let range = null;
  for (let n = 0; n < 80 && !range; n++) {
    await w(100);
    range = zone === "media" ? D.querySelector('#m-vol .mx-row[data-key="spotify.exe"] .mx-range')
                             : D.querySelector('#mx-apps .mx-row[data-key="spotify.exe"] .mx-range');
  }
  if (!range) { f.remove(); W.fetch = realFetch; return { erreur: "curseur introuvable (" + zone + ")" }; }
  await w(1200);
  const rowEl = range.closest(".mx-row");
  let deplacements = 0;
  const mo = new W.MutationObserver(ms => { for (const m of ms) for (const n of m.removedNodes) if (n === rowEl) deplacements++; });
  mo.observe(rowEl.parentElement, { childList: true });
  // ---- glisser : 20 → 40 %, petit retour à 38 % ----
  const rep = { zone, ecrasePendantGlisser: 0, retoursApresLacher: 0, deplacePendantGlisser: 0 };
  range.dispatchEvent(new W.PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
  const t0 = performance.now();
  let voulu = 20;
  while (performance.now() - t0 < DRAG) {
    const p = (performance.now() - t0) / DRAG;
    voulu = p < .85 ? Math.round(20 + 20 * p / .85) : 38;
    if (Number(range.value) !== voulu) {
      range.value = voulu;
      range.dispatchEvent(new W.Event("input", { bubbles: true }));
    }
    await w(30);
    if (Number(range.value) !== voulu) rep.ecrasePendantGlisser++;     // la page a réécrit le curseur sous le pointeur
  }
  rep.deplacePendantGlisser = deplacements;
  range.dispatchEvent(new W.PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
  const fin = voulu;
  if (opts.externe) setTimeout(() => { vrai["spotify.exe"] = .7; snap(); }, 500);   // réglé ailleurs (autre appareil, Windows)
  // ---- après le lâcher : le curseur ne doit jamais revenir en arrière ----
  const t1 = performance.now();
  while (performance.now() - t1 < (opts.externe ? 5500 : 3500)) {
    await w(50);
    if (!opts.externe && Number(range.value) !== fin) rep.retoursApresLacher++;
  }
  mo.disconnect();
  rep.valeurVoulue = fin;
  rep.affichageFinal = Number(range.value);
  rep.volumeFinalServeur = Math.round(vrai["spotify.exe"] * 100);
  rep.envois = log.posts.length;
  rep.envoisSimultanesMax = log.maxEnVol;
  rep.chevauchements = log.chevauchements;
  rep.ordreEnvois = log.posts.slice(-6).join(" ");
  if (opts.externe) { rep.OK = rep.affichageFinal === 70 && rep.volumeFinalServeur === 70 && rep.ecrasePendantGlisser === 0; f.remove(); return rep; }
  rep.OK = rep.ecrasePendantGlisser === 0 && rep.retoursApresLacher === 0 && rep.deplacePendantGlisser === 0 &&
           rep.volumeFinalServeur === fin && rep.affichageFinal === fin && rep.chevauchements === 0;
  f.remove();
  return rep;
};
