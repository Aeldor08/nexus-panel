"use strict";
/* Icônes dessinées de Philibert (traits arrondis, 24 × 24, couleur du texte) : actions, jauges, météo, saisons.
   Une seule famille d'icônes pour toute l'île : plus lisible et plus homogène que des émojis (qui changent
   d'aspect selon l'appareil). PhilibertIcones.ico("nourrir") → <svg>. */
(() => {
  const P = {
    nourrir: `<path d="M5 19c0-8.5 5.2-14 15-14 0 9.2-6 14-15 14z"/><path d="M5 19c3.6-4.6 7-7.6 11-9.6"/>`,
    soleil: `<circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.2M12 19.3v2.2M2.5 12h2.2M19.3 12h2.2M5.3 5.3l1.6 1.6M17.1 17.1l1.6 1.6M5.3 18.7l1.6-1.6M17.1 6.9l1.6-1.6"/>`,
    flamme: `<path d="M12 3c.8 3 5 5.2 5 10a5 5 0 0 1-10 0c0-2.8 1.8-4 2.2-6 1 .9 1.8 2 1.8 3.2 1.1-2 1.4-4.6 1-7.2z"/>`,
    lune: `<path d="M19.5 14.5A8 8 0 1 1 9.5 4.5a6.2 6.2 0 0 0 10 10z"/>`,
    ampoule: `<path d="M9.2 18h5.6M10.2 21h3.6"/><path d="M12 3a6 6 0 0 0-3.6 10.8c.7.6 1.1 1.3 1.1 2.2h5c0-.9.4-1.6 1.1-2.2A6 6 0 0 0 12 3z"/>`,
    goutte: `<path d="M12 3c3.2 4.2 6 7.2 6 11a6 6 0 0 1-12 0c0-3.8 2.8-6.8 6-11z"/><path d="M9.2 14.6a2.8 2.8 0 0 0 2.4 2.6"/>`,
    balai: `<path d="M15.5 3 11 11.5"/><path d="M6.5 12h9l1.4 8.5H5.1z"/><path d="M9 15.5v5M12 15.5v5"/>`,
    soin: `<rect x="4" y="4" width="16" height="16" rx="4.5"/><path d="M12 8.2v7.6M8.2 12h7.6"/>`,
    main: `<path d="M8 13V6.2a1.5 1.5 0 0 1 3 0V11M11 11V4.7a1.5 1.5 0 0 1 3 0V11M14 11V6.2a1.5 1.5 0 0 1 3 0V14c0 3.9-2.8 7-6.4 7-2.8 0-4.8-1.6-5.8-3.8l-1.4-3.4a1.5 1.5 0 0 1 2.6-1.4L8 14.6"/>`,
    de: `<rect x="4" y="4" width="16" height="16" rx="4.5"/><circle cx="8.8" cy="8.8" r="1.25" fill="currentColor" stroke="none"/><circle cx="12" cy="12" r="1.25" fill="currentColor" stroke="none"/><circle cx="15.2" cy="15.2" r="1.25" fill="currentColor" stroke="none"/>`,
    etoile: `<path d="M12 3.2l2.6 5.5 6 .8-4.4 4.1 1.1 5.9L12 16.6l-5.3 2.9 1.1-5.9-4.4-4.1 6-.8z"/>`,
    bulle: `<path d="M5 5h14v10.5h-8.5L6.5 19.5v-4H5z"/><path d="M12 8v3.4M12 13.4h.01"/>`,
    coquillage: `<path d="M4 15.5C4 9.6 7.6 5 12 5s8 4.6 8 10.5L17 19H7z"/><path d="M12 19V6.5M9 19l-1.2-10M15 19l1.2-10"/>`,
    panier: `<path d="M3.8 9.5h16.4l-1.6 9.5H5.4z"/><path d="M8 9.5l4-5.2 4 5.2M9.5 13v3M14.5 13v3"/>`,
    chapeau: `<path d="M3 16.5c3 2.4 15 2.4 18 0"/><path d="M6.2 16c0-6 2.2-9 5.8-9s5.8 3 5.8 9"/><path d="M6.6 13h10.8"/>`,
    livre: `<path d="M5 4.5h10a3 3 0 0 1 3 3v13H8a3 3 0 0 1-3-3z"/><path d="M5 17.5a3 3 0 0 1 3-3h10"/>`,
    reglages: `<circle cx="12" cy="12" r="3"/><path d="M12 2.6v3M12 18.4v3M2.6 12h3M18.4 12h3M5.4 5.4l2.1 2.1M16.5 16.5l2.1 2.1M5.4 18.6l2.1-2.1M16.5 7.5l2.1-2.1"/>`,
    fermer: `<path d="M6.5 6.5l11 11M17.5 6.5l-11 11"/>`,
    coeur: `<path d="M12 20s-7.5-4.6-7.5-10.3A4.2 4.2 0 0 1 12 7.2a4.2 4.2 0 0 1 7.5 2.5C19.5 15.4 12 20 12 20z"/>`,
    eclair: `<path d="M13.2 3 5.5 13.6h6l-1 7.4 8-10.8h-6z"/>`,
    bulles: `<circle cx="9" cy="14.2" r="4.3"/><circle cx="16.2" cy="7.8" r="3"/><circle cx="17.2" cy="16.4" r="2"/>`,
    thermo: `<path d="M10 13.8V5a2 2 0 0 1 4 0v8.8a4.2 4.2 0 1 1-4 0z"/><path d="M12 9v7"/>`,
    nuage: `<path d="M7.2 18.5a4.2 4.2 0 0 1-.4-8.4 5.4 5.4 0 0 1 10.2-1.4 4 4 0 0 1 .2 9.8z"/>`,
    pluie: `<path d="M7.2 14.5a4.2 4.2 0 0 1-.4-8.4 5.4 5.4 0 0 1 10.2-1.4 4 4 0 0 1 .2 9.8z"/><path d="M8.5 17.5l-1 2.5M12.5 17.5l-1 2.5M16.5 17.5l-1 2.5"/>`,
    arc: `<path d="M3.5 17a8.5 8.5 0 0 1 17 0"/><path d="M7 17a5 5 0 0 1 10 0"/>`,
    fleur: `<circle cx="12" cy="12" r="2.4"/><path d="M12 9.6c-1.6-2.6-1-5.6 0-6.6 1 1 1.6 4 0 6.6zM14.4 12c2.6-1.6 5.6-1 6.6 0-1 1-4 1.6-6.6 0zM12 14.4c1.6 2.6 1 5.6 0 6.6-1-1-1.6-4 0-6.6zM9.6 12c-2.6 1.6-5.6 1-6.6 0 1-1 4-1.6 6.6 0z"/>`,
    vent: `<path d="M3 9.5h11a3 3 0 1 0-3-3M3 14.5h15a3 3 0 1 1-3 3"/>`,
    photo: `<rect x="3" y="5" width="18" height="14" rx="2.5"/><circle cx="9" cy="10.2" r="2"/><path d="M21 16.5l-5.2-5.2-9 8.5"/>`,
    drapeau: `<path d="M5.5 21V4M5.5 4.5h11l-2.2 4 2.2 4h-11"/>`,
    maison: `<path d="M4 11.5 12 5l8 6.5M6.5 10v9.5h11V10"/><path d="M10 19.5v-5h4v5"/>`,
    loupe: `<circle cx="10.5" cy="10.5" r="6"/><path d="M15 15l5 5"/>`,
  };
  function ico(nom, cls = "") {
    const p = P[nom];
    if (!p) return "";
    return `<svg class="phb-ico ${cls}" viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" stroke-width="1.9" stroke-linecap="round" stroke-linejoin="round">${p}</svg>`;
  }
  window.PhilibertIcones = { ico, noms: Object.keys(P) };
})();
