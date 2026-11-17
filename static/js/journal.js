"use strict";
// ===== Onglet Journal quotidien : humeur, activités, texte libre (enregistré pendant l'écriture) =====
// Données sur ce PC (journal.py, base SQLite). Option : mot de passe du panel avant d'ouvrir le Journal.
(() => {
  const root = $("tab-journal");
  const pad = n => String(n).padStart(2, "0");
  const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parse = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const addDays = (s, n) => { const d = parse(s); d.setDate(d.getDate() + n); return ymd(d); };
  let st = null, day = ymd(new Date()), month = day.slice(0, 7), entry = null, saveTimer = null, dirty = false;

  async function api2(path, body, method) {
    try { return await api(path, body, method); }
    catch (e) { if (e.status === 401) { st = { ...(st || {}), deverrouille: false }; renderLock(); } throw e; }
  }

  // ---- Visage du jour : humeur au centre, émojis des activités en arc (ou en cercle s'il y en a beaucoup) ----
  // Au-delà de max, un « +N » donne la liste au survol (et au toucher).
  const actName = e => ((st && st.activites.find(a => a.emoji === e)) || {}).nom || "";
  function face(mood, acts, small) {
    const max = small ? 4 : 8;
    const shown = acts.length > max ? acts.slice(0, max - 1) : acts;
    const rest = acts.slice(shown.length);
    const n = shown.length + (rest.length ? 1 : 0);
    const angle = i => n <= 5 ? -150 + (n === 1 ? 60 : i * 120 / (n - 1)) : -90 + i * 360 / n;
    const label = `${mood ? "Humeur " + mood : "Pas d'humeur"}${acts.length ? ", activités : " + acts.map(a => `${a} ${actName(a)}`.trim()).join(", ") : ""}`;
    const restTxt = rest.map(a => `${a} ${actName(a)}`.trim()).join(", ");
    return `<span class="jn-face${small ? " sm" : ""}" ${small ? "" : `role="img" aria-label="${esc(label)}"`}>
      <span class="jn-face-mood">${mood || (acts.length ? "·" : "")}</span>
      ${shown.map((a, i) => `<span class="jn-orb" style="--a:${angle(i)}deg" title="${esc(actName(a))}" aria-hidden="true">${a}</span>`).join("")}
      ${rest.length ? `<span class="jn-orb jn-more" style="--a:${angle(n - 1)}deg" title="Aussi : ${esc(restTxt)}"
        ${small ? 'aria-hidden="true"' : `tabindex="0" role="button" data-more="${esc(restTxt)}" aria-label="et ${rest.length} autres : ${esc(restTxt)}"`}>+${rest.length}</span>` : ""}
    </span>`;
  }
  function drawFace() {
    const f = $("jn-face");
    if (f && entry) f.innerHTML = face(entry.humeur, entry.activites, false);
  }

  // ---- Verrou ----
  function renderLock() {
    // (data-nx-hors : écran de passage, jamais un bloc déplaçable — il ne doit pas écraser la disposition du Journal)
    root.innerHTML = `<section class="card c-journal jn-lock" data-nx-hors>
      <h2>🔒 Journal verrouillé</h2>
      <p>Le Journal demande le mot de passe du panel (celui du stream deck), même si le panel est ouvert.</p>
      <form id="jn-unlock" class="form-row"><input class="in grow" type="password" id="jn-pw" placeholder="Mot de passe" autocomplete="current-password" aria-label="Mot de passe">
        <button class="btn big">Ouvrir le journal</button></form>
      <div class="dk-err" id="jn-err"></div></section>`;
    $("jn-pw").focus();
    $("jn-unlock").addEventListener("submit", async e => {
      e.preventDefault();
      try { await api("/api/journal/deverrouiller", { mot_de_passe: $("jn-pw").value }); await start(); }
      catch (err) { $("jn-err").textContent = err.message; $("jn-pw").select(); }
    });
  }

  // ---- Page ----
  function renderPage() {
    root.innerHTML = `
      <div class="jn-bar">
        <button class="btn" id="jn-prev" aria-label="Jour précédent">◀</button>
        <button class="btn" id="jn-today">Aujourd'hui</button>
        <button class="btn" id="jn-next" aria-label="Jour suivant">▶</button>
        <input class="in" type="date" id="jn-pick" aria-label="Aller au jour">
        <input class="in jn-q" type="search" id="jn-q" placeholder="Rechercher dans le journal…" aria-label="Rechercher dans le journal">
        <a class="btn" id="jn-md" href="/api/journal/export?format=md" download>⤓ Markdown</a>
        <a class="btn" id="jn-txt" href="/api/journal/export?format=txt" download>⤓ Texte</a>
        ${st.verrou_actif ? `<button class="btn" id="jn-relock" title="Reverrouiller maintenant">🔒</button>` : ""}
      </div>
      <div class="jn-results" id="jn-results" hidden></div>
      <div class="jn-cols">
        <section class="card c-journal jn-day">
          <h2 id="jn-title"></h2>
          <div class="jn-facebox" id="jn-face"></div>
          <div class="jn-label">Humeur</div>
          <div class="jn-moods" id="jn-mood" role="radiogroup" aria-label="Humeur du jour">
            ${st.humeurs.map(m => `<button class="jn-mood" role="radio" data-mood="${m.emoji}" title="${esc(m.nom)}" aria-label="${esc(m.nom)}">${m.emoji}</button>`).join("")}
          </div>
          <div class="jn-label">Activités</div>
          <div class="jn-acts" id="jn-acts">
            ${st.activites.map(a => `<button class="jn-act" data-act="${a.emoji}" aria-pressed="false" title="${esc(a.nom)}">${a.emoji}<small>${esc(a.nom)}</small></button>`).join("")}
          </div>
          <div class="jn-label">Notes du jour <small class="saved" id="jn-saved"></small></div>
          <textarea class="in jn-text" id="jn-text" placeholder="Qu'est-ce qui s'est passé aujourd'hui ?" maxlength="50000"></textarea>
        </section>
        <section class="card c-journal jn-monthcard">
          <h2>Vue mois</h2>
          <div class="cal-head"><button class="btn" id="jn-mprev" aria-label="Mois précédent">◀</button><span class="m" id="jn-mname"></span>
            <button class="btn" id="jn-mnext" aria-label="Mois suivant">▶</button></div>
          <div class="jn-month" id="jn-month"></div>
          <label class="ag-chk jn-lockopt"><input type="checkbox" id="jn-lockopt" ${st.verrou_actif ? "checked" : ""} ${st.mot_de_passe_defini ? "" : "disabled"}>
            Demander le mot de passe du panel pour ouvrir le Journal${st.mot_de_passe_defini ? "" : " (définis d'abord un mot de passe avec configurer.bat)"}</label>
        </section>
      </div>`;
    bind();
  }

  // ---- Taille de la zone de texte, par jour ----
  // Sans réglage : elle s'adapte au texte du jour (260 px au moins, 900 au plus, puis défilement).
  // Redimensionnée à la main (poignée en bas à droite) : la hauteur est retenue pour CE jour, sur cet appareil,
  // et retrouvée telle quelle après F5 (la page ne « saute » plus au rechargement).
  const H_KEY = "nexus-journal-hauteurs", H_MIN = 260, H_MAX = 900;
  const hauteurs = () => { try { return JSON.parse(localStorage.getItem(H_KEY) || "{}") || {}; } catch (e) { return {}; } };
  function retenirHauteur(jour, h) {
    const m = hauteurs();
    m[jour] = Math.round(h);
    const cles = Object.keys(m).sort();
    while (cles.length > 400) delete m[cles.shift()];        // les 400 jours les plus récents suffisent
    try { localStorage.setItem(H_KEY, JSON.stringify(m)); } catch (e) {}
  }
  function ajusterTexte() {
    const t = $("jn-text"); if (!t) return;
    const voulue = hauteurs()[day];
    if (voulue) t.style.height = voulue + "px";
    else { t.style.height = "auto"; t.style.height = Math.min(H_MAX, Math.max(H_MIN, t.scrollHeight + 4)) + "px"; }
  }

  function fill() {
    $("jn-title").textContent = parse(day).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    $("jn-pick").value = day;
    root.querySelectorAll("[data-mood]").forEach(b => b.setAttribute("aria-checked", b.dataset.mood === entry.humeur ? "true" : "false"));
    root.querySelectorAll("[data-act]").forEach(b => b.setAttribute("aria-pressed", entry.activites.includes(b.dataset.act) ? "true" : "false"));
    $("jn-text").value = entry.texte;
    ajusterTexte();
    $("jn-saved").textContent = entry.modifie ? "enregistré" : "";
    drawFace();
  }

  async function loadDay() {
    await flush();
    try { entry = await api2(`/api/journal/jour/${day}`); } catch (e) { return; }
    fill();
    loadMonth();
  }
  async function loadMonth() {
    let days = {};
    try { days = (await api2(`/api/journal/mois/${month}`)).jours; } catch (e) { return; }
    $("jn-mname").textContent = parse(month + "-01").toLocaleDateString("fr-FR", { month: "long", year: "numeric" });
    const first = parse(month + "-01"), start = new Date(first); start.setDate(1 - ((first.getDay() + 6) % 7));
    const today = ymd(new Date());
    let html = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"].map(d => `<div class="dow">${d}</div>`).join("");
    for (let i = 0; i < 42; i++) {
      const d = new Date(start); d.setDate(start.getDate() + i);
      const k = ymd(d), e = days[k];
      html += `<button class="jn-mday${d.getMonth() !== first.getMonth() ? " other" : ""}${k === day ? " sel" : ""}${k === today ? " today" : ""}${e ? " filled" : ""}"
        data-day="${k}" aria-label="${d.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })}${e ? ", écrit" + (e.humeur ? ", humeur " + e.humeur : "") + (e.activites && e.activites.length ? ", activités : " + e.activites.map(a => `${a} ${actName(a)}`.trim()).join(", ") : "") : ""}">
        <span>${d.getDate()}</span>${e ? (e.humeur || (e.activites || []).length ? face(e.humeur, e.activites || [], true) : "<b>✎</b>") : ""}</button>`;
      if (i === 34 && new Date(d.getFullYear(), d.getMonth(), d.getDate() + 1).getMonth() !== first.getMonth()) break;
    }
    $("jn-month").innerHTML = html;
  }

  // ---- Enregistrement automatique ----
  async function flush() {
    if (!dirty || !entry) return;
    clearTimeout(saveTimer); saveTimer = null; dirty = false;
    const body = { humeur: entry.humeur, activites: entry.activites, texte: entry.texte };
    const d = entry.jour;
    try {
      await api2(`/api/journal/jour/${d}`, body, "PUT");
      const s = $("jn-saved"); if (s && d === day) s.textContent = "enregistré ✔";
      if (d.slice(0, 7) === month) loadMonth();
    } catch (e) { const s = $("jn-saved"); if (s) s.textContent = "⚠ " + e.message; dirty = true; }
  }
  function changed(now) {
    dirty = true;
    const s = $("jn-saved"); if (s) s.textContent = "…";
    clearTimeout(saveTimer);
    saveTimer = setTimeout(flush, now ? 0 : 700);
  }
  window.addEventListener("pagehide", () => {
    if (!dirty || !entry) return;
    fetch(`/api/journal/jour/${entry.jour}`, { method: "PUT", keepalive: true, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ humeur: entry.humeur, activites: entry.activites, texte: entry.texte }) });
  });

  // ---- Recherche ----
  let qTimer = null;
  async function search(q) {
    const box = $("jn-results");
    if (q.trim().length < 2) { box.hidden = true; return; }
    let r;
    try { r = (await api2(`/api/journal/recherche?q=${encodeURIComponent(q)}`)).resultats; } catch (e) { return; }
    box.hidden = false;
    box.innerHTML = r.map(x => `<button class="jn-hit" data-day="${x.jour}"><b>${parse(x.jour).toLocaleDateString("fr-FR", { day: "numeric", month: "long", year: "numeric" })}</b>
      ${x.humeur || ""}<span>${esc(x.extrait)}</span></button>`).join("") || `<div class="empty">Aucun résultat pour « ${esc(q)} ».</div>`;
  }

  function bind() {
    $("jn-prev").addEventListener("click", () => go(addDays(day, -1)));
    $("jn-next").addEventListener("click", () => go(addDays(day, 1)));
    $("jn-today").addEventListener("click", () => go(ymd(new Date())));
    $("jn-pick").addEventListener("change", e => { if (e.target.value) go(e.target.value); });
    $("jn-mprev").addEventListener("click", () => { const d = parse(month + "-01"); d.setMonth(d.getMonth() - 1); month = ymd(d).slice(0, 7); loadMonth(); });
    $("jn-mnext").addEventListener("click", () => { const d = parse(month + "-01"); d.setMonth(d.getMonth() + 1); month = ymd(d).slice(0, 7); loadMonth(); });
    $("jn-text").addEventListener("input", e => {
      entry.texte = e.target.value; changed();
      if (!hauteurs()[day]) ajusterTexte();                   // pas de taille choisie : elle suit le texte
    });
    // redimensionnement À LA MAIN (poignée en bas à droite) : hauteur au début et à la fin du geste ; si elle a
    // changé, elle est retenue pour ce jour
    let hDebut = 0;
    $("jn-text").addEventListener("pointerdown", e => { hDebut = e.currentTarget.offsetHeight; });
    addEventListener("pointerup", () => {
      const t = $("jn-text");
      if (!hDebut || !t) return;
      const h = t.offsetHeight;
      if (Math.abs(h - hDebut) > 2) retenirHauteur(day, h);
      hDebut = 0;
    });
    $("jn-text").addEventListener("blur", () => flush());
    $("jn-q").addEventListener("input", e => { clearTimeout(qTimer); qTimer = setTimeout(() => search(e.target.value), 300); });
    const relock = $("jn-relock");
    if (relock) relock.addEventListener("click", async () => { await flush(); await api("/api/journal/reverrouiller", {}); start(); });
    $("jn-lockopt").addEventListener("change", async e => {
      const on = e.target.checked;
      const pw = prompt(`${on ? "Activer" : "Désactiver"} le mot de passe du Journal : tape le mot de passe du panel (celui du deck).`);
      if (pw === null) { e.target.checked = !on; return; }
      try {
        await api("/api/journal/verrou", { actif: on, mot_de_passe: pw });
        toast(on ? "Le Journal demandera désormais le mot de passe." : "Le Journal s'ouvre sans mot de passe.");
        if (on) await api("/api/journal/deverrouiller", { mot_de_passe: pw });
        await start();
      } catch (err) { e.target.checked = !on; toast(err.message, true); }
    });
  }
  function go(d) { day = d; month = d.slice(0, 7); $("jn-results").hidden = true; loadDay(); }

  root.addEventListener("click", e => {
    const m = e.target.closest("[data-mood]"), a = e.target.closest("[data-act]"), d = e.target.closest("[data-day]");
    if (m && entry) {
      entry.humeur = entry.humeur === m.dataset.mood ? "" : m.dataset.mood;
      fill(); changed(true);
    } else if (a && entry) {
      const k = a.dataset.act;
      entry.activites = entry.activites.includes(k) ? entry.activites.filter(x => x !== k) : [...entry.activites, k];
      a.setAttribute("aria-pressed", entry.activites.includes(k) ? "true" : "false");
      drawFace();
      changed(true);
    } else if (e.target.closest("[data-more]")) {
      toast("Aussi : " + e.target.closest("[data-more]").dataset.more);     // au doigt (pas de survol)
    } else if (d) { go(d.dataset.day); }
  });

  async function start() {
    try { st = await api("/api/journal/etat"); } catch (e) { root.innerHTML = `<div class="empty">Journal indisponible : ${esc(e.message)}</div>`; return; }
    if (st.verrou_actif && !st.deverrouille) return renderLock();
    renderPage();
    entry = null; dirty = false;
    await loadDay();
  }

  Tabs.register("journal", {
    show() { start(); },
    hide() { flush(); },
  });
})();
