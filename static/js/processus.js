"use strict";
/* Classement des processus (onglet PC, bouton « ▤ Classement » de la carte Processus) : tous les programmes
   regroupés par nom, triés par processeur ou par mémoire, rafraîchis toutes les 2 s. Bouton « Fermer » avec
   confirmation (comme « Fin de tâche ») ; jamais un processus vital de Windows ni NEXUS lui-même (refusé aussi
   par le serveur), et seulement depuis le PC. Chaque fermeture est notée dans le journal d'activité. */
(() => {
  const dlg = document.createElement("dialog");
  dlg.className = "ver-dlg proc-dlg";
  dlg.setAttribute("aria-labelledby", "proc-titre");
  document.body.appendChild(dlg);
  let tri = "cpu", timer = null, data = null, enCours = null;

  function lignes() {
    if (!data) return `<div class="empty">Analyse en cours…</div>`;
    const total = (window.lastStats && window.lastStats.ram.total) || 1;
    const max = Math.max(1, ...data.processus.map(p => tri === "ram" ? p.ram : p.cpu));
    return `<table class="tbl proc-tbl"><thead><tr><th>#</th><th>Programme</th><th>Processeur</th><th>Mémoire</th><th></th></tr></thead><tbody>
      ${data.processus.map((p, i) => {
        const part = (tri === "ram" ? p.ram : p.cpu) / max * 100;
        return `<tr><td class="muted">${i + 1}</td>
          <td><b>${esc(p.name)}</b>${p.count > 1 ? ` <small class="muted">×${p.count}</small>` : ""}
            <span class="proc-part" aria-hidden="true"><i style="width:${part.toFixed(1)}%"></i></span></td>
          <td>${p.cpu.toFixed(1)} %</td><td>${fmtBytes(p.ram)} <small class="muted">${(p.ram / total * 100).toFixed(1)} %</small></td>
          <td>${p.protege ? `<small class="muted" title="Processus vital de Windows ou NEXUS lui-même">protégé</small>`
            : `<button class="btn danger" data-fermer="${esc(p.name)}" ${enCours === p.name ? "disabled" : ""}
                aria-label="Fermer ${esc(p.name)}">${enCours === p.name ? "Fermeture…" : "✖ Fermer"}</button>`}</td></tr>`;
      }).join("")}</tbody></table>`;
  }
  function render() {
    dlg.innerHTML = `
      <div class="ver-head"><h2 id="proc-titre">Classement des processus</h2>
        <button class="btn" data-proc="fermer-fenetre" aria-label="Fermer la fenêtre">✕</button></div>
      <div class="ver-body">
        <div class="form-row" role="group" aria-label="Trier par">
          <button class="btn${tri === "cpu" ? " on" : ""}" data-tri="cpu">Trier par processeur</button>
          <button class="btn${tri === "ram" ? " on" : ""}" data-tri="ram">Trier par mémoire</button>
          <small class="muted" id="proc-info"></small>
        </div>
        <div id="proc-liste">${lignes()}</div>
        <small class="muted">« Fermer » ferme toutes les fenêtres de ce programme (comme « Fin de tâche ») : le travail non
          enregistré y est perdu. Les processus vitaux de Windows et NEXUS lui-même ne peuvent pas être fermés.</small>
      </div>`;
  }
  async function charger() {
    try { data = await api("/api/processus?tri=" + tri); } catch (e) { return; }
    const l = $("proc-liste"); if (l) l.innerHTML = lignes();
    const info = $("proc-info");
    if (info) info.textContent = `${data.total} programmes${data.paused ? " · figé pendant le mode jeu" : ""}`;
  }
  async function ouvrir() {
    render();
    if (!dlg.open) dlg.showModal();
    await charger();
    clearInterval(timer);
    timer = setInterval(() => { if (!document.hidden && !enCours) charger(); }, 2000);
  }
  dlg.addEventListener("close", () => { clearInterval(timer); timer = null; });
  dlg.addEventListener("click", async ev => {
    if (ev.target === dlg) { dlg.close(); return; }
    const b = ev.target.closest("button");
    if (!b) return;
    if (b.dataset.proc === "fermer-fenetre") { dlg.close(); return; }
    if (b.dataset.tri) { tri = b.dataset.tri; render(); charger(); return; }
    const nom = b.dataset.fermer;
    if (!nom) return;
    const p = data && data.processus.find(x => x.name === nom);
    const n = p ? p.count : 1;
    if (!confirm(`Fermer « ${nom} »${n > 1 ? ` (${n} processus)` : ""} ?\n\nLe programme est arrêté tout de suite : ce qui n'est pas enregistré y sera perdu.`)) return;
    enCours = nom; charger();
    try {
      const r = await api("/api/processus/fermer", { nom, confirmation: nom });
      toast(r.refuses ? `${nom} : ${r.fermes}/${r.trouves} fermé(s), ${r.refuses} refusé(s) par Windows (droits administrateur ?)`
        : `${nom} fermé${r.trouves > 1 ? ` (${r.trouves} processus)` : ""}${r.forces ? ", arrêt forcé" : ""}.`, !!r.refuses);
    } catch (e) { toast("Fermeture impossible : " + e.message, true); }
    enCours = null;
    setTimeout(charger, 600);
  });
  $("btn-proc-classement").addEventListener("click", ev => { ev.stopPropagation(); ouvrir(); });
  window.nxProcessus = { ouvrir };
})();
