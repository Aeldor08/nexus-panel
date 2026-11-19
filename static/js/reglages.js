"use strict";
/* Menu ⚙ Réglages (barre du haut) : taille de chaque composant + son des rappels.
   Les tailles sont des variables CSS (--nx-z-…) posées sur <html> en « !important » : un profil visuel
   ne peut pas les annuler (il n'a pas non plus le droit d'utiliser zoom ni --nx-…, voir profiles.py).
   Mémorisé sur CET appareil (localStorage « nexus-tailles ») : le téléphone et le PC ont leurs propres tailles.
   Le même calcul est fait très tôt dans <head> (index.html) pour éviter un saut à l'ouverture. */
(() => {
  const KEY = "nexus-tailles";
  const SIZES = [
    { id: "lanceur", label: "Lanceur", def: 125 },
    { id: "deck", label: "Stream deck (boutons)", def: 115 },
    { id: "melangeur", label: "Mélangeur de son", def: 115 },
    { id: "agenda", label: "Agenda (contenu des fenêtres)", def: 105 },
  ];
  const MIN = 80, MAX = 150;
  const INTRO_KEY = "nexus-intro-profils";          // lu par js/splash.js
  const introOn = () => { try { return localStorage.getItem(INTRO_KEY) !== "0"; } catch (e) { return true; } };
  // Passage au sommaire : choisi et retenu PAR PROFIL visuel (lu par js/splash.js).
  // { id du profil: "cercle" | "tele" | "fondu" | "profil" (= celui prévu par le profil) } ; ancien réglage commun en repli.
  const OUV_MAP = "nexus-ouverture-profils", OUV_OLD = "nexus-ouverture";
  const OUV_NOMS = { cercle: "Ouverture en rond", tele: "Vieille télé qui s'allume", fondu: "Simple fondu" };
  const curProfil = () => { const p = window.nexusProfile; return p && p.id === document.documentElement.dataset.profile ? p : null; };
  const ouvMap = () => { try { return JSON.parse(localStorage.getItem(OUV_MAP) || "{}") || {}; } catch (e) { return {}; } };
  const ouvChoice = id => { const m = ouvMap(); let v = Object.prototype.hasOwnProperty.call(m, id) ? m[id] : null;
    if (v === null) { try { v = localStorage.getItem(OUV_OLD); } catch (e) {} }
    return OUV_NOMS[v] ? v : ""; };
  const read = () => { try { return JSON.parse(localStorage.getItem(KEY)) || {}; } catch (e) { return {}; } };
  const write = v => { try { localStorage.setItem(KEY, JSON.stringify(v)); } catch (e) {} };
  let cur = read();
  const value = s => Math.min(MAX, Math.max(MIN, Number(cur[s.id]) || s.def));

  function apply() {
    for (const s of SIZES) document.documentElement.style.setProperty(`--nx-z-${s.id}`, String(value(s) / 100), "important");
    dispatchEvent(new Event("resize"));            // grilles et canevas se recalculent
  }

  const wrap = document.getElementById("rg-wrap"), btn = document.getElementById("btn-reglages"), menu = document.getElementById("rg-menu");
  function render() {
    menu.innerHTML = `
      <div class="pf-head">Réglages <small>· mémorisés sur cet appareil</small></div>
      <div class="rg-group">Tailles de l'interface</div>
      ${SIZES.map(s => `<label class="rg-row"><span>${esc(s.label)}</span>
        <input type="range" min="${MIN}" max="${MAX}" step="5" value="${value(s)}" data-size="${s.id}" aria-label="Taille : ${esc(s.label)}">
        <b data-out="${s.id}">${value(s)} %</b></label>`).join("")}
      <button class="btn" data-act="reset-sizes">↺ Tailles par défaut</button>
      <div class="rg-group">Page de garde</div>
      <label class="rg-row rg-chk"><input type="checkbox" data-act="intro" ${introOn() ? "checked" : ""}>
        <span>Jouer l'intro animée des profils visuels (Sakura, Pluie d'étoiles…)</span></label>
      ${(() => { const p = curProfil(), a = p && p.animations;
        if (!p || !a || !a.remplace_transition) return `<small class="muted rg-note">Passage au sommaire : réglable pour chaque profil visuel animé
          (Sakura, Pluie d'étoiles, Dés du destin…). Choisis d'abord le profil dans le menu des profils.</small>`;
        const def = OUV_NOMS[a.ouverture] || OUV_NOMS.fondu, cur = ouvChoice(p.id);
        return `<label class="rg-row rg-sel"><span>Passage au sommaire · <b>${esc(p.nom || p.id)}</b></span>
        <select class="in" data-act="ouverture" data-profil="${esc(p.id)}" aria-label="Passage de la page de garde au sommaire pour le profil ${esc(p.nom || p.id)}">
          ${[["", `Celui du profil (${def})`], ...Object.entries(OUV_NOMS)]
            .map(([v, t]) => `<option value="${v}"${cur === v ? " selected" : ""}>${esc(t)}</option>`).join("")}
        </select></label>
        <small class="muted rg-note">Retenu pour ce profil seulement : chaque profil garde son propre passage.</small>`; })()}
      ${window.nxRepos ? `<div class="rg-group">Économie</div>
      <label class="rg-row rg-chk"><input type="checkbox" data-act="repos" ${window.nxRepos.actif() ? "checked" : ""}>
        <span>Mettre les animations en pause quand NEXUS n'est pas au premier plan (après 20 s)</span></label>
      <small class="muted rg-note">Les valeurs continuent de se mettre à jour. Moins de travail pour le processeur et la
        carte graphique, surtout sur un écran 144/165 Hz.</small>` : ""}
      ${window.nxFps60 ? `<label class="rg-row rg-chk"><input type="checkbox" data-act="fps60" ${window.nxFps60.actif() ? "checked" : ""}>
        <span>Limiter les animations à 60 images/s</span></label>
      <small class="muted rg-note">Sur un écran 144/165 Hz : même mouvement, presque trois fois moins de travail.</small>` : ""}
      ${window.nxPhilibert ? `<div class="rg-group">Philibert, l'iguane</div>
      <label class="rg-row rg-chk"><input type="checkbox" data-act="philibert-visible" ${window.nxPhilibert.visible() ? "checked" : ""}>
        <span>Le voir se promener sous la barre du haut</span></label>
      <button class="btn" data-act="philibert">🦎 Ouvrir son île</button>` : ""}
      <div class="rg-group">Version et mises à jour</div>
      <div id="rg-maj"><small class="muted rg-note">Chargement…</small></div>
      <div class="rg-group">Rappels de l'agenda</div>
      <label class="rg-row rg-chk"><input type="checkbox" data-act="sound" ${window.reminderSound && window.reminderSound.on ? "checked" : ""}>
        <span>Jouer un son à chaque rappel</span></label>
      <button class="btn" data-act="test-sound">♪ Tester le son</button>
      <small class="muted rg-note">Délais par défaut et heure de référence des rappels : config.json, section « agenda » (voir README).</small>`;
  }
  // ---- Mises à jour : réglages (config.json, hors Git) ; le jeton n'est jamais réaffiché ----
  async function renderMaj() {
    const box = document.getElementById("rg-maj");
    if (!box) return;
    let m;
    try { m = await api("/api/maj"); } catch (e) { box.innerHTML = `<small class="muted rg-note">Indisponible : ${esc(e.message)}</small>`; return; }
    const r = m.reglages;
    box.innerHTML = `
      <button class="btn" data-maj-act="ouvrir">ℹ Version ${esc(m.version)}${m.disponible ? ` · ${esc(m.disponible.version)} disponible` : ""}</button>
      <label class="rg-row rg-chk"><input type="checkbox" data-maj="actif" ${r.actif ? "checked" : ""}>
        <span>Vérifier les mises à jour automatiquement</span></label>
      <label class="rg-row rg-sel"><span>Toutes les</span>
        <select class="in" data-maj="intervalle_heures" aria-label="Intervalle de vérification">
          ${[1, 3, 6, 12, 24, 48, 168].map(h => `<option value="${h}"${Number(r.intervalle_heures) === h ? " selected" : ""}>${h < 24 ? h + " h" : h === 168 ? "semaine" : h / 24 + " j"}</option>`).join("")}
        </select></label>
      <label class="rg-row rg-chk"><input type="checkbox" data-maj="discord" ${r.discord ? "checked" : ""}>
        <span>Me prévenir sur Discord quand une version sort (le bot n'installe jamais rien)</span></label>
      <label class="rg-row rg-sel"><span>Dépôt GitHub</span>
        <input class="in" data-maj-champ="depot" value="${esc(r.depot)}" placeholder="propriétaire/nom" spellcheck="false" aria-label="Dépôt GitHub à surveiller"></label>
      <label class="rg-row rg-sel"><span>Jeton (dépôt privé)</span>
        <input class="in" type="password" data-maj-champ="jeton" autocomplete="off" placeholder="${m.jeton.enregistre ? "•••••• enregistré" : "github_pat_…"}" aria-label="Jeton GitHub en lecture seule"></label>
      <div class="form-row"><button class="btn" data-maj-act="enregistrer">Enregistrer</button>
        ${m.jeton.enregistre ? `<button class="btn danger" data-maj-act="effacer">Effacer le jeton</button>` : ""}</div>
      <small class="muted rg-note">Jeton en lecture seule, limité à ce dépôt (voir docs\\JETON_GITHUB.md) ; rangé dans le gestionnaire
        d'identifiants de Windows, envoyé uniquement à api.github.com.</small>`;
  }
  menu.addEventListener("change", async e => {
    const k = e.target.dataset && e.target.dataset.maj;
    if (!k) return;
    try { await api("/api/maj/reglages", { [k]: e.target.type === "checkbox" ? e.target.checked : Number(e.target.value) }); toast("Réglage enregistré."); }
    catch (x) { toast("Mises à jour : " + x.message, true); }
  });
  menu.addEventListener("click", async e => {
    const b = e.target.closest("[data-maj-act]");
    if (!b) return;
    const act = b.dataset.majAct;
    if (act === "ouvrir") { menu.hidden = true; if (window.nxVersion) window.nxVersion.ouvrir(); return; }
    try {
      if (act === "enregistrer") {
        const depot = menu.querySelector('[data-maj-champ="depot"]').value.trim(), jeton = menu.querySelector('[data-maj-champ="jeton"]').value.trim();
        await api("/api/maj/reglages", { depot });
        if (jeton) { const r = await api("/api/maj/jeton", { jeton }); toast(r.verification.resultat === "ok" ? "Jeton enregistré et vérifié ✔" : "Jeton enregistré, mais : " + r.verification.erreur, r.verification.resultat !== "ok"); }
        else toast("Dépôt enregistré.");
      } else if (act === "effacer") { await api("/api/maj/jeton", { jeton: "" }); toast("Jeton effacé."); }
      renderMaj();
    } catch (x) { toast("Mises à jour : " + x.message, true); }
  });
  menu.addEventListener("input", e => {
    const r = e.target.closest("[data-size]");
    if (!r) return;
    cur[r.dataset.size] = Number(r.value);
    write(cur);
    menu.querySelector(`[data-out="${r.dataset.size}"]`).textContent = r.value + " %";
    apply();
  });
  menu.addEventListener("change", e => {
    if (e.target.dataset.act === "sound" && window.reminderSound) window.reminderSound.on = e.target.checked;
    if (e.target.dataset.act === "repos" && window.nxRepos) window.nxRepos.regler(e.target.checked);
    if (e.target.dataset.act === "fps60" && window.nxFps60) window.nxFps60.regler(e.target.checked);
    if (e.target.dataset.act === "philibert-visible" && window.nxPhilibert) window.nxPhilibert.afficher(e.target.checked);
    if (e.target.dataset.act === "intro") { try { localStorage.setItem(INTRO_KEY, e.target.checked ? "1" : "0"); } catch (x) {} }
    if (e.target.dataset.act === "ouverture") {
      const m = ouvMap();
      m[e.target.dataset.profil] = e.target.value || "profil";     // « profil » : celui prévu par le profil (même si l'ancien réglage commun existe)
      try { localStorage.setItem(OUV_MAP, JSON.stringify(m)); } catch (x) {}
      toast(`Passage au sommaire retenu pour ce profil : ${e.target.selectedOptions[0].textContent}.`);
    }
  });
  menu.addEventListener("click", e => {
    const a = e.target.closest("button[data-act]");
    if (!a) return;
    if (a.dataset.act === "reset-sizes") { cur = {}; write(cur); apply(); render(); }
    if (a.dataset.act === "test-sound" && window.reminderSound) window.reminderSound.play();
    if (a.dataset.act === "philibert" && window.nxPhilibert) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); window.nxPhilibert.ouvrir(); }
  });
  btn.addEventListener("click", e => {
    e.stopPropagation();
    if (menu.hidden) { render(); renderMaj(); menu.hidden = false; btn.setAttribute("aria-expanded", "true"); }
    else { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); }
  });
  document.addEventListener("click", e => { if (!menu.hidden && !wrap.contains(e.target)) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
  document.addEventListener("keydown", e => {
    if (e.key === "Escape" && !menu.hidden) { e.stopImmediatePropagation(); menu.hidden = true; btn.focus(); }
  }, true);
  apply();
})();
