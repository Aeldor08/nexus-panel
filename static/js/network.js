"use strict";
// ===== Onglet Réseau : ping, qualité, coupures, test de débit, appareils connectés =====
(() => {
  const root = $("tab-reseau");
  const COLORS = { gateway: css("--yellow"), cloudflare: css("--cyan"), google: css("--magenta") };
  addEventListener("nexus:profile", () => Object.assign(COLORS, { gateway: css("--yellow"), cloudflare: css("--cyan"), google: css("--magenta") }));
  root.innerHTML = `
    <section class="ping-cards">
      <div class="card c-net"><h2>Box / routeur <small id="p-ip-gateway"></small></h2><div id="p-gateway"></div></div>
      <div class="card c-net"><h2>Cloudflare <small>1.1.1.1</small></h2><div id="p-cloudflare"></div></div>
      <div class="card c-net"><h2>Google <small>8.8.8.8</small></h2><div id="p-google"></div></div>
      <div class="card c-net"><h2>Qualité</h2><div id="p-quality"></div></div>
    </section>
    <div class="card c-net" style="margin-top:18px">
      <h2>Latence — 5 dernières minutes <small id="p-scale"></small></h2>
      <canvas class="chart" id="p-chart"></canvas>
      <div class="legend">
        <span><i style="background:${COLORS.gateway}"></i>Box</span>
        <span><i style="background:${COLORS.cloudflare}"></i>Cloudflare</span>
        <span><i style="background:${COLORS.google}"></i>Google</span>
        <span><i style="background:${css("--hot")}"></i>Paquet perdu</span>
      </div>
    </div>
    <section class="row2">
      <div class="card c-net">
        <h2>Appareils connectés <small id="d-sub"></small></h2>
        <div class="form-row" style="margin-bottom:10px">
          <button class="btn big" id="d-scan">Scanner maintenant</button>
          <span class="muted" style="font-size:14px" id="d-status"></span>
        </div>
        <div class="table-wrap"><table class="tbl">
          <thead><tr><th></th><th>Appareil</th><th>IP</th><th>MAC</th><th>Ping</th><th>Vu</th><th></th></tr></thead>
          <tbody id="d-list"></tbody>
        </table></div>
        <p class="hint">Scan automatique toutes les 5 minutes. Les appareils hors ligne restent listés (en gris).
          « MAC privée » = adresse aléatoire, typique des téléphones : renommez-les avec ✎ pour les reconnaître.</p>
      </div>
      <div>
        <div class="card c-net">
          <h2>Test de débit</h2>
          <div class="speed">
            <div class="rate down"><div class="label">▼ Descendant</div><div class="v" id="s-down">–</div></div>
            <div class="rate up"><div class="label">▲ Montant</div><div class="v" id="s-up">–</div></div>
          </div>
          <div class="form-row"><button class="btn big" id="s-run">Lancer le test</button>
            <span class="muted" style="font-size:14px" id="s-status"></span></div>
          <div id="s-hist" style="margin-top:12px"></div>
          <p class="hint">Serveurs Cloudflare, ~8 s dans chaque sens. Consomme quelques centaines de Mo.</p>
        </div>
        <div class="card c-net" style="margin-top:18px">
          <h2>Coupures Internet</h2>
          <div id="o-list"></div>
        </div>
      </div>
    </section>`;

  let last = null;
  const fmtMbps = v => v == null ? "–" : (v >= 1000 ? (v / 1000).toFixed(2) + " Gb/s" : v.toFixed(v >= 100 ? 0 : 1) + " Mb/s");
  const ms = v => v == null ? "–" : (v < 1 ? "<1" : v.toFixed(v < 10 ? 1 : 0));
  const pingClass = v => v == null ? "t-hot" : v < 30 ? "t-ok" : v < 80 ? "t-warn" : "t-hot";

  function renderTargets(d) {
    for (const t of d.targets) {
      if (t.key === "gateway") $("p-ip-gateway").textContent = t.ip || "inconnue";
      $("p-" + t.key).innerHTML = `
        <div class="ping-big ${pingClass(t.last)}">${t.last == null ? "perdu" : ms(t.last) + "<small> ms</small>"}</div>
        <div class="kv">
          <span>Moyenne (1 min)</span><b>${ms(t.avg)} ms</b>
          <span>Min / max</span><b>${ms(t.min)} / ${ms(t.max)} ms</b>
          <span>Gigue</span><b>${ms(t.jitter)} ms</b>
          <span>Pertes</span><b class="${t.loss > 0 ? (t.loss >= 5 ? "t-hot" : "t-warn") : ""}">${t.loss == null ? "–" : t.loss.toFixed(t.loss % 1 ? 1 : 0) + " %"}</b>
        </div>`;
    }
    const q = d.quality;
    $("p-quality").innerHTML = `<div class="grade g-${q.grade}">${esc(q.label)}</div>
      <div class="kv"><span>Score</span><b>${q.score == null ? "–" : q.score + " / 100"}</b>
      <span>Jeu en ligne</span><b>${q.score == null ? "–" : q.score >= 75 ? "✔ idéal" : q.score >= 50 ? "jouable" : "✖ difficile"}</b>
      <span>Visio / stream</span><b>${q.score == null ? "–" : q.score >= 50 ? "✔ ok" : "✖ instable"}</b></div>`;
  }

  function drawChart(d) {
    const c = $("p-chart"), dpr = window.devicePixelRatio || 1;
    const w = c.clientWidth, h = c.clientHeight;
    if (!w) return;
    if (c.width !== w * dpr || c.height !== h * dpr) { c.width = w * dpr; c.height = h * dpr; }
    const ctx = c.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);
    const all = d.targets.flatMap(t => t.history.filter(v => v != null));
    const peak = Math.max(20, ...all);
    const max = [20, 50, 100, 200, 500, 1000].find(v => v >= peak) || peak;
    $("p-scale").textContent = `échelle 0–${max} ms`;
    ctx.strokeStyle = C.track; ctx.lineWidth = 1; ctx.setLineDash([2, 4]);
    ctx.fillStyle = css("--muted"); ctx.font = "10px " + css("--mono");
    [0, 0.5, 1].forEach(f => {
      const y = Math.round(4 + (h - 8) * f) + 0.5;
      ctx.beginPath(); ctx.moveTo(34, y); ctx.lineTo(w, y); ctx.stroke();
      ctx.fillText(String(Math.round(max * (1 - f))), 0, y + 3);
    });
    ctx.setLineDash([]);
    const N = 300, x0 = 34, step = (w - x0) / (N - 1);
    const yOf = v => 4 + (h - 8) * (1 - Math.min(v, max) / max);
    for (const t of d.targets) {
      const hist = t.history, off = N - hist.length;
      ctx.strokeStyle = COLORS[t.key]; ctx.lineWidth = 1.5; ctx.shadowColor = COLORS[t.key]; ctx.shadowBlur = 6;
      ctx.beginPath();
      let pen = false;
      hist.forEach((v, i) => {
        const x = x0 + (off + i) * step;
        if (v == null) { pen = false; return; }
        pen ? ctx.lineTo(x, yOf(v)) : ctx.moveTo(x, yOf(v));
        pen = true;
      });
      ctx.stroke(); ctx.shadowBlur = 0;
      if (t.key !== "gateway") {
        ctx.fillStyle = css("--hot");
        hist.forEach((v, i) => { if (v == null) ctx.fillRect(x0 + (off + i) * step - 1, h - 6, 3, 6); });
      }
    }
  }

  // ---- Test de débit, exécuté par le navigateur vers les serveurs de speed.cloudflare.com ----
  const SPEED_SECONDS = 8, STREAMS = 4;
  const speed = { running: false, phase: null, progress_mbps: null, error: null, history: [] };
  api("/api/store/speedtests").then(r => { speed.history = Array.isArray(r.value) ? r.value : []; renderSpeed(speed); }).catch(() => {});

  async function measure(worker) {
    let bytes = 0;
    const t0 = performance.now(), stopAt = t0 + SPEED_SECONDS * 1000;
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), SPEED_SECONDS * 1000 + 500);
    const add = n => {
      bytes += n;
      const el = (performance.now() - t0) / 1000;
      if (el > 0.5) { speed.progress_mbps = bytes * 8 / el / 1e6; renderSpeed(speed); }
    };
    await Promise.all(Array.from({ length: STREAMS }, () => worker(add, stopAt, ctrl.signal).catch(e => {
      if (e.name !== "AbortError") throw e;
    })));
    clearTimeout(timer);
    return bytes * 8 / ((performance.now() - t0) / 1000) / 1e6;
  }
  async function down(add, stopAt, signal) {
    while (performance.now() < stopAt) {
      const r = await fetch("https://speed.cloudflare.com/__down?bytes=25000000", { cache: "no-store", signal });
      if (!r.ok) throw new Error("HTTP " + r.status);
      const reader = r.body.getReader();
      while (performance.now() < stopAt) {
        const { done, value } = await reader.read();
        if (done) break;
        add(value.byteLength);
      }
      reader.cancel().catch(() => {});
    }
  }
  const upBlock = new Uint8Array(2 * 1024 * 1024);
  async function up(add, stopAt, signal) {
    while (performance.now() < stopAt) {
      const r = await fetch("https://speed.cloudflare.com/__up", { method: "POST", body: upBlock, signal });
      if (!r.ok) throw new Error("HTTP " + r.status);
      add(upBlock.byteLength);
    }
  }
  async function runSpeedTest() {
    if (speed.running) return;
    Object.assign(speed, { running: true, phase: "download", progress_mbps: null, error: null });
    renderSpeed(speed);
    try {
      const d = await measure(down);
      Object.assign(speed, { phase: "upload", progress_mbps: null });
      const u = await measure(up);
      const cf = last && last.targets.find(t => t.key === "cloudflare");
      speed.history = [{ time: Date.now() / 1000, down_mbps: Math.round(d * 10) / 10, up_mbps: Math.round(u * 10) / 10,
                         ping_ms: cf ? cf.min : null }, ...speed.history].slice(0, 10);
      Object.assign(speed, { running: false, phase: "done" });
      api("/api/store/speedtests", { value: speed.history }, "PUT").catch(() => {});
    } catch (e) {
      Object.assign(speed, { running: false, phase: "error", error: e.message });
    }
    renderSpeed(speed);
  }

  function renderSpeed(st) {
    const h = st.history[0];
    const running = st.running;
    $("s-run").disabled = running;
    $("s-down").textContent = running && st.phase === "download" ? fmtMbps(st.progress_mbps) : fmtMbps(h && h.down_mbps);
    $("s-up").textContent = running && st.phase === "upload" ? fmtMbps(st.progress_mbps) : fmtMbps(h && h.up_mbps);
    $("s-status").textContent = running ? (st.phase === "download" ? "Mesure du débit descendant…" : "Mesure du débit montant…")
      : st.phase === "error" ? "Erreur : " + st.error : h ? "Dernier test " + fmtAgo(h.time) + (h.ping_ms != null ? ` · ping ${ms(h.ping_ms)} ms` : "") : "";
    $("s-hist").innerHTML = st.history.slice(1, 6).map(r =>
      `<div class="outage"><span class="muted">${new Date(r.time * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" })}</span>
       <b>▼ ${fmtMbps(r.down_mbps)} · ▲ ${fmtMbps(r.up_mbps)}</b></div>`).join("");
  }

  function renderOutages(d) {
    $("o-list").innerHTML = d.outages.map(o => {
      const end = o.end ? new Date(o.end * 1000) : null;
      const dur = (o.end || Date.now() / 1000) - o.start;
      return `<div class="outage"><span>${new Date(o.start * 1000).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "medium" })}</span>
        <b class="${end ? "t-warn" : "t-hot"}">${end ? fmtDur(dur) : "EN COURS · " + fmtDur(dur)}</b></div>
        ${o.box_ok ? "" : `<div class="muted" style="font-size:13px">la box ne répondait pas non plus</div>`}`;
    }).join("") || `<div class="empty">Aucune coupure depuis le lancement du panel ✔</div>`;
  }

  function renderDevices(lan) {
    const on = lan.devices.filter(x => x.online).length;
    $("d-sub").textContent = `${on} en ligne · ${lan.devices.length} connus${lan.network ? " · " + lan.network : ""}`;
    $("d-scan").disabled = lan.scanning;
    $("d-status").textContent = lan.scanning ? "Scan en cours…" : lan.error ? "Erreur : " + lan.error
      : lan.last_scan ? "Dernier scan " + fmtAgo(lan.last_scan) : "";
    $("d-list").innerHTML = lan.devices.map(x => {
      const name = x.label || x.hostname || (x.private_mac ? "Appareil (MAC privée)" : "Appareil inconnu");
      const sub = x.label && x.hostname ? `<br><small>${esc(x.hostname)}</small>` : "";
      const tags = (x.is_gateway ? `<span class="tag box">box</span>` : "") + (x.is_self ? `<span class="tag me">ce PC</span>` : "")
        + (x.private_mac ? `<span class="tag">MAC privée</span>` : "");
      return `<tr class="${x.online ? "" : "off"}">
        <td><span class="dot ${x.online ? "on" : ""}"></span></td>
        <td class="name">${esc(name)}${tags}${sub}</td>
        <td>${esc(x.ip || "–")}</td><td>${esc(x.mac.startsWith("ip:") ? "–" : x.mac.toUpperCase())}</td>
        <td>${x.rtt != null ? ms(x.rtt) + " ms" : "–"}</td>
        <td>${x.online ? "en ligne" : fmtAgo(x.last_seen)}</td>
        <td style="white-space:nowrap"><button class="edit" data-mac="${esc(x.mac)}" title="Renommer">✎</button>
          ${x.online ? "" : `<button class="del" data-forget="${esc(x.mac)}" title="Oublier cet appareil">✕</button>`}</td></tr>`;
    }).join("") || `<tr><td colspan="7" class="empty">${lan.scanning ? "Premier scan en cours…" : "Aucun appareil"}</td></tr>`;
  }

  root.addEventListener("click", async ev => {
    const ed = ev.target.closest("button.edit[data-mac]");
    if (ed && last) {
      const x = last.lan.devices.find(d => d.mac === ed.dataset.mac);
      const label = prompt(`Nom pour ${x.hostname || x.ip || x.mac}\n(ex. « Téléphone de Léa », « PS5 » ; vide = nom d'origine)`, x.label || "");
      if (label !== null) { await api("/api/net/device", { mac: x.mac, label }); poll.now(); }
      return;
    }
    const fg = ev.target.closest("button[data-forget]");
    if (fg && confirm("Oublier cet appareil ? Il réapparaîtra s'il se reconnecte.")) {
      await api("/api/net/device", { mac: fg.dataset.forget, forget: true });
      poll.now();
    }
  });
  $("d-scan").addEventListener("click", async () => { await api("/api/net/scan", {}); setTimeout(poll.now, 300); });
  $("s-run").addEventListener("click", runSpeedTest);

  const poll = poller(async () => {
    const d = await api("/api/net");
    last = d;
    renderTargets(d);
    drawChart(d);
    renderOutages(d);
    renderDevices(d.lan);
  }, 1000);
  Tabs.register("reseau", { show: () => poll.start(), hide: () => poll.stop() });
})();
