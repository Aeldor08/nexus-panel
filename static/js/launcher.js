"use strict";
// ===== Onglet Lanceur : jeux Steam / Epic + applications =====
(() => {
  const root = $("tab-lanceur");
  root.innerHTML = `
    <div class="card c-launch">
      <h2>Jeux <small id="l-sub"></small></h2>
      <div class="launch-bar">
        <input class="in grow" id="l-search" type="search" placeholder="Rechercher un jeu ou une appli…" aria-label="Rechercher">
        <label class="muted" style="font-size:14px"><input type="checkbox" id="l-showhidden"> afficher les jeux masqués</label>
      </div>
      <div class="section-title">Récemment joués en premier</div>
      <div class="games" id="l-games"></div>
    </div>
    <div class="card c-launch" style="margin-top:18px">
      <h2>Applications</h2>
      <div class="apps" id="l-apps"></div>
      <details class="add-app">
        <summary class="btn big" style="display:inline-block">+ Ajouter une application</summary>
        <div class="form-row" style="margin-top:12px">
          <input class="in" id="l-name" placeholder="Nom (ex. Battle.net)" maxlength="40" style="flex:0 1 200px">
          <input class="in grow" id="l-target" placeholder="Chemin du .exe ou .lnk, ou un lien (steam://, https://…)">
          <input class="in" id="l-args" placeholder="Arguments (optionnel)" style="flex:0 1 200px">
          <button class="btn big" id="l-add">Ajouter</button>
        </div>
        <p class="hint">Astuce : clic droit sur un raccourci → <i>Copier en tant que chemin</i>, puis collez-le ici.</p>
      </details>
    </div>`;

  let data = null;

  function initials(name) {
    return name.replace(/[^\p{L}\p{N} ]/gu, "").split(/\s+/).filter(Boolean).slice(0, 2).map(w => w[0]).join("").toUpperCase() || "?";
  }

  function render() {
    if (!data) return;
    const q = $("l-search").value.trim().toLowerCase();
    const showHidden = $("l-showhidden").checked;
    const games = data.games.filter(g => (showHidden || !g.hidden) && (!q || g.name.toLowerCase().includes(q)));
    const hiddenCount = data.games.filter(g => g.hidden).length;
    $("l-sub").textContent = `${data.games.length} jeu${data.games.length > 1 ? "x" : ""}` + (hiddenCount ? ` · ${hiddenCount} masqué(s)` : "");
    $("l-games").innerHTML = games.map(g => `
      <div class="game${g.hidden ? " hidden-game" : ""}" role="button" tabindex="0" data-id="${esc(g.id)}" title="Lancer ${esc(g.name)}">
        <button class="tile-x" data-hide="${esc(g.id)}" data-state="${g.hidden ? "0" : "1"}" title="${g.hidden ? "Réafficher" : "Masquer ce jeu"}">${g.hidden ? "↺" : "✕"}</button>
        ${g.cover ? `<img class="art" src="${g.cover}" alt="" loading="lazy">` : `<div class="art ph">${esc(initials(g.name))}</div>`}
        <span class="play" aria-hidden="true">▶</span>
        <div class="info"><span class="n">${esc(g.name)}</span>
          <small>${esc(g.store)}${g.last_played ? " · " + fmtAgo(g.last_played) : ""}</small></div>
      </div>`).join("") || `<div class="empty">${q ? "Aucun jeu ne correspond" : "Aucun jeu Steam ou Epic détecté"}</div>`;
    const apps = data.apps.filter(a => !q || a.name.toLowerCase().includes(q));
    $("l-apps").innerHTML = apps.map(a => `
      <div class="app" role="button" tabindex="0" data-id="${esc(a.id)}" title="${esc(a.target)}">
        <button class="tile-x" data-remove="${esc(a.id)}" title="Retirer du lanceur">✕</button>
        <img src="${a.icon}" alt="" onerror="this.replaceWith(Object.assign(document.createElement('span'),{className:'ico-ph',textContent:'${esc(initials(a.name))}'}))">
        <span class="n">${esc(a.name)}</span>
      </div>`).join("") || `<div class="empty">Aucune application</div>`;
  }

  async function launch(id, name) {
    try {
      await api("/api/launcher/launch", { id });
      toast("▶ Lancement : " + name);
    } catch (e) { toast("Échec : " + e.message, true); }
  }

  root.addEventListener("click", async ev => {
    const hide = ev.target.closest("[data-hide]");
    if (hide) {
      ev.stopPropagation();
      await api("/api/launcher/hide", { id: hide.dataset.hide, hidden: hide.dataset.state === "1" });
      return load();
    }
    const rm = ev.target.closest("[data-remove]");
    if (rm) {
      ev.stopPropagation();
      const a = data.apps.find(x => x.id === rm.dataset.remove);
      if (a && confirm(`Retirer « ${a.name} » du lanceur ? (l'application n'est pas désinstallée)`)) {
        await api("/api/launcher/remove", { id: a.id });
        load();
      }
      return;
    }
    const tile = ev.target.closest(".game[data-id], .app[data-id]");
    if (tile) {
      const item = [...data.games, ...data.apps].find(x => x.id === tile.dataset.id);
      if (item) launch(item.id, item.name);
    }
  });
  root.addEventListener("keydown", ev => {
    if ((ev.key === "Enter" || ev.key === " ") && ev.target.matches(".game[data-id], .app[data-id]")) {
      ev.preventDefault();
      ev.target.click();
    }
  });
  $("l-search").addEventListener("input", render);
  $("l-showhidden").addEventListener("change", render);
  $("l-add").addEventListener("click", async () => {
    const name = $("l-name").value.trim(), target = $("l-target").value.trim().replace(/^"|"$/g, "");
    const args = $("l-args").value.trim();
    if (!name || !target) { toast("Indiquez un nom et un chemin", true); return; }
    try {
      await api("/api/launcher/app", { name, target, args: args ? args.match(/"[^"]*"|\S+/g).map(a => a.replace(/^"|"$/g, "")) : [] });
      $("l-name").value = $("l-target").value = $("l-args").value = "";
      toast("Ajouté : " + name);
      load();
    } catch (e) { toast(e.message, true); }
  });

  async function load() {
    data = await api("/api/launcher");
    render();
  }
  Tabs.register("lanceur", { show() { load().catch(e => { $("l-games").innerHTML = `<div class="empty">Erreur : ${esc(e.message)}</div>`; }); } });
})();
