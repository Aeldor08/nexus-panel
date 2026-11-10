"use strict";
/* Minuteur Pomodoro et mode focus (bouton ⏱ du haut). L'état vit sur le serveur (focus.py) : le même sur le PC et
   le téléphone, et il survit à un redémarrage. Pendant une séance de TRAVAIL, le temps compte dans « travail »
   des statistiques. Si l'option est cochée, un profil sobre (Ardoise) est appliqué pendant toute la session,
   sans changer le profil choisi : il revient à la fin. Son + message à chaque fin de séance ou de pause.
   État exposé aux profils : body[data-focus="travail|pause|longue"] pendant une session. */
(() => {
  const wrap = $("focus-wrap"), btn = $("btn-focus"), menu = $("focus-menu");
  const PROFIL_SOBRE = "ardoise";
  const PHASES = { travail: "Travail", pause: "Pause", longue: "Pause longue" };
  let e = null, recu = 0, vuChangement = null, poll = null;

  const mmss = s => { s = Math.max(0, Math.round(s)); return `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`; };
  const reste = () => !e || !e.actif ? 0 : e.suspendu ? e.reste_s : Math.max(0, e.reste_s - (Date.now() - recu) / 1000);

  function bouton() {
    if (!e || !e.actif) { btn.textContent = "⏱ Focus"; btn.classList.remove("focus-actif", "focus-pause"); return; }
    btn.textContent = `${e.suspendu ? "❚❚" : "⏱"} ${mmss(reste())} · ${PHASES[e.phase]}`;
    btn.classList.add("focus-actif");
    btn.classList.toggle("focus-pause", e.phase !== "travail");
  }

  function contenu() {
    if (!e) return `<div class="empty">Chargement…</div>`;
    const r = e.reglages;
    if (!e.actif) return `
      <div class="pf-head">Mode focus <small>· minuteur Pomodoro</small></div>
      <div class="focus-reglages">
        <label>Travail <input class="in" type="number" min="5" max="180" data-focus-r="travail_min" value="${r.travail_min}"> min</label>
        <label>Pause <input class="in" type="number" min="1" max="60" data-focus-r="pause_min" value="${r.pause_min}"> min</label>
        <label>Pause longue <input class="in" type="number" min="1" max="90" data-focus-r="longue_min" value="${r.longue_min}"> min</label>
        <label>toutes les <input class="in" type="number" min="1" max="12" data-focus-r="cycles" value="${r.cycles}"> séances</label>
      </div>
      <label class="rg-row rg-chk"><input type="checkbox" data-focus-r="profil_sobre" ${r.profil_sobre ? "checked" : ""}>
        <span>Profil sobre (Ardoise) pendant la session</span></label>
      <button class="btn on" data-focus="demarrer">▶ Démarrer une session</button>
      <small class="muted rg-note">Le temps des séances de travail compte dans « Travail » de tes statistiques.</small>`;
    const d = e.duree_s || 1, fait = Math.min(1, 1 - reste() / d);
    return `
      <div class="pf-head">Mode focus <small>· ${PHASES[e.phase]}${e.suspendu ? " (en pause)" : ""}</small></div>
      <div class="focus-temps" aria-live="off">${mmss(reste())}</div>
      <div class="focus-barre" role="progressbar" aria-valuemin="0" aria-valuemax="100" aria-valuenow="${Math.round(fait * 100)}"><i style="width:${(fait * 100).toFixed(1)}%"></i></div>
      <p class="muted focus-info">${e.seances} séance${e.seances > 1 ? "s" : ""} terminée${e.seances > 1 ? "s" : ""} ·
        ${Math.round(e.travail_s / 60)} min de travail · ${e.reglages.travail_min}/${e.reglages.pause_min} min</p>
      <div class="form-row">
        ${e.suspendu ? `<button class="btn on" data-focus="reprendre">▶ Reprendre</button>` : `<button class="btn" data-focus="suspendre">❚❚ Suspendre</button>`}
        <button class="btn" data-focus="passer">⏭ ${e.phase === "travail" ? "Passer à la pause" : "Reprendre le travail"}</button>
        <button class="btn danger" data-focus="arreter">■ Arrêter</button>
      </div>`;
  }
  const dessiner = () => { if (!menu.hidden) menu.innerHTML = contenu(); };

  // Appliqué UNE fois par session : si tu choisis toi-même un autre profil pendant la session, il est respecté
  let sobre = false;
  function profil() {
    const P = window.nexusProfils;
    if (!P) return;
    if (e && e.actif && e.reglages.profil_sobre) { if (!sobre && P.temporaire(PROFIL_SOBRE)) sobre = true; }
    else if (sobre) { P.temporaire(null); sobre = false; }
  }

  function appliquer(nv) {
    const ancien = e;
    e = nv; recu = Date.now();
    if (e.actif) document.body.dataset.focus = e.phase; else delete document.body.dataset.focus;
    // fin d'une séance / d'une pause (pas au chargement de la page)
    if (e.actif && e.changement && vuChangement !== null && e.changement !== vuChangement) {
      toast(e.phase === "travail" ? "⏱ Pause terminée : on reprend le travail !" : `⏱ Séance terminée : ${PHASES[e.phase].toLowerCase()} de ${e.phase === "longue" ? e.reglages.longue_min : e.reglages.pause_min} min.`);
      try { if (window.reminderSound) window.reminderSound.play(); } catch (x) {}
    }
    vuChangement = e.actif ? (e.changement || 0) : null;
    if (ancien && ancien.actif && !e.actif) toast(`Session de focus terminée : ${Math.round((ancien.travail_s || 0) / 60)} min de travail.`);
    profil();
    bouton();
    // le menu ouvert n'est redessiné qu'au changement d'état (pas pendant qu'on tape une durée)
    if (!menu.hidden && (!ancien || e.actif || ancien.actif !== e.actif)) dessiner();
  }

  async function charger() {
    try { appliquer(await api("/api/focus")); } catch (x) {}
    clearTimeout(poll);
    poll = setTimeout(charger, e && e.actif ? 5000 : 15000);
  }
  // compte à rebours affiché chaque seconde (entre deux lectures du serveur)
  setInterval(() => {
    if (!e || !e.actif || document.hidden) return;
    bouton();
    if (!menu.hidden) {
      const t = menu.querySelector(".focus-temps"), b = menu.querySelector(".focus-barre i");
      if (t) t.textContent = mmss(reste());
      if (b) b.style.width = (Math.min(1, 1 - reste() / (e.duree_s || 1)) * 100).toFixed(1) + "%";
    }
    if (!e.suspendu && reste() <= 0) charger();            // fin de phase : on demande la suite au serveur
  }, 1000);

  async function action(a, corps = {}) {
    try { appliquer(await api("/api/focus/" + a, corps)); dessiner(); } catch (x) { toast("Focus : " + x.message, true); }
    clearTimeout(poll); poll = setTimeout(charger, e && e.actif ? 5000 : 15000);
  }
  menu.addEventListener("click", ev => {
    const b = ev.target.closest("[data-focus]");
    if (!b) return;
    const a = b.dataset.focus;
    if (a === "arreter" && !confirm("Arrêter la session de focus ?")) return;
    if (a === "demarrer") {
      const r = {};
      menu.querySelectorAll("[data-focus-r]").forEach(i => { r[i.dataset.focusR] = i.type === "checkbox" ? i.checked : Number(i.value); });
      action("demarrer", { reglages: r });
    } else action(a);
  });
  menu.addEventListener("change", ev => {
    const i = ev.target.closest("[data-focus-r]");
    if (i && !(e && e.actif)) action("reglages", { [i.dataset.focusR]: i.type === "checkbox" ? i.checked : Number(i.value) });
  });
  btn.addEventListener("click", ev => {
    ev.stopPropagation();
    menu.hidden = !menu.hidden;
    btn.setAttribute("aria-expanded", String(!menu.hidden));
    if (!menu.hidden) dessiner();
  });
  document.addEventListener("click", ev => { if (!menu.hidden && !wrap.contains(ev.target)) { menu.hidden = true; btn.setAttribute("aria-expanded", "false"); } });
  document.addEventListener("keydown", ev => { if (ev.key === "Escape" && !menu.hidden) { ev.stopImmediatePropagation(); menu.hidden = true; btn.focus(); } }, true);
  // les profils se chargent après la page : on réapplique le profil sobre dès qu'ils sont prêts
  addEventListener("nexus:profile", () => { if (!sobre) profil(); });
  charger();
  window.nxFocus = { etat: () => e, charger };
})();
