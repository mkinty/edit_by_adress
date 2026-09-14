"""Lecture rapide d'un classeur xlsx, sans openpyxl.

Un fichier ``.xlsx`` est une archive ZIP de documents XML. Pour repérer les
lignes à modifier, il suffit de lire **une seule colonne** : construire pour
cela l'intégralité des objets du classeur, comme le fait ``load_workbook``,
revient à payer très cher une information minuscule.

Ce module balaie donc le XML de la feuille en flux, par blocs, et n'extrait que
les cellules de la colonne demandée. Sur un classeur de 60 000 lignes, le
repérage passe de plus de trois secondes à un peu plus d'un dixième de seconde,
ce qui le rend négligeable devant le chargement d'openpyxl — et permet surtout
de **ne pas charger du tout** les fichiers où aucun ID erreur ne figure.

**Il ne fait que lire.** L'écriture reste confiée à openpyxl : aucun risque de
corrompre un classeur ici. Devant une structure inattendue (cellules sans
référence, archive illisible), une :class:`LectureImpossible` est levée et
l'appelant retombe sur openpyxl.
"""

from __future__ import annotations

from collections.abc import Iterator
from xml.etree.ElementTree import fromstring
from xml.sax.saxutils import unescape
import re
import zipfile

NS_FEUILLE = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
NS_REL_DOC = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
NS_REL_PKG = "{http://schemas.openxmlformats.org/package/2006/relationships}"

# Taille des blocs lus dans le XML de la feuille. Le découpage se fait toujours
# sur une fin de ligne (</row>), de sorte qu'aucune cellule n'est coupée en deux.
TAILLE_BLOC = 4 * 1024 * 1024

_FIN_LIGNE = b"</row>"

# Cellule sans attribut « r » : la position ne serait plus déductible.
_CELLULE_SANS_REFERENCE = re.compile(rb"<c(?![^>]*\sr=)[ />]")

_TEXTES = re.compile(rb"<t[^>]*>(.*?)</t>", re.S)
_NOMBRE = re.compile(rb"<v[^>]*>(.*?)</v>", re.S)
_ENTITES = {"&quot;": '"', "&apos;": "'"}

# Les caractères accentués sont souvent échappés en références numériques
# (« contrôle » → « contr&#244;le ») : sans cette substitution, aucun en-tête
# accenté ne serait reconnu.
_REFERENCE_NUMERIQUE = re.compile(r"&#([xX]?)([0-9a-fA-F]+);")


class LectureImpossible(Exception):
    """Le classeur ne se prête pas à la lecture rapide (structure inattendue)."""


# ── API ───────────────────────────────────────────────────────────
def lire_entetes(chemin: str, ligne_entete: int = 1) -> dict[int, str]:
    """Libellés de la ligne d'en-tête, ``{index de colonne: libellé}``.

    La lecture s'arrête dès la ligne d'en-tête dépassée : son coût ne dépend
    pas de la taille du fichier.
    """
    entetes: dict[int, str] = {}
    for ligne, index, valeur in _cellules(chemin, colonne=None, ligne_max=ligne_entete):
        if ligne == ligne_entete and valeur not in (None, ""):
            entetes[index] = str(valeur).strip()
    return entetes


def lire_colonne(
    chemin: str, index_colonne: int, ligne_debut: int = 2
) -> Iterator[tuple[int, str]]:
    """Valeurs non vides d'une colonne : ``(numéro de ligne, valeur)``.

    Les lignes sans valeur dans cette colonne ne sont pas produites : c'est sans
    conséquence ici, une cellule vide ne pouvant porter aucun ID erreur.
    """
    for ligne, _index, valeur in _cellules(chemin, colonne=index_colonne):
        if ligne >= ligne_debut and valeur not in (None, ""):
            yield ligne, valeur


# ── Balayage de la feuille ────────────────────────────────────────
def _cellules(
    chemin: str, colonne: int | None, ligne_max: int | None = None
) -> Iterator[tuple[int, int, str | None]]:
    """Produit ``(ligne, colonne, valeur)`` pour la feuille active du classeur."""
    try:
        with zipfile.ZipFile(chemin) as archive:
            feuille = _chemin_feuille_active(archive)
            motif = _motif_cellule(colonne)
            textes: list[str] | None = None

            with archive.open(feuille) as flux:
                for premier, bloc in _blocs(flux):
                    if premier and _CELLULE_SANS_REFERENCE.search(bloc):
                        raise LectureImpossible("cellules sans référence de position")

                    for cellule in motif.finditer(bloc):
                        ligne = int(cellule.group(2))
                        if ligne_max is not None and ligne > ligne_max:
                            return
                        attributs, corps = cellule.group(3), cellule.group(4)
                        if b'"s"' in attributs and textes is None:
                            textes = _textes_partages(archive)
                        yield (
                            ligne,
                            _index_colonne(cellule.group(1)),
                            _valeur(attributs, corps, textes or []),
                        )
    except LectureImpossible:
        raise
    except (OSError, zipfile.BadZipFile, ValueError, KeyError) as exc:
        raise LectureImpossible(str(exc)) from exc


