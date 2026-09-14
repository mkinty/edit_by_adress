"""Orchestration : traitement d'un lot de communes.

L'entrée est le dictionnaire ``{insee: [SaisieAdresse, …]}`` construit par
``services.adresses.grouper_par_commune`` à partir de la saisie de
l'utilisateur (code INSEE, adresse, valeur d'ID erreur) : une entrée = un
fichier audit à ouvrir.

Le cœur métier est totalement découplé de l'interface : il communique via trois
callbacks optionnels (progression, étape, résultat) et retourne la liste des
résultats. Appelé sans callbacks, il reste parfaitement testable.

Le callback ``on_etape`` est appelé **pendant** le traitement d'une commune
(recherche du fichier, analyse, chargement, écriture, enregistrement) : c'est
lui qui évite à l'utilisateur d'attendre devant un journal vide.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
import os
import time

from ..models.base import ResultatCommune, Statut
from ..models.config_adresses import ConfigAdresses
from .adresses import SaisieAdresse, normaliser_adresse
from .excel import appliquer_adresses
from .fichiers import trouver_fichier_audit

# Signatures des callbacks
CallbackProgression = Callable[[int, int, str], None]   # (fait, total, libellé)
CallbackEtape = Callable[[str, str], None]              # (commune, message)
CallbackResultat = Callable[[ResultatCommune], None]


def traiter_communes(
    groupes: Mapping[str, Sequence[SaisieAdresse]],
    config: ConfigAdresses,
    racine: str,
    simuler: bool = False,
    on_progression: CallbackProgression | None = None,
    on_resultat: CallbackResultat | None = None,
    on_etape: CallbackEtape | None = None,
) -> list[ResultatCommune]:
    """Écrit la valeur d'ID erreur des adresses trouvées, commune par commune.

    Args:
        groupes: ``{insee: [SaisieAdresse, …]}`` — cf. ``services.adresses``.
        config: colonnes et ligne d'en-tête du classeur.
        racine: dossier racine des fichiers audit.
        simuler: n'écrit rien sur le disque, compte seulement les modifications.
        on_progression: appelé avant chaque commune (facultatif).
        on_etape: appelé à chaque étape interne d'une commune (facultatif).
        on_resultat: appelé après chaque commune avec son résultat (facultatif).

    Returns:
        La liste des :class:`ResultatCommune`, dans l'ordre de traitement.
    """
    communes = list(groupes)
    total = len(communes)
    resultats: list[ResultatCommune] = []

    _notifier_progression(on_progression, 0, total, "Démarrage...")

    for index, commune in enumerate(communes, start=1):
        saisies = list(groupes[commune])
        _notifier_progression(
            on_progression, index, total,
            f"{commune} ({len(saisies)} adresse(s))",
        )
        resultat = _traiter_une_commune(commune, saisies, config, racine, simuler, on_etape)
        resultats.append(resultat)
        if on_resultat is not None:
            on_resultat(resultat)

    _notifier_progression(on_progression, total, total, "Terminé")
    return resultats


def _traiter_une_commune(
    commune: str,
    saisies: list[SaisieAdresse],
    config: ConfigAdresses,
    racine: str,
    simuler: bool,
    on_etape: CallbackEtape | None,
) -> ResultatCommune:
    """Traite une seule commune et renvoie son résultat (ne lève jamais)."""
    def etape(message: str) -> None:
        if on_etape is not None:
            on_etape(commune, message)

    etape("recherche du fichier audit…")
    fichier = trouver_fichier_audit(racine, commune)
    if fichier is None:
        return ResultatCommune(
            commune, Statut.INTROUVABLE,
            message="fichier introuvable", nb_adresses_demandees=len(saisies),
        )

    etape(f"{os.path.basename(fichier)} ({_taille(fichier)})")
    depart = time.perf_counter()
    try:
        bilan = appliquer_adresses(fichier, config, saisies, simuler=simuler, on_etape=etape)
        absentes = [
            s.adresse for s in saisies
            if normaliser_adresse(s.adresse) not in bilan.adresses_trouvees
        ]
        return ResultatCommune(
            commune,
            Statut.SUCCES,
            nb_modifications=bilan.nb_modifications,
            nb_adresses_demandees=len(saisies),
            nb_lignes=bilan.nb_lignes,
            adresses_absentes=absentes,
            duree=time.perf_counter() - depart,
        )
    except Exception as exc:  # noqa: BLE001 — on isole l'échec d'une commune
        return ResultatCommune(
            commune, Statut.ERREUR, message=str(exc), nb_adresses_demandees=len(saisies),
            duree=time.perf_counter() - depart,
        )


def _taille(chemin: str) -> str:
    """Taille lisible d'un fichier, pour situer la durée annoncée."""
    try:
        octets = os.path.getsize(chemin)
    except OSError:
        return "taille inconnue"
    if octets >= 1024 * 1024:
        return f"{octets / (1024 * 1024):.1f} Mo"
    return f"{max(octets // 1024, 1)} Ko"


def _notifier_progression(
    callback: CallbackProgression | None, fait: int, total: int, libelle: str
) -> None:
    if callback is not None:
        callback(fait, total, libelle)
