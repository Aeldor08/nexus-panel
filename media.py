"""Lecture en cours (Spotify, Deezer, YouTube dans n'importe quel navigateur, etc.) via les contrôles
multimédias de Windows (System Media Transport Controls).

Réactivité :
- les ÉVÉNEMENTS de Windows (piste, lecture / pause, position, nouvelle source) réveillent aussitôt la lecture
  de l'état ; une relecture chaque seconde reste en secours ;
- après une commande (lecture, suivant…), l'état est relu tout de suite puis 2 fois de plus juste après
  (les applications mettent quelques centaines de millisecondes à le publier) ;
- le panel peut ATTENDRE un changement (wait) : la page reçoit le nouvel état dès qu'il existe, sans attendre
  son prochain tour. « sig » résume ce qui se voit (source, piste, état, pochette…), pas la position qui avance.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import hashlib
import json
import re
import threading
import time

try:
    from winrt.windows.media.control import (
        GlobalSystemMediaTransportControlsSessionManager as SessionManager,
    )
    from winrt.windows.storage.streams import DataReader

    AVAILABLE = True
    IMPORT_ERROR = None
except Exception as exc:  # paquets winrt absents
    AVAILABLE = False
    IMPORT_ERROR = str(exc)

# Statuts de lecture Windows
STATUS = {0: "closed", 1: "opened", 2: "changing", 3: "stopped", 4: "playing", 5: "paused"}

# Identifiant d'application Windows (AppUserModelID) -> nom affiché. Le premier motif trouvé gagne : les plus
# précis d'abord (« operagx » avant « opera », « edge » des applis du Store avant le reste).
BROWSER_NAMES = [
    ("operagx", "Opera GX"),
    ("opera gx", "Opera GX"),
    ("opera", "Opera"),
    ("msedge", "Edge"),
    ("microsoftedge", "Edge"),
    ("chrome", "Chrome"),
    ("chromium", "Chromium"),
    ("brave", "Brave"),
    ("vivaldi", "Vivaldi"),
    ("yandex", "Yandex"),
    ("thebrowsercompany.arc", "Arc"),
    ("arc.exe", "Arc"),
    ("duckduckgo", "DuckDuckGo"),
    ("thorium", "Thorium"),
    ("waterfox", "Waterfox"),
    ("librewolf", "LibreWolf"),
    ("floorp", "Floorp"),
    ("zen", "Zen"),
    ("palemoon", "Pale Moon"),
    ("seamonkey", "SeaMonkey"),
    ("torbrowser", "Tor Browser"),
    ("firefox", "Firefox"),
    ("maxthon", "Maxthon"),
    ("iridium", "Iridium"),
    ("sidekick", "Sidekick"),
    ("whale", "Naver Whale"),
]
PLAYER_NAMES = [
    ("spotify", "Spotify"),
    ("deezer", "Deezer"),
    ("applemusic", "Apple Music"),
    ("apple music", "Apple Music"),
    ("itunes", "iTunes"),
    ("tidal", "Tidal"),
    ("amazonmusic", "Amazon Music"),
    ("amazon music", "Amazon Music"),
    ("qobuz", "Qobuz"),
    ("youtubemusic", "YouTube Music"),
    ("youtube music", "YouTube Music"),
    ("soundcloud", "SoundCloud"),
    ("pandora", "Pandora"),
    ("napster", "Napster"),
    ("audible", "Audible"),
    ("vlc", "VLC"),
    ("foobar", "foobar2000"),
    ("musicbee", "MusicBee"),
    ("aimp", "AIMP"),
    ("winamp", "Winamp"),
    ("mediamonkey", "MediaMonkey"),
    ("potplayer", "PotPlayer"),
    ("mpc-hc", "MPC-HC"),
    ("mpc-be", "MPC-BE"),
    ("plex", "Plex"),
    ("jellyfin", "Jellyfin"),
    ("kodi", "Kodi"),
    ("strawberry", "Strawberry"),
    ("dopamine", "Dopamine"),
    ("zunemusic", "Lecteur multimédia"),
    ("zunevideo", "Films et TV"),
    ("microsoft.media.player", "Lecteur multimédia"),
    ("wmplayer", "Windows Media Player"),
    ("discord", "Discord"),
    ("twitch", "Twitch"),
    ("netflix", "Netflix"),
    ("disney", "Disney+"),
    ("primevideo", "Prime Video"),
    ("steam", "Steam"),
]
BROWSERS = {name for _, name in BROWSER_NAMES}
# Firefox (et ses dérivés) s'annonce par un code hexadécimal de 16 caractères (ex. 308046B0AF4A39CB)
FIREFOX_AUMID = re.compile(r"^[0-9A-F]{16}$", re.I)


def app_name(source: str) -> str:
    low = (source or "").lower()
    for key, name in PLAYER_NAMES + BROWSER_NAMES:
        if key in low:
            return name
    base = (source or "").split("!")[0]
    if FIREFOX_AUMID.match(base):
        return "Firefox"
    base = base.rsplit("\\", 1)[-1].removesuffix(".exe").removesuffix(".EXE")
    if "_" in base and "." in base.split("_")[0]:  # application du Store : « Editeur.Nom_hash »
        base = base.split("_")[0].split(".")[-1]
    return base or "Lecteur"


def web_service(name: str, props_artist: str, props_album: str, title: str) -> str | None:
    """Site de musique / vidéo deviné dans un navigateur (Windows ne donne pas l'adresse de la page)."""
    blob = f"{props_artist} | {props_album} | {title}".lower()
    for key, label in (
        ("deezer", "Deezer"),
        ("spotify", "Spotify"),
        ("youtube music", "YouTube Music"),
        ("youtube", "YouTube"),
        ("soundcloud", "SoundCloud"),
        ("twitch", "Twitch"),
        ("netflix", "Netflix"),
        ("tidal", "Tidal"),
        ("apple music", "Apple Music"),
        ("bandcamp", "Bandcamp"),
        ("qobuz", "Qobuz"),
        ("amazon music", "Amazon Music"),
    ):
        if key in blob:
            return label
    return None


def _secs(value) -> float:
    if value is None:
        return 0.0
    if isinstance(value, dt.timedelta):
        return value.total_seconds()
    return float(getattr(value, "duration", value)) / 1e7  # TimeSpan en ticks de 100 ns


def signature(sessions: list[dict]) -> str:
    """Ce qui se VOIT (sans la position qui avance) : change quand une piste, un état ou une source change."""
    keys = ("source", "status", "title", "artist", "album", "cover", "duration", "can_play_pause", "can_next", "can_prev", "can_seek")
    return hashlib.md5(json.dumps([[s.get(k) for k in keys] for s in sessions]).encode()).hexdigest()[:12]


class MediaMonitor:
    POLL_S = 1.0  # relecture de secours
    COALESCE_S = 0.04  # regroupe une rafale d'événements

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cond = threading.Condition(self._lock)
        self._state = {"available": AVAILABLE, "error": IMPORT_ERROR, "current": None, "sessions": [], "sig": "", "updated": 0}
        self._covers: dict[str, tuple[str, bytes]] = {}  # source -> (hash, octets)
        self._sessions = {}
        self._subs: dict[str, tuple] = {}  # source -> (objet session, jetons d'événements)
        self._mgr = None
        self._mgr_tokens = []
        self._wake: asyncio.Event | None = None
        self._loop = asyncio.new_event_loop()
        self.events_ok = False  # au moins un événement Windows reçu (diagnostic)
        if AVAILABLE:
            threading.Thread(target=self._run, daemon=True).start()

    # -- réveil (appelé depuis les fils de Windows ou après une commande) -----------
    def _poke(self, *_args) -> None:
        self.events_ok = True
        try:
            self._loop.call_soon_threadsafe(self._set_wake)
        except RuntimeError:
            pass

    def _set_wake(self) -> None:
        if self._wake is not None:
            self._wake.set()

    # -- boucle asyncio dédiée ------------------------------------------------
    def _run(self) -> None:
        asyncio.set_event_loop(self._loop)
        self._wake = asyncio.Event()
        self._loop.run_until_complete(self._poll_forever())

    async def _poll_forever(self) -> None:
        while True:
            try:
                if self._mgr is None:
                    self._mgr = await SessionManager.request_async()
                    self._subscribe_manager()
                await self._poll()
            except Exception as exc:
                with self._lock:
                    self._state = {**self._state, "error": f"{type(exc).__name__}: {exc}"}
                self._mgr = None
                self._subs.clear()
                await asyncio.sleep(3)
            try:
                await asyncio.wait_for(self._wake.wait(), timeout=self.POLL_S)
                await asyncio.sleep(self.COALESCE_S)
            except asyncio.TimeoutError:
                pass
            self._wake.clear()

    def _subscribe_manager(self) -> None:
        self._mgr_tokens = []
        for ev in ("sessions_changed", "current_session_changed"):
            try:
                self._mgr_tokens.append(getattr(self._mgr, "add_" + ev)(self._poke))
            except Exception:
                pass

    def _subscribe(self, source: str, s) -> None:
        if source in self._subs:
            return
        toks = []
        for ev in ("playback_info_changed", "media_properties_changed", "timeline_properties_changed"):
            try:
                toks.append((ev, getattr(s, "add_" + ev)(self._poke)))
            except Exception:
                pass
        self._subs[source] = (s, toks)

    def _unsubscribe_gone(self, present: set[str]) -> None:
        for source in [x for x in self._subs if x not in present]:
            s, toks = self._subs.pop(source)
            for ev, tok in toks:
                try:
                    getattr(s, "remove_" + ev)(tok)
                except Exception:
                    pass

    async def _poll(self) -> None:
        cur = self._mgr.get_current_session()
        cur_id = cur.source_app_user_model_id if cur else None
        sessions, objs = [], {}
        for s in self._mgr.get_sessions():
            source = s.source_app_user_model_id
            try:
                props = await s.try_get_media_properties_async()
            except Exception:
                continue
            self._subscribe(source, s)
            pb = s.get_playback_info()
            tl = s.get_timeline_properties()
            status = STATUS.get(int(pb.playback_status), "unknown")
            pos, end = _secs(tl.position), _secs(tl.end_time) - _secs(tl.start_time)
            # Windows ne met pas la position à jour en continu : on extrapole.
            try:
                updated = tl.last_updated_time
                if status == "playing" and updated is not None:
                    age = (dt.datetime.now(dt.timezone.utc) - updated).total_seconds()
                    if 0 < age < 6 * 3600:
                        pos += age
            except Exception:
                pass
            if end > 0:
                pos = min(pos, end)
            cover_hash = await self._cover(source, props)
            name = app_name(source)
            ctrl = pb.controls
            is_browser = name in BROWSERS
            title, artist, album = props.title or "", props.artist or "", props.album_title or ""
            sessions.append(
                {
                    "source": source,
                    "app": name,
                    "is_browser": is_browser,
                    "site": web_service(name, artist, album, title) if is_browser else None,
                    "title": title,
                    "artist": artist,
                    "album": album,
                    "status": status,
                    "position": round(pos, 1),
                    "duration": round(end, 1) if end > 0 else None,
                    "cover": cover_hash,
                    "can_play_pause": bool(ctrl.is_play_pause_toggle_enabled or ctrl.is_play_enabled or ctrl.is_pause_enabled),
                    "can_next": bool(ctrl.is_next_enabled),
                    "can_prev": bool(ctrl.is_previous_enabled),
                    "can_seek": bool(ctrl.is_playback_position_enabled) and end > 0,
                    "current": source == cur_id,
                }
            )
            objs[source] = s
        self._unsubscribe_gone(set(objs))
        # Priorité : celle en lecture, puis celle que Windows considère comme active.
        sessions.sort(key=lambda x: (x["status"] == "playing", x["current"]), reverse=True)
        sig = signature(sessions)
        with self._cond:
            changed = sig != self._state.get("sig")
            self._sessions = objs
            self._state = {
                "available": True,
                "error": None,
                "current": sessions[0]["source"] if sessions else None,
                "sessions": sessions,
                "sig": sig,
                "updated": time.time(),
                "events": self.events_ok,
            }
            if changed:
                self._cond.notify_all()

    async def _cover(self, source: str, props) -> str | None:
        key = f"{props.title}|{props.artist}|{props.album_title}"
        old = self._covers.get(source)
        if old and old[0].startswith(hashlib.md5(key.encode()).hexdigest()[:8]):
            return old[0]
        if props.thumbnail is None:
            self._covers.pop(source, None)
            return None
        try:
            stream = await props.thumbnail.open_read_async()
            size = int(stream.size)
            if not 0 < size < 5_000_000:
                return None
            reader = DataReader(stream)
            await reader.load_async(size)
            buf = bytearray(size)
            reader.read_bytes(buf)
            data = bytes(buf)
        except Exception:
            return None
        digest = hashlib.md5(key.encode()).hexdigest()[:8] + hashlib.md5(data).hexdigest()[:8]
        self._covers[source] = (digest, data)
        return digest

    # -- API ------------------------------------------------------------------
    def state(self) -> dict:
        with self._lock:
            return self._state

    def wait(self, sig: str, timeout: float) -> dict:
        """Attend (au plus timeout s) un état différent de « sig » ; renvoie l'état courant dans tous les cas."""
        with self._cond:
            self._cond.wait_for(lambda: self._state.get("sig") != sig, timeout=max(0.0, min(timeout, 25.0)))
            return self._state

    def cover(self, source: str) -> bytes | None:
        item = self._covers.get(source)
        return item[1] if item else None

    def control(self, source: str, action: str, position: float | None = None) -> bool:
        with self._lock:
            s = self._sessions.get(source)
        if s is None:
            return False

        async def run():
            if action == "toggle":
                return await s.try_toggle_play_pause_async()
            if action == "next":
                return await s.try_skip_next_async()
            if action == "prev":
                return await s.try_skip_previous_async()
            if action == "seek" and position is not None:
                return await s.try_change_playback_position_async(int(position * 1e7))
            return False

        fut = asyncio.run_coroutine_threadsafe(run(), self._loop)
        try:
            ok = bool(fut.result(timeout=2.5))
        except Exception:
            ok = False
        # relire l'état tout de suite, puis encore un peu plus tard (l'appli publie son nouvel état en différé)
        self._poke()
        for delay in (0.25, 0.7):
            try:
                self._loop.call_soon_threadsafe(self._loop.call_later, delay, self._set_wake)
            except RuntimeError:
                pass
        return ok
