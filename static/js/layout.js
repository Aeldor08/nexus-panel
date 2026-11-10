"use strict";
/* Blocs déplaçables et redimensionnables : LE système de fenêtres du panel (agenda, toutes les catégories,
   et les gestes du mur de souvenirs via nxGesture).

   NxBoard(conteneur, { key, minW, minH, defaults, flux }) :
   - chaque bloc se déplace par sa barre de titre (son <h2>, un [data-drag], ou une poignée ⠿ ajoutée) et se
     redimensionne par la poignée ◢ en bas à droite, à la souris comme au doigt (Pointer Events) ;
   - au clavier : Tab jusqu'à la barre de titre, flèches = déplacer, Maj + flèches = redimensionner ;
   - taille minimale pour rester lisible ; le bloc reste dans la largeur du tableau ;
   - aimant léger : grille de 8 px, bords du tableau et des autres blocs (touche Alt : sans aimant) ;
   - pas de chevauchement accidentel : un bloc posé sur un autre pousse celui-ci vers le bas ;
   - mémorisé sur CET appareil (localStorage), par catégorie, par mode (Terminal / Sentinelle) et par largeur
     (« large » = PC, « étroit » = téléphone) ; verrouillage et réinitialisation ;
   - flux: true : tant que rien n'a été déplacé, la mise en page d'origine (CSS) est gardée ; au premier geste,
     les blocs deviennent libres à l'endroit exact où ils étaient. « Réinitialiser » revient à la mise en page d'origine.
   Les positions sont posées en style « !important » : un profil visuel ne peut pas les annuler.
   Abscisses et largeurs en fraction de la largeur du tableau, ordonnées et hauteurs en pixels. */

const NX_GRID = 8, NX_SNAP = 10, NX_GAP = 16;

/* Geste commun (souris, doigt, stylet) : onMove(dx, dy, ev) pendant le geste, onEnd(moved, ev) à la fin. */
function nxGesture(ev, target, onMove, onEnd) {
  ev.preventDefault();
  const sx = ev.clientX, sy = ev.clientY;
  let moved = false;
  try { target.setPointerCapture(ev.pointerId); } catch (e) {}
  const move = e => {
    const dx = e.clientX - sx, dy = e.clientY - sy;
    if (!moved && Math.abs(dx) + Math.abs(dy) < 3) return;
    moved = true;
    onMove(dx, dy, e);
  };
  const up = e => {
    target.removeEventListener("pointermove", move);
    target.removeEventListener("pointerup", up);
    target.removeEventListener("pointercancel", up);
    if (onEnd) onEnd(moved, e);
  };
  target.addEventListener("pointermove", move);
  target.addEventListener("pointerup", up);
  target.addEventListener("pointercancel", up);
}

/* Aimant : renvoie v aligné sur la cible la plus proche (à NX_SNAP près), sinon sur la grille. */
function nxSnap(v, targets, free) {
  if (free) return v;
  let best = null;
  for (const t of targets) if (Math.abs(t - v) <= NX_SNAP && (best === null || Math.abs(t - v) < Math.abs(best - v))) best = t;
  return best !== null ? best : Math.round(v / NX_GRID) * NX_GRID;
}

const nxMode = () => document.documentElement.dataset.theme || "terminal";

