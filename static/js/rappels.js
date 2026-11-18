"use strict";
/* Rappels de l'agenda dans le panel. Le serveur calcule et enregistre les rappels (reminders.py) ;
   la page les lit toutes les 15 s et affiche chaque nouveau rappel :
   - bannière en haut à droite, qui reste jusqu'à ce qu'on clique « OK » ;
   - petit son (réglable dans ⚙ Réglages, mémorisé sur cet appareil) ;
   - notification Windows si les notifications du panel sont activées.
   Un rappel déjà affiché sur cet appareil ne réapparaît pas (même après un rechargement). */
(() => {
  const SEEN = "nexus-rappels-vus", SOUND = "nexus-rappel-son";
  const MAX_AGE = 30 * 60;                // un rappel de plus de 30 min n'est plus affiché
  const read = () => { try { return JSON.parse(localStorage.getItem(SEEN)) || []; } catch (e) { return []; } };
  const write = v => { try { localStorage.setItem(SEEN, JSON.stringify(v.slice(-150))); } catch (e) {} };
  window.reminderSound = {
    get on() { try { return localStorage.getItem(SOUND) !== "0"; } catch (e) { return true; } },
    set on(v) { try { localStorage.setItem(SOUND, v ? "1" : "0"); } catch (e) {} },
    play: beep,
  };

  const box = document.createElement("div");
  box.className = "nx-rem-stack";
  box.setAttribute("role", "status");
  box.setAttribute("aria-live", "polite");
  document.body.appendChild(box);

  let ctx = null;
  function beep() {
    try {
      ctx = ctx || new (window.AudioContext || window.webkitAudioContext)();
      if (ctx.state === "suspended") ctx.resume();
      const t = ctx.currentTime;
      [[880, 0], [1175, .18], [880, .36]].forEach(([f, d]) => {
        const o = ctx.createOscillator(), g = ctx.createGain();
        o.type = "sine"; o.frequency.value = f;
        g.gain.setValueAtTime(0, t + d); g.gain.linearRampToValueAtTime(.18, t + d + .02);
        g.gain.exponentialRampToValueAtTime(.001, t + d + .16);
        o.connect(g).connect(ctx.destination); o.start(t + d); o.stop(t + d + .17);
      });
    } catch (e) { /* son bloqué par le navigateur tant qu'on n'a pas cliqué sur la page : sans gravité */ }
  }

  function show(r) {
    const el = document.createElement("div");
    el.className = "nx-rem" + (r.anniversaire ? " bday" : "");
    el.innerHTML = `<b>${esc(r.titre)}</b><span>${esc(r.texte)}</span>
      ${r.en_retard ? `<small>Rappel envoyé en retard (NEXUS était fermé à l'heure prévue)</small>` : ""}
      <button class="btn" aria-label="Fermer le rappel">OK</button>`;
    el.querySelector("button").addEventListener("click", () => el.remove());
    box.appendChild(el);
    if (window.reminderSound.on) beep();
    if (!window.NEXUS_NATIVE && typeof notifOn !== "undefined" && notifOn) {
      try { new Notification(r.titre, { body: r.texte, tag: "rappel-" + r.id }); } catch (e) {}
    }
  }

  async function poll() {
    let list;
    try { list = (await api("/api/agenda/rappels")).rappels || []; } catch (e) { return; }
    const seen = read(), now = Date.now() / 1000;
    let fresh = false;
    for (const r of list) {
      if (seen.includes(r.id)) continue;
      seen.push(r.id);
      if (now - r.envoye > MAX_AGE) continue;
      show(r);
      fresh = true;
    }
    write(seen);
    if (fresh && window.agendaRefresh) window.agendaRefresh();
  }
  poll();
  setInterval(poll, 15000);
})();
