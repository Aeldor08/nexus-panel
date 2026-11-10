"use strict";
/* Toutes les catégories : chaque carte (.card) d'un onglet devient un bloc déplaçable et redimensionnable,
   avec le même moteur que l'agenda (js/layout.js, NxBoard en mode « flux »). Chaque catégorie a sa barre
   « Verrouillé / Déverrouillé · Réinitialiser la disposition ». L'agenda garde son propre tableau (js/agenda.js).
   Une page qui se reconstruit (ex. le Journal, verrouillé puis ouvert) est reprise automatiquement. */
(() => {
  const SKIP = new Set(["agenda"]);
  const LABEL = { accueil: "du sommaire", pc: "de PC", media: "de Média", deck: "du Deck", lanceur: "du Lanceur",
                  reseau: "de Réseau", souvenirs: "des Souvenirs", statistiques: "des Statistiques", journal: "du Journal" };
  const state = {};
  // Pages à valeurs qui bougent : les blocs prennent la hauteur de leur contenu (jamais de barre de défilement)
  const AJUSTE = new Set(["accueil", "pc", "media", "reseau", "statistiques"]);

  const cardsOf = tab => [...tab.querySelectorAll(".card")].filter(c => !c.parentElement.closest(".card") && !c.closest("dialog"));

  function panelId(card, i, used) {
    const first = card.querySelector("[id]");
    let id = card.dataset.panel || card.id || (first && first.id) ||
      [...card.classList].filter(k => k !== "card" && !k.startsWith("nx-")).join("-") + "-" + i;
    while (used.has(id)) id += "+";
    used.add(id);
    card.dataset.panel = id;
  }

  function attach(tab) {
    const name = tab.id.slice(4);
    const s = state[name] || (state[name] = {});
    if (!s.bar || !tab.contains(s.bar)) {
      s.bar = document.createElement("div");
      tab.prepend(s.bar);
      s.tools = NxTools(s.bar, () => s.board, LABEL[name] || "");
    }
    const cards = cardsOf(tab);
    if (s.cards && s.cards.length === cards.length && s.cards.every((c, i) => c === cards[i])) return;   // inchangé
    if (s.board) s.board.destroy();
    s.cards = cards;
    s.board = null;
    if (!cards.length) return;
    const used = new Set();
    cards.forEach((c, i) => panelId(c, i, used));
    s.board = NxBoard(tab, { key: name, flux: true, panels: cards, minW: 220, minH: 110, ajuste: AJUSTE.has(name) });
    s.tools.show();
  }

  for (const tab of document.querySelectorAll("main.tab")) {
    if (SKIP.has(tab.id.slice(4))) continue;
    let pending = false;
    // (setTimeout et non requestAnimationFrame : ce dernier ne part pas quand la page n'est pas affichée)
    const later = () => { if (!pending) { pending = true; setTimeout(() => { pending = false; attach(tab); }, 0); } };
    new MutationObserver(later).observe(tab, { childList: true });
    attach(tab);
  }
  window.NxBlocs = { board: name => (state[name] || {}).board || null };
})();
