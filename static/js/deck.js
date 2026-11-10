"use strict";
// ===== Onglet Deck : grille de gros boutons, confirmation, mode édition =====
// Le navigateur n'envoie que l'identifiant du bouton : l'action est lue côté serveur dans deck.json.
(() => {
  const root = $("tab-deck");
  root.innerHTML = `
    <div class="card c-deck">
      <h2>Stream deck <small id="dk-sub"></small></h2>
      <div id="dk-body"></div>
    </div>
    <div class="card c-deck" style="margin-top:18px">
      <h2>Journal <small>dernières actions</small></h2>
      <div id="dk-log"></div>
      <div class="hint" id="dk-discord"></div>
    </div>`;
  const dlg = document.createElement("dialog");
  dlg.className = "ver-dlg deck-dlg";
  document.body.appendChild(dlg);

  let data = null, editing = false;
  const color = b => b.color || "#00ff9c";

  // ---------------------------------------------------------------- écran de connexion
  function renderLogin() {
    $("dk-sub").textContent = "verrouillé";
    $("dk-body").innerHTML = data.password_set ? `
      <form class="dk-login" id="dk-login">
        <p class="muted">Le stream deck peut lancer des applications et verrouiller la session :
          il est protégé par le mot de passe défini dans <code>config.json</code> (<code>deck.password</code>).</p>
        <div class="form-row">
          <input class="in grow" id="dk-pw" type="password" autocomplete="current-password" placeholder="Mot de passe du deck" aria-label="Mot de passe du deck">
          <button class="btn big">Déverrouiller</button>
        </div>
        <div class="dk-err" id="dk-err" role="alert"></div>
      </form>`
      : `<div class="empty">Aucun mot de passe défini. Ajoute <code>"password"</code> dans la section <code>deck</code> de
          <code>config.json</code>, puis relance NEXUS.</div>`;
    $("dk-log").innerHTML = `<div class="empty">Déverrouille le deck pour voir le journal.</div>`;
    $("dk-discord").textContent = "";
    const f = $("dk-login");
    if (f) f.addEventListener("submit", async ev => {
      ev.preventDefault();
      try { await api("/api/deck/login", { password: $("dk-pw").value }); await load(); }
      catch (e) { $("dk-err").textContent = e.message; $("dk-pw").select(); }
    });
  }

  // ---------------------------------------------------------------- grille
  function render() {
    if (!data.logged_in) return renderLogin();
    $("dk-sub").textContent = `${data.buttons.length} bouton${data.buttons.length > 1 ? "s" : ""}`;
    $("dk-body").innerHTML = `
      <div class="dk-bar">
        <button class="btn big ${editing ? "on" : ""}" id="dk-edit">${editing ? "✔ Terminer" : "✎ Modifier"}</button>
        ${editing ? `<button class="btn big" id="dk-add">+ Ajouter un bouton</button>` : ""}
        <button class="btn" id="dk-logout" style="margin-left:auto">Verrouiller le deck</button>
      </div>
      ${data.warnings.length ? `<div class="dk-warn">${data.warnings.map(esc).join("<br>")}</div>` : ""}
      <div class="dk-grid ${editing ? "editing" : ""}" id="dk-grid">
        ${data.buttons.map((b, i) => `
          <div class="dk-cell">
            <button class="dk-btn" data-id="${esc(b.id)}" style="--c:${esc(color(b))}" ${editing ? "disabled" : ""}
              aria-label="${esc(b.label)}${b.confirm ? " (demande confirmation)" : ""}">
              <span class="dk-ico" aria-hidden="true">${esc(b.icon || "▣")}</span>
              <span class="dk-lbl">${esc(b.label)}</span>
              ${b.confirm ? `<span class="dk-tag warn" title="Demande confirmation">⚠</span>` : ""}
              ${b.discord ? `<span class="dk-tag disc" title="Utilisable avec /deck sur Discord">/deck</span>` : ""}
            </button>
            ${editing ? `<div class="dk-tools">
              <button class="btn" data-mv="${i}" data-d="-1" aria-label="Déplacer avant" ${i === 0 ? "disabled" : ""}>◀</button>
              <button class="btn" data-ed="${i}" aria-label="Modifier ${esc(b.label)}">✎</button>
              <button class="btn danger" data-rm="${i}" aria-label="Supprimer ${esc(b.label)}">🗑</button>
              <button class="btn" data-mv="${i}" data-d="1" aria-label="Déplacer après" ${i === data.buttons.length - 1 ? "disabled" : ""}>▶</button>
            </div>` : ""}
          </div>`).join("") || `<div class="empty">Aucun bouton. Clique sur « Modifier » puis « Ajouter un bouton ».</div>`}
      </div>`;
    $("dk-log").innerHTML = data.log.length ? data.log.map(l => {
      const [date, src, ip, id, label, res, detail] = l.split(" | ");
      return `<div class="outage"><span class="muted">${esc(date)} · ${esc((src || "").trim())}</span>
        <b class="${(res || "").trim() === "ok" ? "t-ok" : "t-warn"}">${esc(label)} — ${esc((detail || "").trim())}</b></div>`;
    }).join("") : `<div class="empty">Aucune action pour l'instant.</div>`;
    const d = data.discord || {};
    $("dk-discord").innerHTML = `Bot Discord : <b>${esc({ online: "● connecté", connecting: "connexion…", disabled: "désactivé",
      no_token: "pas de jeton", bad_token: "jeton refusé", error: "erreur", stopped: "arrêté", bad_config: "config incomplète" }[d.state] || d.state || "–")}</b>
      ${d.user ? ` · ${esc(d.user)} sur « ${esc(d.guild || "")} » ${esc(d.channel || "")}` : ""}${d.detail && d.state !== "online" ? ` — ${esc(d.detail)}` : ""}`;
    $("dk-edit").onclick = () => { editing = !editing; render(); };
    $("dk-logout").onclick = async () => { await api("/api/deck/logout", {}); editing = false; load(); };
    if ($("dk-add")) $("dk-add").onclick = () => openEditor(-1);
  }

  // ---------------------------------------------------------------- exécution
  async function run(b, confirmed) {
    const el = root.querySelector(`.dk-btn[data-id="${CSS.escape(b.id)}"]`);
    try {
      const r = await api("/api/deck/run", { id: b.id, confirmed: !!confirmed });
      toast(`${b.icon || "▶"} ${b.label} — ${r.message}`);
      if (el) { el.classList.remove("fired"); void el.offsetWidth; el.classList.add("fired"); }
    } catch (e) {
      toast(`${b.label} : ${e.message}`, true);
      if (e.message.includes("mot de passe")) load();
    }
    refreshLog();
  }
  function confirmAndRun(b) {
    dlg.innerHTML = `
      <div class="ver-head"><h2>Confirmer</h2></div>
      <div class="ver-body dk-confirm">
        <div class="dk-big-ico">${esc(b.icon || "⚠")}</div>
        <p>Exécuter <b>« ${esc(b.label)} »</b> ?</p>
        ${b.type === "power" ? `<p class="muted">Arrêt et redémarrage ont lieu après 15 s (annulable avec <code>shutdown /a</code>).</p>` : ""}
        <div class="form-row" style="justify-content:center">
          <button class="btn big" id="dk-no">Annuler</button>
          <button class="btn big danger" id="dk-yes">Confirmer</button>
        </div>
      </div>`;
    $("dk-no").onclick = () => dlg.close();
    $("dk-yes").onclick = () => { dlg.close(); run(b, true); };
    dlg.showModal();
    $("dk-no").focus();
  }

  root.addEventListener("click", async ev => {
    const btn = ev.target.closest(".dk-btn[data-id]");
    if (btn && !editing) {
      const b = data.buttons.find(x => x.id === btn.dataset.id);
      if (b) (b.confirm ? confirmAndRun(b) : run(b, false));
      return;
    }
    const mv = ev.target.closest("[data-mv]"), ed = ev.target.closest("[data-ed]"), rm = ev.target.closest("[data-rm]");
    if (mv) {
      const i = +mv.dataset.mv, j = i + +mv.dataset.d, list = [...data.buttons];
      [list[i], list[j]] = [list[j], list[i]];
      await save(list);
    } else if (ed) openEditor(+ed.dataset.ed);
    else if (rm) {
      const b = data.buttons[+rm.dataset.rm];
      if (confirm(`Supprimer le bouton « ${b.label} » ?`)) await save(data.buttons.filter((_, k) => k !== +rm.dataset.rm));
    }
  });

  async function save(list) {
    try {
      const r = await api("/api/deck", { buttons: list }, "PUT");
      data.buttons = r.buttons;
      render();
      return true;
    } catch (e) { toast("Enregistrement refusé : " + e.message, true); return false; }
  }

  // ---------------------------------------------------------------- éditeur d'un bouton
  function openEditor(index) {
    const c = data.catalog;
    const b = index >= 0 ? JSON.parse(JSON.stringify(data.buttons[index]))
      : { id: "", label: "", icon: "⭐", color: "#00ff9c", type: "url", params: {}, confirm: false, discord: false };
    const opt = (obj, sel) => Object.entries(obj).map(([k, v]) => `<option value="${esc(k)}" ${k === sel ? "selected" : ""}>${esc(v)}</option>`).join("");
    dlg.innerHTML = `
      <div class="ver-head"><h2>${index >= 0 ? "Modifier" : "Nouveau"} bouton</h2><button class="btn" id="be-x" aria-label="Fermer">✕</button></div>
      <form class="ver-body dk-form" id="be-form">
        <div class="dk-form-row">
          <label>Libellé<input class="in" id="be-label" maxlength="30" required value="${esc(b.label)}"></label>
          <label class="sm">Icône / emoji<input class="in" id="be-icon" maxlength="8" value="${esc(b.icon)}"></label>
          <label class="sm">Couleur<input class="in" id="be-color" type="color" value="${esc(b.color)}"></label>
        </div>
        <label>Action<select id="be-type">${opt(c.types, b.type)}</select></label>
        <div id="be-params"></div>
        <label class="chk"><input type="checkbox" id="be-confirm" ${b.confirm ? "checked" : ""}> Demander une confirmation avant d'exécuter</label>
        <label class="chk"><input type="checkbox" id="be-discord" ${b.discord ? "checked" : ""}> Autoriser <code>/deck</code> depuis Discord</label>
        <div class="dk-err" id="be-err" role="alert"></div>
        <div class="form-row" style="justify-content:flex-end">
          <button type="button" class="btn big" id="be-cancel">Annuler</button>
          <button class="btn big">Enregistrer</button>
        </div>
      </form>`;
    const params = () => {
      const t = $("be-type").value, p = b.params || {};
      const box = $("be-params");
      box.innerHTML =
        t === "app" ? `<label>Chemin de l'application (${c.app_exts.join(", ")})
            <input class="in" id="bp-path" placeholder="C:\\Program Files\\…\\appli.exe" value="${esc(p.path || "")}"></label>
            <label>Arguments (optionnel, séparés par des espaces)<input class="in" id="bp-args" value="${esc((p.args || []).join(" "))}"></label>`
        : t === "url" ? `<label>Adresse (http ou https)<input class="in" id="bp-url" type="url" placeholder="https://…" value="${esc(p.url || "")}"></label>`
        : t === "media" ? `<label>Touche<select id="bp-key">${opt(c.media, p.key)}</select></label>`
        : t === "script" ? (c.scripts.length ? `<label>Script du dossier actions/<select id="bp-name">${c.scripts.map(s => `<option ${s === p.name ? "selected" : ""}>${esc(s)}</option>`).join("")}</select></label>`
                           : `<div class="dk-warn">Aucun script dans le dossier <code>actions/</code> de NEXUS (.bat, .cmd, .ps1, .py).</div>`)
        : t === "power" ? `<label>Opération<select id="bp-op">${opt(c.power, p.op)}</select></label>
            <div class="muted" style="font-size:14px">Action sensible : la confirmation est obligatoire et Discord interdit.</div>`
        : `<div class="muted" style="font-size:14px">Aucun paramètre.</div>`;
      // Alimentation : confirmation forcée, jamais depuis Discord (on rend la main en quittant ce type)
      const power = t === "power";
      if (power && !$("be-confirm").disabled) { $("be-confirm").dataset.before = $("be-confirm").checked ? "1" : "0"; $("be-confirm").checked = true; }
      if (!power && $("be-confirm").disabled) $("be-confirm").checked = $("be-confirm").dataset.before === "1";
      $("be-confirm").disabled = power;
      const noDiscord = power || $("be-confirm").checked;
      $("be-discord").disabled = noDiscord; if (noDiscord) $("be-discord").checked = false;
    };
    params();
    $("be-type").onchange = () => { b.params = {}; params(); };
    $("be-confirm").onchange = params;
    $("be-x").onclick = $("be-cancel").onclick = () => dlg.close();
    $("be-form").onsubmit = async ev => {
      ev.preventDefault();
      const t = $("be-type").value, v = id => ($(id) || {}).value || "";
      const nb = {
        id: b.id || undefined, label: v("be-label").trim(), icon: v("be-icon").trim(), color: v("be-color"), type: t,
        confirm: $("be-confirm").checked, discord: $("be-discord").checked,
        params: t === "app" ? { path: v("bp-path").trim(), args: v("bp-args").trim() ? v("bp-args").trim().split(/\s+/) : [] }
              : t === "url" ? { url: v("bp-url").trim() } : t === "media" ? { key: v("bp-key") }
              : t === "script" ? { name: v("bp-name") } : t === "power" ? { op: v("bp-op") } : {},
      };
      const list = [...data.buttons];
      if (index >= 0) list[index] = nb; else list.push(nb);
      try {
        const r = await api("/api/deck", { buttons: list }, "PUT");
        data.buttons = r.buttons; dlg.close(); render();
      } catch (e) { $("be-err").textContent = e.message; }      // le serveur explique ce qui ne va pas
    };
    dlg.showModal();
    $("be-label").focus();
  }
  dlg.addEventListener("click", ev => { if (ev.target === dlg) dlg.close(); });

  async function refreshLog() {
    try { const r = await api("/api/deck"); if (r.logged_in) { data.log = r.log; data.discord = r.discord; if (!editing) render(); } } catch (e) {}
  }
  async function load() {
    try { data = await api("/api/deck"); } catch (e) { $("dk-body").innerHTML = `<div class="empty">${esc(e.message)}</div>`; return; }
    render();
  }
  Tabs.register("deck", { show: load });
})();
