"use strict";
// ===== Jours fériés (France) et fêtes classiques, calculés localement (aucune connexion) =====
// NxFetes.du("2026-12-25") → [{ nom, icone, ferie }] ; NxFetes.entre(debut, fin) → { "aaaa-mm-jj": [...] }.
// Dates mobiles : Pâques (algorithme grégorien de Meeus/Jones/Butcher) et ses dérivées, fêtes des mères /
// pères / grands-parents, changements d'heure (derniers dimanches de mars et d'octobre).
(() => {
  const pad = n => String(n).padStart(2, "0");
  const ymd = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  const plus = (d, n) => new Date(d.getFullYear(), d.getMonth(), d.getDate() + n);

  function paques(y) {
    const a = y % 19, b = Math.floor(y / 100), c = y % 100, d = Math.floor(b / 4), e = b % 4;
    const f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3), h = (19 * a + b - d - g + 15) % 30;
    const i = Math.floor(c / 4), k = c % 4, l = (32 + 2 * e + 2 * i - h - k) % 7, m = Math.floor((a + 11 * h + 22 * l) / 451);
    const mois = Math.floor((h + l - 7 * m + 114) / 31), jour = ((h + l - 7 * m + 114) % 31) + 1;
    return new Date(y, mois - 1, jour);
  }
  // n-ième dimanche d'un mois (n = -1 : le dernier)
  function dimanche(y, mois, n) {
    if (n > 0) { const d = new Date(y, mois, 1); return plus(d, (7 - d.getDay()) % 7 + 7 * (n - 1)); }
    const d = new Date(y, mois + 1, 0); return plus(d, -d.getDay());
  }

  const cache = new Map();
  function annee(y) {
    if (cache.has(y)) return cache.get(y);
    const P = paques(y), pentecote = plus(P, 49);
    let meres = dimanche(y, 4, -1);                               // dernier dimanche de mai…
    if (ymd(meres) === ymd(pentecote)) meres = dimanche(y, 5, 1);   // …ou 1er de juin s'il tombe à la Pentecôte
    const L = [
      // jours fériés (France métropolitaine)
      [new Date(y, 0, 1), "Jour de l'an", "🎆", true],
      [plus(P, 1), "Lundi de Pâques", "🐣", true],
      [new Date(y, 4, 1), "Fête du Travail", "🌿", true],
      [new Date(y, 4, 8), "Victoire 1945", "🕊️", true],
      [plus(P, 39), "Ascension", "☁️", true],
      [plus(P, 50), "Lundi de Pentecôte", "🕊️", true],
      [new Date(y, 6, 14), "Fête nationale", "🇫🇷", true],
      [new Date(y, 7, 15), "Assomption", "⛪", true],
      [new Date(y, 10, 1), "Toussaint", "🕯️", true],
      [new Date(y, 10, 11), "Armistice 1918", "🕊️", true],
      [new Date(y, 11, 25), "Noël", "🎄", true],
      // fêtes et dates classiques (non fériées)
      [new Date(y, 0, 6), "Épiphanie", "👑", false],
      [new Date(y, 1, 2), "Chandeleur", "🥞", false],
      [new Date(y, 1, 14), "Saint-Valentin", "💝", false],
      [plus(P, -47), "Mardi gras", "🎭", false],
      [dimanche(y, 2, 1), "Fête des grands-mères", "💐", false],
      [dimanche(y, 2, -1), "Passage à l'heure d'été (+1 h)", "⏰", false],
      [new Date(y, 3, 1), "Poisson d'avril", "🐟", false],
      [P, "Pâques", "🥚", false],
      [pentecote, "Pentecôte", "🕊️", false],
      [meres, "Fête des mères", "💐", false],
      [dimanche(y, 5, 3), "Fête des pères", "👔", false],
      [new Date(y, 5, 21), "Fête de la musique", "🎶", false],
      [dimanche(y, 9, 1), "Fête des grands-pères", "🎩", false],
      [dimanche(y, 9, -1), "Passage à l'heure d'hiver (−1 h)", "⏰", false],
      [new Date(y, 9, 31), "Halloween", "🎃", false],
      [new Date(y, 11, 24), "Réveillon de Noël", "✨", false],
      [new Date(y, 11, 31), "Saint-Sylvestre", "🥂", false],
    ];
    const parJour = {};
    for (const [d, nom, icone, ferie] of L) (parJour[ymd(d)] ||= []).push({ nom, icone, ferie });
    for (const k in parJour) parJour[k].sort((a, b) => b.ferie - a.ferie);   // le jour férié d'abord
    cache.set(y, parJour);
    return parJour;
  }

  const du = key => (annee(+key.slice(0, 4))[key] || []);
  function entre(debut, fin) {
    const out = {};
    for (let y = +debut.slice(0, 4); y <= +fin.slice(0, 4); y++)
      for (const [k, v] of Object.entries(annee(y))) if (k >= debut && k <= fin) out[k] = v;
    return out;
  }
  window.NxFetes = { du, entre, paques: y => ymd(paques(y)) };
})();