function NxBoard(board, opts) {
  const BASE = "nexus-disposition-" + opts.key;
  const LOCK = BASE + "-verrou";
  const MIN_W = opts.minW || 260, MIN_H = opts.minH || 150;
  const flux = !!opts.flux;
  const panels = opts.panels || [...board.querySelectorAll(":scope > [data-panel]")];
  const cleanup = [];
  let layout = {}, free = !flux, locked = false, z = 10, origin = 0;

  const read = k => { try { return JSON.parse(localStorage.getItem(k)); } catch (e) { return null; } };
  const write = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} };
  // Verrou lu DÈS la création (même onglet caché ou reconstruit en arrière-plan, ex. au changement de profil) ;
  // chaque changement est signalé (« nx-verrou ») pour que le bouton affiche toujours l'état réel.
  const syncLock = () => {
    locked = read(LOCK) === true;
    board.classList.toggle("nx-locked", locked);
    board.dispatchEvent(new CustomEvent("nx-verrou", { bubbles: true }));
  };
  const key = () => BASE + "-" + nxMode();
  const width = () => Math.max(320, board.clientWidth);
  const narrow = () => width() < 760;
  const set = (el, prop, v) => el.style.setProperty(prop, v, "important");
  const STYLE = ["position", "left", "top", "width", "height", "margin", "z-index"];
  const idOf = p => p.dataset.panel;

  // En mode flux : une cale (hauteur des blocs libres) garde le contenu qui suit à sa place, et les conteneurs
  // intermédiaires (grilles) s'effacent (display: contents) pour que les blocs se placent dans le tableau.
  let spacer = null;
  const containers = new Set();
  if (flux) {
    for (const p of panels) for (let a = p.parentElement; a && a !== board; a = a.parentElement) containers.add(a);
    const top = panels[0] && [...board.children].find(ch => ch === panels[0] || ch.contains(panels[0]));
    spacer = document.createElement("div");
    spacer.className = "nx-spacer";
    spacer.setAttribute("aria-hidden", "true");
    board.insertBefore(spacer, top || null);
  }

  function defaults() {
    if (flux) return {};
    const d = narrow() ? opts.defaults.narrow : opts.defaults.wide;
    const out = {};
    let y = 0;
    for (const p of panels) {
      const id = idOf(p), v = d[id];
      if (!v) continue;
      if (narrow()) { out[id] = { x: 0, w: 1, y, h: v.h }; y += v.h + NX_GAP; }   // empilées sur téléphone
      else out[id] = { ...v };
    }
    return out;
  }

  function clamp(id) {
    const W = width(), L = layout[id];
    const wpx = Math.max(Math.min(MIN_W, W), Math.min(W, L.w * W));
    L.w = wpx / W;
    L.x = Math.min(Math.max(0, L.x), 1 - L.w);
    L.h = Math.max(MIN_H, L.h);
    L.y = Math.max(0, L.y);
  }

  // Photo de la mise en page d'origine : chaque bloc devient libre exactement là où il était
  function snapshot() {
    const b = board.getBoundingClientRect(), W = width();
    const top0 = spacer ? spacer.getBoundingClientRect().top : b.top + board.clientTop;
    layout = {};
    for (const p of panels) {
      const r = p.getBoundingClientRect();
      if (!r.width && !r.height) continue;                       // bloc masqué
      layout[idOf(p)] = { x: (r.left - b.left - board.clientLeft) / W, y: Math.max(0, r.top - top0), w: r.width / W, h: r.height };
    }
    free = true;
  }

  function apply() {
    board.classList.toggle("nx-free", free);
    containers.forEach(c => c.classList.toggle("nx-contents", free));
    if (!free) {
      for (const p of panels) STYLE.forEach(s => p.style.removeProperty(s));
      if (spacer) spacer.style.removeProperty("height");
      return;
    }
    if (flux) set(board, "position", "relative");
    const W = width();
    origin = spacer ? spacer.offsetTop : 0;
    let bottom = 0;
    for (const p of panels) {
      const id = idOf(p);
      if (!layout[id]) continue;
      clamp(id);
      const L = layout[id];
      set(p, "position", "absolute");
      set(p, "left", Math.round(L.x * W) + "px");
      set(p, "top", Math.round(origin + L.y) + "px");
      set(p, "width", Math.round(L.w * W) + "px");
      set(p, "height", Math.round(L.h) + "px");
      set(p, "margin", "0");
      bottom = Math.max(bottom, L.y + L.h);
    }
    if (spacer) set(spacer, "height", Math.round(bottom + NX_GAP) + "px");
    else set(board, "height", Math.round(bottom + NX_GAP) + "px");
    setTimeout(ajuster, 0);
  }

  // ajuste: true (pages à valeurs qui bougent : sommaire, PC, Média, Réseau, Statistiques) : un bloc n'a jamais
  // de barre de défilement — s'il est plus petit que son contenu (police d'un profil plus grande, ligne en plus…),
  // il grandit à la taille du contenu et pousse les blocs du dessous. Vérifié à chaque mise en page et chaque seconde.
  // Toutes les autres pages : une barre de défilement seulement s'il y a VRAIMENT quelque chose à faire défiler.
  // Un bloc à qui il ne manque que quelques pixels (marges, coins décorés d'un profil, arrondi de la hauteur
  // enregistrée) grandit d'autant au lieu d'afficher une barre pour rien ; au-delà (longue liste), la barre reste.
  const ajuste = !!opts.ajuste, PETIT = 24;
  if (ajuste) board.classList.add("nx-ajuste");
  function ajuster() {
    if (!free || !board.offsetParent) return;
    const grown = [];
    for (const p of panels) {
      const id = idOf(p), L = layout[id];
      if (!L || p.classList.contains("nx-moving") || p.classList.contains("nx-resizing")) continue;
      const manque = p.scrollHeight - p.clientHeight;
      if (manque > 1 && (ajuste || manque <= PETIT)) { L.h = Math.ceil(L.h + manque); grown.push(id); }
    }
    if (!grown.length) return;
    grown.forEach(pushAway);
    apply(); save();
  }
  const ajusteTimer = setInterval(() => { if (!document.hidden) ajuster(); }, 1000);

  function save() {
    const all = read(key()) || {};
    all[narrow() ? "etroit" : "large"] = layout;
    write(key(), all);
  }

  function load() {
    let saved = read(key());
    if (!saved && opts.ancienneCle) {                          // ancien format (avant les modes) : repris tel quel
      const old = read(opts.ancienneCle);
      if (old && old.panels) saved = { [old.w === "etroit" ? "etroit" : "large"]: old.panels };
    }
    const mine = saved && saved[narrow() ? "etroit" : "large"];
    layout = defaults();
    free = !flux;
    if (flux) apply();                                           // mise en page d'origine, pour la mesurer
    if (mine && typeof mine === "object") {
      if (flux) snapshot();                                      // les blocs nouveaux gardent leur place d'origine
      let fresh = false;
      for (const p of panels) {
        const s = mine[idOf(p)];
        if (s && [s.x, s.y, s.w, s.h].every(Number.isFinite)) layout[idOf(p)] = { ...s };
        else fresh = true;
      }
      if (flux && fresh) placeNew(mine);
      free = true;
    }
    syncLock();
    apply();
  }

  // Bloc apparu depuis la dernière disposition (nouvelle fonction) : posé sous les autres
  function placeNew(mine) {
    let bottom = Math.max(0, ...Object.values(mine).map(s => (s.y || 0) + (s.h || 0)));
    for (const p of panels) {
      const id = idOf(p);
      if (mine[id] || !layout[id]) continue;
      layout[id].y = bottom + NX_GAP; layout[id].x = 0;
      bottom = layout[id].y + layout[id].h;
    }
  }

  // ---- aimant et chevauchements (en pixels) ----
  const rect = id => { const W = width(), L = layout[id]; return { x: L.x * W, y: L.y, w: L.w * W, h: L.h }; };
  function edges(id) {
    const W = width(), xs = [0, W], ys = [0];
    for (const o in layout) if (o !== id) {
      const r = rect(o);
      xs.push(r.x, r.x + r.w, r.x + r.w + NX_GAP, r.x - NX_GAP);
      ys.push(r.y, r.y + r.h, r.y + r.h + NX_GAP, r.y - NX_GAP);
    }
    return { xs, ys };
  }
  const overlap = (a, b) => a.x < b.x + b.w - 1 && b.x < a.x + a.w - 1 && a.y < b.y + b.h - 1 && b.y < a.y + a.h - 1;
  function pushAway(fixedId) {
    for (let iter = 0; iter < 60; iter++) {
      let changed = false;
      const order = [fixedId, ...Object.keys(layout).filter(i => i !== fixedId).sort((a, b) => layout[a].y - layout[b].y)];
      for (let i = 0; i < order.length; i++) for (let j = i + 1; j < order.length; j++) {
        const a = rect(order[i]), b = rect(order[j]);
        if (overlap(a, b)) { layout[order[j]].y = a.y + a.h + NX_GAP; changed = true; }
      }
      if (!changed) break;
    }
  }

  function ensureFree() {
    if (!lastW && board.clientWidth) { lastW = board.clientWidth; load(); }   // 1re mise en page pas encore faite
    if (!free) { snapshot(); apply(); }
  }

  // ---- glisser / redimensionner ----
  function startGesture(ev, p, kind) {
    if (locked || ev.button > 0) return;
    if (kind === "move" && ev.target.closest("button, input, select, textarea, a, label, [contenteditable]")) return;
    ensureFree();
    const id = idOf(p);
    if (!layout[id]) return;
    const W = width(), L = { ...layout[id] }, E = edges(id);
    p.style.setProperty("z-index", String(++z), "important");
    p.classList.add(kind === "move" ? "nx-moving" : "nx-resizing");
    nxGesture(ev, ev.currentTarget, (dx, dy, e) => {
      const off = e.altKey;
      if (kind === "move") {
        let x = L.x * W + dx, y = L.y + dy;
        const xr = nxSnap(x + L.w * W, E.xs, off) - L.w * W, xl = nxSnap(x, E.xs, off);
        x = Math.abs(xl - x) <= Math.abs(xr - x) ? xl : xr;
        const yb = nxSnap(y + L.h, E.ys, off) - L.h, yt = nxSnap(y, E.ys, off);
        y = Math.abs(yt - y) <= Math.abs(yb - y) ? yt : yb;
        layout[id].x = x / W; layout[id].y = y;
      } else {
        layout[id].w = (nxSnap(L.x * W + L.w * W + dx, E.xs, off) - L.x * W) / W;
        layout[id].h = nxSnap(L.y + L.h + dy, E.ys, off) - L.y;
      }
      apply();
    }, () => {
      p.classList.remove("nx-moving", "nx-resizing");
      clamp(id); pushAway(id); apply(); save();
      dispatchEvent(new Event("resize"));      // les canevas éventuels se redessinent
    });
  }

  // ---- clavier : flèches = déplacer, Maj + flèches = redimensionner ----
  let keyTimer = null;
  function onKey(ev, p) {
    const dir = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
    if (!dir || locked || ev.target !== ev.currentTarget) return;
    ev.preventDefault();
    ensureFree();
    const id = idOf(p), W = width(), step = ev.ctrlKey ? 1 : NX_GRID * 2;
    if (!layout[id]) return;
    if (ev.shiftKey) { layout[id].w += dir[0] * step / W; layout[id].h += dir[1] * step; }
    else { layout[id].x += dir[0] * step / W; layout[id].y += dir[1] * step; }
    clamp(id); pushAway(id); apply();
    clearTimeout(keyTimer);
    keyTimer = setTimeout(() => { save(); dispatchEvent(new Event("resize")); }, 300);
  }

  for (const p of panels) {
    p.classList.add("nx-panel");
    let handle = p.querySelector(":scope > [data-drag]") || p.querySelector(":scope > h2");
    if (!handle) {                                            // bloc sans titre : petite poignée ⠿
      handle = document.createElement("div");
      handle.className = "nx-grip";
      handle.textContent = "⠿";
      p.prepend(handle);
    }
    handle.classList.add("nx-drag");
    if (!handle.hasAttribute("tabindex")) handle.tabIndex = 0;
    const title = (handle.textContent || "").trim().split("\n")[0].slice(0, 40) || "bloc";
    handle.setAttribute("aria-label", `${title} — flèches : déplacer, Maj + flèches : redimensionner`);
    handle.title = "Glisser pour déplacer · flèches du clavier : déplacer, Maj + flèches : redimensionner";
    const down = ev => startGesture(ev, p, "move"), key = ev => onKey(ev, p);
    handle.addEventListener("pointerdown", down);
    handle.addEventListener("keydown", key);
    const rs = document.createElement("span");
    rs.className = "nx-rs";
    rs.title = "Redimensionner";
    rs.setAttribute("aria-hidden", "true");
    rs.addEventListener("pointerdown", ev => startGesture(ev, p, "resize"));
    p.appendChild(rs);
    const front = () => { if (free) p.style.setProperty("z-index", String(++z), "important"); };
    p.addEventListener("pointerdown", front, true);
    cleanup.push(() => {
      handle.removeEventListener("pointerdown", down); handle.removeEventListener("keydown", key);
      p.removeEventListener("pointerdown", front, true);
      handle.classList.remove("nx-drag"); handle.removeAttribute("aria-label"); handle.removeAttribute("title");
      if (handle.classList.contains("nx-grip")) handle.remove();
      rs.remove(); p.classList.remove("nx-panel", "nx-moving", "nx-resizing");
    });
  }

  // Onglet caché au démarrage (largeur 0) : la disposition est calculée à la 1re vraie largeur
  let lastW = 0;
  const ro = new ResizeObserver(() => {
    const W = board.clientWidth;
    if (!W || Math.abs(W - lastW) < 2) return;
    const first = !lastW, wasNarrow = lastW < 760, isNarrow = W < 760;
    lastW = W;
    if (first || wasNarrow !== isNarrow) load(); else apply();
  });
  ro.observe(board);
  // Changement de mode (Terminal / Sentinelle) : chaque mode a sa propre disposition
  const mo = new MutationObserver(() => { if (board.clientWidth) load(); });
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });

  syncLock();
  if (board.clientWidth) { lastW = board.clientWidth; load(); }
  return {
    reset() {
      try { localStorage.removeItem(key()); if (opts.ancienneCle) localStorage.removeItem(opts.ancienneCle); } catch (e) {}
      layout = defaults(); free = !flux; apply();
      dispatchEvent(new Event("resize"));
    },
    setLocked(v) { write(LOCK, !!v); syncLock(); },
    get locked() { return locked; },
    get free() { return free; },
    get panels() { return panels; },
    layout: () => JSON.parse(JSON.stringify(layout)),
    refresh: apply,
    destroy() {
      ro.disconnect(); mo.disconnect(); clearInterval(ajusteTimer); board.classList.remove("nx-ajuste");
      cleanup.forEach(f => f());
      for (const p of panels) STYLE.forEach(s => p.style.removeProperty(s));
      containers.forEach(c => c.classList.remove("nx-contents"));
      board.classList.remove("nx-free", "nx-locked");
      if (flux) board.style.removeProperty("position");
      if (spacer) spacer.remove();
    },
  };
}

