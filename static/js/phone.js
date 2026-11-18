"use strict";
// ===== Accès téléphone (fenêtre visible uniquement sur le PC) =====
(() => {
  const btn = $("btn-phone");
  const dlg = document.createElement("dialog");
  dlg.className = "ver-dlg phone-dlg";
  dlg.setAttribute("aria-labelledby", "ph-title");
  document.body.appendChild(dlg);
  let info = null, poll = null, pairTimer = null;

  function fmtLeft(sec) { return `${Math.floor(sec / 60)}:${String(Math.max(0, Math.floor(sec % 60))).padStart(2, "0")}`; }

  function render() {
    const i = info;
    const statusHtml = !i.enabled && !i.active ? `<b class="muted">Désactivé</b> — NEXUS n'est accessible que depuis ce PC.`
      : i.restart_needed ? `<b class="t-warn">Redémarrage de NEXUS en cours…</b>`
      : `<b class="t-ok">● Actif</b> sur le Wi-Fi : <code>${esc(i.url || "réseau introuvable")}</code>`;
    dlg.innerHTML = `
      <div class="ver-head"><h2 id="ph-title">📱 Accès téléphone</h2><button class="btn" id="ph-close" aria-label="Fermer">✕</button></div>
      <div class="ver-body">
        <label class="gm-toggle ph-toggle"><input type="checkbox" id="ph-on" ${i.enabled ? "checked" : ""}>
          <span>Autoriser l'accès depuis mon téléphone <small>(réseau Wi-Fi de la maison uniquement)</small></span></label>
        <p class="ph-status">${statusHtml}</p>
        ${i.active && i.pare_feu === false ? `
          <div class="ph-fw">
            <b class="t-warn">⚠ Le pare-feu Windows bloque le téléphone.</b>
            Il faut autoriser le port <code>${esc(String(i.port))}</code> de NEXUS sur les réseaux privés.
            <button class="btn" id="ph-fw">🛡 Autoriser dans le pare-feu</button>
            <small class="muted">Windows va demander une confirmation administrateur.</small>
          </div>` : ""}
        ${i.active ? `
          <div class="section-title">Appairer un téléphone</div>
          <div id="ph-pair">${i.pairing ? "" : `<button class="btn big" id="ph-start">Afficher le QR code</button>`}</div>` : ""}
        <div class="section-title">Appareils autorisés</div>
        <div id="ph-devs">${i.devices.length ? i.devices.map(d => `
          <div class="ph-dev"><span class="ph-ico">📱</span>
            <span class="ph-name"><b>${esc(d.name)}</b><small>${esc(d.agent || "")} · vu ${fmtAgo(d.last_seen)} · ${esc(d.last_ip || "")}</small></span>
            <button class="edit" data-ren="${d.id}" title="Renommer">✎</button>
            <button class="btn danger" data-rev="${d.id}">Révoquer</button></div>`).join("")
          : `<div class="empty">Aucun appareil pour l'instant.</div>`}</div>
        <p class="hint">
          • Seuls les appareils appairés ici peuvent ouvrir NEXUS ; les adresses Internet sont toujours refusées.<br>
          ${i.pare_feu == null ? `• Au premier démarrage avec l'accès activé, <b>Windows demande d'autoriser Python</b> : coche « Réseaux privés » puis Autoriser.
            Si tu as refusé : Pare-feu Windows → « Autoriser une application » → Python → Privé.<br>`
          : `• Le pare-feu doit laisser passer le port <code>${esc(String(i.port))}</code> (bouton ci-dessus s'il est bloqué).<br>`}
          • Une ancienne adresse enregistrée sur le téléphone (autre port, ex. <code>:8000</code>) ne marche plus :
            appaire-le à nouveau avec le QR code.<br>
          • Sur le téléphone, menu du navigateur → <b>« Ajouter à l'écran d'accueil »</b> pour avoir l'icône NEXUS.<br>
          • Hors de chez toi (4G), ça ne marche pas : c'est voulu (rien n'est ouvert sur Internet).
        </p>
      </div>`;
    $("ph-close").onclick = () => dlg.close();
    $("ph-on").onchange = async ev => {
      const on = ev.target.checked;
      if (on && !confirm("Activer l'accès téléphone ?\n\nNEXUS va redémarrer et écouter sur ton réseau Wi-Fi. Seuls les appareils que tu appaires pourront l'ouvrir.")) {
        ev.target.checked = false; return;
      }
      try {
        const r = await api("/api/remote/config", { enabled: on });
        if (r.restart) waitRestart();
        else load();
      } catch (e) { toast(e.message, true); }
    };
    const start = $("ph-start");
    if (start) start.onclick = startPairing;
    const fw = $("ph-fw");
    if (fw) fw.onclick = async () => {
      try {
        await api("/api/remote/pare-feu", {});
        fw.disabled = true;
        fw.textContent = "Confirme dans la fenêtre Windows…";
      } catch (e) { toast(e.message, true); }
    };
    if (i.pairing) showPairing(i.pairing);
    dlg.querySelectorAll("[data-rev]").forEach(b => b.onclick = async () => {
      const d = info.devices.find(x => x.id === b.dataset.rev);
      if (!confirm(`Révoquer « ${d.name} » ? Il devra être appairé à nouveau.`)) return;
      await api("/api/remote/revoke", { id: d.id }); load();
    });
    dlg.querySelectorAll("[data-ren]").forEach(b => b.onclick = async () => {
      const d = info.devices.find(x => x.id === b.dataset.ren);
      const name = prompt("Nom de l'appareil :", d.name);
      if (name && name.trim()) { await api("/api/remote/rename", { id: d.id, name: name.trim() }); load(); }
    });
  }

  function showPairing(p) {
    const box = $("ph-pair");
    if (!box) return;
    box.innerHTML = `
      <div class="ph-pair">
        <img class="ph-qr" src="/api/remote/qr.svg?t=${p.expires}" alt="QR code d'appairage">
        <div class="ph-pair-info">
          <ol><li>Connecte le téléphone au <b>même Wi-Fi</b> que le PC.</li>
              <li>Scanne ce QR code avec l'appareil photo.</li>
              <li>Ou ouvre <code>${esc(info.url)}/pair</code> et tape le code :</li></ol>
          <div class="ph-code">${p.code.slice(0, 3)} ${p.code.slice(3)}</div>
          <div class="muted" id="ph-left"></div>
          <button class="btn" id="ph-cancel">Annuler</button>
        </div>
      </div>`;
    $("ph-cancel").onclick = async () => { await api("/api/remote/pair/cancel", {}); load(); };
    clearInterval(pairTimer);
    const tick = () => {
      const left = p.expires - Date.now() / 1000;
      const el = $("ph-left");
      if (!el) { clearInterval(pairTimer); return; }
      el.textContent = left > 0 ? `Expire dans ${fmtLeft(left)}` : "Expiré";
      if (left <= 0) { clearInterval(pairTimer); load(); }
    };
    tick(); pairTimer = setInterval(tick, 1000);
  }

  async function startPairing() {
    try {
      const p = await api("/api/remote/pair", {});
      info.pairing = p;
      showPairing(p);
    } catch (e) { toast(e.message, true); }
  }

  // Après activation/désactivation, le serveur redémarre : on attend qu'il revienne
  async function waitRestart() {
    info.restart_needed = true; render();
    await new Promise(r => setTimeout(r, 2500));
    for (let k = 0; k < 40; k++) {
      try { await api("/api/version"); break; } catch (e) { await new Promise(r => setTimeout(r, 750)); }
    }
    await load();
    toast(info.active ? "📱 Accès téléphone actif" : "Accès téléphone désactivé");
  }

  async function load() {
    const prev = info;
    info = await api("/api/remote");
    // Un appairage était en cours et un appareil vient d'apparaître : succès
    if (prev && prev.pairing && info.devices.length > prev.devices.length) {
      toast(`✔ ${info.devices[info.devices.length - 1].name} est appairé`);
    }
    if (dlg.open) render();
    btn.classList.toggle("on", info.active);
  }

  btn.addEventListener("click", async () => {
    try { await load(); } catch (e) { toast(e.message, true); return; }
    render(); dlg.showModal();
    clearInterval(poll);
    poll = setInterval(() => { if (dlg.open) load().catch(() => {}); else clearInterval(poll); }, 2000);
  });
  dlg.addEventListener("click", ev => { if (ev.target === dlg) dlg.close(); });
  dlg.addEventListener("close", () => { clearInterval(poll); clearInterval(pairTimer); });

  // Le bouton n'apparaît que sur le PC (le téléphone reçoit un refus de /api/remote)
  api("/api/remote").then(r => { info = r; btn.hidden = false; btn.classList.toggle("on", r.active); }).catch(() => {});
})();
