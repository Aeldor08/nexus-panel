"use strict";
/* Mode repos : quand NEXUS n'est plus au premier plan (autre fenêtre active, NEXUS posé sur un second écran),
   les animations DÉCORATIVES se mettent en pause au bout de 20 s : Philibert, éclats, balayages, intros des
   profils. Les valeurs (CPU, RAM, températures…), les alertes et les notifications continuent de se mettre à jour.
   Sur un écran 144/165 Hz, ces animations faisaient recalculer le style de la page à chaque image (≈ 30 % d'un
   cœur processeur et autant pour la carte graphique), même quand personne ne regardait.
   Retour immédiat dès que la fenêtre reprend le focus ou que la souris passe dessus.
   Réglable dans ⚙ Réglages (« Mettre les animations en pause quand NEXUS n'est pas au premier plan »),
   mémorisé sur CET appareil (localStorage « nexus-repos »). */
(() => {
  const KEY = "nexus-repos", DELAI = 20000;
  const root = document.documentElement;
  let timer = 0;
  const actif = () => { try { return localStorage.getItem(KEY) !== "0"; } catch (e) { return true; } };

  function poser(on) {
    if (root.classList.contains("nx-repos") === on) return;
    root.classList.toggle("nx-repos", on);
    dispatchEvent(new CustomEvent("nexus:repos", { detail: on }));
  }
  function reveil() {
    clearTimeout(timer); timer = 0;
    poser(false);
    if (actif() && !document.hasFocus()) attendre();
  }
  function attendre() {
    clearTimeout(timer);
    if (!actif()) return;
    timer = setTimeout(() => { timer = 0; if (!document.hasFocus()) poser(true); }, DELAI);
  }

  addEventListener("focus", reveil);
  addEventListener("blur", attendre);
  // Survol de la fenêtre sans la sélectionner (second écran) : on rejoue, puis repos 20 s après le dernier mouvement
  let dernier = 0;
  document.addEventListener("pointermove", () => {
    const t = Date.now();
    if (t - dernier < 1000) return;          // pas plus d'une fois par seconde
    dernier = t;
    reveil();
  }, { passive: true });
  document.addEventListener("visibilitychange", () => { if (!document.hidden) reveil(); });
  if (!document.hasFocus()) attendre();

  window.nxRepos = {
    actif,
    regler(on) {
      try { localStorage.setItem(KEY, on ? "1" : "0"); } catch (e) {}
      if (on) attendre(); else reveil();
    },
    enCours: () => root.classList.contains("nx-repos"),
  };
})();