/* Barre « Verrouillé / Déverrouillé · Réinitialiser la disposition » d'une catégorie (une seule version, partout).
   Le bouton affiche l'ÉTAT actuel de la mise en page (cadenas fermé ou ouvert, couleur propre à chaque état) ;
   un clic bascule. aria-pressed = vrai quand la mise en page est verrouillée. */
function NxTools(bar, getBoard, label) {
  bar.classList.add("nx-tools");
  bar.innerHTML = `
    <button class="btn nx-verrou" data-nx="lock" aria-pressed="false"></button>
    <button class="btn" data-nx="reset" title="Remet les blocs à leur place et taille d'origine (sur cet appareil, dans ce mode)">↺ Réinitialiser la disposition</button>
    <span class="muted nx-hint"></span>`;
  const lock = bar.querySelector('[data-nx="lock"]'), hint = bar.querySelector(".nx-hint");
  const show = () => {
    const b = getBoard();
    const on = !!(b && b.locked);
    lock.textContent = on ? "🔒 Verrouillé" : "🔓 Déverrouillé";
    lock.dataset.etat = on ? "verrouille" : "deverrouille";
    lock.setAttribute("aria-pressed", on);
    lock.setAttribute("aria-label", on ? "Mise en page verrouillée : cliquer pour la déverrouiller" : "Mise en page déverrouillée : cliquer pour la verrouiller");
    lock.title = on ? "Mise en page verrouillée : aucun déplacement ni redimensionnement. Clic : déverrouiller"
                    : "Mise en page déverrouillée : les blocs se déplacent et se redimensionnent. Clic : verrouiller";
    hint.textContent = on ? "Mise en page verrouillée : clique sur « 🔒 Verrouillé » pour la modifier."
                          : "Glisse un bloc par son titre, agrandis-le avec le coin ◢ · clavier : flèches, Maj + flèches.";
  };
  bar.addEventListener("click", e => {
    const b = getBoard(), a = e.target.closest("[data-nx]");
    if (!a || !b) return;
    if (a.dataset.nx === "lock") { b.setLocked(!b.locked); show(); }
    else { b.reset(); toast(`Disposition ${label} réinitialisée (sur cet appareil, mode ${nxMode() === "terminal" ? "Terminal" : "Sentinelle"}).`); }
  });
  document.addEventListener("nx-verrou", () => { if (bar.isConnected) show(); });   // état réel, toujours
  show();
  return { show };
}
