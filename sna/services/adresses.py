"""Extraction des triplets (code INSEE, adresse, valeur ID erreur) saisis.

L'utilisateur saisit, pour chaque correction, les trois informations
nécessaires : le **code INSEE** de la commune (il localise le fichier audit,
comme le préfixe de l'ancien ID erreur), l'**adresse** (elle sélectionne la
ligne dans ce fichier, colonne « Adresse ») et la **valeur d'ID erreur** à y
écrire. Une ligne de saisie s'écrit :

    <code INSEE><séparateur><adresse><séparateur><valeur ID erreur>

où le séparateur est un point-virgule (``;``), une tabulation (copier/coller
depuis trois colonnes Excel) ou une flèche (``->`` ou ``=>``). Le code INSEE
est pris sur le **premier** séparateur rencontré, la valeur d'ID erreur sur
le **dernier** : l'adresse, au milieu, peut ainsi elle-même contenir un point-
virgule ou une flèche sans perturber l'analyse.

Le code INSEE étant fourni directement par l'utilisateur, aucune résolution
(géocodage, appel réseau) n'est nécessaire : un seul fichier audit est ouvert
par commune, quel que soit le nombre d'adresses qui s'y trouvent.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import re

# Point-virgule, tabulation (copier/coller Excel), ou flèche.
_SEPARATEUR = re.compile(r"\t|=>|->|;")

# Code INSEE : 5 chiffres (métropole/DOM), ou format corse 2A/2B + 3 chiffres.
_MOTIF_INSEE = re.compile(r"^(?:2[AB]\d{3}|\d{5})$", re.IGNORECASE)

# Libellés reconnus comme une ligne d'en-tête copiée avec les données
# (« Code INSEE ; Adresse ; ID erreur », dans le champ du code INSEE).
_LIBELLES_INSEE = {"insee", "code insee", "codeinsee"}


@dataclass(frozen=True)
class SaisieAdresse:
    """Une ligne de saisie : adresse et valeur d'ID erreur à lui donner.

    ``insee`` n'est conservé que pour information (traçabilité, journal) — le
    regroupement par commune s'appuie dessus, mais l'écriture dans le
    classeur (``services.excel``) ne s'en sert pas : seule l'adresse compare
    les lignes.
    """

    adresse: str
    valeur_id: str
    insee: str = ""


def normaliser_adresse(valeur) -> str:
    """Forme comparable d'une adresse : espaces normalisés, majuscules.

    Utilisée des deux côtés — saisie utilisateur et cellules du classeur —
    pour qu'une adresse tolère la casse et les espaces multiples ou en trop.
    """
    if valeur is None:
        return ""
    return " ".join(str(valeur).split()).upper()


def normaliser_insee(valeur) -> str:
    """Forme comparable d'un code INSEE : espaces supprimés, majuscules."""
    if valeur is None:
        return ""
    return "".join(str(valeur).split()).upper()


def extraire_saisies(texte: str) -> list[SaisieAdresse]:
    """Retourne les triplets valides, une entrée par ligne non vide.

    Une ligne sans deux séparateurs reconnus, dont le premier membre n'est
    pas un code INSEE valide, ou dont l'adresse ou la valeur d'ID erreur est
    vide, ne produit aucune entrée : elle est signalée séparément par
    :func:`lignes_incompletes`. Une éventuelle ligne d'en-tête est ignorée
    silencieusement.
    """
    saisies = []
    for ligne in texte.splitlines():
        brut = ligne.strip()
        if not brut or _est_ligne_entete(brut):
            continue
        saisie = _analyser_ligne(brut)
        if saisie is not None:
            saisies.append(saisie)
    return saisies


def lignes_incompletes(texte: str) -> list[str]:
    """Lignes non vides qui n'ont pas produit d'entrée exploitable."""
    incompletes = []
    for ligne in texte.splitlines():
        brut = ligne.strip()
        if brut and not _est_ligne_entete(brut) and _analyser_ligne(brut) is None:
            incompletes.append(brut)
    return incompletes


def grouper_par_commune(saisies: Iterable[SaisieAdresse]) -> dict[str, list[SaisieAdresse]]:
    """Regroupe les saisies par code INSEE, dans leur ordre d'apparition.

    Returns:
        ``{insee: [SaisieAdresse, …]}`` — un seul fichier audit est ouvert
        par entrée du dictionnaire, quel que soit le nombre d'adresses qui
        s'y trouvent.
    """
    groupes: dict[str, list[SaisieAdresse]] = {}
    for saisie in saisies:
        groupes.setdefault(saisie.insee, []).append(saisie)
    return groupes


# ── Helpers ───────────────────────────────────────────────────────
def _est_ligne_entete(brut: str) -> bool:
    premier = _SEPARATEUR.split(brut, maxsplit=1)[0]
    return premier.strip().casefold() in _LIBELLES_INSEE


def _analyser_ligne(brut: str) -> SaisieAdresse | None:
    premier = _SEPARATEUR.split(brut, maxsplit=1)
    if len(premier) != 2:
        return None
    insee_brut, reste = premier
    insee = normaliser_insee(insee_brut)
    if not _MOTIF_INSEE.match(insee):
        return None

    occurrences = list(_SEPARATEUR.finditer(reste))
    if not occurrences:
        return None
    dernier = occurrences[-1]
    adresse = reste[: dernier.start()].strip()
    valeur_id = reste[dernier.end() :].strip()
    if not adresse or not valeur_id:
        return None
    return SaisieAdresse(adresse=adresse, valeur_id=valeur_id, insee=insee)
