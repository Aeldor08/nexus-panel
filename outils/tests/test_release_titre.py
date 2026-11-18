"""Option --titre de outils/release.py, sur un CHANGELOG temporaire (le vrai n'est jamais touché) :
en-tête « ## [X.Y.Z] - date - titre », titre de la release GitHub, lecture du titre par version.py (le panel)."""
import shutil
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
sys.path.insert(0, str(BASE / "outils"))
import release  # noqa: E402
import version  # noqa: E402

passed = failed = 0


def ok(c, m):
    global passed, failed
    if c:
        passed += 1
        print("OK   ", m)
    else:
        failed += 1
        print("ÉCHEC", m)


vrai = (BASE / "CHANGELOG.md").read_bytes()
tmp = Path(tempfile.mkdtemp(prefix="nexus-release-"))
try:
    (tmp / "CHANGELOG.md").write_text("# Changelog\n\n## [Non publié]\n\nPhilibert arrive ! Un petit iguane.\n\n### Ajouté\n- Philibert\n\n"
                                      "## [1.0.10] - 2026-11-16\n\n### Corrigé\n- Post-it\n", encoding="utf-8", newline="\n")
    release.BASE = tmp
    release.dater_changelog("1.1.0", "2026-11-16", release.verifier_titre("  Philibert   arrive !  "))
    t = (tmp / "CHANGELOG.md").read_text(encoding="utf-8")
    ok("## [Non publié]\n\n## [1.1.0] - 2026-11-16 - Philibert arrive !\n" in t, "en-tête « ## [1.1.0] - date - Philibert arrive ! »")
    ok("Philibert arrive ! Un petit iguane." in release.section_changelog(t, "1.1.0"), "le paragraphe d'introduction suit dans les notes")
    ok(release.section_changelog(t, "1.0.10").startswith("### Corrigé"), "les versions précédentes sont intactes")
    ok(release.titre_release("1.1.0", "Philibert arrive !") == "NEXUS 1.1.0 — Philibert arrive !", "titre de la release GitHub")
    ok(release.titre_release("1.1.0") == "NEXUS 1.1.0", "sans --titre : « NEXUS X.Y.Z » comme avant")
    try:
        release.verifier_titre("x" * 90)
        ok(False, "titre trop long refusé")
    except release.Arret:
        ok(True, "titre trop long refusé")
    version.BASE = tmp
    e = next(x for x in version.changelog() if x["version"] == "1.1.0")
    ok(e["title"] == "Philibert arrive !" and e["date"] == "2026-11-16" and e["items"] == ["Ajouté : Philibert"], "le panel lit le titre et les points")
finally:
    shutil.rmtree(tmp, ignore_errors=True)
ok((BASE / "CHANGELOG.md").read_bytes() == vrai, "le vrai CHANGELOG.md n'a pas changé")

# notes de la release GitHub : encadré « Télécharger » en tête (lien direct vers l'archive), puis le CHANGELOG
n = release.notes_release("### Ajouté\n- Philibert", "1.6.0", "proprio/nexus-panel", 2.345)
ok(n.startswith("## ⬇️ Télécharger NEXUS 1.6.0"), "notes : encadré Télécharger en tête")
ok("(https://github.com/proprio/nexus-panel/releases/download/v1.6.0/NEXUS-1.6.0.zip)" in n and "2.3 Mo" in n,
   "notes : lien direct vers l'archive de la version, avec sa taille")
ok("installer.bat" in n and n.index("installer.bat") < n.index("- Philibert") < n.index("certutil -hashfile NEXUS-1.6.0.zip"),
   "notes : installation, puis CHANGELOG, puis vérification SHA256")

print(f"\n{passed} tests réussis, {failed} échec(s)")
sys.exit(1 if failed else 0)
