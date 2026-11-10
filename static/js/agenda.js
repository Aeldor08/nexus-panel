"use strict";
// ===== Onglet Agenda : calendrier, jour (évènements + formulaire), à venir, to-do, notes =====
// Les évènements, leurs répétitions et leurs rappels sont gérés par le serveur (agenda.py, reminders.py) :
// le navigateur demande les occurrences d'une période et envoie les créations / modifications / suppressions.
// To-do et notes sont enregistrés à part (PUT /api/agenda/carnet). Fenêtres déplaçables : js/layout.js.
(() => {
  const root = $("tab-agenda");
  root.innerHTML = `
    <div class="ag-tools" id="ag-tools"></div>
    <section class="ag-board" id="ag-board">
      <div class="card c-agenda cal-card ag-panel" data-panel="cal">
        <h2 data-drag>Calendrier</h2>
        <div class="cal-head">
          <button class="btn big" id="a-prev" aria-label="Mois précédent">◀</button>
          <span class="m" id="a-month"></span>
          <span class="form-row"><button class="btn big" id="a-today">Aujourd'hui</button>
          <button class="btn big" id="a-next" aria-label="Mois suivant">▶</button>
          <select class="in" id="a-fetes" aria-label="Fêtes affichées" title="Fêtes et jours fériés affichés dans le calendrier">
            <option value="toutes">★ Fêtes et jours fériés</option><option value="feries">★ Jours fériés seulement</option>
            <option value="aucune">Sans les fêtes</option></select></span>
        </div>
        <div class="cal" id="a-cal"></div>
      </div>
      <div class="card c-agenda ag-panel" data-panel="jour">
        <h2 data-drag><span id="a-day-title">Jour</span></h2>
        <div class="ag-scroll">
          <div class="day-panel" id="a-day"></div>
          <form class="ag-form" id="a-form" novalidate></form>
        </div>
      </div>
      <div class="card c-agenda ag-panel" data-panel="avenir">
        <h2 data-drag>À venir <small>7 jours</small></h2>
        <div class="upcoming ag-scroll" id="a-up"></div>
      </div>
      <div class="card c-agenda ag-panel" data-panel="todo">
        <h2 data-drag>To-do <small id="t-sub"></small></h2>
        <div class="ag-scroll">
          <form class="form-row" id="t-form">
            <input class="in grow" id="t-text" placeholder="Nouvelle tâche…" maxlength="200" aria-label="Nouvelle tâche">
            <input class="in" id="t-due" type="date" aria-label="Échéance (optionnelle)" title="Échéance (optionnelle)">
            <button class="btn big">+</button>
          </form>
          <div id="t-list" style="margin-top:8px"></div>
          <button class="btn" id="t-clear" style="margin-top:10px" hidden>Effacer les tâches terminées</button>
        </div>
      </div>
      <div class="card c-agenda ag-panel" data-panel="notes">
        <h2 data-drag>Notes <small id="n-sub"></small></h2>
        <div class="ag-scroll">
          <div class="form-row" style="margin-bottom:10px"><button class="btn big" id="n-new">+ Nouvelle note</button></div>
          <div class="notes-list" id="n-list"></div>
          <div class="note-edit" id="n-edit"></div>
        </div>
      </div>
    </section>`;

  const pad = n => String(n).padStart(2, "0");
  const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const parse = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
  const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
  const MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre", "octobre", "novembre", "décembre"];
  const DOW = ["lun", "mar", "mer", "jeu", "ven", "sam", "dim"];
  const fmtDay = s => parse(s).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" });
  let REPEAT = { none: "Une fois", daily: "Tous les jours", weekly: "Toutes les semaines", monthly: "Tous les mois", yearly: "Tous les ans" };

  // ---- Fenêtres déplaçables (plus grandes par défaut qu'avant) ----
  const board = NxBoard($("ag-board"), {
    key: "agenda", minW: 280, minH: 180, ancienneCle: "nexus-disposition-agenda",
    defaults: {
      wide: { cal: { x: 0, y: 0, w: .585, h: 640 }, jour: { x: .6, y: 0, w: .4, h: 640 },
              avenir: { x: 0, y: 656, w: .32, h: 330 }, todo: { x: .34, y: 656, w: .32, h: 330 },
              notes: { x: .68, y: 656, w: .32, h: 330 } },
      narrow: { cal: { h: 470 }, jour: { h: 560 }, avenir: { h: 320 }, todo: { h: 380 }, notes: { h: 440 } },
    },
  });
  NxTools($("ag-tools"), () => board, "de l'agenda");

  // ---- Données ----
  let occ = [], events = {}, todos = [], notes = [], defaults = { rappels_minutes: [60, 30], heure_reference: "09:00" };
  let range = null, loaded = false, view = new Date(), selDay = ymd(new Date()), noteId = null;
  let editing = null;          // { event, occurrence } quand on modifie
  view.setDate(1);

  const eventsOn = key => occ.filter(o => o.date === key);
  // Fêtes et jours fériés (js/fetes.js, calculés localement) : choix mémorisé sur cet appareil
  const FETES_KEY = "nexus-agenda-fetes";
  let fetesMode = "toutes";
  try { fetesMode = localStorage.getItem(FETES_KEY) || "toutes"; } catch (e) {}
  const fetesOn = key => !window.NxFetes || fetesMode === "aucune" ? [] : NxFetes.du(key).filter(f => fetesMode === "toutes" || f.ferie);
  const evLabel = o => o.birthday ? `🎂 ${o.title}${o.age ? ` (${o.age} an${o.age > 1 ? "s" : ""})` : ""}` : o.title;
  const fmtDur = m => m >= 60 ? `${Math.floor(m / 60)} h${m % 60 ? " " + pad(m % 60) : ""}` : `${m} min`;
  const fmtRem = list => list.map(m => m >= 1440 && m % 1440 === 0 ? `${m / 1440} j` : m >= 60 ? fmtDur(m) : `${m} min`).join(" et ");

  // Période demandée : les 6 semaines du mois affiché (+ les 7 prochains jours pour « À venir », demandés à part
  // si le mois affiché est loin d'aujourd'hui)
  function wantedRange() {
    const first = new Date(view.getFullYear(), view.getMonth(), 1);
    const start = addDays(first, -((first.getDay() + 6) % 7));
    return { debut: ymd(start), fin: ymd(addDays(start, 41)) };
  }

  let refreshing = 0;
  async function refresh() {
    const r = wantedRange(), today = new Date();
    const up = { debut: ymd(today), fin: ymd(addDays(today, 8)) };
    const ticket = ++refreshing;
    try {
      const data = await api(`/api/agenda?debut=${r.debut}&fin=${r.fin}`);
      let list = data.occurrences;
      if (up.debut < r.debut || up.fin > r.fin) {
        const more = await api(`/api/agenda?debut=${up.debut}&fin=${up.fin}`);
        const have = new Set(list.map(o => o.id));
        list = list.concat(more.occurrences.filter(o => !have.has(o.id)));
      }
      if (ticket !== refreshing) return;          // une demande plus récente est partie entre-temps
      occ = list; todos = data.todos; notes = data.notes;
      events = Object.fromEntries(data.evenements.map(e => [e.id, e]));
      defaults = data.reglages; REPEAT = data.repetitions || REPEAT;
      range = r; loaded = true;
    } catch (e) { toast("Agenda : " + e.message, true); if (Tabs.current === "agenda") renderCal(); return; }
    if (Tabs.current === "agenda") renderAll();
  }

  // ---- To-do et notes : enregistrement différé (regroupe les frappes) ----
  let saveTimer;
  function saveNotebook(now) {
    clearTimeout(saveTimer);
    const run = async () => {
      saveTimer = null;
      try {
        await api("/api/agenda/carnet", { todos, notes }, "PUT");
        const s = $("n-saved"); if (s) s.textContent = "Enregistré ✔";
      } catch (e) { toast("Enregistrement impossible : " + e.message, true); }
    };
    if (now) run(); else saveTimer = setTimeout(run, 600);
  }
  window.addEventListener("pagehide", () => {
    if (!saveTimer) return;
    clearTimeout(saveTimer);
    fetch("/api/agenda/carnet", { method: "PUT", keepalive: true, headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ todos, notes }) });
  });

  // ---- Calendrier ----
  function renderCal() {
    $("a-month").textContent = `${MONTHS[view.getMonth()]} ${view.getFullYear()}`;
    const first = new Date(view.getFullYear(), view.getMonth(), 1);
    const start = addDays(first, -((first.getDay() + 6) % 7));
    const today = ymd(new Date());
    let html = DOW.map(d => `<div class="dow">${d}</div>`).join("");
    for (let i = 0; i < 42; i++) {
      const d = addDays(start, i), key = ymd(d);
      const fetes = fetesOn(key);
      const chips = [...fetes.map(f => `<span class="ev fete${f.ferie ? " ferie" : ""}" title="${esc(f.nom)}${f.ferie ? " (jour férié)" : ""}">${f.icone} ${esc(f.nom)}</span>`),
                     ...eventsOn(key).map(o => `<span class="ev${o.birthday ? " bday" : ""}">${o.time ? o.time + " " : ""}${esc(evLabel(o))}</span>`),
                     ...todos.filter(t => t.due === key && !t.done).map(t => `<span class="ev todo">☐ ${esc(t.text)}</span>`)];
      html += `<button class="day${d.getMonth() !== view.getMonth() ? " other" : ""}${key === today ? " today" : ""}${key === selDay ? " sel" : ""}${fetes.some(f => f.ferie) ? " ferie" : ""}" data-day="${key}"
        aria-label="${fmtDay(key)}${chips.length ? ", " + chips.length + " élément(s)" : ""}">
        <span class="num">${d.getDate()}</span>${chips.slice(0, 3).join("")}${chips.length > 3 ? `<span class="more">+${chips.length - 3}</span>` : ""}</button>`;
      if (i === 34 && addDays(d, 1).getMonth() !== view.getMonth()) break;   // 5 semaines suffisent
    }
    $("a-cal").innerHTML = html;
    renderDay();
  }

  function renderDay() {
    $("a-day-title").textContent = fmtDay(selDay);
    const evs = eventsOn(selDay), tds = todos.filter(t => t.due === selDay);
    const rep = o => o.repeat !== "none" ? `<span class="due" title="${esc(REPEAT[o.repeat])} depuis le ${parse(o.series_start).toLocaleDateString("fr-FR")}">↻ ${esc(REPEAT[o.repeat].toLowerCase())}</span>` : "";
    const fts = fetesOn(selDay);
    $("a-day").innerHTML = `
      ${fts.map(f => `<div class="item ag-fete${f.ferie ? " ferie" : ""}"><span class="t">${f.icone}</span>
        <span class="x">${esc(f.nom)}</span><span class="due">${f.ferie ? "jour férié" : "fête"}</span></div>`).join("")}
      ${evs.map(o => `<div class="item ag-ev${editing && editing.occurrence === o.id ? " editing" : ""}">
        <span class="t">${o.time || (o.birthday ? "🎂" : "journée")}</span>
        <span class="x">${esc(evLabel(o).replace(/^🎂 /, ""))}${o.duration ? ` <small class="muted">· ${fmtDur(o.duration)}</small>` : ""}
          ${o.description ? `<small class="ag-desc">${esc(o.description)}</small>` : ""}</span>${rep(o)}
        ${o.exception ? `<span class="due" title="Cette occurrence a été modifiée seule">modifié</span>` : ""}
        <button class="del" data-edit="${esc(o.id)}" title="Modifier" aria-label="Modifier ${esc(o.title)}">✎</button>
        <button class="del" data-del="${esc(o.id)}" title="Supprimer" aria-label="Supprimer ${esc(o.title)}">✕</button></div>`).join("")}
      ${tds.map(t => `<div class="item${t.done ? " done" : ""}"><input type="checkbox" data-todo="${t.id}" ${t.done ? "checked" : ""} aria-label="Terminée">
        <span class="x">${esc(t.text)}</span><span class="due">to-do</span></div>`).join("")}
      ${!evs.length && !tds.length && !fts.length ? `<div class="muted" style="font-size:15px;padding:4px 0">Rien de prévu.</div>` : ""}`;
    // le formulaire n'est refait que si on change de jour : une saisie en cours n'est jamais effacée
    const form = $("a-form");
    if (!editing && form.dataset.formDay !== selDay) {
      if (form.elements.title && form.elements.title.value.trim()) { form.elements.date.value = selDay; form.dataset.formDay = selDay; }
      else renderForm();
    }
  }

  // ---- Formulaire : nouvel évènement ou modification ----
  function renderForm(o = null) {
    const e = o ? events[o.event_id] : null;
    editing = o ? { event: e, occurrence: o.id, original: o.original_date, occ: o } : null;
    const v = o ? { title: o.title, date: o.date, time: o.time || "", duration: o.duration || "", description: o.description || "",
                    repeat: o.repeat, until: o.until || "", birthday: o.birthday, birth_year: o.birth_year || "",
                    reminders: o.reminders } :
                  { title: "", date: selDay, time: "", duration: "", description: "", repeat: "none", until: "", birthday: false,
                    birth_year: "", reminders: null };
    const custom = v.reminders != null;
    $("a-form").dataset.formDay = o ? "edition" : selDay;
    $("a-form").innerHTML = `
      <h3>${o ? (o.birthday ? "Modifier l'anniversaire" : "Modifier l'évènement") : "Nouvel évènement"}</h3>
      ${o && o.repeat !== "none" ? `<p class="muted ag-note">↻ Fait partie d'une série (${esc(REPEAT[o.repeat].toLowerCase())}). À l'enregistrement, tu choisiras : cette occurrence, les suivantes, ou toute la série.</p>` : ""}
      <label class="ag-f"><span>Titre ${v.birthday ? "(prénom)" : ""}</span><input class="in" name="title" maxlength="120" value="${esc(v.title)}" required><em data-err="title"></em></label>
      <label class="ag-chk"><input type="checkbox" name="birthday" ${v.birthday ? "checked" : ""}> 🎂 C'est un anniversaire (chaque année, toute la journée)</label>
      <div class="ag-row">
        <label class="ag-f"><span>Date</span><input class="in" type="date" name="date" value="${esc(v.date)}" required><em data-err="date"></em></label>
        <label class="ag-f ag-time"><span>Heure</span><input class="in" type="time" name="time" value="${esc(v.time)}"><em data-err="time"></em></label>
        <label class="ag-f ag-time"><span>Durée (min)</span><input class="in" type="number" name="duration" min="1" max="20160" step="5" value="${esc(v.duration)}" placeholder="—"><em data-err="duration"></em></label>
      </div>
      <small class="muted ag-time">Sans heure = toute la journée (rappels calculés depuis ${esc(defaults.heure_reference)}).</small>
      <div class="ag-row ag-norep">
        <label class="ag-f"><span>Répétition</span><select class="in" name="repeat">${Object.entries(REPEAT).map(([k, t]) => `<option value="${k}" ${k === v.repeat ? "selected" : ""}>${esc(t)}</option>`).join("")}</select><em data-err="repeat"></em></label>
        <label class="ag-f ag-until"><span>Jusqu'au (facultatif)</span><input class="in" type="date" name="until" value="${esc(v.until)}"><em data-err="until"></em></label>
      </div>
      <label class="ag-f ag-byear"><span>Année de naissance (pour l'âge, facultatif)</span><input class="in" type="number" name="birth_year" min="1900" max="${new Date().getFullYear()}" value="${esc(v.birth_year)}"><em data-err="birth_year"></em></label>
      <label class="ag-f"><span>Description (facultatif)</span><textarea class="in" name="description" rows="2" maxlength="2000">${esc(v.description)}</textarea><em data-err="description"></em></label>
      <fieldset class="ag-rem"><legend>Rappels</legend>
        <label class="ag-chk"><input type="radio" name="rem_mode" value="defaut" ${custom ? "" : "checked"}> Par défaut : ${esc(fmtRem(defaults.rappels_minutes) || "aucun")} avant</label>
        <label class="ag-chk"><input type="radio" name="rem_mode" value="perso" ${custom ? "checked" : ""}> Personnalisés (minutes avant, séparées par des virgules) :</label>
        <input class="in" name="reminders" value="${custom ? esc(v.reminders.join(", ")) : esc(defaults.rappels_minutes.join(", "))}" placeholder="ex. 1440, 60, 10 — vide = aucun rappel" ${custom ? "" : "disabled"}>
        <em data-err="reminders"></em>
      </fieldset>
      <div class="form-row ag-actions">
        <button class="btn big" type="submit">${o ? "Enregistrer" : "Ajouter"}</button>
        ${o ? `<button class="btn" type="button" data-cancel>Annuler</button>
               <button class="btn danger" type="button" data-del="${esc(o.id)}">Supprimer</button>` : ""}
      </div>`;
    syncForm();
  }

  function syncForm() {
    const f = $("a-form");
    if (!f.elements.title) return;
    const bday = f.elements.birthday.checked;
    f.querySelectorAll(".ag-time").forEach(el => { el.hidden = bday; });
    f.querySelector(".ag-norep").hidden = bday;
    f.querySelector(".ag-byear").hidden = !bday;
    f.querySelector(".ag-until").hidden = f.elements.repeat.value === "none";
    f.elements.reminders.disabled = f.elements.rem_mode.value !== "perso";
    f.elements.title.placeholder = bday ? "Prénom (ex. Léa)" : "Titre de l'évènement";
  }

  function formValues() {
    const f = $("a-form").elements, bday = f.birthday.checked;
    const v = { title: f.title.value.trim(), date: f.date.value, birthday: bday, description: f.description.value.trim() };
    if (bday) { v.birth_year = f.birth_year.value ? Number(f.birth_year.value) : null; v.repeat = "yearly"; v.time = null; v.duration = null; }
    else {
      v.time = f.time.value || null;
      v.duration = f.duration.value === "" ? null : Number(f.duration.value);
      v.repeat = f.repeat.value;
      v.until = v.repeat !== "none" && f.until.value ? f.until.value : null;
    }
    v.reminders = f.rem_mode.value === "perso"
      ? f.reminders.value.split(/[,; ]+/).filter(Boolean).map(Number) : null;
    return v;
  }

  function showErrors(champs) {
    const f = $("a-form");
    f.querySelectorAll("[data-err]").forEach(el => { el.textContent = (champs && champs[el.dataset.err]) || ""; });
    const firstBad = champs && Object.keys(champs)[0];
    if (firstBad && f.elements[firstBad]) f.elements[firstBad].focus();
  }

  // Vérifications locales (le serveur revérifie tout)
  function check(v) {
    const err = {};
    if (!v.title) err.title = "Le titre est obligatoire.";
    if (!v.date || isNaN(parse(v.date))) err.date = "Date invalide.";
    if (v.duration != null && !(Number.isInteger(v.duration) && v.duration > 0)) err.duration = "La durée doit être un nombre de minutes positif.";
    if (v.until && v.date && v.until < v.date) err.until = "La date de fin doit être après la date de début.";
    if (v.reminders && v.reminders.some(m => !Number.isInteger(m) || m < 0)) err.reminders = "Rappels : des nombres de minutes positifs (ex. 60, 30).";
    return err;
  }

  // Choix de la portée pour une série
  function askScope(action) {
    return new Promise(resolve => {
      const d = document.createElement("dialog");
      d.className = "pf-dlg ag-scope";
      d.innerHTML = `<h3>${action === "delete" ? "Supprimer" : "Modifier"} un évènement répété</h3>
        <div class="pf-dlg-body"><p>Quelles occurrences ${action === "delete" ? "supprimer" : "modifier"} ?</p></div>
        <div class="ag-scope-btns">
          <button class="btn big" data-v="one">Cet évènement seulement</button>
          <button class="btn big" data-v="following">Cet évènement et les suivants</button>
          <button class="btn big ${action === "delete" ? "danger" : ""}" data-v="all">Tous les évènements de la série</button>
          <button class="btn" data-v="">Annuler</button></div>`;
      document.body.appendChild(d);
      d.addEventListener("click", ev => { const b = ev.target.closest("[data-v]"); if (b) { d.close(); resolve(b.dataset.v || null); } });
      d.addEventListener("cancel", () => resolve(null));
      d.addEventListener("close", () => setTimeout(() => d.remove(), 50));
      d.showModal();
      d.querySelector("[data-v=one]").focus();
    });
  }

  async function submitForm() {
    const v = formValues();
    const err = check(v);
    showErrors(err);
    if (Object.keys(err).length) return;
    try {
      if (!editing) {
        await api("/api/agenda/evenements", { champs: v });
        toast(v.birthday ? "Anniversaire ajouté." : "Évènement ajouté.");
      } else {
        const o = editing.occ, e = editing.event;
        let scope = "all", champs = v;
        if (o.repeat !== "none") {
          scope = await askScope("edit");
          if (!scope) return;
          if (scope === "one") {   // seuls les champs d'une occurrence
            champs = Object.fromEntries(["title", "date", "time", "duration", "description", "reminders"]
              .filter(k => k in v).map(k => [k, v[k]]));
            if (v.repeat !== o.repeat || v.birthday !== o.birthday || (v.until || null) !== (o.until || null)) {
              toast("La répétition ne se change pas pour une seule occurrence : choisis « toute la série » ou « les suivants ».", true);
              return;
            }
          }
        }
        await api(`/api/agenda/evenements/${encodeURIComponent(e.id)}/modifier`, { champs, occurrence: editing.original, portee: scope });
        toast({ one: "Cette occurrence a été modifiée.", following: "Cette occurrence et les suivantes ont été modifiées.",
                all: o.repeat !== "none" ? "Toute la série a été modifiée." : "Évènement modifié." }[scope]);
      }
      selDay = v.date;
      editing = null;
      if (parse(selDay).getMonth() !== view.getMonth()) view = new Date(parse(selDay).getFullYear(), parse(selDay).getMonth(), 1);
      await refresh();
      renderForm();
    } catch (ex) {
      if (ex.data && ex.data.champs) showErrors(ex.data.champs);
      toast(ex.message, true);
    }
  }

  async function removeOcc(id) {
    const o = occ.find(x => x.id === id);
    if (!o) return;
    let scope = "all";
    if (o.repeat !== "none") { scope = await askScope("delete"); if (!scope) return; }
    else if (!confirm(`Supprimer « ${evLabel(o)} » ?`)) return;
    try {
      await api(`/api/agenda/evenements/${encodeURIComponent(o.event_id)}/supprimer`, { occurrence: o.original_date, portee: scope });
      toast(scope === "one" && o.repeat !== "none" ? "Cette occurrence a été supprimée." : scope === "following" ? "Cette occurrence et les suivantes ont été supprimées." : "Supprimé.");
      editing = null;
      await refresh();
    } catch (ex) { toast(ex.message, true); }
  }

  function renderUpcoming() {
    const now = new Date(), today = ymd(now), hm = `${pad(now.getHours())}:${pad(now.getMinutes())}`, end = ymd(addDays(now, 6));
    const list = occ.filter(o => o.date >= today && o.date <= end && !(o.date === today && o.time && o.time < hm))
      .map(o => ({ date: o.date, time: o.time || "", label: esc(evLabel(o)), cls: "" }));
    for (let d = 0; d < 7; d++) {                      // fêtes de la semaine, en tête de leur journée
      const key = ymd(addDays(now, d));
      for (const f of fetesOn(key)) list.push({ date: key, time: "", label: `${f.icone} ${esc(f.nom)}`, cls: " fete", fete: true });
    }
    list.sort((a, b) => a.date.localeCompare(b.date) || (b.fete || 0) - (a.fete || 0) || a.time.localeCompare(b.time));
    $("a-up").innerHTML = list.slice(0, 12).map(o => `<button class="item ag-up${o.cls}" data-goto="${o.date}"><span class="d">${o.date === today ? "aujourd'hui" :
      parse(o.date).toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" })}</span>
      <span class="t">${o.time}</span><span class="x">${o.label}</span></button>`).join("")
      || `<div class="empty">Rien dans les 7 prochains jours</div>`;
  }

  // ---- To-do ----
  function renderTodos() {
    const today = ymd(new Date());
    const list = [...todos].sort((a, b) => (a.done - b.done) || ((a.due || "9999").localeCompare(b.due || "9999")) || (a.created - b.created));
    $("t-sub").textContent = todos.length ? `${todos.filter(t => !t.done).length} à faire` : "";
    $("t-list").innerHTML = list.map(t => `<div class="item${t.done ? " done" : ""}">
      <input type="checkbox" data-todo="${t.id}" ${t.done ? "checked" : ""} aria-label="Terminée">
      <span class="x">${esc(t.text)}</span>
      ${t.due ? `<span class="due${!t.done && t.due < today ? " late" : ""}">${t.due === today ? "aujourd'hui" : parse(t.due).toLocaleDateString("fr-FR", { day: "numeric", month: "short" })}</span>` : ""}
      <button class="del" data-del-todo="${t.id}" aria-label="Supprimer">✕</button></div>`).join("")
      || `<div class="empty">Aucune tâche</div>`;
    $("t-clear").hidden = !todos.some(t => t.done);
  }

  // ---- Notes ----
  function renderNotes() {
    const list = [...notes].sort((a, b) => b.updated - a.updated);
    $("n-sub").textContent = list.length ? `${list.length}` : "";
    if (!list.some(n => n.id === noteId)) noteId = list.length ? list[0].id : null;
    $("n-list").innerHTML = list.map(n => `<button class="note-btn${n.id === noteId ? " sel" : ""}" data-note="${n.id}">
      <span>${esc(n.title || "Sans titre")}</span><small>${fmtAgo(n.updated / 1000)}</small></button>`).join("");
    const n = notes.find(x => x.id === noteId), ed = $("n-edit");
    if (!n) { ed.innerHTML = `<div class="empty">Aucune note. Cliquez sur « + Nouvelle note ».</div>`; ed.dataset.id = ""; return; }
    if (ed.dataset.id === n.id) return;
    ed.dataset.id = n.id;
    ed.innerHTML = `<input class="in" id="n-title" maxlength="80" placeholder="Titre" aria-label="Titre de la note">
      <textarea id="n-text" placeholder="Écrivez ici…" aria-label="Contenu de la note"></textarea>
      <div class="form-row" style="justify-content:space-between"><span class="saved" id="n-saved"></span>
      <button class="btn danger" id="n-del">Supprimer la note</button></div>`;
    $("n-title").value = n.title || "";
    $("n-text").value = n.text || "";
    const onEdit = () => {
      n.title = $("n-title").value; n.text = $("n-text").value; n.updated = Date.now();
      $("n-saved").textContent = "…";
      saveNotebook();
      const b = $("n-list").querySelector(`[data-note="${n.id}"] span`);
      if (b) b.textContent = n.title || "Sans titre";
    };
    $("n-title").addEventListener("input", onEdit);
    $("n-text").addEventListener("input", onEdit);
    $("n-del").addEventListener("click", () => {
      if (!confirm(`Supprimer la note « ${n.title || "Sans titre"} » ?`)) return;
      notes = notes.filter(x => x.id !== n.id);
      saveNotebook(true); renderNotes();
    });
  }

  function renderAll() { renderCal(); renderUpcoming(); renderTodos(); renderNotes(); }

  function goMonth(d) {
    view = new Date(d.getFullYear(), d.getMonth(), 1);
    const r = wantedRange();
    renderCal();                                   // le mois change tout de suite (évènements complétés juste après)
    if (!range || r.debut < range.debut || r.fin > range.fin) refresh();
  }

  // ---- Interactions ----
  root.addEventListener("click", ev => {
    const day = ev.target.closest("[data-day]");
    if (day) {
      selDay = day.dataset.day; editing = null;
      const d = parse(selDay);
      if (d.getMonth() !== view.getMonth()) goMonth(d); else renderCal();
      return;
    }
    const go = ev.target.closest("[data-goto]");
    if (go) { selDay = go.dataset.goto; editing = null; goMonth(parse(selDay)); renderCal(); return; }
    const ed = ev.target.closest("[data-edit]");
    if (ed) { const o = occ.find(x => x.id === ed.dataset.edit); if (o) { renderForm(o); renderDay(); $("a-form").elements.title.focus(); } return; }
    const del = ev.target.closest("[data-del]");
    if (del) { removeOcc(del.dataset.del); return; }
    if (ev.target.closest("[data-cancel]")) { editing = null; renderForm(); renderDay(); return; }    const dt = ev.target.closest("[data-del-todo]");
    if (dt) { todos = todos.filter(t => t.id !== dt.dataset.delTodo); saveNotebook(true); renderTodos(); renderCal(); return; }
    const nb = ev.target.closest("[data-note]");
    if (nb) { noteId = nb.dataset.note; renderNotes(); }
  });
  root.addEventListener("change", ev => {
    if (ev.target.closest("#a-form")) { syncForm(); return; }
    const cb = ev.target.closest("input[data-todo]");
    if (!cb) return;
    const t = todos.find(x => x.id === cb.dataset.todo);
    if (t) { t.done = cb.checked; saveNotebook(true); renderTodos(); renderCal(); }
  });
  root.addEventListener("submit", ev => {
    ev.preventDefault();
    if (ev.target.id === "a-form") submitForm();
    else if (ev.target.id === "t-form") {
      const text = $("t-text").value.trim();
      if (!text) return;
      todos.push({ id: uid(), text, done: false, due: $("t-due").value || null, created: Date.now() });
      $("t-text").value = ""; $("t-due").value = "";
      saveNotebook(true); renderTodos(); renderCal();
    }
  });
  $("t-clear").addEventListener("click", () => { todos = todos.filter(t => !t.done); saveNotebook(true); renderTodos(); renderCal(); });
  $("n-new").addEventListener("click", () => {
    const n = { id: uid(), title: "", text: "", updated: Date.now() };
    notes.push(n); noteId = n.id; saveNotebook(true); renderNotes(); $("n-title").focus();
  });
  $("a-prev").addEventListener("click", () => goMonth(new Date(view.getFullYear(), view.getMonth() - 1, 1)));
  $("a-next").addEventListener("click", () => goMonth(new Date(view.getFullYear(), view.getMonth() + 1, 1)));
  $("a-fetes").value = ["toutes", "feries", "aucune"].includes(fetesMode) ? fetesMode : "toutes";
  $("a-fetes").addEventListener("change", ev => {
    fetesMode = ev.target.value;
    try { localStorage.setItem(FETES_KEY, fetesMode); } catch (e) {}
    renderCal(); renderUpcoming();
  });
  $("a-today").addEventListener("click", () => { selDay = ymd(new Date()); editing = null; goMonth(new Date()); });

  // Pour le sommaire : prochains évènements (répétitions comprises) et tâches ouvertes
  window.agendaSummary = (days = 7) => {
    if (!loaded) return null;
    const now = new Date(), today = ymd(now), hm = `${pad(now.getHours())}:${pad(now.getMinutes())}`, end = ymd(addDays(now, days - 1));
    return { next: occ.filter(o => o.date >= today && o.date <= end && !(o.date === today && o.time && o.time < hm))
                      .map(o => ({ key: o.date, time: o.time, label: evLabel(o) })),
             todos: todos.filter(t => !t.done).length };
  };
  window.agendaRefresh = refresh;       // utilisé après un rappel, et toutes les 5 min (changement de jour…)
  setInterval(() => { if (!document.hidden) refresh(); }, 5 * 60 * 1000);

  refresh();
  Tabs.register("agenda", { show() { if (loaded) renderAll(); board.refresh(); } });
})();
