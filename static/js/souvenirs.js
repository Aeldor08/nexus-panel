"use strict";
// ===== Onglet Souvenirs : le jour en grand, l'heure, le mur de photos du jour, « Ce jour-là », calendrier, diaporama =====
// Photos et notes sur ce PC uniquement (data\souvenirs\, index SQLite) : voir souvenirs.py. Mur libre : js/mur.js.
(() => {
  const root = $("tab-souvenirs");
  const pad = n => String(n).padStart(2, "0");
  const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parse = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const addDays = (s, n) => { const d = parse(s); d.setDate(d.getDate() + n); return ymd(d); };
  const EXIF_KEY = "nexus-souvenirs-exif";
  let day = ymd(new Date()), month = day.slice(0, 7), photos = [], clockTimer = null;

  root.innerHTML = `
    <section class="card c-souv sv-hero">
      <div class="sv-day"><div class="sv-weekday" id="sv-weekday"></div><div class="sv-date" id="sv-date"></div></div>
      <div class="sv-clock" id="sv-clock"></div>
      <div class="sv-nav">
        <button class="btn" id="sv-prev" aria-label="Jour précédent">◀</button>
        <button class="btn" id="sv-today">Aujourd'hui</button>
        <button class="btn" id="sv-next" aria-label="Jour suivant">▶</button>
        <input class="in" type="date" id="sv-pick" aria-label="Aller au jour">
        <button class="btn" id="sv-slide" title="Diaporama aléatoire des anciens souvenirs">▶ Diaporama</button>
      </div>
    </section>
    <div class="sv-cols">
      <section class="card c-souv sv-wallcard">
        <h2>Mur du jour <small id="sv-count"></small></h2>
        <div class="sv-walltools">
          <button class="btn" id="sv-note-add">＋ Ajouter une note</button>
          <button class="btn" id="sv-auto" title="Range photos et notes du jour en grille propre">▦ Réorganiser automatiquement</button>
          <button class="btn" id="sv-undo" disabled title="Annule le dernier déplacement, redimensionnement ou rangement du mur de ce jour">↶ Annuler la dernière modification</button>
        </div>
        <div class="sv-wall" id="sv-wall"></div>
      </section>
      <div class="sv-side">
        <section class="card c-souv">
          <h2>Ajouter des photos</h2>
          <label class="sv-drop" id="sv-drop" tabindex="0">
            <input type="file" id="sv-file" accept="image/jpeg,image/png,image/webp" multiple hidden>
            <b>Glisse tes photos ici</b><span>ou touche pour en choisir (JPG, PNG, WebP · 25 Mo max)</span>
          </label>
          <div class="sv-form">
            <label class="ag-f"><span>Jour du souvenir</span><input class="in" type="date" id="sv-up-day"></label>
            <label class="ag-f"><span>Légende (facultatif)</span><input class="in" id="sv-up-cap" maxlength="300" placeholder="ex. Pique-nique au parc"></label>
            <label class="ag-chk"><input type="checkbox" id="sv-up-exif"> <span>Garder les métadonnées (date de prise de vue, appareil, <b>position GPS</b>). Décoché : elles sont retirées.</span></label>
          </div>
          <div class="sv-progress" id="sv-progress"></div>
        </section>
        <section class="card c-souv">
          <h2>Ce jour-là <small id="sv-otd-sub"></small></h2>
          <div class="sv-otd" id="sv-otd"></div>
        </section>
        <section class="card c-souv">
          <h2>Calendrier</h2>
          <div class="cal-head">
            <button class="btn" id="sv-mprev" aria-label="Mois précédent">◀</button><span class="m" id="sv-month"></span>
            <button class="btn" id="sv-mnext" aria-label="Mois suivant">▶</button></div>
          <div class="sv-cal" id="sv-cal"></div>
          <h3 class="sv-h3">Derniers jours avec des photos</h3>
          <div class="sv-frise" id="sv-frise"></div>
        </section>
      </div>
    </div>`;

  try { $("sv-up-exif").checked = localStorage.getItem(EXIF_KEY) === "1"; } catch (e) {}
  $("sv-up-exif").addEventListener("change", e => { try { localStorage.setItem(EXIF_KEY, e.target.checked ? "1" : "0"); } catch (x) {} });

  // ---- En-tête : jour en grand, heure en direct ----
  function hero() {
    const d = parse(day);
    $("sv-weekday").textContent = d.toLocaleDateString("fr-FR", { weekday: "long" });
    $("sv-date").textContent = d.toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" });
    $("sv-pick").value = day;
    $("sv-up-day").value = day;
    tick();
  }
  function tick() { $("sv-clock").textContent = new Date().toLocaleTimeString("fr-FR"); }

  // ---- Mur libre du jour (js/mur.js) ----
  const plural = (n, w) => `${n} ${w}${n > 1 ? "s" : ""}`;
  const wall = SvWall($("sv-wall"), {
    onRender(d) {
      photos = d.photos;
      const parts = [d.photos.length && plural(d.photos.length, "photo"), d.notes.length && plural(d.notes.length, "note")].filter(Boolean);
      $("sv-count").textContent = parts.join(" · ");
    },
    onUndo(can) { $("sv-undo").disabled = !can; },
  });
  $("sv-note-add").addEventListener("click", () => wall.addNote());
  $("sv-auto").addEventListener("click", () => wall.auto());
  $("sv-undo").addEventListener("click", () => wall.undo());

  async function loadDay() {
    hero();
    if (!(await wall.load(day))) return;
    loadOtd(); loadMonth(); loadFrise();
  }
  async function loadOtd() {
    try {
      const list = (await api(`/api/souvenirs/ce-jour-la/${day}`)).photos;
      $("sv-otd-sub").textContent = parse(day).toLocaleDateString("fr-FR", { day: "numeric", month: "long" }) + " des années passées";
      const years = {};
      list.forEach(p => (years[p.jour.slice(0, 4)] = years[p.jour.slice(0, 4)] || []).push(p));
      $("sv-otd").innerHTML = Object.keys(years).sort().reverse().map(y => `<div class="sv-year"><b>${y}</b> <small>il y a ${parse(day).getFullYear() - y} an(s)</small>
        <div class="sv-strip">${years[y].map(p => `<button class="sv-thumb" data-open="${p.id}" data-list="otd"><img src="${p.miniature}" alt="${esc(p.legende)}" loading="lazy"></button>`).join("")}</div></div>`).join("")
        || `<div class="empty">Aucun souvenir à cette date les années précédentes.</div>`;
      otdList = list;
    } catch (e) { $("sv-otd").innerHTML = `<div class="empty">indisponible</div>`; }
  }
  let otdList = [];
  async function loadMonth() {
    $("sv-month").textContent = parse(month + "-01").toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
    let counts = {};
    try { counts = (await api(`/api/souvenirs/mois/${month}`)).jours; } catch (e) {}
    const first = parse(month + "-01"), start = new Date(first); start.setDate(1 - ((first.getDay() + 6) % 7));
    const today = ymd(new Date());
    let html = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"].map(d => `<div class="dow">${d}</div>`).join("");
    for (let i = 0; i < 42; i++) {
      const d = new Date(start); d.setDate(start.getDate() + i);
      const k = ymd(d), n = counts[k] || 0;
      html += `<button class="sv-cday${d.getMonth() !== first.getMonth() ? " other" : ""}${k === day ? " sel" : ""}${k === today ? " today" : ""}${n ? " has" : ""}"
        data-day="${k}" aria-label="${d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}${n ? `, ${n} photo(s)` : ""}">
        <span>${d.getDate()}</span>${n ? `<i>${n}</i>` : ""}</button>`;
      if (i === 34 && new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1).getMonth() !== first.getMonth()) break;
    }
    $("sv-cal").innerHTML = html;
  }
  async function loadFrise() {
    try {
      const list = (await api("/api/souvenirs/frise")).jours;
      $("sv-frise").innerHTML = list.map(j => `<button class="sv-fday${j.jour === day ? " sel" : ""}" data-day="${j.jour}">
        <img src="${j.miniature}" alt="" loading="lazy"><span>${parse(j.jour).toLocaleDateString("fr-FR", { day: "numeric", month: "short", year: "2-digit" })}</span><small>${j.n}</small></button>`).join("")
        || `<div class="empty">La frise se remplira avec tes photos.</div>`;
    } catch (e) {}
  }

  function go(d) { day = d; month = d.slice(0, 7); loadDay(); }

  // ---- Envoi ----
  async function upload(files) {
    const list = [...files].filter(f => f.size);
    if (!list.length) return;
    const target = $("sv-up-day").value || day, cap = $("sv-up-cap").value.trim(), exif = $("sv-up-exif").checked ? 1 : 0;
    const box = $("sv-progress");
    let ok = 0;
    for (const f of list) {
      const row = document.createElement("div");
      row.className = "sv-prog";
      row.textContent = `⏳ ${f.name}`;
      box.prepend(row);
      if (f.size > 25 * 1024 * 1024) { row.textContent = `❌ ${f.name} : trop lourd (25 Mo max)`; continue; }
      try {
        const r = await fetch(`/api/souvenirs?jour=${encodeURIComponent(target)}&legende=${encodeURIComponent(cap)}&exif=${exif}`,
          { method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: f });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) throw new Error(data.error || "HTTP " + r.status);
        row.textContent = `✔ ${f.name}`; ok++;
      } catch (e) { row.textContent = `❌ ${f.name} : ${e.message}`; }
    }
    if (ok) { toast(`${ok} photo${ok > 1 ? "s" : ""} ajoutée${ok > 1 ? "s" : ""}.`); $("sv-up-cap").value = ""; go(target); }
    setTimeout(() => { box.querySelectorAll(".sv-prog").forEach((r, i) => { if (i > 4) r.remove(); }); }, 5000);
  }
  const drop = $("sv-drop");
  $("sv-file").addEventListener("change", e => { upload(e.target.files); e.target.value = ""; });
  drop.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); $("sv-file").click(); } });
  ["dragenter", "dragover"].forEach(t => drop.addEventListener(t, e => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave", "drop"].forEach(t => drop.addEventListener(t, () => drop.classList.remove("drag")));
  drop.addEventListener("drop", e => { e.preventDefault(); upload(e.dataTransfer.files); });

  // ---- Visionneuse et diaporama ----
  const view = document.createElement("dialog");
  view.className = "sv-view";
  document.body.appendChild(view);
  let vList = [], vIdx = 0, slideTimer = null;
  function showView() {
    const p = vList[vIdx];
    if (!p) return view.close();
    view.innerHTML = `<img src="${p.url}" alt="${esc(p.legende)}">
      <div class="sv-vbar"><span><b>${parse(p.jour).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" })}</b>
        ${p.legende ? " · " + esc(p.legende) : ""}</span>
        <span class="sv-vbtns">${vList.length > 1 ? `<button class="btn" data-v="-1" aria-label="Précédente">◀</button>
        <span class="muted">${vIdx + 1} / ${vList.length}</span><button class="btn" data-v="1" aria-label="Suivante">▶</button>` : ""}
        ${slideTimer ? `<button class="btn" data-v="pause">❚❚</button>` : ""}<button class="btn" data-v="go">Aller à ce jour</button>
        <button class="btn" data-v="x" aria-label="Fermer">✕</button></span></div>`;
    view.querySelector("img").classList.add("in");
  }
  function openView(list, idx, slide = false) {
    vList = list; vIdx = idx;
    clearInterval(slideTimer); slideTimer = null;
    if (slide) slideTimer = setInterval(() => { vIdx = (vIdx + 1) % vList.length; showView(); }, 5000);
    showView();
    if (!view.open) view.showModal();
  }
  view.addEventListener("close", () => { clearInterval(slideTimer); slideTimer = null; });
  view.addEventListener("click", e => {
    const b = e.target.closest("[data-v]");
    if (e.target === view) return view.close();
    if (!b) return;
    const v = b.dataset.v;
    if (v === "x") view.close();
    else if (v === "pause") { clearInterval(slideTimer); slideTimer = null; showView(); }
    else if (v === "go") { const d = vList[vIdx].jour; view.close(); go(d); }
    else { vIdx = (vIdx + Number(v) + vList.length) % vList.length; showView(); }
  });
  view.addEventListener("keydown", e => {
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") { vIdx = (vIdx + (e.key === "ArrowRight" ? 1 : -1) + vList.length) % vList.length; showView(); }
  });

  // ---- Clics ----
  root.addEventListener("click", async e => {
    const t = e.target.closest("[data-open],[data-day],[data-cap],[data-move],[data-del]");
    if (!t) return;
    if (t.dataset.open) {
      const list = t.dataset.list === "otd" ? otdList : photos;
      return openView(list, Math.max(0, list.findIndex(p => p.id === t.dataset.open)));
    }
    if (t.dataset.day && !t.closest(".sv-photo")) return go(t.dataset.day);
    const id = t.dataset.cap || t.dataset.move || t.dataset.del;
    const p = photos.find(x => x.id === id);
    if (!p) return;
    try {
      if (t.dataset.cap) {
        const cap = prompt("Légende de la photo :", p.legende || "");
        if (cap === null) return;
        await api(`/api/souvenirs/${id}/modifier`, { legende: cap });
      } else if (t.dataset.move) {
        const d = prompt("Déplacer vers quel jour ? (format AAAA-MM-JJ)", p.jour);
        if (d === null) return;
        if (!/^\d{4}-\d{2}-\d{2}$/.test(d.trim()) || isNaN(parse(d.trim()))) return toast("Date invalide (ex. 2026-11-08).", true);
        await api(`/api/souvenirs/${id}/modifier`, { jour: d.trim() });
        toast("Photo déplacée au " + parse(d.trim()).toLocaleDateString("fr-FR"));
      } else {
        if (!confirm("Supprimer définitivement cette photo de ce PC ?")) return;
        await api(`/api/souvenirs/${id}/supprimer`, {});
        toast("Photo supprimée.");
      }
      loadDay();
    } catch (err) { toast(err.message, true); }
  });
  $("sv-prev").addEventListener("click", () => go(addDays(day, -1)));
  $("sv-next").addEventListener("click", () => go(addDays(day, 1)));
  $("sv-today").addEventListener("click", () => go(ymd(new Date())));
  $("sv-pick").addEventListener("change", e => { if (e.target.value) go(e.target.value); });
  $("sv-mprev").addEventListener("click", () => { const d = parse(month + "-01"); d.setMonth(d.getMonth() - 1); month = ymd(d).slice(0, 7); loadMonth(); });
  $("sv-mnext").addEventListener("click", () => { const d = parse(month + "-01"); d.setMonth(d.getMonth() + 1); month = ymd(d).slice(0, 7); loadMonth(); });
  $("sv-slide").addEventListener("click", async () => {
    try {
      const list = (await api(`/api/souvenirs/aleatoire?avant=${ymd(new Date())}`)).photos;
      if (!list.length) return toast("Pas encore d'anciens souvenirs pour le diaporama.");
      openView(list, 0, true);
    } catch (e) { toast(e.message, true); }
  });

  Tabs.register("souvenirs", {
    show() { loadDay(); clearInterval(clockTimer); clockTimer = setInterval(tick, 1000); },
    hide() { clearInterval(clockTimer); clockTimer = null; },
  });
})();
