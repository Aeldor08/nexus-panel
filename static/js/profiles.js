"use strict";
/* Profils visuels (dossier profils\ du serveur, voir profils/FORMAT.md).
   - Un menu déroulant en haut choisit le profil du mode en cours (Terminal ou Sentinelle).
   - Le choix est mémorisé par mode ET par appareil (localStorage « nexus-profil-<mode> »).
   - Le profil s'applique tout de suite : sa feuille de style (vérifiée par le serveur) est ajoutée
     par-dessus le mode ; « Défaut » = aucune feuille en plus. Si un profil est cassé : retour à Défaut.
   - Rescan à chaud : la liste est relue à l'ouverture du menu, avec « Actualiser », et toutes les 5 s
     pour le profil actif (modifier style.css se voit sans recharger la page).
   - Exporter (.zip) / Importer (.zip ou dossier déposé) / Supprimer. */
(() => {
  const root = document.documentElement;
  const MODE = root.dataset.theme || "terminal";
  const MODE_NAME = { terminal: "Terminal", sentinelle: "Sentinelle" }[MODE] || MODE;
  const KEY = "nexus-profil-" + MODE;
  const DEFAULT = "defaut";
  const MAX_BYTES = 5 * 1024 * 1024, MAX_FILES = 60;
  const btn = document.getElementById("btn-profil");
  const menu = document.getElementById("pf-menu");
  const curLabel = document.getElementById("pf-cur");
  const h = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  let all = [], invalid = [], active = root.dataset.profile || DEFAULT, loaded = false;

  const compatible = () => all.filter(p => p.modes.includes(MODE));
  const save = id => { try { localStorage.setItem(KEY, id); } catch (e) {} };

  // ---------- messages ----------
  function toast(text, kind = "") {
    const t = document.createElement("div");
    t.className = "pf-toast " + kind;
    t.textContent = text;
    document.body.appendChild(t);
    setTimeout(() => t.classList.add("out"), 4200);
    setTimeout(() => t.remove(), 4700);
  }

  function dialog(title, bodyHtml, buttons) {
    return new Promise(resolve => {
      const d = document.createElement("dialog");
      d.className = "pf-dlg";
      d.innerHTML = `<h3>${h(title)}</h3><div class="pf-dlg-body">${bodyHtml}</div>
        <div class="pf-dlg-btns">${buttons.map((b, i) => `<button class="btn ${b.cls || ""}" data-i="${i}">${h(b.label)}</button>`).join("")}</div>`;
      document.body.appendChild(d);
      d.addEventListener("click", e => {
        const b = e.target.closest("button[data-i]");
        if (b) { d.close(); resolve(buttons[+b.dataset.i].value); }
      });
      d.addEventListener("cancel", () => resolve(null));
      d.addEventListener("close", () => setTimeout(() => d.remove(), 50));
      d.showModal();
    });
  }

  // ---------- application d'un profil ----------
  function fire() { requestAnimationFrame(() => dispatchEvent(new Event("nexus:profile"))); }

  function setLabel() {
    const p = all.find(x => x.id === active);
    curLabel.textContent = p ? p.nom : "Défaut";
    // profil actif et ses animations (profil.json → "animations"), lus par la page de garde (splash.js)
    window.nexusProfile = p && !p.integre ? { id: p.id, nom: p.nom, version: p.version, animations: p.animations || null } : null;
  }

  function apply(id, { remember = true, onFail = null } = {}) {
    const p = compatible().find(x => x.id === id);
    const old = document.getElementById("nx-profile-css");
    if (!p || !p.css) {                                   // Défaut (ou profil introuvable) : aucune feuille en plus
      old?.remove();
      delete root.dataset.profile;
      active = DEFAULT;
      if (remember) save(DEFAULT);
      setLabel(); render(); fire();
      return;
    }
    if (old && old.getAttribute("href") === p.css && root.dataset.profile === id) { active = id; setLabel(); return; }
    // nouvelle feuille chargée à côté de l'ancienne, puis échange : pas de flash de l'apparence par défaut
    const link = document.createElement("link");
    link.rel = "stylesheet";
    link.href = p.css;
    link.onload = () => {
      old?.remove();
      link.id = "nx-profile-css";
      root.dataset.profile = id;
      try { localStorage.setItem("nexus-profil-css-" + id, p.css); } catch (e) {}   // relu par le <head> (index.html)
      fire();
    };
    link.onerror = () => {
      link.remove();
      if (onFail) { active = root.dataset.profile || DEFAULT; setLabel(); onFail(new Error("feuille de style refusée")); return; }
      toast(`Le profil « ${p.nom} » n'a pas pu être chargé : retour au profil Défaut.`, "err");
      apply(DEFAULT);
    };
    document.head.appendChild(link);
    active = id;
    if (remember) save(id);
    setLabel(); render();
  }

  // ---------- changement de profil en douceur (générique, pour tous les profils) ----------
  // L'interface s'estompe sous un écran NEXUS neutre (« Chargement du profil … », version, barre) ;
  // la feuille du profil ET ses fichiers (images, polices) sont préchargés ; on ne bascule qu'une fois tout
  // prêt, puis le nouveau thème apparaît en fondu. États exposés aux profils : <body data-profil-etat=
  // "changement" (écran affiché, ancien thème encore là) → "pret" (nouveau thème appliqué, l'écran s'efface).
  const reduceMotion = () => matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  let busy = false, queued = null;

  function overlay(p) {
    let ov = document.getElementById("nx-bascule");
    if (!ov) {
      ov = document.createElement("div");
      ov.id = "nx-bascule";
      ov.className = "nx-bascule";
      ov.setAttribute("role", "status");
      ov.setAttribute("aria-live", "polite");
      ov.innerHTML = `<div class="nx-b-box"><img class="nx-b-logo" src="/static/nexus-logo.svg" alt="">
        <div class="nx-b-titre">NEXUS</div><div class="nx-b-txt"></div><div class="nx-b-ver"></div>
        <div class="nx-b-barre"><i></i></div></div>`;
      document.body.appendChild(ov);
    }
    ov.querySelector(".nx-b-txt").innerHTML = `Chargement du profil <b>${h(p ? p.nom : "Défaut")}</b>`;
    ov.querySelector(".nx-b-ver").textContent = p && !p.integre ? `version ${p.version} · ${MODE_NAME}` : `apparence d'origine · ${MODE_NAME}`;
    ov.classList.toggle("calme", reduceMotion());
    progress(0);
    return ov;
  }
  function progress(f) {
    const bar = document.querySelector("#nx-bascule .nx-b-barre i");
    if (bar) bar.style.transform = `scaleX(${Math.max(0, Math.min(1, f))})`;
  }

  // Précharge la feuille vérifiée du profil et tous les fichiers qu'elle cite (images décodées, polices)
  async function preload(p) {
    const r = await fetch(p.css, { cache: "force-cache" });
    if (!r.ok) throw new Error("feuille de style introuvable (HTTP " + r.status + ")");
    const css = await r.text();
    const base = new URL(p.css, location.href);
    const urls = [...new Set([...css.matchAll(/url\(\s*["']?([^"')]+)["']?\s*\)/g)].map(m => new URL(m[1], base).href))];
    let done = 0;
    const one = u => (/\.(woff2?|ttf|otf)(\?|$)/i.test(u)
      ? fetch(u, { cache: "force-cache" }).then(x => x.arrayBuffer())
      : new Promise(res => { const img = new Image(); img.onload = img.onerror = res; img.src = u; })
          .then(() => null))
      .catch(() => null)
      .finally(() => progress(.15 + .7 * (++done / Math.max(1, urls.length))));
    progress(.15);
    await Promise.race([Promise.all(urls.map(one)), wait(6000)]);          // un fichier lent ne bloque pas tout
    // Tout venait-il du cache du navigateur ? (aucun octet transféré) → transition plus courte
    return [p.css, ...urls].every(u => {
      const e = performance.getEntriesByName(new URL(u, location.href).href).pop();
      return !e || e.transferSize === 0;
    });
  }

  // Applique la feuille et attend qu'elle soit prise en compte (ou échoue)
  function applyReady(id) {
    return new Promise((resolve, reject) => {
      const p = compatible().find(x => x.id === id);
      if (!p || !p.css) { apply(DEFAULT); return resolve(); }
      const before = document.getElementById("nx-profile-css");
      if (before && before.getAttribute("href") === p.css && root.dataset.profile === id) { apply(id); return resolve(); }
      // La feuille est appliquée (root.dataset.profile) dès son chargement : on la guette directement
      let over = false;
      const t0 = performance.now();
      const check = () => {
        if (over) return;
        if (root.dataset.profile === id) { over = true; return resolve(); }
        if (performance.now() - t0 > 8000) { over = true; return reject(new Error("délai dépassé")); }
        setTimeout(check, 25);
      };
      apply(id, { onFail: err => { over = true; reject(err); } });
      check();
    });
  }

  async function switchTo(id) {
    close();
    if (id === active && !busy) return;
    if (busy) { queued = id; return; }                 // clic pendant la transition : mis en file (le dernier gagne)
    busy = true;
    const p = compatible().find(x => x.id === id) || null;
    const prev = active, calm = reduceMotion();
    const ov = overlay(p);
    document.body.dataset.profilEtat = "changement";
    void ov.offsetWidth;
    ov.classList.add("on");
    const t0 = performance.now();
    let failed = null, cached = true;
    try {
      if (p && p.css) cached = await preload(p);         // tout était déjà en cache : transition plus courte
      await wait(Math.max(0, (calm ? 150 : cached ? 330 : 420) - (performance.now() - t0)));   // l'ancien thème a fini de s'estomper
      progress(.9);
      await applyReady(p ? p.id : DEFAULT);
    } catch (e) { failed = e; }
    if (failed) {
      try { await applyReady(compatible().some(x => x.id === prev) ? prev : DEFAULT); } catch (e) { apply(DEFAULT); }
      toast(`Le profil « ${p ? p.nom : id} » n'a pas pu être chargé (${failed.message}) : retour au profil ${active === DEFAULT ? "Défaut" : "précédent"}.`, "err");
    }
    progress(1);
    document.body.dataset.profilEtat = "pret";
    const minTotal = calm ? 300 : cached ? 600 : 1000;   // plus court si tout était en cache
    await wait(Math.max(calm ? 0 : 180, minTotal - (performance.now() - t0)));
    ov.classList.remove("on");
    await wait(calm ? 160 : 420);
    delete document.body.dataset.profilEtat;
    busy = false;
    if (queued !== null) { const q = queued; queued = null; if (q !== active) switchTo(q); }
  }

  // ---------- liste ----------
  async function refresh({ quiet = false } = {}) {
    try {
      const r = await fetch("/api/profils", { cache: "no-store" });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const data = await r.json();
      all = data.profils || [];
      invalid = data.invalides || [];
    } catch (e) {
      if (!quiet) toast("Liste des profils indisponible : " + e.message, "err");
      if (window.nexusProfile === undefined) window.nexusProfile = null;   // la page de garde n'attend pas
      return;
    }
    const first = !loaded;
    loaded = true;
    if (busy) { if (!menu.hidden) render(); return; }   // un changement de profil est en cours : on n'y touche pas
    const p = compatible().find(x => x.id === active);
    if (active !== DEFAULT && !p) {
      toast(`Le profil enregistré pour ce mode n'est plus disponible (supprimé, invalide ou incompatible avec ${MODE_NAME}) : profil Défaut.`, "err");
      apply(DEFAULT);
    } else if (p) {
      apply(p.id, { remember: false });                  // met à jour la feuille si le profil a changé sur le disque
      if (first) fire();
    }
    setLabel();
    if (!menu.hidden) render();
  }

  // ---------- menu ----------
  function preview(p) {
    if (p.miniature) return `<img src="${h(p.miniature)}" alt="" loading="lazy">`;
    if (p.integre) return `<span class="pf-sw pf-sw-def" aria-hidden="true"><i></i><i></i><i></i></span>`;
    const c = p.couleurs.length ? p.couleurs : ["#333", "#666"];
    return `<span class="pf-sw" aria-hidden="true">${c.map(x => `<i style="background:${h(x)}"></i>`).join("")}</span>`;
  }

  function render() {
    const items = compatible().map(p => `
      <li role="option" tabindex="-1" data-id="${h(p.id)}" aria-selected="${p.id === active}" class="${p.id === active ? "on" : ""}">
        <span class="pf-prev">${preview(p)}</span>
        <span class="pf-info"><b>${h(p.nom)}</b><small>${h(p.integre ? "intégré" : `v${p.version} · ${p.auteur}`)}${p.modes.length === 2 ? " · les deux modes" : ""}</small>
          ${p.description ? `<em>${h(p.description)}</em>` : ""}
          ${p.avertissements.length ? `<em class="pf-warn" title="${h(p.avertissements.join("\n"))}">⚠ ${p.avertissements.length} élément(s) retiré(s) ou à corriger</em>` : ""}</span>
        ${p.integre ? "" : `<span class="pf-acts">
          <button class="pf-act" data-act="export" title="Exporter en .zip" aria-label="Exporter ${h(p.nom)}">⤓</button>
          <button class="pf-act" data-act="delete" title="Supprimer" aria-label="Supprimer ${h(p.nom)}">🗑</button></span>`}
      </li>`).join("");
    const others = all.length - compatible().length;
    menu.innerHTML = `
      <div class="pf-head">Profil du mode <b>${h(MODE_NAME)}</b> <small>· mémorisé sur cet appareil</small></div>
      <ul class="pf-list" role="listbox" aria-label="Profils visuels">${items}</ul>
      ${others ? `<div class="pf-note">${others} autre(s) profil(s) réservé(s) à l'autre mode.</div>` : ""}
      ${invalid.length ? `<details class="pf-bad"><summary>⚠ ${invalid.length} profil(s) ignoré(s) car invalide(s)</summary>
        ${invalid.map(x => `<div><b>profils/${h(x.dossier)}</b><ul>${x.erreurs.map(e => `<li>${h(e)}</li>`).join("")}</ul></div>`).join("")}
        <small>Vérifie-les avec : python valider_profil.py profils\\${h(invalid[0].dossier)}</small></details>` : ""}
      <div class="pf-foot">
        <button class="btn" data-act="refresh">⟳ Actualiser</button>
        <button class="btn" data-act="import">⤒ Importer…</button>
        <input type="file" accept=".zip,application/zip" hidden id="pf-file">
      </div>
      <div class="pf-drop">ou dépose ici un <b>.zip</b> ou un <b>dossier</b> de profil</div>`;
    menu.querySelector("#pf-file").addEventListener("change", e => {
      const f = e.target.files[0];
      e.target.value = "";
      if (f) importZip(f);
    });
  }

  function open() {
    render();
    menu.hidden = false;
    btn.setAttribute("aria-expanded", "true");
    (menu.querySelector("li.on") || menu.querySelector("li"))?.focus();
    refresh({ quiet: true });
  }
  function close() {
    menu.hidden = true;
    btn.setAttribute("aria-expanded", "false");
  }

  btn.addEventListener("click", e => { e.stopPropagation(); menu.hidden ? open() : close(); });
  document.addEventListener("click", e => { if (!menu.hidden && !e.target.closest("#pf-wrap") && !e.target.closest(".pf-dlg")) close(); });
  document.addEventListener("keydown", e => {
    if (menu.hidden) return;
    if (e.key === "Escape") { e.stopImmediatePropagation(); e.preventDefault(); close(); btn.focus(); return; }
    const opts = [...menu.querySelectorAll("li[role=option]")];
    const i = opts.indexOf(document.activeElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      opts[(i + (e.key === "ArrowDown" ? 1 : -1) + opts.length) % opts.length]?.focus();
    } else if ((e.key === "Enter" || e.key === " ") && i >= 0) {
      e.preventDefault(); switchTo(opts[i].dataset.id);
    }
  }, true);

  menu.addEventListener("click", async e => {
    const act = e.target.closest("[data-act]");
    const li = e.target.closest("li[data-id]");
    if (act) {
      e.stopPropagation();
      const p = li && all.find(x => x.id === li.dataset.id);
      if (act.dataset.act === "refresh") { await refresh(); toast("Liste des profils actualisée."); }
      else if (act.dataset.act === "import") menu.querySelector("#pf-file").click();
      else if (act.dataset.act === "export" && p) {
        const a = document.createElement("a");
        a.href = `/api/profils/${encodeURIComponent(p.id)}/export`;
        a.download = `profil-${p.id}.zip`;
        document.body.appendChild(a); a.click(); a.remove();
      } else if (act.dataset.act === "delete" && p) remove(p);
      return;
    }
    if (li) switchTo(li.dataset.id);
  });

  // ---------- suppression ----------
  async function remove(p) {
    const ok = await dialog("Supprimer ce profil ?",
      `<p>Le profil <b>${h(p.nom)}</b> et son dossier <code>profils\\${h(p.id)}</code> seront effacés de ce PC.</p>
       <p>Pense à l'exporter avant si tu veux le garder.</p>`,
      [{ label: "Supprimer", value: true, cls: "danger" }, { label: "Annuler", value: false }]);
    if (!ok) return;
    const r = await fetch(`/api/profils/${encodeURIComponent(p.id)}/supprimer`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) return toast(data.error || "Suppression impossible", "err");
    toast(`Profil « ${p.nom} » supprimé.`);
    if (active === p.id) apply(DEFAULT);
    refresh();
  }

  // ---------- import ----------
  const b64 = buf => {
    const bytes = new Uint8Array(buf);
    let s = "";
    for (let i = 0; i < bytes.length; i += 0x8000) s += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
    return btoa(s);
  };

  async function sendImport(payload) {
    const post = body => fetch("/api/profils/import", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) })
      .then(async r => ({ status: r.status, data: await r.json().catch(() => ({ error: "réponse illisible" })) }));
    let res = await post(payload);
    if (res.status === 409 && res.data.conflict) {
      const choice = await dialog("Ce profil existe déjà",
        `<p>Un profil <b>${h(res.data.nom_existant)}</b> est déjà installé (<code>profils\\${h(res.data.id)}</code>).</p>
         <p>Que faire du profil importé « ${h(res.data.nom)} » ?</p>`,
        [{ label: "Remplacer l'existant", value: "replace", cls: "danger" },
         { label: "Garder les deux", value: "keep" }, { label: "Annuler", value: null }]);
      if (!choice) return;
      res = await post({ ...payload, si_existe: choice });
    }
    if (res.status !== 200 || !res.data.ok) {
      const details = res.data.details || [];
      await dialog("Profil refusé",
        `<p>${h(res.data.error || "Erreur " + res.status)}</p>${details.length ? `<ul>${details.map(d => `<li>${h(d)}</li>`).join("")}</ul>` : ""}
         <p><small>Le format attendu est décrit dans <code>profils\\FORMAT.md</code>.</small></p>`,
        [{ label: "OK", value: true }]);
      return;
    }
    const d = res.data;
    await refresh();
    const fits = d.modes.includes(MODE);
    toast(`Profil « ${d.nom} » installé${fits ? "" : ` (pour le mode ${d.modes.map(m => m === "terminal" ? "Terminal" : "Sentinelle").join(" / ")})`}.`);
    if (fits) switchTo(d.id);
  }

  async function importZip(file) {
    if (file.size > MAX_BYTES + 512 * 1024) return toast("Fichier trop gros (5 Mo maximum).", "err");
    if (!/\.zip$/i.test(file.name)) return toast("Choisis un fichier .zip (ou dépose un dossier).", "err");
    await sendImport({ zip_base64: b64(await file.arrayBuffer()) });
  }

  // Dossier déposé : on lit ses fichiers (API des entrées du glisser-déposer)
  function readEntry(entry, path, out) {
    return new Promise((resolve, reject) => {
      if (entry.isFile) {
        entry.file(f => { out.push({ path: path + f.name, file: f }); resolve(); }, reject);
      } else if (entry.isDirectory) {
        const reader = entry.createReader(), children = [];
        const batch = () => reader.readEntries(async ents => {
          if (!ents.length) {
            try { for (const c of children) await readEntry(c, path + entry.name + "/", out); resolve(); }
            catch (e) { reject(e); }
            return;
          }
          children.push(...ents);
          if (out.length + children.length > MAX_FILES * 2) return reject(new Error("trop de fichiers"));
          batch();
        }, reject);
        batch();
      } else resolve();
    });
  }

  async function importFolder(entry) {
    const files = [];
    try { await readEntry(entry, "", files); }
    catch (e) { return toast("Dossier illisible : " + e.message, "err"); }
    if (files.length > MAX_FILES) return toast(`Trop de fichiers (${MAX_FILES} maximum).`, "err");
    const total = files.reduce((n, f) => n + f.file.size, 0);
    if (total > MAX_BYTES) return toast("Dossier trop lourd (5 Mo maximum).", "err");
    const fichiers = [];
    for (const f of files) fichiers.push({ chemin: f.path, base64: b64(await f.file.arrayBuffer()) });
    await sendImport({ fichiers });
  }

  menu.addEventListener("dragover", e => { e.preventDefault(); menu.classList.add("drag"); });
  menu.addEventListener("dragleave", e => { if (!menu.contains(e.relatedTarget)) menu.classList.remove("drag"); });
  menu.addEventListener("drop", e => {
    e.preventDefault();
    menu.classList.remove("drag");
    const item = [...(e.dataTransfer.items || [])].find(i => i.kind === "file");
    const entry = item && item.webkitGetAsEntry && item.webkitGetAsEntry();
    if (entry && entry.isDirectory) return importFolder(entry);
    const file = e.dataTransfer.files[0];
    if (file) importZip(file);
  });

  window.nexusProfils = { switchTo, get busy() { return busy; }, get active() { return active; } };   // (tests)

  // ---------- démarrage + rescan à chaud ----------
  refresh();
  setInterval(() => {
    if (document.hidden || document.body.classList.contains("gamemode")) return;
    if (active !== DEFAULT || !menu.hidden) refresh({ quiet: true });
  }, 5000);
})();
