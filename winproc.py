"""Liste rapide des processus Windows en UN seul appel système (NtQuerySystemInformation, comme le Gestionnaire
des tâches) : pid, pid parent, nom, temps processeur cumulé (s) et mémoire (working set, octets).

Environ 100 fois plus rapide que d'interroger chaque processus avec psutil (qui ouvre chaque processus, et
échoue lentement sur ceux qui sont protégés). Sans Windows, ou si l'appel échoue : None (l'appelant revient à psutil).
"""

from __future__ import annotations

import ctypes
import struct
import sys

_SYSTEM_PROCESS_INFORMATION = 5
_STATUS_INFO_LENGTH_MISMATCH = 0xC0000004
_buf_taille = 1 << 20  # agrandi tout seul si besoin (et gardé pour les appels suivants)

if sys.platform == "win32" and struct.calcsize("P") == 8:
    _ntdll = ctypes.WinDLL("ntdll")
    _ntdll.NtQuerySystemInformation.restype = ctypes.c_long
    _ntdll.NtQuerySystemInformation.argtypes = [ctypes.c_ulong, ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(ctypes.c_ulong)]
else:  # (le panel ne tourne que sous Windows 64 bits)
    _ntdll = None

# Décalages dans SYSTEM_PROCESS_INFORMATION (Windows 64 bits)
_O_NEXT, _O_USER, _O_KERNEL, _O_NAME_LEN, _O_NAME_PTR, _O_PID, _O_PPID, _O_WS = 0, 40, 48, 56, 64, 80, 88, 144


def processus() -> list[tuple[int, int, str, float, int]] | None:
    """[(pid, pid_parent, nom, temps_cpu_s, memoire_octets), …] ou None si indisponible."""
    global _buf_taille
    if _ntdll is None:
        return None
    try:
        for _ in range(6):
            buf = ctypes.create_string_buffer(_buf_taille)
            besoin = ctypes.c_ulong(0)
            st = _ntdll.NtQuerySystemInformation(_SYSTEM_PROCESS_INFORMATION, buf, _buf_taille, ctypes.byref(besoin))
            if st & 0xFFFFFFFF == _STATUS_INFO_LENGTH_MISMATCH:
                _buf_taille = max(_buf_taille * 2, besoin.value + (1 << 16))
                continue
            if st != 0:
                return None
            break
        else:
            return None
        brut = buf.raw
        base = ctypes.addressof(buf)
        out = []
        off = 0
        lire_q = struct.Struct("<Q").unpack_from
        while True:
            nxt = struct.unpack_from("<I", brut, off + _O_NEXT)[0]
            pid = lire_q(brut, off + _O_PID)[0]
            if pid:  # (pid 0 : processus inactif du système)
                longueur = struct.unpack_from("<H", brut, off + _O_NAME_LEN)[0]
                ptr = lire_q(brut, off + _O_NAME_PTR)[0]
                if ptr and longueur:
                    debut = ptr - base  # le nom est dans le même tampon
                    nom = brut[debut : debut + longueur].decode("utf-16-le", "replace")
                else:
                    nom = "System" if pid == 4 else f"pid {pid}"
                cpu = (lire_q(brut, off + _O_USER)[0] + lire_q(brut, off + _O_KERNEL)[0]) / 1e7
                out.append((pid, lire_q(brut, off + _O_PPID)[0], nom, cpu, lire_q(brut, off + _O_WS)[0]))
            if not nxt:
                break
            off += nxt
        return out
    except Exception:
        return None
