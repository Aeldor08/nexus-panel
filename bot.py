"""Bot Discord de NEXUS (discord.py), dans le même programme que le serveur (thread dédié).

- Commandes slash en lecture seule : /stats, /disques, /gpu ; plus /deck <bouton> (boutons marqués
  "discord": true et sans confirmation uniquement).
- Les commandes ne répondent qu'à l'utilisateur configuré, et seulement dans le salon configuré.
- Alertes automatiques dans le salon (seuils de config.json), une par type toutes les X minutes,
  et un message quand la situation revient à la normale.
- Jeton absent ou invalide : NEXUS démarre quand même, avec un avertissement clair.
"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import threading
import time

import config

# discord.py (~30 Mo de mémoire avec aiohttp) n'est chargé QUE si le bot démarre vraiment (jeton configuré) :
# sans bot, NEXUS ne paie pas ce coût. Voir _charger_discord().
discord = app_commands = None
AVAILABLE = importlib.util.find_spec("discord") is not None
IMPORT_ERROR = None if AVAILABLE else "module discord introuvable"


def _charger_discord() -> bool:
    global discord, app_commands, AVAILABLE, IMPORT_ERROR
    if discord is not None:
        return True
    try:
        import discord as _d
        from discord import app_commands as _ac

        discord, app_commands = _d, _ac
        return True
    except Exception as exc:  # discord.py absent ou cassé
        AVAILABLE, IMPORT_ERROR = False, str(exc)
        return False


COLOR_OK, COLOR_HOT, COLOR_INFO = 0x3DFFA2, 0xFF2A55, 0x00F0FF
HYSTERESIS = {"temp": 3.0, "percent": 2.0}  # marge avant d'annoncer le retour à la normale


def _gb(b) -> str:
    return f"{b / 1024**3:.1f} Go" if b is not None else "–"


def _bar(pct: float, n: int = 12) -> str:
    full = max(0, min(n, round(pct / 100 * n)))
    return "▰" * full + "▱" * (n - full)


def _p(v) -> str:
    return f"{v:.0f} %" if v is not None else "–"


def _t(v, unit="°C") -> str:
    return f"{v:.0f} {unit}" if v is not None else "indisponible"


# --------------------------------------------------------------------------- #
#  Contenu des réponses (fonctions pures : testables sans Discord)
# --------------------------------------------------------------------------- #
def stats_fields(s: dict) -> list[tuple[str, str]]:
    g = s["gpu"]["devices"][0] if s["gpu"]["devices"] else None
    ram = s["ram"]
    return [
        ("🧠 CPU", f"**{s['cpu']['percent']:.0f} %** · {_t(s['cpu']['temperature'])}" + (f" · {s['cpu']['power_w']:.0f} W" if s["cpu"].get("power_w") else "")),
        ("💾 RAM", f"**{ram['percent']:.0f} %** · {_gb(ram['used'])} / {_gb(ram['total'])}"),
        ("🎮 GPU", f"**{_p(g['load_percent'])}** · {_t(g['temperature'])} · VRAM {_gb(g['vram_used'])} / {_gb(g['vram_total'])}" if g else "indisponible"),
        ("🗄️ Disques", "\n".join(f"`{d['mountpoint']}` {d['percent']:.0f} % · {_gb(d['free'])} libres" for d in s["disks"]) or "–"),
    ]


def disks_fields(s: dict) -> list[tuple[str, str]]:
    return [
        (
            f"`{d['mountpoint']}` ({d['fstype']})",
            f"{_bar(d['percent'])} **{d['percent']:.0f} %**\n{_gb(d['used'])} utilisés · **{_gb(d['free'])} libres** · {_gb(d['total'])}",
        )
        for d in s["disks"]
    ]


def gpu_fields(s: dict) -> list[tuple[str, str]]:
    out = []
    for g in s["gpu"]["devices"]:
        lines = [
            f"Charge **{_p(g['load_percent'])}** {_bar(g['load_percent'] or 0)}",
            f"VRAM **{_gb(g['vram_used'])} / {_gb(g['vram_total'])}**" + (f" ({g['vram_percent']:.0f} %)" if g.get("vram_percent") is not None else ""),
            f"Température **{_t(g['temperature'])}**",
        ]
        if g.get("power_w") is not None:
            lines.append(f"Consommation {g['power_w']:.0f} W" + (f" / {g['power_limit_w']} W" if g.get("power_limit_w") else ""))
        if g.get("clock_core_mhz") is not None:
            lines.append(f"Fréquence {g['clock_core_mhz']} MHz" + (f" · mémoire {g['clock_mem_mhz']} MHz" if g.get("clock_mem_mhz") is not None else ""))
        if g.get("fan_percent") is not None:
            lines.append("Ventilateur " + ("à l'arrêt (0 dB)" if g["fan_percent"] == 0 else f"{g['fan_percent']} %"))
        if s["gpu"].get("source_label"):
            lines.append(f"*{g.get('vendor') or ''} · lu par {s['gpu']['source_label']}*")
        if s["gpu"].get("hint"):
            lines.append(f"*{s['gpu']['hint']}*")
        out.append((g["name"], "\n".join(lines)))
    return out or [("GPU", f"indisponible — {s['gpu'].get('error') or 'aucune carte graphique détectée'}")]


def help_fields(commands: list[tuple[str, str]], deck_labels: list[str], th: dict) -> list[tuple[str, str]]:
    """Contenu de /command : commandes disponibles, boutons du deck utilisables, alertes actives."""
    out = [("📜 Commandes", "\n".join(f"**/{n}** — {d}" for n, d in commands) or "–")]
    out.append(
        (
            "🎛️ Boutons utilisables avec /deck",
            ", ".join(f"`{nom}`" for nom in deck_labels)
            if deck_labels
            else "aucun — coche « Autoriser /deck depuis Discord » sur un bouton, dans le mode édition du Deck",
        )
    )
    parts = [f"CPU ≥ {th.get('cpu_temp')} °C", f"GPU ≥ {th.get('gpu_temp')} °C", f"RAM ≥ {th.get('ram_percent')} %", f"disque ≥ {th.get('disk_percent')} %"]
    out.append(
        ("🚨 Alertes automatiques", " · ".join(parts) + f"\nRappel au plus toutes les {th.get('cooldown_minutes', 30)} min, message au retour à la normale.")
    )
    return out


class AlertTracker:
    """Décide quelles alertes envoyer : anti-spam par type + message de retour à la normale."""

    def __init__(self) -> None:
        self.state: dict[str, dict] = {}  # clé -> {"active": bool, "sent": horodatage}

    def evaluate(self, s: dict, th: dict, now: float | None = None) -> list[dict]:
        now = time.time() if now is None else now
        cooldown = max(1, float(th.get("cooldown_minutes", 30))) * 60
        checks = []  # (clé, libellé, valeur, seuil, unité, genre)
        checks.append(("cpu_temp", "Température CPU", s["cpu"]["temperature"], th["cpu_temp"], "°C", "temp"))
        for g in s["gpu"]["devices"]:
            checks.append((f"gpu_temp_{g['index']}", f"Température GPU ({g['name']})", g["temperature"], th["gpu_temp"], "°C", "temp"))
        checks.append(("ram", "RAM utilisée", s["ram"]["percent"], th["ram_percent"], "%", "percent"))
        for d in s["disks"]:
            checks.append((f"disk_{d['mountpoint']}", f"Disque {d['mountpoint']} plein", d["percent"], th["disk_percent"], "%", "percent"))

        events = []
        for key, label, value, limit, unit, kind in checks:
            if value is None or limit is None:
                continue
            st = self.state.setdefault(key, {"active": False, "sent": 0.0})
            if value >= limit:
                if not st["active"] or now - st["sent"] >= cooldown:
                    events.append({"type": "reminder" if st["active"] else "alert", "key": key, "label": label, "value": value, "limit": limit, "unit": unit})
                    st["active"], st["sent"] = True, now
            elif st["active"] and value <= limit - HYSTERESIS[kind]:
                events.append({"type": "recovered", "key": key, "label": label, "value": value, "limit": limit, "unit": unit})
                st["active"] = False
        return events


def alert_text(e: dict) -> tuple[str, str, int]:
    v = f"{e['value']:.0f} {e['unit']}"
    if e["type"] == "recovered":
        return f"✅ {e['label']} : retour à la normale", f"Maintenant **{v}** (seuil {e['limit']} {e['unit']}).", COLOR_OK
    title = ("⚠️ " if e["type"] == "alert" else "⏰ Toujours en alerte · ") + e["label"]
    return title, f"**{v}** — seuil {e['limit']} {e['unit']}.", COLOR_HOT


# --------------------------------------------------------------------------- #
#  Bot
# --------------------------------------------------------------------------- #
class DiscordBot:
    def __init__(self, sensors, deck=None) -> None:
        self.sensors = sensors
        self.deck = deck
        self.status = {"state": "stopped", "detail": "", "user": None, "guild": None, "channel": None}
        self.tracker = AlertTracker()
        self._loop = None
        self._client = None
        self._channel = None
        self._stop = threading.Event()

    def _set(self, state: str, detail: str = "", **extra) -> None:
        self.status.update(state=state, detail=detail, **extra)

    def start(self) -> None:
        self._stop.clear()
        if os.environ.get("NEXUS_NO_BOT"):
            self._set("disabled", "désactivé (NEXUS_NO_BOT)")
            return
        if not AVAILABLE:
            self._warn("missing_lib", f"discord.py n'est pas installé ({IMPORT_ERROR}) : lance lancer.bat pour l'installer")
            return
        cfg = config.get("discord")
        if not cfg.get("enabled", True):
            self._set("disabled", "désactivé dans config.json")
            return
        token = str(cfg.get("token") or "").strip()
        if not token or "COLLE_ICI" in token:
            self._warn("no_token", "jeton du bot absent (configurer.bat ou « Configurer NEXUS ») : le bot ne démarre pas")
            return
        if not config.as_int(cfg.get("user_id")) or not config.as_int(cfg.get("alert_channel_id")):
            self._warn("bad_config", "discord.user_id ou discord.alert_channel_id manquant ou invalide dans config.json")
            return
        if not _charger_discord():
            self._warn("missing_lib", f"discord.py n'est pas installé ({IMPORT_ERROR}) : lance lancer.bat pour l'installer")
            return
        threading.Thread(target=self._run, args=(token,), daemon=True, name="discord-bot").start()

    def _warn(self, state: str, msg: str) -> None:
        self._set(state, msg)
        print(f"[Discord] AVERTISSEMENT : {msg}")

    # -- boucle asyncio du bot ------------------------------------------------------
    def _run(self, token: str) -> None:
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        delay = 30
        while not self._stop.is_set():
            self._set("connecting", "connexion à Discord…")
            client = self._build_client()
            self._client = client
            try:
                self._loop.run_until_complete(client.start(token))
                return
            except discord.LoginFailure:
                self._warn("bad_token", "jeton refusé par Discord (invalide ou régénéré) : entre le nouveau avec configurer.bat ou « Configurer NEXUS »")
                return
            except discord.PrivilegedIntentsRequired:
                self._warn("error", "intents non autorisés pour ce bot")
                return
            except Exception as exc:  # réseau coupé, Discord indisponible… on réessaie
                self._warn("error", f"connexion impossible ({type(exc).__name__}: {exc}) ; nouvel essai dans {delay} s")
            finally:
                try:
                    self._loop.run_until_complete(client.close())
                except Exception:
                    pass
            if self._stop.wait(delay):
                return
            delay = min(delay * 2, 600)

    def stop(self) -> None:
        """Ferme la connexion Discord (appelé à l'arrêt propre de l'application)."""
        self._stop.set()
        client, loop = self._client, self._loop
        if client is not None and loop is not None:
            try:
                asyncio.run_coroutine_threadsafe(client.close(), loop)
            except Exception:
                pass

    def _build_client(self):
        intents = discord.Intents.none()
        intents.guilds = True  # aucun intent privilégié (pas de lecture des messages)
        client = discord.Client(intents=intents, allowed_mentions=discord.AllowedMentions(users=True, everyone=False, roles=False))
        tree = app_commands.CommandTree(client)
        cfg = config.get("discord")
        owner_id = config.as_int(cfg.get("user_id"))
        channel_id = config.as_int(cfg.get("alert_channel_id"))

        async def guard(inter: discord.Interaction) -> bool:
            if inter.user.id != owner_id or inter.channel_id != channel_id:
                await inter.response.send_message("⛔ Commande réservée au propriétaire de NEXUS, dans son salon.", ephemeral=True)
                return False
            return True

        async def snapshot() -> dict:
            return await asyncio.get_running_loop().run_in_executor(None, self.sensors.core)

        def embed(title: str, fields, color=COLOR_INFO) -> discord.Embed:
            e = discord.Embed(title=title, color=color)
            for name, value in fields:
                e.add_field(name=name, value=value[:1024], inline=False)
            e.set_footer(text="NEXUS")
            e.timestamp = discord.utils.utcnow()
            return e

        @tree.command(name="stats", description="Résumé CPU, RAM, GPU, températures")
        async def cmd_stats(inter: discord.Interaction):
            if await guard(inter):
                await inter.response.send_message(embed=embed("📊 État du PC", stats_fields(await snapshot())))

        @tree.command(name="disques", description="Espace utilisé et libre de chaque disque")
        async def cmd_disques(inter: discord.Interaction):
            if await guard(inter):
                await inter.response.send_message(embed=embed("🗄️ Disques", disks_fields(await snapshot())))

        @tree.command(name="gpu", description="Charge, VRAM et température du GPU")
        async def cmd_gpu(inter: discord.Interaction):
            if await guard(inter):
                await inter.response.send_message(embed=embed("🎮 Carte graphique", gpu_fields(await snapshot())))

        @tree.command(name="deck", description="Déclencher un bouton du stream deck (boutons autorisés pour Discord)")
        @app_commands.describe(bouton="Nom du bouton")
        async def cmd_deck(inter: discord.Interaction, bouton: str):
            if not await guard(inter):
                return
            if not self.deck:
                await inter.response.send_message("Stream deck indisponible.", ephemeral=True)
                return
            btn = self.deck.find_for_discord(bouton)
            if not btn:
                await inter.response.send_message(f"❓ Aucun bouton autorisé pour Discord ne s'appelle « {bouton} ».", ephemeral=True)
                return
            ok, msg = await asyncio.get_running_loop().run_in_executor(None, lambda: self.deck.run(btn["id"], source="discord"))
            await inter.response.send_message(f"{'▶️' if ok else '❌'} **{btn['label']}** — {msg}")

        @cmd_deck.autocomplete("bouton")
        async def deck_autocomplete(inter: discord.Interaction, current: str):
            if inter.user.id != owner_id or not self.deck:
                return []
            cur = current.lower()
            return [app_commands.Choice(name=b["label"][:100], value=b["label"][:100]) for b in self.deck.discord_buttons() if cur in b["label"].lower()][:25]

        @tree.command(name="command", description="Liste de toutes les commandes disponibles")
        async def cmd_command(inter: discord.Interaction):
            if not await guard(inter):
                return
            cmds = sorted((c.name, c.description) for c in tree.get_commands())
            labels = [b["label"] for b in self.deck.discord_buttons()] if self.deck else []
            await inter.response.send_message(embed=embed("🤖 Commandes NEXUS", help_fields(cmds, labels, config.get("alerts"))), ephemeral=True)

        @client.event
        async def on_ready():
            try:
                channel = client.get_channel(channel_id) or await client.fetch_channel(channel_id)
            except discord.Forbidden:
                self._warn("error", "le bot n'a pas accès au salon d'alertes (permissions du salon)")
                return
            except discord.NotFound:
                self._warn("error", "salon d'alertes introuvable : le bot est-il invité sur ce serveur ?")
                return
            guild = channel.guild
            # Commandes enregistrées sur ce serveur uniquement : disponibles immédiatement
            tree.clear_commands(guild=guild)
            tree.copy_global_to(guild=guild)
            try:
                synced = await tree.sync(guild=guild)
            except discord.Forbidden:
                self._warn("error", "impossible d'enregistrer les commandes : réinvite le bot avec la permission « applications.commands »")
                return
            perms = channel.permissions_for(guild.me)
            missing = [
                n
                for n, ok in (("Voir le salon", perms.view_channel), ("Envoyer des messages", perms.send_messages), ("Intégrer des liens", perms.embed_links))
                if not ok
            ]
            self._set(
                "online" if not missing else "error",
                "connecté" if not missing else "permissions manquantes dans le salon : " + ", ".join(missing),
                user=str(client.user),
                guild=guild.name,
                channel=f"#{channel.name}",
                commands=[c.name for c in synced],
            )
            print(
                f"[Discord] Connecté : {client.user} · serveur « {guild.name} » · salon #{channel.name} · commandes : {', '.join('/' + c.name for c in synced)}"
            )
            self._channel = channel
            if not getattr(client, "_alerts_started", False):
                client._alerts_started = True
                client.loop.create_task(self._alert_loop(client, channel))

        return client

    def notify(self, title: str, text: str) -> bool | None:
        """Envoie un message dans le salon configuré depuis un autre thread (rappels de l'agenda).
        True : envoyé ; False : bot momentanément indisponible (à réessayer) ; None : pas de bot configuré."""
        if self.status["state"] in ("stopped", "disabled", "missing_lib", "no_token", "bad_config", "bad_token"):
            return None
        if self.status["state"] != "online" or not self._channel or not self._loop or not AVAILABLE:
            return False
        owner = config.as_int(config.get("discord").get("user_id"))
        em = discord.Embed(title=title, description=text, color=COLOR_INFO)
        em.set_footer(text="NEXUS · agenda")
        em.timestamp = discord.utils.utcnow()
        fut = asyncio.run_coroutine_threadsafe(self._channel.send(content=f"<@{owner}>" if owner else None, embed=em), self._loop)
        try:
            fut.result(timeout=15)
            return True
        except Exception as exc:
            print(f"[Discord] rappel non envoyé : {exc}")
            return False

    async def _alert_loop(self, client, channel) -> None:
        owner = config.as_int(config.get("discord").get("user_id"))
        while not client.is_closed():
            th = config.get("alerts")
            try:
                s = await asyncio.get_running_loop().run_in_executor(None, self.sensors.core)
                for e in self.tracker.evaluate(s, th):
                    title, desc, color = alert_text(e)
                    em = discord.Embed(title=title, description=desc, color=color)
                    em.set_footer(text="NEXUS · alertes")
                    em.timestamp = discord.utils.utcnow()
                    await channel.send(content=f"<@{owner}>" if e["type"] == "alert" else None, embed=em)
            except discord.HTTPException as exc:
                self._set("error", f"envoi d'alerte impossible : {exc}")
            except Exception as exc:
                print(f"[Discord] erreur pendant la vérification des alertes : {exc}")
            await asyncio.sleep(max(10, float(th.get("check_seconds", 30))))
