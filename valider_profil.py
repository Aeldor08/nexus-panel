r"""Vérifie un dossier (ou un .zip) de profil visuel NEXUS et explique les erreurs.

Utilisation :
    python valider_profil.py profils\mon-profil
    python valider_profil.py profil-mon-profil.zip
    python valider_profil.py --tous          (tous les profils du dossier profils\)

Code de sortie : 0 si tout est valide, 1 sinon. Le format est décrit dans profils\FORMAT.md.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import profiles


def report(folder: Path, label: str | None = None) -> bool:
    res = profiles.validate_dir(folder, strict=True)
    name = label or str(folder)
    print(f"\n=== {name}")
    if not profiles.ID_RE.match(folder.name) and label is None:
        res["errors"].append(f"nom de dossier « {folder.name} » invalide : minuscules, chiffres et tirets "
                             "uniquement, 40 caractères max (ex. ocean-calme)")
        res["ok"] = False
    if folder.name == profiles.DEFAULT_ID:
        res["errors"].append("« defaut » est réservé au profil intégré")
        res["ok"] = False
    m = res["meta"]
    if m:
        print(f"    {m['nom'] or '?'} v{m['version'] or '?'} par {m['auteur']} — modes : {', '.join(m['modes']) or '?'}")
    print(f"    {res['size'] / 1024:.0f} Ko, {len(res['assets'])} fichier(s) dans assets/")
    for e in res["errors"]:
        print(f"  [ERREUR] {e}")
    for w in res["warnings"]:
        print(f"  [conseil] {w}")
    print("  => PROFIL VALIDE" if res["ok"] else f"  => PROFIL INVALIDE ({len(res['errors'])} erreur(s)) — voir profils\\FORMAT.md")
    return res["ok"]


def main(args: list[str]) -> int:
    if not args or args[0] in ("-h", "--help", "/?"):
        print(__doc__)
        return 1
    targets = []
    if args[0] == "--tous":
        targets = [p for p in sorted(profiles.PROFILES_DIR.iterdir()) if p.is_dir() and not p.name.startswith((".", "_"))]
    else:
        targets = [Path(a) for a in args]
    ok = True
    for t in targets:
        if t.suffix.lower() == ".zip" and t.is_file():
            # même lecture que l'import du panel, dans un dossier temporaire
            with tempfile.TemporaryDirectory() as tmp:
                lib = profiles.ProfileLibrary(Path(tmp))
                try:
                    res = lib.import_zip(t.read_bytes())
                except profiles.ProfileError as exc:
                    print(f"\n=== {t}\n  [ERREUR] {exc}")
                    for d in exc.details:
                        print(f"  [ERREUR] {d}")
                    print("  => PROFIL INVALIDE — voir profils\\FORMAT.md")
                    ok = False
                    continue
                ok &= report(Path(tmp) / res["id"], label=f"{t} (identifiant à l'import : {res['id']})")
        elif t.is_dir():
            ok &= report(t)
        else:
            print(f"\n=== {t}\n  [ERREUR] introuvable (attendu : un dossier de profil ou un .zip)")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
