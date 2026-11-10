"use strict";
// ===== Carte « Mode jeu » (onglet PC) : état, plan d'alimentation automatique, exceptions =====
(() => {
  const card = document.createElement("section");
  card.className = "grid";
  card.style.marginTop = "18px";
  card.innerHTML = `
    <div class="card c-gm">
      <h2>Mode jeu <small id="gm-sub"></small></h2>
      <div class="gm-grid">
        <div>
          <div class="gm-state" id="gm-state">–</div>
          <div class="gm-actions" id="gm-actions"></div>
          <p class="hint" style="margin-top:8px">Détection automatique (jeux Steam, Riot, Rockstar, Epic, Xbox…).
            Pendant une partie, le panel s'allège : animations coupées, scan automatique du réseau local en pause.
            L'onglet PC (processus, températures, jauges) reste à jour chaque seconde, et le ping reste surveillé.</p>
        </div>
        <div>
          <label class="gm-toggle"><input type="checkbox" id="gm-power">
            <span>Changer de <b>plan d'alimentation</b> automatiquement</span></label>
          <div class="form-row" style="margin-top:10px">
            <label class="muted" style="font-size:14px;min-width:80px" for="gm-game">En jeu</label>
            <select id="gm-game" class="grow"></select>
          </div>
          <div class="form-row" style="margin-top:6px">
            <label class="muted" style="font-size:14px;min-width:80px" for="gm-normal">Hors jeu</label>
            <select id="gm-normal" class="grow"></select>
          </div>
          <div class="hint" id="gm-plan" style="margin-top:8px"></div>
        </div>
        <div>
          <div class="form-row"><label class="muted" style="font-size:14px" for="gm-extra">Jeux non détectés (nom du .exe)</label></div>
          <div class="form-row" style="margin-top:4px">
            <input class="in grow" id="gm-extra" placeholder="ex. MonJeu.exe, AutreJeu.exe">
          </div>
          <div class="form-row" style="margin-top:8px"><label class="muted" style="font-size:14px" for="gm-ignore">À ne jamais considérer comme un jeu</label></div>
          <div class="form-row" style="margin-top:4px">
            <input class="in grow" id="gm-ignore">
            <button class="btn big" id="gm-save">Enregistrer</button>
          </div>
        </div>
      </div>
    </div>`;
  $("tab-pc").appendChild(card);

  let info = null;
  const list = s => s.split(/[,;\n]/).map(x => x.trim()).filter(Boolean);
  const planName = g => (info && info.plans.find(p => p.guid === g) || {}).name || g || "–";

  function fill(sel, value) {
    sel.innerHTML = info.plans.map(p => `<option value="${p.guid}">${esc(p.name)}</option>`).join("");
    sel.value = value;
  }

  function render() {
    if (!info) return;
    const c = info.config;
    const off = c.enabled === false;
    $("gm-sub").textContent = off ? "désactivé" : info.in_game ? "actif" : "en veille";
    const depuis = info.since ? `<span class="muted" style="font-size:14px">depuis ${fmtDur(Date.now() / 1000 - info.since)}</span>` : "";
    $("gm-state").innerHTML = off
      ? `<span class="t-warn">⏸ Mode jeu désactivé</span>` +
        (info.detected ? ` · <span class="muted">jeu détecté : <b>${esc(gameLabel(info.game))}</b> (le panel ne s'allège pas)</span>` : "")
      : info.in_game
        ? `<span class="t-ok">▶ En jeu</span> · <b>${esc(gameLabel(info.game))}</b> ${depuis}`
        : `<span class="muted">Aucun jeu détecté</span>`;
    // Boutons : désactiver / réactiver à tout moment ; « ce n'est pas un jeu » met le programme dans les exceptions
    const acts = [];
    acts.push(off
      ? `<button class="btn gm-on" data-gm="on" title="Le panel s'allégera de nouveau pendant les parties">▶ Réactiver le mode jeu</button>`
      : `<button class="btn gm-off" data-gm="off" title="Le panel ne s'allège plus pendant les parties (animations et scan du réseau normaux). La détection continue pour les statistiques.">⏸ Désactiver le mode jeu</button>`);
    if (info.detected && info.game)
      acts.push(`<button class="btn" data-gm="ignore" title="Ajoute ${esc(info.game)} à la liste « à ne jamais considérer comme un jeu »">✖ Ce n'est pas un jeu</button>`);
    const box = $("gm-actions"), html = acts.join("");
    if (box.dataset.html !== html) { box.innerHTML = html; box.dataset.html = html; }
    if (document.activeElement !== $("gm-game") && document.activeElement !== $("gm-normal")) {
      fill($("gm-game"), c.game_plan);
      fill($("gm-normal"), c.normal_plan);
    }
    $("gm-power").checked = c.power_enabled;
    $("gm-game").disabled = $("gm-normal").disabled = !c.power_enabled;
    const ls = info.last_switch;
    $("gm-plan").innerHTML = `Plan actif : <b>${esc(planName(info.active_plan))}</b>` +
      (ls ? ` · dernier changement ${fmtAgo(ls.time)} vers « ${esc(planName(ls.plan))} » ${ls.ok ? "✔" : "<span class='t-hot'>✖ échec</span>"}` : "") +
      (c.power_enabled ? "" : `<br>Désactivé : le plan d'alimentation n'est jamais modifié.`);
    if (document.activeElement !== $("gm-extra")) $("gm-extra").value = c.extra_games.join(", ");
    if (document.activeElement !== $("gm-ignore")) $("gm-ignore").value = c.ignore.join(", ");
  }

  async function save(changes, msg) {
    try {
      await api("/api/gamemode/config", changes);
      if (msg) toast(msg);
      await load();
    } catch (e) { toast("Erreur : " + e.message, true); }
  }

  $("gm-power").addEventListener("change", ev => {
    const on = ev.target.checked;
    save({ power_enabled: on }, on
      ? "Plan automatique activé : il changera au prochain lancement / arrêt d'un jeu"
      : "Plan automatique désactivé");
  });
  $("gm-game").addEventListener("change", ev => save({ game_plan: ev.target.value }));
  $("gm-normal").addEventListener("change", ev => save({ normal_plan: ev.target.value }));
  $("gm-save").addEventListener("click", () =>
    save({ extra_games: list($("gm-extra").value), ignore: list($("gm-ignore").value) }, "Listes enregistrées"));
  $("gm-actions").addEventListener("click", ev => {
    const b = ev.target.closest("[data-gm]");
    if (!b || !info) return;
    if (b.dataset.gm === "off") save({ enabled: false }, "Mode jeu désactivé : le panel ne s'allège plus pendant les parties");
    else if (b.dataset.gm === "on") save({ enabled: true }, "Mode jeu réactivé");
    else if (b.dataset.gm === "ignore" && info.game) {
      const name = info.game;
      save({ ignore: [...new Set([...info.config.ignore, name])] }, `${name} ne sera plus considéré comme un jeu`);
    }
  });

  async function load() {
    info = await api("/api/gamemode");
    document.body.classList.toggle("gamemode", !!info.in_game);   // effet immédiat (sans attendre le prochain relevé)
    render();
  }
  const poll = poller(load, 5000);
  Tabs.register("pc", { show: () => poll.start(), hide: () => poll.stop() });
})();
