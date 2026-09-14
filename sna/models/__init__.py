"""Modèles de données du domaine.

    sna.models.base             → Statut, ResultatCommune
    sna.models.config_adresses  → ConfigAdresses

Tout est ré-exporté ici pour que ``from sna.models import ...`` reste possible.
"""

from .base import ResultatCommune, Statut
from .config_adresses import COLONNE_ADRESSE_DEFAUT, COLONNE_ID_DEFAUT, ConfigAdresses

__all__ = [
    "COLONNE_ADRESSE_DEFAUT",
    "COLONNE_ID_DEFAUT",
    "ConfigAdresses",
    "ResultatCommune",
    "Statut",
]
