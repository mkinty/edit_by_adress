"""Thème de l'interface : couleurs et polices centralisées.

Toute la charte graphique est regroupée ici. Changer une couleur dans ce
fichier la met à jour partout dans l'application.
"""

from ..models.base import Statut


class Couleurs:
    # Fonds
    FOND = "#0f1117"
    FOND_HEADER = "#161b2e"
    FOND_CHAMP = "#1a1f35"
    FOND_JOURNAL = "#0a0d14"
    FOND_CARTE = "#131925"
    FOND_PANNEAU = "#11161f"
    FOND_PANNEAU2 = "#1b2333"
    BORDURE = "#2a3447"

    # Textes
    TEXTE = "#e8eaf6"
    TEXTE_SECONDAIRE = "#78909c"
    TEXTE_TERTIAIRE = "#546e7a"
    BLANC = "white"

    # Accents
    BLEU = "#1565c0"
    BLEU_CLAIR = "#90caf9"
    VERT = "#42e2a0"
    AMBRE = "#ffc05a"
    ROUGE = "#ff6b7a"

    # États (utilisés dans le journal)
    SUCCES = "#69f0ae"
    AVERTISSEMENT = "#ffb74d"
    ERREUR = "#ef5350"
    INFO = "#90caf9"
    SEPARATEUR = "#78909c"


class Polices:
    TITRE = ("Segoe UI", 14, "bold")
    SOUS_TITRE = ("Segoe UI", 11, "bold")
    LOT = ("Segoe UI", 13, "bold")
    CORPS = ("Segoe UI", 10)
    LABEL = ("Segoe UI", 9)
    LABEL_GRAS = ("Segoe UI", 9, "bold")
    PETIT = ("Segoe UI", 8)
    BOUTON = ("Segoe UI", 12, "bold")
    BOUTON_PETIT = ("Segoe UI", 9, "bold")
    JOURNAL = ("Consolas", 9)
    MONO = ("Consolas", 10)


# Association d'un statut de traitement à une couleur et une icône de journal.
STYLE_STATUT: dict[Statut, tuple[str, str]] = {
    Statut.SUCCES: (Couleurs.SUCCES, "✅"),
    Statut.INTROUVABLE: (Couleurs.AVERTISSEMENT, "⚠️"),
    Statut.ERREUR: (Couleurs.ERREUR, "❌"),
}
