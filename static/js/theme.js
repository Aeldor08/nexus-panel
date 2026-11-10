/* Thèmes NEXUS : Terminal (rouge, look Ultron) <-> Sentinelle (orange et bleu).
   - Sentinelle -> Terminal : animation de GLITCH (le signal se corrompt, puis l'accès root revient).
   - Terminal -> Sentinelle : le terminal se dérègle, puis CORRECTION DU GLITCH (un balayage répare
     l'écran de haut en bas).
   Le changement recharge la page (pour recolorer aussi les courbes) : la 1re moitié de l'animation joue
   avant le rechargement, la 2de après (sessionStorage "nexus-tx"). */
(() => {
  const root = document.documentElement;
  const THEMES = { terminal: "Terminal", sentinelle: "Sentinelle" };
  const cur = root.dataset.theme || "terminal";
  const btn = document.getElementById("btn-theme");
  const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const wait = ms => new Promise(r => setTimeout(r, ms));
  let busy = false;
  btn.textContent = "◐ " + THEMES[cur];

  function overlay(kind) {
    const o = document.createElement("div");
    o.className = "tx-overlay tx-" + kind;
    o.setAttribute("aria-hidden", "true");
    o.innerHTML = '<div class="tx-black"></div><div class="tx-dirty"><div class="tx-slices"></div><div class="tx-noise"></div></div>'
      + '<div class="tx-scan"></div><div class="tx-label"></div>';
    document.body.appendChild(o);
    return o;
  }

  // Bandes horizontales décalées / recolorées, régénérées à chaque image
  function scramble(o, k) {
    const box = o.querySelector(".tx-slices");
    let html = "";
    const n = Math.round(3 + 12 * k);
    for (let i = 0; i < n; i++) {
      const top = Math.random() * 100, h = 1 + Math.random() * 9 * k;
      const dx = ((Math.random() - .5) * 80 * k).toFixed(1), hue = Math.floor(Math.random() * 360);
      html += `<i style="top:${top}%;height:${h}vh;--dx:${dx}px;--hue:${hue}deg"></i>`;
    }
    box.innerHTML = html;
    root.style.setProperty("--tx-k", k.toFixed(3));
    root.style.setProperty("--tx-dx", ((Math.random() - .5) * 26 * k).toFixed(1) + "px");
    root.style.setProperty("--tx-dy", ((Math.random() - .5) * 6 * k).toFixed(1) + "px");
  }

  // Fait varier l'intensité du glitch de « from » à « to » pendant « ms »
  function glitch(o, ms, from, to, onStep) {
    root.classList.add("tx-run");
    return new Promise(res => {
      const t0 = performance.now();
      (function step() {
        const p = Math.min(1, (performance.now() - t0) / ms);
        const k = from + (to - from) * p;
        scramble(o, Math.max(0, k * (.7 + Math.random() * .6)));
        if (onStep) onStep(p);
        if (p < 1) setTimeout(step, 50); else res();
      })();
    });
  }

  function cleanup(o) {
    root.classList.remove("tx-run", "tx-calm");
    ["--tx-k", "--tx-dx", "--tx-dy", "--tx-y"].forEach(v => root.style.removeProperty(v));
    o.classList.add("tx-done");
    setTimeout(() => o.remove(), 400);
  }

  // ---- 1re moitié : avant le rechargement ----
  async function switchTo(next) {
    if (busy) return;
    busy = true;
    try { localStorage.setItem("nexus-theme", next); } catch (e) {}
    if (reduce) { location.reload(); return; }
    const kind = next === "terminal" ? "glitch" : "fix";
    try { sessionStorage.setItem("nexus-tx", kind); } catch (e) {}
    const o = overlay("out");
    o.querySelector(".tx-label").textContent = kind === "glitch" ? "⚠ SIGNAL CORROMPU" : "⚠ INSTABILITÉ DÉTECTÉE";
    await glitch(o, 750, .15, 1);
    o.classList.add("tx-blackout");
    await wait(160);
    location.reload();
  }

  // ---- 2de moitié : après le rechargement ----
  async function arrive(kind) {
    const o = overlay(kind);
    o.classList.add("tx-blackout", "tx-instant");
    root.classList.remove("tx-pending");
    // On attend que la page soit réellement dessinée sous l'écran noir avant de la dévoiler
    await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
    await wait(150);
    o.classList.remove("tx-blackout", "tx-instant");
    const label = o.querySelector(".tx-label");
    if (kind === "glitch") {
      // Terminal (rouge, façon Ultron) : le signal crache, tremble, puis la prise de contrôle aboutit
      label.textContent = "PRISE DE CONTRÔLE…";
      await glitch(o, 1100, 1, 0, p => { if (p > .55) label.textContent = "CONTRÔLE ACQUIS_"; });
    } else {
      // Sentinelle : un balayage de haut en bas répare l'écran ; au-dessus de la ligne, tout est propre
      root.style.setProperty("--tx-y", "0%");
      root.classList.add("tx-calm");      // pas de tremblement : la partie déjà corrigée reste nette
      await glitch(o, 1300, 1, .15, p => {
        const e = 1 - Math.pow(1 - p, 2);
        root.style.setProperty("--tx-y", (e * 100).toFixed(1) + "%");
        label.textContent = `CORRECTION DU SIGNAL… ${Math.round(e * 100)} %`;
      });
      label.textContent = "SYSTÈME STABILISÉ";
      o.classList.add("tx-stable");
      await wait(450);
    }
    cleanup(o);
  }

  btn.addEventListener("click", () => switchTo(cur === "terminal" ? "sentinelle" : "terminal"));

  let pending = null;
  try { pending = sessionStorage.getItem("nexus-tx"); sessionStorage.removeItem("nexus-tx"); } catch (e) {}
  if (pending && !reduce) arrive(pending);
  else root.classList.remove("tx-pending");
})();
