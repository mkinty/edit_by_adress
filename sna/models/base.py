"""Structures de base du domaine (statut d'un traitement, résultat par commune).

Ces objets ne dépendent d'aucune bibliothèque externe : ils décrivent *ce que*
le programme manipule, pas *comment* il le fait.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Statut(Enum):
    """Issue du traitement d'une commune."""

    SUCCES = "succes"            # Fichier trouvé et traité
    INTROUVABLE = "introuvable"  # Aucun fichier audit pour cette commune
    ERREUR = "erreur"            # Une exception est survenue pendant le traitement


@dataclass
class ResultatCommune:
    """Résultat du traitement d'une seule commune.

    ``adresses_absentes`` liste les adresses demandées pour cette commune mais
    introuvables dans le fichier : sans cette remontée, une adresse mal saisie
    (ou mal orthographiée dans le classeur) passerait pour un traitement réussi.
    """

    commune: str
    statut: Statut
    nb_modifications: int = 0
    message: str = ""
    nb_adresses_demandees: int = 0
    nb_lignes: int = 0
    adresses_absentes: list[str] = field(default_factory=list)
    duree: float = 0.0

    def resume_duree(self) -> str:
        """Durée du traitement, arrondie à la milliseconde près (« 2,4 s »)."""
        return f"{self.duree:.1f} s".replace(".", ",")

    def resume_adresses(self) -> str:
        """Ex. « 4/5 adresses trouvées » (adresses manquantes signalées)."""
        trouvees = self.nb_adresses_demandees - len(self.adresses_absentes)
        return f"{trouvees}/{self.nb_adresses_demandees} adresses trouvées"
