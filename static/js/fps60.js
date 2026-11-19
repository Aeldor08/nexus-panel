"use strict";
/* Animations limitées à 60 images/s.
   Le CSS ne sait pas brider la cadence d'une animation : sur un écran 144/165 Hz, chaque animation en boucle
   (pattes et queue de Philibert, voyants, balayage de l'en-tête, glitch du titre…) faisait recalculer le style
   de la page 144 à 165 fois par seconde. Ce script prend la main sur les animations CSS EN BOUCLE : il les met
   en pause et les fait avancer lui-même 60 fois par seconde (via nxImage, déjà bridé à 60, voir index.html).
   Le mouvement est le même, à la cadence d'un écran 60 Hz.
   - Les animations qui ont une fin (intros, apparitions, transitions) restent gérées par le navigateur : courtes,
     elles ne coûtent rien, et leurs évènements de fin doivent partir normalement.
   - Mode repos (html.nx-repos), onglet caché (html.nx-pause) ou « réduire les animations » : elles n'avancent pas.
   - Réglable dans ⚙ Réglages → Économie (localStorage « nexus-fps60 », sur CET appareil). */
(() => {
  if (!document.getAnimations || !window.nxImage) return;
  const KEY = "nexus-fps60";
  const root = document.documentElement;
  const reduit = matchMedia("(prefers-reduced-motion: reduce)");
  const gerees = new Set();
  let dernier = 0, boucle = false;

  const actif = () => { try { return localStorage.getItem(KEY) !== "0"; } catch (e) { return true; } };
  const fige = () => root.classList.contains("nx-repos") || root.classList.contains("nx-pause") || reduit.matches;

  function enBoucle(a) {
    if (typeof CSSTransition !== "undefined" && a instanceof CSSTransition) return false;
    try { return a.effect && a.effect.getComputedTiming().iterations === Infinity; } catch (e) { return false; }
  }

  // Relire la liste des animations force un recalcul de style : on ne le fait que quand une animation démarre
  // (évènement animationstart) ou, par sécurité, 4 fois par seconde. Entre deux, on avance seulement les nôtres.
  let aScanner = true, scanT = 0;
  document.addEventListener("animationstart", () => { aScanner = true; }, true);
  function scanner(now) {
    aScanner = false; scanT = now;
    for (const a of document.getAnimations()) {
      if (gerees.has(a) || a.playState !== "running" || !enBoucle(a)) continue;
      a.pause();
      gerees.add(a);
    }
    // Les animations retirées (classe enlevée, élément supprimé) sont oubliées
    for (const a of gerees) if (a.playState === "idle" || !a.effect || !a.effect.target || !a.effect.target.isConnected) gerees.delete(a);
  }

  function tic(now) {
    if (!boucle) return;
    const dt = dernier ? Math.min(now - dernier, 100) : 0;     // (retour d'une longue pause : pas de bond)
    dernier = now;
    if (aScanner || now - scanT > 250) scanner(now);
    if (!fige() && dt) for (const a of gerees) if (a.currentTime != null) a.currentTime += dt * (a.playbackRate || 1);
    nxImage(tic);
  }

  function demarrer() {
    if (boucle || !actif()) return;
    boucle = true; dernier = 0;
    nxImage(tic);
  }
  function arreter() {
    boucle = false;
    for (const a of gerees) { try { a.play(); } catch (e) {} }   // rendues au navigateur, là où elles en étaient
    gerees.clear();
  }

  // Une animation CSS mise en pause par le script reste en pause si le CSS la remet « running » plus tard :
  // à la sortie du mode repos / de l'onglet caché, elles repartent simplement au tic suivant.
  document.addEventListener("visibilitychange", () => { if (!document.hidden) dernier = 0; });
  addEventListener("nexus:repos", () => { dernier = 0; });
  demarrer();

  window.nxFps60 = {
    actif,
    regler(on) {
      try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) {}
      if (on) demarrer(); else arreter();
    },
  };
})();
