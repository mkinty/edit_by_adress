"""Détection des colonnes d'un classeur et résolution des références.

Trois usages :
    - alimenter les menus déroulants du panneau de configuration (liste
      réelle des colonnes + type déduit, pour proposer la bonne saisie) ;
    - traduire une référence de colonne (« Z » ou « Audit - Street View ») en
      numéro de colonne au moment d'appliquer les modifications ;
    - lire les seuls en-têtes d'une feuille déjà ouverte, sans échantillonner
      les données — c'est le chemin rapide utilisé pendant le traitement.

Le type ``date`` est reconnu soit par le libellé de l'en-tête (tout en-tête
contenant le mot « date »), soit par les valeurs elles-mêmes.
"""

from __future__ import annotations

from datetime import date, datetime, time
from math import isfinite
import os
import re
import warnings
from dataclasses import dataclass

from openpyxl import load_workbook
from openpyxl.utils import get_column_letter

# Types de colonnes déduits du libellé et des valeurs. Ils n'informent plus
# qu'un affichage (badge « colonne · type » du panneau de configuration) :
# le choix des lignes et de la colonne écrite ne dépend plus du type.
TYPE_NUM = "numérique"
TYPE_TEXTE = "texte"
TYPE_DATE = "date"

# openpyxl émet des avertissements bénins sur certaines extensions Excel.
warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")

_MOTIF_LETTRE = re.compile(r"^[A-Z]{1,3}$")

# Part minimale de valeurs d'un même genre pour qualifier le type d'une colonne.
_SEUIL_NUMERIQUE = 0.8
_SEUIL_DATE = 0.5

# Mot recherché dans l'en-tête pour forcer le type date.
_MOT_DATE = "date"


@dataclass(frozen=True)
class Colonne:
    """Une colonne détectée dans le classeur."""

    nom: str      # libellé de l'en-tête
    index: int    # numéro de colonne (1 = A)
    type: str     # TYPE_NUM, TYPE_DATE ou TYPE_TEXTE

    @property
    def lettre(self) -> str:
        return get_column_letter(self.index)

    @property
    def libelle(self) -> str:
        """Ex. « Z — Audit - Street View » (affichage dans l'interface)."""
        return f"{self.lettre} — {self.nom}"


# ── Lecture rapide des en-têtes ───────────────────────────────────
def entetes_depuis_feuille(feuille, ligne_entete: int = 1) -> dict[int, str]:
    """Libellés de la ligne d'en-tête d'une feuille déjà ouverte.

    Fonctionne aussi bien sur une feuille normale que sur une feuille ouverte
    en lecture seule, et ne lit qu'**une seule ligne** : c'est ce qui permet
    d'éviter, pendant le traitement, la coûteuse détection de type par
    échantillonnage.
    """
    for ligne in feuille.iter_rows(
        min_row=ligne_entete, max_row=ligne_entete, values_only=True
    ):
        return {
            index: str(valeur).strip()
            for index, valeur in enumerate(ligne, start=1)
            if valeur not in (None, "")
        }
    return {}


def table_depuis_entetes(entetes: dict[int, str]) -> dict[str, int]:
    """Table de résolution « référence → index » à partir des seuls en-têtes.

    Sont acceptés : le nom d'en-tête exact, sa forme normalisée (espaces et
    casse ignorés) et la lettre de colonne. Les noms d'en-tête sont prioritaires
    sur les lettres en cas de collision (une colonne nommée « Z », par exemple).
    """
    table: dict[str, int] = {}
    for index in entetes:  # lettres d'abord : les noms pourront les écraser
        table.setdefault(get_column_letter(index), index)
    for index, nom in entetes.items():
        table[normaliser(nom)] = index
    return table


def entete_est_date(nom: str) -> bool:
    """Vrai si le libellé d'un en-tête désigne une colonne de dates."""
    return _MOT_DATE in normaliser(nom)


