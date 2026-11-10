"use strict";
// ===== Version du panel et mises à jour =====
// Bouton « vX.Y.Z » de la barre du haut (et boutons Version du sommaire et des Réglages) → fenêtre : version installée,
// date, profil actif, dernière vérification, mise à jour disponible (changelog, taille) avec « Installer » (mot de passe
// du panel) ou « Plus tard », retour à la version précédente, notes de version.
// Pastille sur le bouton + petite bannière quand une version plus récente existe ; écran de transition NEXUS (couleurs
// du profil) pendant l'installation et le redémarrage, puis retour au panel.
(() => {
  const btn = $("btn-ver");
  const dlg = document.createElement("dialog");
  dlg.className = "ver-dlg";
  dlg.setAttribute("aria-labelledby", "ver-title");
  document.body.appendChild(dlg);
  const ban = document.createElement("div");
  ban.className = "nx-maj-ban"; ban.hidden = true; ban.setAttribute("role", "status");
  document.body.appendChild(ban);

  let info = null, maj = null, profils = null;
  const seenKey = "panel-version-seen";
  const getSeen = () => { try { return localStorage.getItem(seenKey); } catch (e) { return null; } };
  const setSeen = v => { try { localStorage.setItem(seenKey, v); } catch (e) {} };
  const dateFr = d => d ? new Date(d.length === 10 ? d + "T12:00" : d).toLocaleDateString("fr-FR", { dateStyle: "long" }) : "";
  const quand = t => t ? new Date(t * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" }) : "jamais";

  function profilActif() {
    const p = window.nexusProfile;
    return p ? `${esc(p.nom || p.id)}${p.version ? ` <small>v${esc(p.version)}</small>` : ""}` : "Défaut <small>(intégré)</small>";
  }

  // Notes de release (Markdown simple de GitHub) : titres, puces, **gras**, `code` ; tout le reste est échappé
  function notesHtml(md) {
    const inl = s => esc(s).replace(/\*\*([^*]+)\*\*/g, "<b>$1</b>").replace(/`([^`]+)`/g, "<code>$1</code>");
    let html = "", liste = false;
    for (const brut of String(md || "").split(/\r?\n/)) {
      const l = brut.trim(), puce = /^[-*] /.test(l);
      if (liste && !puce) { html += "</ul>"; liste = false; }
      if (!l) continue;
      const h = l.match(/^#{1,6}\s+(.*)$/);
      if (h) html += `<b class="maj-notes-h">${inl(h[1])}</b>`;
      else if (puce) { if (!liste) { html += "<ul>"; liste = true; } html += `<li>${inl(l.slice(2))}</li>`; }
      else html += `<p>${inl(l)}</p>`;
    }
    return (liste ? html + "</ul>" : html) || "<p>(pas de notes de version)</p>";
  }
  function blocProfils() {
    if (!profils) return "";
    const actif = document.documentElement.dataset.profile || "defaut";
    return `<div class="maj-profils">${profils.filter(p => !p.integre).map(p =>
      `<span class="${p.id === actif ? "on" : ""}">${esc(p.nom)} <small>v${esc(p.version)}</small></span>`).join("")}</div>`;
  }

  function blocMaj() {
    if (!maj) return `<div class="empty">Chargement…</div>`;
    const v = maj.verification || {}, r = maj.reglages || {};
    const etat = !r.depot ? `Aucun dépôt configuré : ⚙ Réglages → Mises à jour.`
      : v.resultat === "erreur" ? `<span class="t-warn">⚠ ${esc(v.erreur || "erreur")}</span>`
      : v.resultat === "ok" ? (v.a_jour ? "✔ Tu as la dernière version." : "Une version plus récente existe.")
      : "Pas encore vérifié.";
    const d = maj.disponible;
    const travail = maj.travail || {};
    return `
      <div class="maj-etat">
        <div><small>Dépôt surveillé</small><b>${r.depot ? esc(r.depot) : "—"}</b></div>
        <div><small>Dernière vérification</small><b>${quand(v.derniere)}</b></div>
        <div><small>Vérification automatique</small><b>${r.actif ? `toutes les ${r.intervalle_heures} h` : "désactivée"}</b></div>
        <div><small>Jeton (dépôt privé)</small><b>${maj.jeton.enregistre ? ({ windows: "enregistré (Windows)", config: "enregistré (config.json)", environnement: "variable d'environnement" }[maj.jeton.ou] || "enregistré") : "aucun"}</b></div>
      </div>
      <p class="maj-msg">${etat}</p>
      <div class="form-row"><button class="btn" data-maj="verifier">⟳ Vérifier maintenant</button>
        ${maj.retour_possible ? `<button class="btn" data-maj="revenir">↶ Revenir à la version précédente (v${esc(maj.sauvegardes[0].version)})</button>` : ""}</div>
      ${travail.etape === "erreur" ? `<p class="t-warn">⚠ Installation impossible : ${esc(travail.erreur)}</p>` : ""}
      ${d ? `
        <section class="maj-dispo">
          <div class="ver-line"><b>Version ${esc(d.version)} disponible</b>
            <small>${dateFr(d.date)}${d.archive && d.archive.taille ? " · " + fmtBytes(d.archive.taille) : ""}</small></div>
          <div class="maj-notes">${notesHtml(d.notes)}</div>
          <div class="form-row maj-actions">
            <input class="in" type="password" id="maj-mdp" autocomplete="current-password" placeholder="Mot de passe du panel" aria-label="Mot de passe du panel">
            <button class="btn on" data-maj="installer">⬇ Installer la version ${esc(d.version)}</button>
            <button class="btn" data-maj="plus-tard">Plus tard</button>
          </div>
          <small class="muted">Rien ne s'installe sans ton clic et ton mot de passe. Avant d'installer : vérification de
            l'archive (SHA256), sauvegarde du code, de tes données et de ta configuration ; en cas de problème au
            redémarrage, la version actuelle est restaurée automatiquement.</small>
        </section>` : ""}`;
  }

  function render() {
    const snaps = info.snapshots;
    dlg.innerHTML = `
      <div class="ver-head">
        <h2 id="ver-title">NEXUS <span class="ver-num">v${esc(info.version)}</span></h2>
        <button class="btn" id="ver-close" aria-label="Fermer">✕</button>
      </div>
      <div class="ver-body">
        <div class="maj-etat">
          <div><small>Version installée</small><b>v${esc(info.version)}</b></div>
          <div><small>Date</small><b>${dateFr(info.date) || "—"}</b></div>
          <div><small>Profil actif</small><b>${profilActif()}</b></div>
        </div>
        <div class="section-title">Profils visuels installés</div>
        <div id="maj-profils">${blocProfils()}</div>
        <div class="section-title">Mises à jour</div>
        <div id="maj-bloc">${blocMaj()}</div>
        <div class="section-title">Notes de version</div>
        ${info.changelog.map(e => `
          <section class="ver-entry${e.version === info.version ? " cur" : ""}">
            <div class="ver-line"><b>v${esc(e.version)}</b> <span>${esc(e.title)}</span>
              <small>${dateFr(e.date)}</small>
              ${e.version === info.version ? `<em>version actuelle</em>` : ""}</div>
            <ul>${e.items.map(x => `<li>${esc(x)}</li>`).join("")}</ul>
          </section>`).join("")}
        <div class="section-title">Sauvegardes de code</div>
        ${snaps.length ? snaps.slice(0, 8).map(s => `<div class="outage"><span>versions\\${esc(s.file)}</span>
          <b>${fmtBytes(s.size)} · ${new Date(s.time * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</b></div>`).join("")
          : `<div class="empty">Aucune sauvegarde pour l'instant.</div>`}
      </div>`;
    $("ver-close").addEventListener("click", () => dlg.close());
  }
  const majBloc = () => { const b = $("maj-bloc"); if (b) b.innerHTML = blocMaj(); };

  async function charger() {
    try { maj = await api("/api/maj"); } catch (e) { maj = null; }
    pastille();
  }
  async function ouvrir() {
    try { info = await api("/api/version"); } catch (e) { toast("Version : " + e.message, true); return; }
    render();
    if (!dlg.open) dlg.showModal();
    setSeen(info.version);
    btn.classList.remove("new");
    await charger(); majBloc();
    try { profils = (await api("/api/profils")).profils; const b = $("maj-profils"); if (b) b.innerHTML = blocProfils(); } catch (e) {}
  }
  window.nxVersion = { ouvrir };

  dlg.addEventListener("click", async ev => {
    if (ev.target === dlg) { dlg.close(); return; }
    const b = ev.target.closest("[data-maj]");
    if (!b) return;
    const a = b.dataset.maj;
    try {
      if (a === "verifier") { b.disabled = true; b.textContent = "⟳ Vérification…"; maj = await api("/api/maj/verifier", {}); majBloc(); pastille(); }
      else if (a === "plus-tard") { maj = await api("/api/maj/plus-tard", { heures: 24 }); majBloc(); pastille(); toast("D'accord : rappel dans 24 h."); }
      else if (a === "installer" || a === "revenir") {
        let mdp = ($("maj-mdp") || {}).value;
        if (!mdp) mdp = prompt(a === "installer" ? "Mot de passe du panel pour installer :" : "Mot de passe du panel pour revenir à la version précédente :");
        if (!mdp) return;
        if (a === "revenir" && !confirm(`Revenir à la version ${maj.sauvegardes[0].version} ? Le panel va redémarrer (tes données sont gardées).`)) return;
        const vers = a === "installer" ? maj.disponible.version : maj.sauvegardes[0].version;
        await api("/api/maj/" + a, { mot_de_passe: mdp });
        dlg.close();
        ecranTransition(vers, a);
      }
    } catch (e) { toast("Mise à jour : " + e.message, true); if (a === "verifier") { await charger(); majBloc(); } }
  });

  // ---- pastille sur le bouton + bannière discrète ----
  function pastille() {
    const d = maj && maj.disponible;
    btn.classList.toggle("maj-dispo", !!d);
    btn.title = d ? `Version ${d.version} disponible : voir` : "Version et mises à jour";
    const res = maj && maj.dernier_resultat;
    if (res) {
      ban.hidden = false;
      ban.className = "nx-maj-ban " + (res.ok ? "ok" : "ko");
      ban.innerHTML = `<span>${res.ok ? "✔" : "⚠"} ${esc(res.message)}</span><button class="btn" data-ban="vu">OK</button>`;
    } else if (d && !maj.rappel_repousse) {
      ban.hidden = false; ban.className = "nx-maj-ban";
      ban.innerHTML = `<span>🆕 NEXUS ${esc(d.version)} est disponible${d.archive && d.archive.taille ? ` (${fmtBytes(d.archive.taille)})` : ""}.</span>
        <button class="btn on" data-ban="voir">Voir</button><button class="btn" data-ban="plus-tard">Plus tard</button>`;
    } else ban.hidden = true;
  }
  ban.addEventListener("click", async ev => {
    const b = ev.target.closest("[data-ban]");
    if (!b) return;
    if (b.dataset.ban === "voir") ouvrir();
    if (b.dataset.ban === "plus-tard") { try { maj = await api("/api/maj/plus-tard", { heures: 24 }); } catch (e) {} pastille(); }
    if (b.dataset.ban === "vu") { try { await api("/api/maj/resultat-vu", {}); } catch (e) {} maj.dernier_resultat = null; pastille(); }
  });

  // ---- écran de transition pendant l'installation et le redémarrage ----
  function ecranTransition(vers, mode) {
    const ov = document.createElement("div");
    ov.className = "nx-maj-ecran";
    ov.innerHTML = `<div class="nx-maj-boite">
        <img src="/static/nexus-logo.svg" alt="" class="nx-maj-logo">
        <div class="nx-maj-titre">NEXUS</div>
        <div class="nx-maj-txt" id="nx-maj-txt">${mode === "revenir" ? "Retour à la version " : "Mise à jour vers la version "}${esc(vers)}</div>
        <div class="nx-maj-barre"><i id="nx-maj-fill"></i></div>
        <div class="nx-maj-etape" id="nx-maj-etape">Préparation…</div>
      </div>`;
    document.body.appendChild(ov);
    const ETAPES = { telechargement: "Téléchargement de l'archive…", verification: "Vérification de l'empreinte SHA256…",
      sauvegarde: "Sauvegarde du code, de tes données et de ta configuration…", redemarrage: "Redémarrage du panel…" };
    let vuArret = false, t0 = Date.now();
    const fill = p => { $("nx-maj-fill").style.width = Math.max(4, Math.min(100, p)) + "%"; };
    const tour = async () => {
      let r = null;
      try { r = await (await fetch("/api/maj", { cache: "no-store" })).json(); } catch (e) { vuArret = true; }
      if (r) {
        const tr = r.travail || {};
        if (vuArret || (r.version === vers && mode !== "revenir") || (mode === "revenir" && vuArret)) {
          $("nx-maj-etape").textContent = "Version " + r.version + " prête : retour au panel…"; fill(100);
          setTimeout(() => location.reload(), 700); return;
        }
        if (tr.etape === "erreur") {
          $("nx-maj-etape").innerHTML = `⚠ ${esc(tr.erreur)} <button class="btn" onclick="this.closest('.nx-maj-ecran').remove()">Fermer</button>`;
          return;
        }
        $("nx-maj-etape").textContent = ETAPES[tr.etape] || "Préparation…";
        fill(tr.etape === "telechargement" ? 10 + (tr.progres || 0) * .5 : tr.etape === "verification" ? 65 : tr.etape === "sauvegarde" ? 78 : 88);
      } else {
        $("nx-maj-etape").textContent = "Redémarrage du panel et test de la nouvelle version…";
        fill(88 + Math.min(11, (Date.now() - t0) / 3000));
      }
      if (Date.now() - t0 > 6 * 60 * 1000) { $("nx-maj-etape").textContent = "Le panel tarde à revenir : regarde sa fenêtre noire."; return; }
      setTimeout(tour, 700);
    };
    tour();
  }

  btn.addEventListener("click", ouvrir);
  api("/api/version").then(r => {
    info = r;
    btn.textContent = "v" + r.version;
    const seen = getSeen();
    if (seen && seen !== r.version) { btn.classList.add("new"); }
    if (!seen) setSeen(r.version);
  }).catch(() => {});
  charger();
  setInterval(() => { if (!document.hidden) charger(); }, 10 * 60 * 1000);   // l'état vient du serveur (qui vérifie seul)
})();
