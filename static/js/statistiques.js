"use strict";
// ===== Onglet Statistiques personnelles : temps de PC, de jeu, de musique, activité CPU/GPU =====
// Les mesures sont faites par le serveur (statistiques.py) : noms de processus et durées uniquement.
(() => {
  const root = $("tab-statistiques");
  const CAT_COLOR = { jeu: "var(--cyan)", musique: "var(--magenta)", video: "var(--yellow)", navigation: "var(--green)",
                      travail: "var(--ok)", autre: "var(--muted)" };
  let period = "jour", timer = null;
  const dur = s => {
    const m = Math.round((s || 0) / 60);
    return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}` : `${m} min`;
  };
  const hm = t => new Date(t * 1000).toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  const pct = v => v == null ? "–" : Math.round(v) + " %";

  root.innerHTML = `
    <div class="st-bar">
      <div class="st-periods" role="tablist">
        <button class="btn on" data-p="jour">Aujourd'hui</button><button class="btn" data-p="7j">7 jours</button><button class="btn" data-p="30j">30 jours</button>
      </div>
      <span class="st-service" id="st-service"></span>
      <button class="btn" id="st-pause">⏸ Mettre en pause</button>
      <label class="st-keep">Garder <select class="in" id="st-keep">
        ${[30, 90, 180, 365, 730, 1825].map(d => `<option value="${d}">${d >= 365 ? (d / 365) + " an" + (d >= 730 ? "s" : "") : d + " jours"}</option>`).join("")}
      </select></label>
      <button class="btn danger" id="st-clear">🗑 Tout effacer</button>
    </div>
    <div class="st-grid">
      <section class="card c-stat"><h2>Résumé <small id="st-range"></small></h2><div id="st-summary"></div></section>
      <section class="card c-stat"><h2>Par catégorie</h2><div class="st-donut-wrap"><div class="st-donut" id="st-donut"></div><div id="st-legend"></div></div></section>
      <section class="card c-stat"><h2>Jeux les plus joués</h2><div id="st-games"></div></section>
      <section class="card c-stat st-wide"><h2 id="st-days-title">Activité</h2><div class="st-chart" id="st-days"></div><div class="st-load" id="st-load"></div></section>
      <section class="card c-stat st-wide st-detail-card"><h2 id="st-dhead">Détail du jour <small id="st-dtitle"></small></h2>
        <div class="st-dnav">
          <button class="btn" id="st-dprev" aria-label="Jour précédent">◀</button>
          <button class="btn" id="st-dtoday">Aujourd'hui</button>
          <button class="btn" id="st-dnext" aria-label="Jour suivant">▶</button>
          <input class="in" type="date" id="st-dpick" aria-label="Choisir un jour">
          <small class="muted">ou clique sur une barre de « Activité par jour » (7 ou 30 jours)</small>
        </div>
        <div id="st-detail"></div></section>
      <section class="card c-stat"><h2>Autres applis <small>(premier plan, lecture)</small></h2><div id="st-apps"></div></section>
    </div>
    <p class="hint">Seuls des <b>noms de processus et des durées</b> sont enregistrés, sur ce PC : jamais de titre de fenêtre,
      d'historique de navigation, de frappe ni de contenu d'écran. Associe tes jeux et applis dans <code>jeux.json</code> (voir README).</p>`;

  const CAT_NAME = { jeu: "jeu", musique: "musique", video: "vidéo", navigation: "navigation", travail: "travail", autre: "autre" };
  function bars(list, max, withCat = false) {
    return list.map(a => `<div class="st-row"><span class="st-name">${esc(a.nom)}${withCat ? ` <small class="muted">· ${CAT_NAME[a.categorie] || ""}</small>` : ""}</span>
      <span class="st-track"><i style="width:${Math.max(2, a.secondes / max * 100)}%;background:${CAT_COLOR[a.categorie] || "var(--cyan)"}"></i></span>
      <b>${dur(a.secondes)}</b></div>`).join("");
  }

  async function load() {
    let r;
    try { r = await api(`/api/statistiques?periode=${period}`); } catch (e) { toast("Statistiques : " + e.message, true); return; }
    root.querySelectorAll("[data-p]").forEach(b => b.classList.toggle("on", b.dataset.p === period));
    const svc = r.service || {};
    $("st-service").innerHTML = r.pause ? `<b class="t-warn">⏸ Suivi en pause</b>` :
      svc.etat === "erreur" ? `<b class="t-hot">⚠ mesure en erreur</b> <small class="muted">${esc(svc.erreur || "")}</small>` :
      svc.erreur_jeux ? `<b class="t-warn">⚠ ${esc(svc.erreur_jeux)}</b>` : `<span class="dot on"></span> suivi actif`;
    $("st-pause").textContent = r.pause ? "▶ Reprendre le suivi" : "⏸ Mettre en pause";
    $("st-pause").dataset.pause = r.pause ? "1" : "0";
    $("st-keep").value = String(r.conservation_jours);
    $("st-range").textContent = r.du === r.au ? new Date(r.au + "T12:00").toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })
      : `du ${new Date(r.du + "T12:00").toLocaleDateString("fr-FR")} au ${new Date(r.au + "T12:00").toLocaleDateString("fr-FR")}`;
    const first = r.sessions[0], last = r.sessions[r.sessions.length - 1];
    const totalApps = r.categories.reduce((n, c) => n + c.secondes, 0);
    $("st-summary").innerHTML = `
      <div class="st-kpis">
        <div class="rate"><div class="label">Actif</div><div class="v">${dur(r.actif_s)}</div></div>
        <div class="rate"><div class="label">Inactif</div><div class="v">${dur(r.inactif_s)}</div></div>
        <div class="rate"><div class="label">Jeu</div><div class="v">${dur((r.categories.find(c => c.categorie === "jeu") || {}).secondes)}</div></div>
        <div class="rate"><div class="label">Musique</div><div class="v">${dur((r.categories.find(c => c.categorie === "musique") || {}).secondes)}</div></div>
      </div>
      <div class="facts">${period === "jour" ? (first ? `Début de session <b>${hm(first.debut)}</b> · dernière activité <b>${hm(last.fin)}</b> ·
        <b>${r.sessions.length}</b> session${r.sessions.length > 1 ? "s" : ""}` : "Pas encore d'activité aujourd'hui.")
        : `<b>${r.sessions.length}</b> session${r.sessions.length > 1 ? "s" : ""} · moyenne <b>${dur(r.actif_s / r.jours.length)}</b> d'activité par jour`}
        ${r.jeux[0] ? `<br>Jeu le plus joué : <b>${esc(r.jeux[0].nom)}</b> (${dur(r.jeux[0].secondes)})` : ""}</div>`;
    // camembert (conic-gradient : suit les couleurs du mode et du profil)
    let acc = 0;
    const parts = r.categories.filter(c => c.secondes > 0).map(c => {
      const a = acc; acc += c.secondes / (totalApps || 1) * 360;
      return `${CAT_COLOR[c.categorie]} ${a}deg ${acc}deg`;
    });
    $("st-donut").style.background = parts.length ? `conic-gradient(${parts.join(",")})` : "var(--track)";
    $("st-donut").setAttribute("aria-label", r.categories.map(c => `${c.nom} ${dur(c.secondes)}`).join(", "));
    $("st-legend").innerHTML = r.categories.map(c => `<div class="st-leg"><i style="background:${CAT_COLOR[c.categorie]}"></i>${c.nom}
      <b>${dur(c.secondes)}</b><small>${totalApps ? Math.round(c.secondes / totalApps * 100) : 0} %</small></div>`).join("");
    const gmax = Math.max(1, ...r.jeux.map(a => a.secondes));
    $("st-games").innerHTML = bars(r.jeux, gmax) || `<div class="empty">Aucun jeu compté sur la période.</div>`;
    const others = r.applis.filter(a => a.categorie !== "jeu");
    $("st-apps").innerHTML = bars(others, Math.max(1, ...others.map(a => a.secondes)), true) ||`<div class="empty">Rien pour l'instant.</div>`;
    // activité : par heure (aujourd'hui) ou par jour
    const pts = period === "jour" ? r.heures.map(h => ({ k: h.heure + "h", v: h.actif_s, max: 3600, cpu: h.cpu_moy, cpux: h.cpu_max, gpu: h.gpu_moy, gpux: h.gpu_max }))
      : r.jours.map(d => ({ k: new Date(d.jour + "T12:00").toLocaleDateString("fr-FR", { day: "numeric", month: "numeric" }), v: d.actif_s, max: 0,
                            cpu: d.cpu_moy, cpux: d.cpu_max, gpu: d.gpu_moy, gpux: d.gpu_max }));
    const vmax = period === "jour" ? 3600 : Math.max(3600, ...pts.map(p => p.v));
    $("st-days-title").textContent = period === "jour" ? "Activité par heure" : "Activité par jour";
    const days = period === "jour" ? null : r.jours.map(d => d.jour);
    $("st-days").innerHTML = pts.map((p, i) => {
      const tip = `${p.k} : ${dur(p.v)} actif · CPU moy. ${pct(p.cpu)} (pic ${pct(p.cpux)}) · GPU moy. ${pct(p.gpu)} (pic ${pct(p.gpux)})`;
      const inner = `<i style="height:${p.v / vmax * 100}%"></i>${p.cpu != null ? `<s style="bottom:${Math.min(100, p.cpu)}%"></s>` : ""}<span>${p.k}</span>`;
      return days ? `<button class="st-col${days[i] === dDay ? " sel" : ""}" data-sday="${days[i]}" title="${tip} — clic : détail de ce jour" aria-label="${tip}">${inner}</button>`
        : `<div class="st-col" title="${tip}">${inner}</div>`;
    }).join("");
    const withCpu = pts.filter(p => p.cpu != null);
    const avg = k => withCpu.length ? withCpu.reduce((n, p) => n + (p[k] || 0), 0) / withCpu.length : null;
    const peak = k => withCpu.length ? Math.max(...withCpu.map(p => p[k] || 0)) : null;
    $("st-load").innerHTML = `<span><i class="st-k act"></i>temps actif</span><span><i class="st-k cpu"></i>charge CPU moyenne</span>
      <span>CPU : moy. <b>${pct(avg("cpu"))}</b> · pic <b>${pct(peak("cpux"))}</b></span>
      <span>GPU : moy. <b>${pct(avg("gpu"))}</b> · pic <b>${pct(peak("gpux"))}</b></span>`;
  }

  // ---- Détail d'un jour (n'importe quel jour gardé : clic sur une barre, ◀ ▶, date) ----
  const pad = n => String(n).padStart(2, "0");
  const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const shift = (s, n) => { const d = new Date(s + "T12:00"); d.setDate(d.getDate() + n); return ymd(d); };
  let dDay = ymd(new Date());
  async function loadDetail() {
    let d;
    try { d = await api(`/api/statistiques/jour/${dDay}`); } catch (e) { $("st-detail").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    const today = ymd(new Date());
    $("st-dtitle").textContent = new Date(dDay + "T12:00").toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    $("st-dpick").value = dDay; $("st-dpick").max = today;
    $("st-dnext").disabled = dDay >= today;
    root.querySelectorAll("[data-sday]").forEach(b => b.classList.toggle("sel", b.dataset.sday === dDay));
    if (d.vide) {
      $("st-detail").innerHTML = `<div class="empty">Aucune donnée pour ce jour : le PC était éteint, le suivi était en pause,
        ou ce jour est plus ancien que la durée de conservation.</div>`;
      return;
    }
    const cats = d.categories.filter(c => c.secondes > 0).map(c => ({ ...c, nom: c.nom }));
    const block = (title, list, withCat) => `<div class="st-dblock"><h3>${title}</h3>${bars(list, Math.max(1, ...list.map(a => a.secondes)), withCat)
      || `<div class="muted">—</div>`}</div>`;
    const hmax = 3600;
    $("st-detail").innerHTML = `
      <div class="st-kpis st-dkpis">
        <div class="rate"><div class="label">Début</div><div class="v">${d.debut ? hm(d.debut) : "–"}</div></div>
        <div class="rate"><div class="label">Fin</div><div class="v">${d.fin ? hm(d.fin) : "–"}</div></div>
        <div class="rate"><div class="label">Actif</div><div class="v">${dur(d.actif_s)}</div></div>
        <div class="rate"><div class="label">Inactif</div><div class="v">${dur(d.inactif_s)}</div></div>
      </div>
      <div class="facts">${d.sessions.length} session${d.sessions.length > 1 ? "s" : ""}
        · CPU moy. <b>${pct(d.cpu_moy)}</b> (pic <b>${pct(d.cpu_max)}</b>) · GPU moy. <b>${pct(d.gpu_moy)}</b> (pic <b>${pct(d.gpu_max)}</b>)</div>
      <div class="st-frise" role="img" aria-label="Activité heure par heure">${d.heures.map(h => `<div class="st-fh" title="${h.heure} h : ${dur(h.actif_s)} actif, ${dur(h.inactif_s)} inactif · CPU ${pct(h.cpu_moy)} · GPU ${pct(h.gpu_moy)}">
        <i style="height:${Math.min(100, h.actif_s / hmax * 100)}%"></i>${h.cpu_moy != null ? `<s style="bottom:${Math.min(100, h.cpu_moy)}%"></s>` : ""}
        ${h.heure % 3 === 0 ? `<span>${h.heure}h</span>` : ""}</div>`).join("")}</div>
      <div class="st-dgrid">
        ${block("Par catégorie", cats.map(c => ({ nom: c.nom, categorie: c.categorie, secondes: c.secondes })))}
        ${block("Jeux", d.jeux)}
        ${block("Musique et médias", d.medias, true)}
        ${block("Applis", d.applis.filter(a => a.categorie !== "jeu"), true)}
      </div>`;
  }
  function goDay(s) { const t = ymd(new Date()); dDay = s > t ? t : s; loadDetail(); }
  $("st-dprev").addEventListener("click", () => goDay(shift(dDay, -1)));
  $("st-dnext").addEventListener("click", () => goDay(shift(dDay, 1)));
  $("st-dtoday").addEventListener("click", () => goDay(ymd(new Date())));
  $("st-dpick").addEventListener("change", e => { if (e.target.value) goDay(e.target.value); });

  root.addEventListener("click", async e => {
    const p = e.target.closest("[data-p]"), sd = e.target.closest("[data-sday]");
    if (p) { period = p.dataset.p; load(); }
    else if (sd) goDay(sd.dataset.sday);
  });
  $("st-pause").addEventListener("click", async () => {
    try { await api("/api/statistiques/reglages", { pause: $("st-pause").dataset.pause !== "1" }); load(); } catch (e) { toast(e.message, true); }
  });
  $("st-keep").addEventListener("change", async e => {
    try { await api("/api/statistiques/reglages", { conservation_jours: Number(e.target.value) }); toast("Durée de conservation enregistrée."); load(); }
    catch (err) { toast(err.message, true); }
  });
  $("st-clear").addEventListener("click", async () => {
    const t = prompt("Effacer TOUTES les statistiques personnelles (temps, jeux, sessions, activité) ? C'est définitif.\nTape EFFACER pour confirmer :");
    if (t !== "EFFACER") { if (t !== null) toast("Rien n'a été effacé (il fallait taper EFFACER)."); return; }
    try { await api("/api/statistiques/effacer", { confirmation: "EFFACER" }); toast("Statistiques effacées."); load(); } catch (e) { toast(e.message, true); }
  });

  Tabs.register("statistiques", {
    show() { load(); loadDetail(); clearInterval(timer); timer = setInterval(() => { if (!document.hidden) { load(); if (dDay === ymd(new Date())) loadDetail(); } }, 30000); },
    hide() { clearInterval(timer); timer = null; },
  });
})();
