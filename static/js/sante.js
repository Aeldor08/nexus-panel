"use strict";
/* Santé de NEXUS (bouton ✚ du haut, lien du sommaire) : état de chaque service (serveur, bot Discord,
   LibreHardwareMonitor, carte graphique, suivi des statistiques, lecture en cours, mises à jour, base, disque,
   téléphone), dernières erreurs du serveur, et journal d'activité des actions sensibles (deck, mises à jour,
   appareils, processus, focus). Pastille sur le bouton quand quelque chose ne va pas. */
(() => {
  const btn = $("btn-sante");
  const dlg = document.createElement("dialog");
  dlg.className = "ver-dlg sante-dlg";
  dlg.setAttribute("aria-labelledby", "sante-titre");
  document.body.appendChild(dlg);
  let onglet = "etat", cat = "", timer = null, donnees = null, journal = null;

  const ICONES = { ok: "●", attention: "▲", erreur: "✖", inactif: "○" };
  const NOMS = { ok: "OK", attention: "à surveiller", erreur: "problème", inactif: "inactif" };
  const heure = t => new Date(t * 1000).toLocaleString("fr-FR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const RES = { ok: "t-ok", refusé: "t-hot", erreur: "t-hot", partiel: "t-warn" };

  function blocEtat() {
    if (!donnees) return `<div class="empty">Chargement…</div>`;
    const e = donnees.erreurs;
    return `
      <div class="sante-liste">${donnees.elements.map(x => `
        <div class="sante-el s-${x.etat}"><span class="sante-ico" aria-hidden="true">${ICONES[x.etat]}</span>
          <b>${esc(x.nom)}</b><span class="sante-etat">${NOMS[x.etat]}</span><small>${esc(x.detail)}</small></div>`).join("")}</div>
      <div class="section-title">Dernières erreurs du serveur</div>
      ${e.length ? `<div class="sante-err">${e.slice(0, 40).map(x => `
        <div class="${x.niveau === "erreur" ? "t-hot" : "t-warn"}"><small>${heure(x.t)} · ${esc(x.source)}${x.n > 1 ? ` · ×${x.n}` : ""}</small>
          <code>${esc(x.message)}</code></div>`).join("")}</div>`
        : `<div class="empty">Aucune erreur depuis le démarrage du serveur ✔</div>`}`;
  }

  function blocJournal() {
    if (!journal) return `<div class="empty">Chargement…</div>`;
    const cats = journal.categories;
    return `
      <div class="form-row sante-filtres" role="group" aria-label="Filtrer le journal">
        <button class="btn${cat === "" ? " on" : ""}" data-cat="">Tout</button>
        ${Object.entries(cats).map(([k, v]) => `<button class="btn${cat === k ? " on" : ""}" data-cat="${k}">${esc(v)}</button>`).join("")}
      </div>
      ${journal.evenements.length ? `<table class="tbl sante-journal"><thead><tr><th>Quand</th><th>Type</th><th>Action</th><th>Résultat</th><th>Détail</th><th>Appareil</th></tr></thead>
        <tbody>${journal.evenements.map(x => `<tr><td>${heure(x.t)}</td><td>${esc(cats[x.cat] || x.cat)}</td><td>${esc(x.action)}</td>
          <td class="${RES[x.resultat] || ""}">${esc(x.resultat)}</td><td>${esc(x.detail)}</td>
          <td>${esc(x.ip && x.ip !== "127.0.0.1" && x.ip !== "::1" ? x.ip : x.source === "discord" ? "Discord" : "ce PC")}</td></tr>`).join("")}</tbody></table>`
        : `<div class="empty">Rien dans le journal${cat ? " pour ce type" : ""} pour l'instant.</div>`}
      <small class="muted">Gardé sur ce PC (data\\activite.jsonl, jamais partagé) ; les 2000 derniers évènements environ.</small>`;
  }

  function render() {
    dlg.innerHTML = `
      <div class="ver-head">
        <h2 id="sante-titre">Santé de NEXUS</h2>
        <button class="btn" data-sante="fermer" aria-label="Fermer">✕</button>
      </div>
      <div class="ver-body">
        <div class="form-row sante-onglets" role="tablist">
          <button class="btn${onglet === "etat" ? " on" : ""}" role="tab" aria-selected="${onglet === "etat"}" data-onglet="etat">État et erreurs</button>
          <button class="btn${onglet === "journal" ? " on" : ""}" role="tab" aria-selected="${onglet === "journal"}" data-onglet="journal">Journal d'activité</button>
        </div>
        <div id="sante-contenu">${onglet === "etat" ? blocEtat() : blocJournal()}</div>
      </div>`;
  }
  const contenu = () => { const c = $("sante-contenu"); if (c) c.innerHTML = onglet === "etat" ? blocEtat() : blocJournal(); };

  async function charger() {
    try { donnees = await api("/api/sante"); } catch (e) { donnees = null; }
    pastille();
    if (dlg.open && onglet === "etat") contenu();
  }
  async function chargerJournal() {
    try { journal = await api("/api/activite?n=300" + (cat ? "&cat=" + encodeURIComponent(cat) : "")); } catch (e) { journal = { evenements: [], categories: {} }; }
    if (dlg.open && onglet === "journal") contenu();
  }
  function pastille() {
    const r = donnees ? donnees.resume : "ok";
    btn.classList.toggle("s-attention", r === "attention");
    btn.classList.toggle("s-erreur", r === "erreur");
    btn.title = r === "ok" ? "Santé de NEXUS : tout va bien" : r === "attention" ? "Santé de NEXUS : quelque chose est à surveiller" : "Santé de NEXUS : un service a un problème";
  }

  async function ouvrir(o) {
    if (o) onglet = o;
    render();
    if (!dlg.open) dlg.showModal();
    await Promise.all([charger(), chargerJournal()]);
    contenu();
    clearInterval(timer);
    timer = setInterval(() => { if (!document.hidden) { charger(); if (onglet === "journal") chargerJournal(); } }, 4000);
  }
  dlg.addEventListener("close", () => { clearInterval(timer); timer = null; });
  dlg.addEventListener("click", ev => {
    if (ev.target === dlg) { dlg.close(); return; }
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.sante === "fermer") dlg.close();
    else if (b.dataset.onglet) { onglet = b.dataset.onglet; render(); contenu(); if (onglet === "journal") chargerJournal(); }
    else if (b.dataset.cat !== undefined) { cat = b.dataset.cat; journal = null; contenu(); chargerJournal(); }
  });
  btn.addEventListener("click", () => ouvrir());
  window.nxSante = { ouvrir };
  charger();
  setInterval(() => { if (!document.hidden && !dlg.open) charger(); }, 60000);
})();
