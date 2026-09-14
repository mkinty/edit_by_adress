"""Configuration de la modification par adresse.

Le choix des lignes n'est plus dicté par un « ID erreur » mais par une
**adresse** : une ligne n'est envisagée que si la valeur de sa colonne
« Adresse » correspond à l'une des adresses saisies. Sur cette ligne, la seule
opération possible est d'écrire, dans la colonne « ID erreur », la valeur
associée à cette adresse dans la saisie.

``ConfigAdresses`` ne porte donc que les repères nécessaires à cette seule
opération :

    colonne_adresse  → colonne comparée aux adresses saisies (« Adresse » par
                        défaut) ;
    colonne_id       → colonne écrite avec la valeur associée à l'adresse
                        (« ID erreur » par défaut) ;
    ligne_entete     → ligne des libellés de colonnes (1 par défaut) ;
    harmoniser_style → reprise de la police / du format de la colonne écrite.

Il n'y a pas de configuration livrée par défaut : à la première utilisation,
l'utilisateur confirme (ou change) le nom des deux colonnes depuis le panneau
de configuration.
"""

from __future__ import annotations

from dataclasses import dataclass

# Libellés de colonne recherchés par défaut.
COLONNE_ADRESSE_DEFAUT = "Adresse"
COLONNE_ID_DEFAUT = "ID erreur"


@dataclass
class ConfigAdresses:
    """Repères de lecture du classeur pour la modification par adresse."""

    colonne_adresse: str = COLONNE_ADRESSE_DEFAUT
    colonne_id: str = COLONNE_ID_DEFAUT
    ligne_entete: int = 1
    harmoniser_style: bool = True

    # ── Sérialisation JSON ────────────────────────────────────────
    def to_dict(self) -> dict:
        return {
            "colonne_adresse": self.colonne_adresse,
            "colonne_id": self.colonne_id,
            "ligne_entete": self.ligne_entete,
            "harmoniser_style": self.harmoniser_style,
        }

    @staticmethod
    def from_dict(data: dict) -> "ConfigAdresses":
        return ConfigAdresses(
            colonne_adresse=str(data.get("colonne_adresse") or COLONNE_ADRESSE_DEFAUT),
            colonne_id=str(data.get("colonne_id") or COLONNE_ID_DEFAUT),
            ligne_entete=int(data.get("ligne_entete", 1) or 1),
            harmoniser_style=bool(data.get("harmoniser_style", True)),
        )