def _blocs(flux) -> Iterator[tuple[bool, bytes]]:
    """Découpe le flux XML en blocs se terminant sur une fin de ligne.

    Couper sur ``</row>`` garantit qu'une cellule n'est jamais scindée entre
    deux blocs, tout en gardant la mémoire bornée quelle que soit la taille du
    classeur.
    """
    reste = b""
    premier = True
    while True:
        morceau = flux.read(TAILLE_BLOC)
        if not morceau:
            break
        reste += morceau
        coupe = reste.rfind(_FIN_LIGNE)
        if coupe == -1:
            continue  # ligne plus longue qu'un bloc : on agrandit
        fin = coupe + len(_FIN_LIGNE)
        yield premier, reste[:fin]
        premier = False
        reste = reste[fin:]

    if reste:
        yield premier, reste


def _motif_cellule(colonne: int | None) -> re.Pattern[bytes]:
    """Motif des cellules à retenir — une colonne précise, ou toutes."""
    cible = rb"[A-Z]+" if colonne is None else re.escape(_lettre_colonne(colonne).encode())
    return re.compile(
        rb'<c r="(' + cible + rb')(\d+)"([^>]*?)(?:/>|>(.*?)</c>)', re.S
    )


def _valeur(attributs: bytes, corps: bytes | None, textes: list[str]) -> str | None:
    """Valeur d'une cellule, résolue selon le type déclaré dans ses attributs.

    Trois cas coexistent dans la nature : le texte « en ligne » (écrit par
    openpyxl), la référence à la table des chaînes partagées (écrite par Excel),
    et la valeur brute (nombres, dates, résultats de formule).
    """
    if not corps:
        return None

    if b'"inlineStr"' in attributs:
        morceaux = _TEXTES.findall(corps)
        return _decoder(b"".join(morceaux)) if morceaux else None

    brut = _NOMBRE.search(corps)
    if brut is None:
        return None
    if b'"s"' in attributs:
        rang = int(brut.group(1))
        return textes[rang] if rang < len(textes) else None
    return _decoder(brut.group(1))


def _textes_partages(archive: zipfile.ZipFile) -> list[str]:
    """Table des chaînes partagées, chargée seulement si le classeur en use."""
    if "xl/sharedStrings.xml" not in archive.namelist():
        return []
    brut = archive.read("xl/sharedStrings.xml")
    return [
        _decoder(b"".join(_TEXTES.findall(entree)))
        for entree in re.findall(rb"<si[^>]*>(.*?)</si>", brut, re.S)
    ]


def _chemin_feuille_active(archive: zipfile.ZipFile) -> str:
    """Chemin, dans l'archive, de la feuille active — celle qu'ouvre openpyxl.

    L'onglet actif est désigné par ``activeTab`` dans ``xl/workbook.xml`` ; le
    lien vers le fichier de la feuille passe par les relations du classeur.
    """
    racine = _analyser(archive, "xl/workbook.xml")

    onglet = 0
    vue = racine.find(f"{NS_FEUILLE}bookViews/{NS_FEUILLE}workbookView")
    if vue is not None:
        onglet = int(vue.get("activeTab") or 0)

    feuilles = racine.findall(f"{NS_FEUILLE}sheets/{NS_FEUILLE}sheet")
    if not feuilles:
        raise LectureImpossible("aucune feuille déclarée")
    if onglet >= len(feuilles):
        onglet = 0

    identifiant = feuilles[onglet].get(f"{NS_REL_DOC}id")
    relations = _analyser(archive, "xl/_rels/workbook.xml.rels")
    for relation in relations.findall(f"{NS_REL_PKG}Relationship"):
        if relation.get("Id") == identifiant:
            cible = relation.get("Target") or ""
            chemin = cible[1:] if cible.startswith("/") else f"xl/{cible}"
            chemin = chemin.replace("xl/xl/", "xl/")
            if chemin in archive.namelist():
                return chemin
    raise LectureImpossible("feuille active introuvable dans l'archive")


# ── Helpers ───────────────────────────────────────────────────────
def _analyser(archive: zipfile.ZipFile, nom: str):
    try:
        return fromstring(archive.read(nom))
    except KeyError as exc:
        raise LectureImpossible(f"{nom} absent de l'archive") from exc


def _decoder(brut: bytes) -> str:
    """Texte XML brut → texte Python (entités nommées et numériques remplacées)."""
    texte = unescape(brut.decode("utf-8", "replace"), _ENTITES)
    if "&#" not in texte:
        return texte
    return _REFERENCE_NUMERIQUE.sub(_caractere, texte)


def _caractere(reference: re.Match[str]) -> str:
    """« &#244; » ou « &#xF4; » → « ô »."""
    hexadecimal, chiffres = reference.groups()
    try:
        return chr(int(chiffres, 16 if hexadecimal else 10))
    except ValueError:
        return reference.group(0)


def _index_colonne(lettres: bytes) -> int:
    """``b"AB"`` → 28. Numéro de colonne porté par une référence de cellule."""
    index = 0
    for caractere in lettres.decode("ascii"):
        index = index * 26 + (ord(caractere) - ord("A") + 1)
    return index


def _lettre_colonne(index: int) -> str:
    """28 → « AB ». Inverse de :func:`_index_colonne`."""
    lettres = ""
    while index > 0:
        index, reste = divmod(index - 1, 26)
        lettres = chr(ord("A") + reste) + lettres
    return lettres