# ── Détection complète (menus déroulants) ─────────────────────────
def detecter_colonnes(chemin: str, ligne_entete: int = 1, echantillon: int = 400) -> list[Colonne]:
    """Retourne les colonnes de la 1re feuille, avec leur type déduit.

    Le type est déduit du libellé puis des valeurs sous l'en-tête :
    « date » si l'en-tête contient ce mot ou si les valeurs en sont,
    « numérique » si la grande majorité des valeurs non vides sont des nombres,
    « texte » sinon.
    """
    if not chemin or not os.path.isfile(chemin):
        return []

    classeur = load_workbook(chemin, read_only=True, data_only=True)
    try:
        feuille = classeur.active
        entetes = entetes_depuis_feuille(feuille, ligne_entete)
        if not entetes:
            return []

        indices = sorted(entetes)
        col_min, col_max = indices[0], indices[-1]
        # index -> [nb numériques, nb dates, nb textes]
        compte = {index: [0, 0, 0] for index in indices}

        vus = 0
        for ligne in feuille.iter_rows(
            min_row=ligne_entete + 1, min_col=col_min, max_col=col_max, values_only=True
        ):
            for index in indices:
                rang = index - col_min
                valeur = ligne[rang] if rang < len(ligne) else None
                if valeur in (None, ""):
                    continue
                compte[index][_genre(valeur)] += 1
            vus += 1
            if vus >= echantillon:
                break

        return [
            Colonne(
                nom=entetes[index],
                index=index,
                type=_type_colonne(entetes[index], compte[index]),
            )
            for index in indices
        ]
    finally:
        classeur.close()


def index_par_reference(colonnes: list[Colonne]) -> dict[str, int]:
    """Table de résolution « référence → index de colonne »."""
    return table_depuis_entetes({c.index: c.nom for c in colonnes})


def resoudre_colonne(reference: str, table: dict[str, int]) -> int | None:
    """Traduit une référence de colonne en numéro de colonne, ou ``None``.

    Une lettre valide (A, Z, AB…) est acceptée même si le fichier n'a pas
    d'en-tête à cet emplacement : la colonne existe physiquement.
    """
    ref = str(reference or "").strip()
    if not ref:
        return None

    index = table.get(normaliser(ref))
    if index is not None:
        return index

    majuscule = ref.upper()
    if majuscule in table:
        return table[majuscule]
    if _MOTIF_LETTRE.match(majuscule):
        return _lettre_vers_index(majuscule)
    return None


def normaliser(valeur) -> str:
    """Forme comparable d'un libellé : espaces supprimés, casse ignorée."""
    return "".join(str(valeur).split()).casefold()


def est_nombre(valeur) -> bool:
    """Vrai si la valeur est convertible en nombre (virgule décimale acceptée)."""
    return to_num(valeur) is not None


def est_date(valeur) -> bool:
    """Vrai si la valeur est une date ou un horodatage Excel."""
    return isinstance(valeur, (datetime, date, time))


def to_num(valeur) -> float | None:
    """Convertit une valeur en float, ou ``None`` si ce n'est pas un nombre.

    Deux pièges de ``float()`` sont écartés ici :

    - Python accepte les soulignés dans les littéraux numériques, si bien que
      ``float("13001_2")`` vaut 130012.0. Un ID erreur imposé comme valeur
      serait alors écrit comme un nombre dans le classeur.
    - ``float("nan")`` et ``float("inf")`` réussissent aussi ; ces textes n'ont
      rien à faire dans une cellule sous forme de nombre.
    """
    if isinstance(valeur, bool) or est_date(valeur):
        return None

    texte = str(valeur).replace(",", ".").strip()
    if "_" in texte:
        return None
    try:
        nombre = float(texte)
    except (TypeError, ValueError):
        return None
    return nombre if isfinite(nombre) else None


# ── Helpers ───────────────────────────────────────────────────────
def _genre(valeur) -> int:
    """Rang de la valeur dans le compteur [numérique, date, texte]."""
    if est_date(valeur):
        return 1
    return 0 if est_nombre(valeur) else 2


def _type_colonne(nom: str, compte: list[int]) -> str:
    """Type retenu pour une colonne, d'après son libellé puis ses valeurs."""
    if entete_est_date(nom):
        return TYPE_DATE

    num, dates, textes = compte
    total = num + dates + textes
    if not total:
        return TYPE_TEXTE
    if dates / total >= _SEUIL_DATE:
        return TYPE_DATE
    if num / total >= _SEUIL_NUMERIQUE:
        return TYPE_NUM
    return TYPE_TEXTE


def _lettre_vers_index(lettre: str) -> int:
    index = 0
    for caractere in lettre:
        index = index * 26 + (ord(caractere) - ord("A") + 1)
    return index
