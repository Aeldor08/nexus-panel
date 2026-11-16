"use strict";
/* Mur libre des Souvenirs, PAR JOUR : photos et notes façon post-it, déplaçables (glisser), redimensionnables
   (coin ◢), empilables (le dernier touché passe devant), à la souris, au doigt et au clavier (Tab jusqu'à la
   poignée ⠿ : flèches = déplacer, Maj + flèches = redimensionner). Les éléments PEUVENT se superposer.
   La disposition est enregistrée sur le serveur (souvenirs.py, table souvenir_disposition), en unités d'un mur
   de 1000 de large : le même mur s'affiche sur le PC et, réduit (sans descendre sous 55 %), sur le téléphone.
   « Annuler » revient en arrière dans les changements de disposition du jour (tant que la page est ouverte). */
function SvWall(host, hooks) {
  // (même liste que souvenirs.py : NOTE_COLORS, NOTE_INKS, NOTE_FONTS)
  const COLORS = [["jaune", "Jaune"], ["rose", "Rose"], ["vert", "Vert"], ["bleu", "Bleu"], ["violet", "Violet"], ["peche", "Pêche"],
                  ["menthe", "Menthe"], ["ciel", "Ciel"], ["lavande", "Lavande"], ["corail", "Corail"], ["sable", "Sable"], ["blanc", "Blanc"],
                  ["kraft", "Kraft"], ["ardoise", "Ardoise"], ["nuit", "Nuit"], ["bordeaux", "Bordeaux"]];
  const INKS = [["auto", "Automatique (selon le fond)"], ["noir", "Noir"], ["sepia", "Sépia"], ["marine", "Bleu marine"], ["bordeaux", "Bordeaux"],
                ["foret", "Vert forêt"], ["violet", "Violet"], ["blanc", "Blanc"], ["or", "Or"]];
  const FONTS = [["theme", "Police du thème"], ["titre", "Titres du thème"], ["sans", "Sans empattement"], ["serif", "Avec empattement"],
                 ["manuscrite", "Manuscrite"], ["plume", "Plume"], ["feutre", "Feutre"], ["machine", "Machine à écrire"], ["elegante", "Élégante"]];
  let palId = null;                                    // note dont la palette (fond + écriture) est ouverte
  const MIN_SCALE = .55, STEP = 10;
  let data = null, scale = 1, saveTimer = null, keyUndo = false;
  const undo = {};                                     // jour -> pile de dispositions précédentes
  host.innerHTML = `<div class="sv-stage" id="sv-stage"><div class="sv-canvas" id="sv-canvas"></div></div>
    <div class="empty sv-empty" id="sv-empty" hidden>Pas encore de photo ni de note ce jour-là. Ajoute des photos avec le cadre
      « Ajouter des photos », ou une note avec « ＋ Ajouter une note ».</div>`;
  const stage = host.querySelector(".sv-stage"), canvas = host.querySelector(".sv-canvas");
  const D = () => data.disposition;
  const copy = o => JSON.parse(JSON.stringify(o));
  const fmtShort = s => new Date(s + "T12:00").toLocaleDateString("fr-FR", { day: "numeric", month: "short" });

  // ---- échelle : le mur garde ses proportions ----
  function rescale() {
    if (!data) return;
    const W = data.largeur_mur;
    scale = Math.max(MIN_SCALE, host.clientWidth / W);
    const bottom = Math.max(380, ...Object.values(D()).map(e => e.y + e.h)) + 40;
    canvas.style.transform = `scale(${scale})`;
    canvas.style.width = W + "px"; canvas.style.height = bottom + "px";
    stage.style.width = Math.round(W * scale) + "px"; stage.style.height = Math.round(bottom * scale) + "px";
  }
  new ResizeObserver(() => rescale()).observe(host);

  function place(el, e) {
    el.style.left = e.x + "px"; el.style.top = e.y + "px";
    el.style.width = e.w + "px"; el.style.height = e.h + "px"; el.style.zIndex = e.z;
  }

  // ---- rendu ----
  const photoHtml = p => `
    <div class="sv-grab" tabindex="0" aria-label="Photo ${esc(p.legende || "")} — glisser ou flèches pour déplacer, Maj + flèches pour redimensionner">⠿</div>
    <button class="sv-open" data-open="${p.id}" aria-label="Agrandir"><img src="${p.miniature}" alt="${esc(p.legende || "Photo du " + p.jour)}" loading="lazy" draggable="false"></button>
    <figcaption>${p.legende ? esc(p.legende) : `<span class="muted">sans légende</span>`}</figcaption>
    <div class="sv-acts"><button class="btn" data-cap="${p.id}" title="Modifier la légende">✎</button>
      <button class="btn" data-move="${p.id}" title="Déplacer vers un autre jour">📅</button>
      <button class="btn danger" data-del="${p.id}" title="Supprimer">🗑</button></div>`;
  // Une note s'affiche en LECTURE (texte seul + petit ✎ en haut à droite) ; ✎ (ou double-clic) passe en ÉDITION :
  // texte modifiable, couleurs, tailles, épingle et suppression ; ✓, Échap, Ctrl + Entrée ou un clic hors de la
  // note la referment (le texte est enregistré pendant l'écriture, et une dernière fois en sortant).
  let editingId = null;
  const noteHtml = n => {
    const ed = n.id === editingId, enc = n.encre || "auto", fon = n.fonte || "theme";
    return `
    <div class="sv-grab" tabindex="0" aria-label="Note — glisser ou flèches pour déplacer, Maj + flèches pour redimensionner">⠿
      ${n.jour !== data.jour ? `<span class="sv-pinfrom" title="Note épinglée : elle se répète chaque jour depuis le ${fmtShort(n.jour)}">📌 depuis le ${fmtShort(n.jour)}</span>` : ""}</div>
    <button class="sv-nedit" data-nedit="${n.id}" title="Modifier la note" aria-label="Modifier la note">✎</button>
    <textarea class="sv-ntext" data-ntext="${n.id}" maxlength="2000" placeholder="Écris ta note…" aria-label="Texte de la note"
      style="font-size:${n.police}px"${ed ? "" : " readonly"}>${esc(n.texte)}</textarea>
    <div class="sv-nbar">
    <div class="sv-npal"${n.id === palId ? "" : " hidden"} role="group" aria-label="Couleurs de la note">
        <small>Fond</small>
        <span class="sv-colors">${COLORS.map(([k, label]) =>
          `<button class="sv-dot c-${k}${k === n.couleur ? " on" : ""}" data-ncolor="${k}" data-nid="${n.id}" title="${label}" aria-label="Fond ${label}" aria-pressed="${k === n.couleur}"></button>`).join("")}</span>
        <small>Écriture</small>
        <span class="sv-colors">${INKS.map(([k, label]) =>
          `<button class="sv-dot sv-ink e-${k}${k === enc ? " on" : ""}" data-nink="${k}" data-nid="${n.id}" title="${label}" aria-label="Écriture ${label}" aria-pressed="${k === enc}">${k === "auto" ? "A" : ""}</button>`).join("")}</span>
      </div>
      <button class="btn sv-ndone" data-ndone="${n.id}" title="Terminer (Échap)" aria-label="Terminer la modification">✓</button>
      <button class="btn${n.id === palId ? " on" : ""}" data-npal="${n.id}" aria-expanded="${n.id === palId}" title="Couleurs du fond et de l'écriture" aria-label="Couleurs">🎨</button>
      <select class="in sv-nfont f-${fon}" data-nfonte="${n.id}" title="Police" aria-label="Police de la note">${FONTS.map(([k, label]) =>
        `<option value="${k}" class="f-${k}"${k === fon ? " selected" : ""}>${label}</option>`).join("")}</select>
      <button class="btn" data-nfont="-2" data-nid="${n.id}" title="Texte plus petit" aria-label="Texte plus petit">A−</button>
      <button class="btn" data-nfont="2" data-nid="${n.id}" title="Texte plus grand" aria-label="Texte plus grand">A+</button>
      <button class="btn${n.epinglee ? " on" : ""}" data-npin="${n.id}" aria-pressed="${n.epinglee}"
        title="${n.epinglee ? "Épinglée : elle se répète sur les jours suivants (clic pour la garder seulement sur son jour)" : "Épingler : la note se répète sur les jours suivants"}">📌</button>
      <button class="btn danger" data-ndel="${n.id}" title="Supprimer la note" aria-label="Supprimer la note">🗑</button>
    </div>`;
  };

  function render() {
    const photos = new Map(data.photos.map(p => ["p:" + p.id, p]));
    const notes = new Map(data.notes.map(n => ["n:" + n.id, n]));
    canvas.innerHTML = "";
    for (const [eid, e] of Object.entries(D())) {
      const isPhoto = eid.startsWith("p:"), item = isPhoto ? photos.get(eid) : notes.get(eid);
      if (!item) continue;
      const el = document.createElement(isPhoto ? "figure" : "div");
      el.className = isPhoto ? "sv-item sv-photo"
        : `sv-item sv-note c-${item.couleur} e-${item.encre || "auto"} f-${item.fonte || "theme"}${item.id === editingId ? " sv-editing" : ""}`;
      el.dataset.el = eid;
      el.innerHTML = isPhoto ? photoHtml(item) : noteHtml(item);
      const rs = document.createElement("span");
      rs.className = "nx-rs sv-rs"; rs.title = "Redimensionner"; rs.setAttribute("aria-hidden", "true");
      el.appendChild(rs);
      place(el, e);
      canvas.appendChild(el);
    }
    host.querySelector(".sv-empty").hidden = !!(data.photos.length || data.notes.length);
    rescale();
    hooks.onRender(data);
  }

  // ---- enregistrement et annulation ----
  function pushUndo() {
    const s = undo[data.jour] || (undo[data.jour] = []);
    s.push(copy(D()));
    if (s.length > 30) s.shift();
    hooks.onUndo(true);
  }
  async function saveLayout(elements) {
    try { data = await api(`/api/souvenirs/disposition/${data.jour}`, { elements }, "PUT"); }
    catch (e) { toast("Mur : " + e.message, true); }
  }
  const maxZ = () => Math.max(0, ...Object.values(D()).map(e => e.z));

  // ---- gestes (souris, doigt) ----
  let dragged = false;
  canvas.addEventListener("pointerdown", ev => {
    const item = ev.target.closest(".sv-item");
    if (!item || ev.button > 0) return;
    const rs = ev.target.closest(".sv-rs"), grab = ev.target.closest(".sv-grab");
    const fromImg = ev.target.closest(".sv-open") && ev.pointerType === "mouse";    // à la souris, la photo se glisse aussi
    if (!rs && !grab && !fromImg) return;
    const eid = item.dataset.el, L = D()[eid], start = copy(L), before = copy(D());
    const lim = data.limites;
    item.classList.add(rs ? "nx-resizing" : "nx-moving");
    L.z = maxZ() + 1; place(item, L);
    dragged = false;
    nxGesture(ev, ev.target, (dx, dy, e) => {
      dragged = true;
      const snap = v => e.altKey ? v : Math.round(v / STEP) * STEP;
      dx /= scale; dy /= scale;
      if (rs) {
        L.w = Math.min(lim.max_w, Math.max(lim.min_w, snap(start.w + dx)));
        L.h = Math.min(lim.max_h, Math.max(lim.min_h, snap(start.h + dy)));
        L.w = Math.min(L.w, data.largeur_mur - L.x);
      } else {
        L.x = Math.min(data.largeur_mur - L.w, Math.max(0, snap(start.x + dx)));
        L.y = Math.max(0, snap(start.y + dy));
      }
      place(item, L);
      rescale();
    }, () => {
      item.classList.remove("nx-moving", "nx-resizing");
      if (!dragged && fromImg) { L.z = start.z; place(item, L); return; }   // simple clic : ouvrir la photo
      if (!dragged) { saveLayout({ [eid]: L }); return; }                 // simple clic : passe devant
      const u = undo[data.jour] || (undo[data.jour] = []);
      u.push(before); if (u.length > 30) u.shift();
      hooks.onUndo(true);
      saveLayout({ [eid]: L });
      setTimeout(() => { dragged = false; }, 0);
    });
  });
  canvas.addEventListener("click", ev => { if (dragged && ev.target.closest(".sv-open")) { ev.stopPropagation(); ev.preventDefault(); } }, true);

  // ---- clavier ----
  canvas.addEventListener("keydown", ev => {
    const grab = ev.target.closest(".sv-grab");
    const dir = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[ev.key];
    if (!grab || !dir) return;
    ev.preventDefault();
    const item = grab.closest(".sv-item"), eid = item.dataset.el, L = D()[eid], lim = data.limites;
    if (!keyUndo) { pushUndo(); keyUndo = true; }
    if (ev.shiftKey) {
      L.w = Math.min(lim.max_w, Math.max(lim.min_w, L.w + dir[0] * STEP), data.largeur_mur - L.x);
      L.h = Math.min(lim.max_h, Math.max(lim.min_h, L.h + dir[1] * STEP));
    } else {
      L.x = Math.min(data.largeur_mur - L.w, Math.max(0, L.x + dir[0] * STEP));
      L.y = Math.max(0, L.y + dir[1] * STEP);
    }
    place(item, L); rescale();
    clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { keyUndo = false; saveLayout({ [eid]: L }); }, 500);
  });

  // ---- notes : texte (enregistré pendant l'écriture), couleur, taille, épingle, suppression ----
  const noteTimers = {};
  async function saveText(id, value) {
    clearTimeout(noteTimers[id]); delete noteTimers[id];
    try { await api(`/api/souvenirs/notes/${id}/modifier`, { texte: value }); const n = data.notes.find(x => x.id === id); if (n) n.texte = value; }
    catch (e) { toast("Note : " + e.message, true); }
  }
  // texte tapé pas encore enregistré (moins de 600 ms) : enregistré tout de suite, AVANT une autre action
  // (couleur, écriture, taille, police, épingle, suppression, rechargement du mur) — sinon il serait effacé
  async function flushTexts() {
    const ids = Object.keys(noteTimers);
    await Promise.all(ids.map(id => {
      const t = canvas.querySelector(`[data-ntext="${id}"]`);
      return t ? saveText(id, t.value) : (clearTimeout(noteTimers[id]), delete noteTimers[id], null);
    }));
  }
  canvas.addEventListener("input", ev => {
    const t = ev.target.closest("[data-ntext]");
    if (!t) return;
    const id = t.dataset.ntext;
    clearTimeout(noteTimers[id]);
    noteTimers[id] = setTimeout(() => saveText(id, t.value), 600);
  });
  // édition : ouvrir / fermer sans tout redessiner (le mur ne bouge pas)
  const noteEl = id => canvas.querySelector(`.sv-note [data-ntext="${id}"]`)?.closest(".sv-note");
  function startEdit(id) {
    if (editingId && editingId !== id) stopEdit();
    const el = noteEl(id); if (!el) return;
    editingId = id;
    el.classList.add("sv-editing");
    const t = el.querySelector(".sv-ntext"); t.readOnly = false;
    t.focus(); t.setSelectionRange(t.value.length, t.value.length);
  }
  function stopEdit() {
    const id = editingId; if (!id) return;
    editingId = null;
    if (palId === id) { palId = null; const pe = noteEl(id); if (pe) { pe.querySelector(".sv-npal").hidden = true; pe.querySelector("[data-npal]").classList.remove("on"); } }
    const el = noteEl(id); if (!el) return;
    const t = el.querySelector(".sv-ntext");
    if (noteTimers[id]) saveText(id, t.value);                  // dernière frappe pas encore enregistrée
    t.readOnly = true; t.blur();
    el.classList.remove("sv-editing");
  }
  canvas.addEventListener("dblclick", ev => {
    const t = ev.target.closest(".sv-note .sv-ntext");
    if (t && t.readOnly) startEdit(t.dataset.ntext);
  });
  canvas.addEventListener("keydown", ev => {
    const t = ev.target.closest(".sv-ntext");
    if (t && !t.readOnly && (ev.key === "Escape" || (ev.key === "Enter" && ev.ctrlKey))) { ev.preventDefault(); ev.stopPropagation(); stopEdit(); }
  });
  document.addEventListener("pointerdown", ev => {          // clic hors de la note en cours : on la referme
    if (!editingId) return;
    const el = noteEl(editingId);
    if (el && !el.contains(ev.target)) stopEdit();
  }, true);
  canvas.addEventListener("click", ev => {
    const e = ev.target.closest("[data-nedit]"), d = ev.target.closest("[data-ndone]"), p = ev.target.closest("[data-npal]");
    if (e) startEdit(e.dataset.nedit);
    else if (d) stopEdit();
    else if (p) {                                            // palette fond + écriture : ouvrir / fermer
      const id = p.dataset.npal, pal = p.closest(".sv-note").querySelector(".sv-npal");
      palId = palId === id ? null : id;
      pal.hidden = palId !== id; p.classList.toggle("on", palId === id); p.setAttribute("aria-expanded", palId === id);
    }
  });
  canvas.addEventListener("change", async ev => {          // police
    const s = ev.target.closest("[data-nfonte]");
    if (!s) return;
    try { await flushTexts(); await api(`/api/souvenirs/notes/${s.dataset.nfonte}/modifier`, { fonte: s.value }); await load(data.jour); }
    catch (e) { toast("Note : " + e.message, true); }
  });
  canvas.addEventListener("click", async ev => {
    const b = ev.target.closest("[data-ncolor],[data-nink],[data-nfont],[data-npin],[data-ndel]");
    if (!b) return;
    const id = b.dataset.nid || b.dataset.npin || b.dataset.ndel, n = data.notes.find(x => x.id === id);
    if (!n) return;
    try {
      await flushTexts();
      if (b.dataset.ncolor) await api(`/api/souvenirs/notes/${id}/modifier`, { couleur: b.dataset.ncolor });
      else if (b.dataset.nink) await api(`/api/souvenirs/notes/${id}/modifier`, { encre: b.dataset.nink });
      else if (b.dataset.nfont) await api(`/api/souvenirs/notes/${id}/modifier`, { police: n.police + Number(b.dataset.nfont) });
      else if (b.dataset.npin) {
        await api(`/api/souvenirs/notes/${id}/modifier`, { epinglee: !n.epinglee });
        toast(n.epinglee ? "Note désépinglée : elle reste seulement sur son jour." : "Note épinglée : elle se répète sur les jours suivants.");
      } else {
        const msg = n.epinglee ? "Supprimer cette note épinglée ? Elle disparaîtra de TOUS les jours où elle se répète." : "Supprimer cette note ?";
        if (!confirm(msg)) return;
        await api(`/api/souvenirs/notes/${id}/supprimer`, {});
      }
      await load(data.jour);
    } catch (e) { toast("Note : " + e.message, true); }
  });

  // ---- API ----
  async function load(day) {
    await flushTexts();                                       // jamais de texte perdu au rechargement du mur
    if (data && data.jour !== day) editingId = null;          // autre jour : plus de note en cours d'édition
    try { data = await api(`/api/souvenirs/jour/${day}`); }
    catch (e) { toast("Souvenirs : " + e.message, true); return null; }
    render();
    if (editingId) {                                          // couleur / taille changées : on reste dans la note
      const t = canvas.querySelector(`[data-ntext="${editingId}"]`);
      if (t) { t.focus(); t.setSelectionRange(t.value.length, t.value.length); } else editingId = null;
    }
    hooks.onUndo(!!(undo[day] && undo[day].length));
    return data;
  }
  return {
    load,
    get data() { return data; },
    async addNote() {
      const r = host.getBoundingClientRect();
      const y = Math.max(0, Math.round((Math.max(0, -r.top) + 30) / scale));
      try {
        pushUndo();
        const res = await api("/api/souvenirs/notes", { jour: data.jour, position: { x: 30, y } });
        editingId = res.note.id;                              // une nouvelle note s'ouvre directement en édition
        await load(data.jour);
      } catch (e) { toast("Note : " + e.message, true); }
    },
    async auto() {
      pushUndo();
      try { data = await api(`/api/souvenirs/disposition/${data.jour}/auto`, {}); render(); toast("Mur réorganisé (↶ pour revenir en arrière)."); }
      catch (e) { toast(e.message, true); }
    },
    async undo() {
      const s = undo[data.jour];
      if (!s || !s.length) return;
      await saveLayout(s.pop());
      render();
      hooks.onUndo(s.length > 0);
    },
  };
}
