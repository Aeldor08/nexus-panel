"use strict";
// ===== Sommaire (écran d'accueil) : une tuile par catégorie, aperçu en direct, accès direct aux sous-parties =====
(() => {
  const TILES = [
    { tab: "pc", title: "PC", icon: "▣", color: "--cyan", desc: "Performances et matériel",
      parts: [["cpu", "CPU"], ["ram", "RAM"], ["gpu", "GPU"], ["temperatures", "Températures"], ["disques", "Disques"],
              ["processus", "Processus"], ["ventilation", "Ventilation"], ["reseau", "Débit réseau"], ["modejeu", "Mode jeu"]] },
    { tab: "media", title: "Média", icon: "♪", color: "--magenta", desc: "Lecture en cours et son",
      parts: [["lecteur", "Lecteur"], ["melangeur", "Mélangeur de son"]] },
    { tab: "deck", title: "Deck", icon: "▦", color: "--magenta", desc: "Boutons d'actions rapides",
      parts: [["boutons", "Boutons"], ["journal", "Journal"]] },
    { tab: "lanceur", title: "Lanceur", icon: "▶", color: "--cyan", desc: "Jeux et applications",
      parts: [["jeux", "Jeux"], ["applis", "Applications"]] },
    { tab: "reseau", title: "Réseau", icon: "⌁", color: "--yellow", desc: "Connexion et appareils",
      parts: [["ping", "Ping & qualité"], ["latence", "Latence"], ["appareils", "Appareils"], ["debit", "Test de débit"], ["coupures", "Coupures"]] },
    { tab: "statistiques", title: "Statistiques", icon: "▤", color: "--cyan", desc: "Temps de PC, de jeu et de musique",
      parts: [["aujourdhui", "Aujourd'hui"], ["jeux", "Jeux"], ["activite", "Activité"]] },
    { tab: "agenda", title: "Agenda", icon: "◷", color: "--yellow", desc: "Événements, to-do, notes",
      parts: [["calendrier", "Calendrier"], ["avenir", "À venir"], ["todo", "To-do"], ["notes", "Notes"]] },
    { tab: "souvenirs", title: "Souvenirs", icon: "▧", color: "--magenta", desc: "Mur de photos jour par jour",
      parts: [["mur", "Mur du jour"], ["ajouter", "Ajouter"], ["cejourla", "Ce jour-là"], ["calendrier", "Calendrier"]] },
    { tab: "journal", title: "Journal", icon: "✎", color: "--yellow", desc: "Humeur et notes du jour",
      parts: [["aujourdhui", "Aujourd'hui"], ["mois", "Vue mois"], ["recherche", "Recherche"]] },
  ];

  const root = $("tab-accueil");
  root.innerHTML = `
    <div class="home-hero">
      <div><div class="home-hello" id="h-hello"></div><div class="home-date" id="h-date"></div></div>
      <div class="home-time" id="h-time"></div>
    </div>
    <div class="nx-maj-accueil" id="h-maj" role="status" hidden></div>
    <section class="home-grid">
      ${TILES.map((t, i) => `
        <article class="card home-tile" style="--accent: var(${t.color})">
          <a class="home-main" href="#${t.tab}" aria-label="Ouvrir ${t.title}">
            <span class="home-ico" aria-hidden="true">${t.icon}</span>
            <span class="home-title">${t.title}<small>${t.desc}</small></span>
            <span class="home-go" aria-hidden="true">→</span>
          </a>
          <div class="home-live" id="h-live-${t.tab}"><span class="muted">…</span></div>
          <nav class="home-parts" aria-label="Accès direct ${t.title}">
            ${t.parts.map(([id, label]) => `<a href="#${t.tab}/${id}">${label}</a>`).join("")}
          </nav>
        </article>`).join("")}
      <article class="card home-tile home-philibert" style="--accent: var(--green)" data-panel="philibert">
        <a class="home-main" href="#accueil" data-philibert="" aria-label="Ouvrir l'île de Philibert">
          <span class="home-ico" aria-hidden="true"><svg viewBox="0 0 24 24" width="30" height="30" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2.5 17.5c2.8.4 4.6-1.4 6.6-3.2 1-1 2.4-1.5 3.9-1.5h3.4c1.3 0 2.2-.9 3.2-1.6.9-.5 2 0 2.2.9.3 1-.3 1.9-1.3 2.2l-2.1.6"/>
            <path d="M10.5 13.6l-1.2 4.2M15.6 12.8l.9 4.4M13 12.8l-.3-2.2M15 12.8l.4-2.4M11 13l-.6-2"/><circle cx="19.4" cy="11.6" r=".7" fill="currentColor" stroke="none"/></svg></span>
          <span class="home-title">Philibert<small>Ton iguane et son île</small></span>
          <span class="home-go" aria-hidden="true">→</span>
        </a>
        <div class="home-live" id="h-live-philibert"><span class="muted">…</span></div>
        <nav class="home-parts" aria-label="Accès direct à l'île de Philibert">
          <a href="#accueil" data-philibert="nourrir">Nourrir</a><a href="#accueil" data-philibert="jouer">Jouer</a>
          <a href="#accueil" data-philibert="boutique">Boutique</a><a href="#accueil" data-philibert="carnet">Carnet</a>
        </nav>
      </article>
    </section>
    <p class="hint" style="text-align:center">Clique sur une catégorie ou directement sur une sous-partie.
      Pour revenir ici : bouton <b>◀ Retour</b>, onglet <b>⌂ Sommaire</b> ou touche <b>Échap</b>. Le logo <b>NEXUS</b> ramène à la page de garde.
      · <a href="#accueil" id="h-intro" style="color:var(--magenta)">▶ Rejouer l'intro</a>
      · <a href="#accueil" id="h-version" style="color:var(--cyan)">ℹ Version et mises à jour</a>
      · <a href="#accueil" id="h-sante" style="color:var(--cyan)">✚ Santé de NEXUS</a></p>`;
  $("h-intro").addEventListener("click", ev => { ev.preventDefault(); if (window.replayIntro) window.replayIntro(); });
  $("h-version").addEventListener("click", ev => { ev.preventDefault(); if (window.nxVersion) window.nxVersion.ouvrir(); });
  $("h-sante").addEventListener("click", ev => { ev.preventDefault(); if (window.nxSante) window.nxSante.ouvrir(); });
  // Tuile Philibert : ouvre son île (directement sur un panneau pour les accès rapides)
  root.addEventListener("click", ev => {
    const a = ev.target.closest("[data-philibert]");
    if (!a) return;
    ev.preventDefault();
    if (window.PhilibertIle) window.PhilibertIle.ouvrir(a.dataset.philibert || undefined);
  });

  // Réécrit une tuile seulement si son contenu a changé (moins de travail de mise en page chaque seconde)
  const dernier = {};
  const live = (tab, html) => {
    if (dernier[tab] === html) return false;
    const el = $("h-live-" + tab);
    if (!el) return false;
    el.innerHTML = html; dernier[tab] = html;
    return true;
  };
  const kv = (label, value, cls = "") => `<span class="hk"><small>${label}</small><b class="${cls}">${value}</b></span>`;
  const pct = v => v == null ? "–" : Math.round(v) + " %";
  const deg = v => v == null ? "–" : Math.round(v) + "°";

  // ---- En-tête : salutation, date, heure ----
  function hero() {
    const now = new Date(), h = now.getHours();
    $("h-hello").textContent = h < 5 ? "Bonne nuit" : h < 12 ? "Bonjour" : h < 18 ? "Bon après-midi" : "Bonsoir";
    $("h-date").textContent = now.toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
    $("h-time").innerHTML = now.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" }) +
      `<small>:${String(now.getSeconds()).padStart(2, "0")}</small>`;
  }

  // ---- Aperçus en direct ----
  function fromStats() {
    const s = window.lastStats;
    if (!s) return;
    const g = s.gpu && s.gpu.devices[0];
    // (n-pct / n-deg : largeur réservée pour la valeur maximale, les blocs ne bougent plus quand un chiffre change)
    live("pc", kv("CPU", pct(s.cpu.percent), "n-pct") + kv("CPU temp.", deg(s.cpu.temperature), "n-deg " + tempClass(s.cpu.temperature, 65, 80)) +
      kv("GPU", g ? pct(g.load_percent) : "–", "n-pct") + kv("GPU temp.", g ? deg(g.temperature) : "–", "n-deg " + (g ? tempClass(g.temperature, 70, 83) : "")) +
      kv("RAM", pct(s.ram.percent), "n-pct") + (s.gamemode && s.gamemode.in_game ? kv("Mode jeu", "▶ " + esc(gameLabel(s.gamemode.game)), "t-ok") : ""));
    // (les alertes s'affichent une seule fois : dans la barre commune sous les onglets, avec « Ignorer »)
  }
  function fromMedia() {
    const m = window.mediaState;
    const s = m && m.sessions && (m.sessions.find(x => x.status === "playing") || m.sessions[0]);
    live("media", s
      ? `<span class="hk wide"><small>${s.status === "playing" ? "▶ En lecture" : "❚❚ En pause"} · ${esc(s.app)}</small><b>${esc(s.title || "Sans titre")}</b></span>`
      : `<span class="muted">Rien en lecture</span>`);
  }
  let lastGame = null;
  async function fromLauncher() {
    try {
      const d = await api("/api/launcher");
      lastGame = d.games.find(g => !g.hidden) || null;
      const neuf = live("lanceur", (lastGame ? kv("Dernier jeu", esc(lastGame.name)) : "") + kv("Jeux", d.games.length) + kv("Applis", d.apps.length) +
        (lastGame ? `<button class="btn" id="h-play" title="Lancer ${esc(lastGame.name)}">▶ Jouer</button>` : ""));
      const b = neuf && $("h-play");             // nouvel écouteur seulement sur un bouton tout neuf
      if (b) b.addEventListener("click", async () => {
        try { await api("/api/launcher/launch", { id: lastGame.id }); toast("▶ Lancement : " + lastGame.name); } catch (e) { toast(e.message, true); }
      });
    } catch (e) { live("lanceur", `<span class="muted">indisponible</span>`); }
  }
  async function fromNet() {
    try {
      const d = await api("/api/net");
      const cf = d.targets.find(t => t.key === "cloudflare");
      const on = d.lan.devices.filter(x => x.online).length;
      live("reseau", kv("Ping", cf && cf.last != null ? Math.round(cf.last) + " ms" : "perdu", cf && cf.last != null && cf.last < 30 ? "t-ok" : "t-warn") +
        kv("Qualité", esc(d.quality.label), `g-${d.quality.grade}`) + kv("Appareils", on) +
        (d.internet_down ? kv("Internet", "COUPÉ", "t-hot") : ""));
    } catch (e) { live("reseau", `<span class="muted">indisponible</span>`); }
  }
  function fromAgenda() {
    const a = window.agendaSummary && window.agendaSummary(7);
    if (!a) return;
    const n = a.next[0];
    const d0 = new Date(), today = `${d0.getFullYear()}-${String(d0.getMonth() + 1).padStart(2, "0")}-${String(d0.getDate()).padStart(2, "0")}`;
    const when = n ? (n.key === today ? "aujourd'hui" :
      new Date(n.key + "T12:00").toLocaleDateString("fr-FR", { weekday: "short", day: "numeric" })) : "";
    live("agenda", (n ? `<span class="hk wide"><small>Prochain · ${when}${n.time ? " " + n.time : ""}</small><b>${esc(n.label)}</b></span>`
                     : `<span class="hk wide"><small>Prochains 7 jours</small><b>Rien de prévu</b></span>`) +
      kv("To-do", a.todos ? a.todos + " à faire" : "✔ rien"));
  }
  // Souvenirs, statistiques, journal : un aperçu sans contenu privé (nombres, durée, humeur seulement)
  const dur = s => { const m = Math.round((s || 0) / 60); return m >= 60 ? `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")}` : `${m} min`; };
  async function fromPerso() {
    try {
      const r = await api("/api/perso/resume");
      live("souvenirs", kv("Aujourd'hui", r.souvenirs.aujourdhui + " photo" + (r.souvenirs.aujourdhui > 1 ? "s" : "")) +
        kv("Ce jour-là", r.souvenirs.ce_jour_la) + kv("Total", r.souvenirs.total));
      live("statistiques", r.stats.pause ? `<span class="hk wide"><small>Suivi</small><b>⏸ en pause</b></span>` :
        kv("Actif aujourd'hui", dur(r.stats.actif_s)) + (r.stats.jeu ? kv(esc(r.stats.jeu.nom), dur(r.stats.jeu.secondes)) : ""));
      live("journal", r.journal.verrouille ? `<span class="hk wide"><small>Journal</small><b>🔒 verrouillé</b></span>` :
        kv("Humeur du jour", r.journal.humeur || "—") + kv("Aujourd'hui", r.journal.ecrit ? "✔ écrit" : "pas encore") + kv("Jours écrits", r.journal.jours));
    } catch (e) { ["souvenirs", "statistiques", "journal"].forEach(t => live(t, `<span class="muted">indisponible</span>`)); }
  }

  // Philibert : humeur, besoin principal, âge et coquillages (mis à jour à chaque nouvel état reçu)
  const HUMEURS = { joyeux: "Joyeux", calme: "Tranquille", dort: "Il dort", malade: "Malade", grognon: "Grognon", appel: "Il t'appelle", froid: "Il a froid",
    oeuf: "Encore un œuf", veto: "Chez la tortue vétérinaire", pension: "En pension chez la voisine" };
  function fromPhilibert(e) {
    e = e || (window.nxPhilibert && window.nxPhilibert.etat());
    if (!e) return;
    const b = (e.besoins || []).filter(x => x.id !== "ventre")[0];
    const ton = e.niveau === "malade" ? "t-hot" : b || e.appel ? "t-warn" : "t-ok";
    live("philibert", kv("Humeur", esc(HUMEURS[e.dort ? "dort" : e.humeur] || "—"), ton) +
      (["veto", "pension", "oeuf"].includes(e.niveau) ? "" : kv("Besoin", b ? esc(b.texte.split(" : ")[0]) : "rien", b ? "t-warn" : "")) +
      kv(e.stade === "oeuf" ? "Stade" : "Âge", e.stade === "oeuf" ? "œuf" : e.age_jours < 1 ? Math.round(e.age_jours * 24) + " h" : e.age_jours.toFixed(1).replace(".", ",") + " j") +
      kv("Coquillages", e.coquillages));
  }
  addEventListener("philibert:maj", ev => fromPhilibert(ev.detail));

  let fast = null, slow = null;
  function fromDeck() {
    live("deck", `<span class="hk wide"><small>Stream deck</small><b>Gros boutons tactiles</b></span>`);
  }
  function tickFast() { if (document.hidden) return; hero(); fromStats(); fromMedia(); fromAgenda(); fromDeck(); }
  let perso = null;
  Tabs.register("accueil", {
    async show() {
      tickFast();
      fromLauncher();
      fromNet();
      fromPerso();
      fromPhilibert();
      clearInterval(fast); clearInterval(slow); clearInterval(perso);
      fast = setInterval(tickFast, 1000);
      slow = setInterval(() => { if (!document.hidden) fromNet(); }, 3000);
      perso = setInterval(() => { if (!document.hidden) fromPerso(); }, 30000);
    },
    hide() { clearInterval(fast); clearInterval(slow); clearInterval(perso); fast = slow = perso = null; },
  });
})();
