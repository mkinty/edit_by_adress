"""Extraction des paires (adresse, valeur ID erreur) saisies par l'utilisateur.

L'utilisateur saisit des **paires** (adresse, ID erreur attendu) : chaque
adresse est associée à la valeur qu'elle doit prendre dans la colonne
« ID erreur » du classeur. Une ligne de saisie s'écrit :

    <adresse><séparateur><ID erreur>   ou   <ID erreur><séparateur><adresse>

où le séparateur est une tabulation (copier/coller depuis deux colonnes
Excel), un point-virgule, ou une flèche (``->`` ou ``=>``). Les deux colonnes
peuvent être copiées dans n'importe quel ordre : le membre qui ressemble à un
ID erreur (``<insee>_<numéro>``, par exemple ``13001_1``) est reconnu comme
tel automatiquement, l'autre étant l'adresse.

Le code INSEE de chaque adresse n'est pas connu à la saisie — contrairement à
l'ancien ID erreur, qui le portait en préfixe — il est résolu séparément par
``services.geocodage``. Ce module se contente donc d'analyser le texte et,
une fois les codes INSEE connus, de regrouper les paires par commune, un seul
fichier audit étant ouvert par commune quel que soit le nombre d'adresses qui
s'y trouvent.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
import re

# Tabulation (copier/coller Excel), point-virgule, ou flèche.
_SEPARATEUR = re.compile(r"\t|=>|->|;")

# ID erreur : code INSEE (5 chiffres, ou 2A/2B + 3 chiffres), un souligné,
# puis le numéro de l'anomalie — sert à reconnaître automatiquement quel
# membre d'une ligne est l'ID erreur, quel que soit l'ordre de saisie.
_MOTIF_ID_ERREUR = re.compile(r"^(?:2[AB]\d{3}|\d{5})_[A-Z0-9]+$", re.IGNORECASE)

# Libellés d'en-tête tolérés en 1re ligne d'un copier/coller (« ID erreur »,
# « Adresse », dans n'importe quel ordre) : ignorés plutôt que traités comme
# une paire à géocoder.
_LIBELLES_ENTETE = {"adresse", "id erreur"}


@dataclass(frozen=True)
class SaisieAdresse:
    """Une ligne de saisie : une adresse et la valeur d'ID erreur à lui donner."""

    adresse: str
    valeur_id: str


def normaliser_adresse(valeur) -> str:
    """Forme comparable d'une adresse : espaces normalisés, majuscules.

    Utilisée des deux côtés — saisie utilisateur et cellules du classeur —
    pour qu'une adresse tolère la casse et les espaces multiples ou en trop.
    """
    if valeur is None:
        return ""
    return " ".join(str(valeur).split()).upper()


def extraire_saisies(texte: str) -> list[SaisieAdresse]:
    """Retourne les paires (adresse, valeur) valides, une par ligne non vide.

    Une ligne sans séparateur reconnu, ou dont l'un des deux membres est vide,
    ne produit aucune paire : elle est signalée séparément par
    :func:`lignes_incompletes`. Une éventuelle ligne d'en-tête (« ID erreur »
    / « Adresse », copiée avec les données) est ignorée silencieusement.
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
    """Lignes non vides qui n'ont pas produit de paire exploitable."""
    incompletes = []
    for ligne in texte.splitlines():
        brut = ligne.strip()
        if brut and not _est_ligne_entete(brut) and _analyser_ligne(brut) is None:
            incompletes.append(brut)
    return incompletes


def grouper_par_commune(
    saisies: Iterable[SaisieAdresse], codes_insee: Mapping[str, str | None],
) -> tuple[dict[str, list[SaisieAdresse]], list[SaisieAdresse]]:
    """Regroupe les saisies par commune, à partir des codes INSEE résolus.

    Args:
        saisies: paires (adresse, valeur) extraites de la saisie.
        codes_insee: ``{adresse: code_insee | None}``, résolu par
            ``services.geocodage.codes_insee_pour_adresses``.

    Returns:
        ``({insee: [SaisieAdresse, …]}, [SaisieAdresse non résolues])`` — les
        adresses sans code INSEE (introuvables ou ambiguës auprès du service
        de géocodage) sont écartées du regroupement et renvoyées à part,
        communes et adresses dans leur ordre d'apparition.
    """
    groupes: dict[str, list[SaisieAdresse]] = {}
    non_resolues: list[SaisieAdresse] = []
    for saisie in saisies:
        insee = codes_insee.get(saisie.adresse.strip())
        if not insee:
            non_resolues.append(saisie)
            continue
        groupes.setdefault(insee, []).append(saisie)
    return groupes, non_resolues


# ── Helpers ───────────────────────────────────────────────────────
def _ressemble_a_un_id_erreur(valeur: str) -> bool:
    return bool(_MOTIF_ID_ERREUR.match(valeur))


def _est_ligne_entete(brut: str) -> bool:
    parts = _SEPARATEUR.split(brut, maxsplit=1)
    if len(parts) != 2:
        return False
    libelles = {parts[0].strip().casefold(), parts[1].strip().casefold()}
    return libelles == _LIBELLES_ENTETE


def _analyser_ligne(ligne: str) -> SaisieAdresse | None:
    brut = ligne.strip()
    if not brut:
        return None
    parts = _SEPARATEUR.split(brut, maxsplit=1)
    if len(parts) != 2:
        return None
    premier, second = parts[0].strip(), parts[1].strip()
    if not premier or not second:
        return None

    # Ordre « ID erreur, adresse » reconnu par la forme du premier membre ;
    # par défaut (aucun des deux ne ressemble à un ID, ou les deux) l'ordre
    # est « adresse, ID erreur ».
    if _ressemble_a_un_id_erreur(premier) and not _ressemble_a_un_id_erreur(second):
        return SaisieAdresse(adresse=second, valeur_id=premier)
    return SaisieAdresse(adresse=premier, valeur_id=second)
