"use strict";
// ===== Onglets + utilitaires partagés par les onglets supplémentaires =====

const Tabs = {
  current: null,
  handlers: {},          // nom -> { show(), hide() }
  register(name, h) { this.handlers[name] = h; if (this.current === name && h.show) h.show(); },
  select(name) {
    if (!document.getElementById("tab-" + name)) name = "accueil";
    const back = document.getElementById("nav-back");
    if (back) back.hidden = name === "accueil";
    if (name === this.current) return;
    const prev = this.current;
    this.current = name;
    document.querySelectorAll("#tabs a[data-tab]").forEach(a =>
      a.setAttribute("aria-selected", a.dataset.tab === name ? "true" : "false"));
    document.querySelectorAll("main.tab").forEach(m => { m.hidden = m.id !== "tab-" + name; });
    if (prev && this.handlers[prev] && this.handlers[prev].hide) this.handlers[prev].hide();
    if (this.handlers[name] && this.handlers[name].show) this.handlers[name].show();
    if (!location.hash.includes("/")) window.scrollTo({ top: 0 });
  },
};

// Sous-parties accessibles directement (#onglet/partie) : élément repère -> sa carte
const SECTIONS = {
  "pc/cpu": "#g-cpu", "pc/ram": "#g-ram", "pc/gpu": "#g-gpu", "pc/temperatures": "#t-cpu",
  "pc/reseau": "#net-rx", "pc/disques": "#disks", "pc/processus": "#proc-cpu",
  "pc/ventilation": "#fans", "pc/modejeu": "#gm-state",
  "media/lecteur": "#m-body", "media/melangeur": "#mx-apps",
  "lanceur/jeux": "#l-games", "lanceur/applis": "#l-apps",
  "deck/boutons": "#dk-grid", "deck/journal": "#dk-log",
  "reseau/ping": "#p-quality", "reseau/latence": "#p-chart", "reseau/appareils": "#d-list",
  "reseau/debit": "#s-run", "reseau/coupures": "#o-list",
  "agenda/calendrier": "#a-cal", "agenda/avenir": "#a-up", "agenda/todo": "#t-list", "agenda/notes": "#n-list",
  "souvenirs/mur": "#sv-wall", "souvenirs/ajouter": "#sv-drop", "souvenirs/cejourla": "#sv-otd", "souvenirs/calendrier": "#sv-cal",
  "statistiques/aujourdhui": "#st-summary", "statistiques/jeux": "#st-games", "statistiques/activite": "#st-days",
  "journal/aujourdhui": "#jn-text", "journal/mois": "#jn-month", "journal/recherche": "#jn-q",
};
function goToSection(key, tries = 0) {
  const sel = SECTIONS[key];
  const el = sel && document.querySelector(sel);
  if (!el) { if (sel && tries < 20) setTimeout(() => goToSection(key, tries + 1), 100); return; }
  const card = el.closest(".card") || el;
  // Après l'affichage de l'onglet (une image), pour que la position soit juste
  requestAnimationFrame(() => {
    const top = card.getBoundingClientRect().top + window.scrollY - 14;
    window.scrollTo({ top, behavior: matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    card.classList.remove("flash"); void card.offsetWidth; card.classList.add("flash");
    setTimeout(() => card.classList.remove("flash"), 1600);
  });
}
function route() {
  const [tab, sec] = location.hash.slice(1).split("/");
  Tabs.select(tab || "accueil");
  if (sec) goToSection(`${tab}/${sec}`);
}
window.addEventListener("hashchange", route);
route();

// Bouton Retour et touche Échap : retour au sommaire
document.getElementById("nav-back").addEventListener("click", () => { location.hash = "#accueil"; });
document.addEventListener("keydown", ev => {
  if (ev.key !== "Escape" || Tabs.current === "accueil") return;
  const t = ev.target instanceof Element ? ev.target : null;
  if ((t && t.closest("input, textarea, select, dialog")) || document.querySelector("dialog[open]")) return;
  location.hash = "#accueil";
});

// Requêtes vers le serveur du panel
async function api(path, body, method) {
  const opt = { cache: "no-store" };
  if (body !== undefined) {
    opt.method = method || "POST";
    opt.headers = { "Content-Type": "application/json" };
    opt.body = JSON.stringify(body);
  }
  const r = await fetch(path, opt);
  let data = null;
  try { data = await r.json(); } catch (e) {}
  if (!r.ok) {
    const err = new Error((data && data.error) || ("HTTP " + r.status));
    err.data = data;            // ex. { champs: { date: "Date invalide" } } pour afficher les erreurs à côté des champs
    err.status = r.status;
    throw err;
  }
  return data;
}

// Petite notification en bas à droite
let toastTimer;
function toast(msg, isErr) {
  let t = document.getElementById("toast");
  if (!t) { t = document.createElement("div"); t.id = "toast"; t.setAttribute("role", "status"); document.body.appendChild(t); }
  t.className = "toast" + (isErr ? " err" : "");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { t.hidden = true; }, 3500);
}

// Onglet caché (autre onglet, fenêtre réduite) : toutes les animations CSS se mettent en pause
// (classe nx-pause, voir theme.css) ; elles reprennent là où elles en étaient.
const nxSyncPause = () => document.documentElement.classList.toggle("nx-pause", document.hidden);
document.addEventListener("visibilitychange", nxSyncPause);
nxSyncPause();

// Polling actif seulement quand l'onglet est visible
function poller(fn, ms) {
  let timer = null, busy = false;
  const run = async () => {
    if (busy || document.hidden) return;        // onglet caché : pas de requête (reprend au prochain tour)
    busy = true;
    try { await fn(); } catch (e) { /* l'onglet affiche son propre état d'erreur */ }
    finally { busy = false; }
  };
  return {
    start() { if (!timer) { run(); timer = setInterval(run, ms); } },
    stop() { clearInterval(timer); timer = null; },
    now: run,
  };
}

// Bouton ✦ Claude : ouvre l'appli de bureau ; clic droit (ou si l'appli est absente) : claude.ai
async function openClaude(web) {
  if (!web) {
    try {
      const r = await api("/api/launcher/launch", { id: "app:claude" });
      if (r.ok) { toast("✦ Ouverture de Claude"); return; }
    } catch (e) { /* appli absente : on bascule sur le site */ }
  }
  window.open("https://claude.ai", "_blank", "noopener");
}
document.getElementById("btn-claude").addEventListener("click", () => openClaude(false));
document.getElementById("btn-claude").addEventListener("contextmenu", ev => { ev.preventDefault(); openClaude(true); });

function fmtDur(s) {
  if (s == null || !isFinite(s)) return "–:––";
  s = Math.max(0, Math.floor(s));
  const h = Math.floor(s / 3600), m = Math.floor(s % 3600 / 60), sec = String(s % 60).padStart(2, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${sec}` : `${m}:${sec}`;
}
function fmtAgo(ts) {
  if (!ts) return "–";
  const d = Date.now() / 1000 - ts;
  if (d < 60) return "à l'instant";
  if (d < 3600) return `il y a ${Math.floor(d / 60)} min`;
  if (d < 86400) return `il y a ${Math.floor(d / 3600)} h`;
  if (d < 86400 * 30) return `il y a ${Math.floor(d / 86400)} j`;
  return new Date(ts * 1000).toLocaleDateString("fr-FR");
}
function uid() { return Date.now().toString(36) + Math.random().toString(36).slice(2, 7); }
