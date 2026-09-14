"""Reprise de la mise en forme du classeur pour la colonne ID erreur écrite.

Une exigence cosmétique mais lourde de conséquences : une valeur écrite dans
une autre police que sa colonne se repère immédiatement à l'œil dans un
livrable.
"""

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Font

from sna.models.config_adresses import ConfigAdresses
from sna.services.adresses import SaisieAdresse
from sna.services.excel import appliquer_adresses


def _config(harmoniser_style=True):
    return ConfigAdresses(
        colonne_adresse="Adresse", colonne_id="ID erreur", ligne_entete=1,
        harmoniser_style=harmoniser_style,
    )


def _saisie(adresse, valeur="corrigé"):
    return [SaisieAdresse(adresse, valeur)]


# ── Reprise de la mise en forme ───────────────────────────────────
def _preparer_police(chemin, cellules: dict, police: Font, alignement: Alignment = None):
    classeur = load_workbook(chemin)
    feuille = classeur.active
    for reference in cellules:
        feuille[reference].font = police
        if alignement is not None:
            feuille[reference].alignment = alignement
    classeur.save(chemin)


def test_police_de_la_colonne_reprise(creer_classeur):
    chemin = creer_classeur({"A": ["12 rue A", "20 rue B"], "C": ["repère", "à changer"]})
    _preparer_police(
        chemin, {"C2"}, Font(name="Calibri", size=14, bold=True, italic=True),
        Alignment(horizontal="center"),
    )

    appliquer_adresses(chemin, _config(), _saisie("20 rue B"))

    cellule = load_workbook(chemin).active["C3"]
    assert cellule.value == "corrigé"
    assert (cellule.font.name, cellule.font.size) == ("Calibri", 14)
    assert cellule.font.bold and cellule.font.italic
    assert cellule.alignment.horizontal == "center"


def test_le_modele_n_est_pas_une_ligne_modifiee(creer_classeur):
    """La forme reprise est celle du fichier, jamais celle qu'on vient d'écrire."""
    chemin = creer_classeur({"A": ["12 rue A", "20 rue B"], "C": ["repère", "autre"]})
    _preparer_police(chemin, {"C2"}, Font(name="Calibri", size=14))
    _preparer_police(chemin, {"C3"}, Font(name="Wingdings", size=6))

    appliquer_adresses(chemin, _config(), _saisie("20 rue B"))

    assert load_workbook(chemin).active["C3"].font.name == "Calibri"


def test_option_desactivee_laisse_la_forme_intacte(creer_classeur):
    chemin = creer_classeur({"A": ["12 rue A", "20 rue B"], "C": ["repère", "à changer"]})
    _preparer_police(chemin, {"C2"}, Font(name="Calibri", size=14))
    _preparer_police(chemin, {"C3"}, Font(name="Wingdings", size=6))

    appliquer_adresses(chemin, _config(harmoniser_style=False), _saisie("20 rue B"))

    assert load_workbook(chemin).active["C3"].font.name == "Wingdings"


# ── Colonnes vides : police dominante du classeur ─────────────────
def test_colonne_vide_reprend_la_police_dominante(creer_classeur):
    """Cas de la colonne ID erreur : vide, donc sans modèle dans sa colonne.

    Sans ce relais, openpyxl écrirait en Calibri 11 dans un classeur composé
    en Calibri 10, et la valeur se repérerait à l'œil.
    """
    chemin = creer_classeur(
        {"A": ["12 rue A", "20 rue B"], "B": ["rue A", "rue B"], "C": [None, None]}
    )
    _preparer_police(chemin, {"A2", "A3", "B2", "B3"}, Font(name="Calibri", size=10))

    appliquer_adresses(chemin, _config(), _saisie("12 rue A", "OK"))

    cellule = load_workbook(chemin).active["C2"]
    assert cellule.value == "OK"
    assert (cellule.font.name, cellule.font.size) == ("Calibri", 10)


def test_police_dominante_l_emporte_sur_une_exception(creer_classeur):
    """C'est la police la plus employée qui fait référence, pas la première."""
    chemin = creer_classeur({
        "A": ["12 rue A", "20 rue B", "5 rue C"],
        "B": ["rue A", "rue B", "rue C"],
        "C": [None, None, None],
    })
    _preparer_police(chemin, {"B2"}, Font(name="Arial", size=18))
    _preparer_police(chemin, {"B3", "B4", "A2", "A3", "A4"}, Font(name="Calibri", size=10))

    appliquer_adresses(chemin, _config(), _saisie("12 rue A", "OK"))

    assert load_workbook(chemin).active["C2"].font.name == "Calibri"


def test_la_colonne_prime_sur_la_police_dominante(creer_classeur):
    """Une colonne qui a sa propre forme la conserve."""
    chemin = creer_classeur({
        "A": ["12 rue A", "20 rue B"], "B": ["rue A", "rue B"], "C": ["repère", None],
    })
    _preparer_police(chemin, {"A2", "A3", "B2", "B3"}, Font(name="Calibri", size=10))
    _preparer_police(chemin, {"C2"}, Font(name="Consolas", size=8))

    appliquer_adresses(chemin, _config(), _saisie("20 rue B", "OK"))

    assert load_workbook(chemin).active["C3"].font.name == "Consolas"


def test_option_desactivee_ignore_aussi_la_police_dominante(creer_classeur):
    chemin = creer_classeur({"A": ["12 rue A"], "B": ["rue A"], "C": [None]})
    _preparer_police(chemin, {"A2", "B2"}, Font(name="Calibri", size=10))
    _preparer_police(chemin, {"C2"}, Font(name="Wingdings", size=6))

    appliquer_adresses(chemin, _config(harmoniser_style=False), _saisie("12 rue A", "OK"))

    assert load_workbook(chemin).active["C2"].font.name == "Wingdings"


def test_classeur_sans_donnees_ne_bloque_pas(creer_classeur):
    """Aucune police à relever : la cellule garde simplement la sienne."""
    chemin = creer_classeur({"A": ["12 rue A"], "C": [None]})

    bilan = appliquer_adresses(chemin, _config(), _saisie("12 rue A", "OK"))

    assert bilan.nb_modifications == 1
    assert load_workbook(chemin).active["C2"].value == "OK"


# ── Effets de bord d'openpyxl ─────────────────────────────────────
def test_aucune_ligne_fantome_ajoutee(creer_classeur):
    """Consulter une cellule la crée : le classeur ne doit pas gonfler pour autant."""
    chemin = creer_classeur({"A": ["12 rue A"], "C": ["x"]})

    appliquer_adresses(chemin, _config(), _saisie("12 rue A", "OK"))

    feuille = load_workbook(chemin).active
    assert feuille.max_row == 2
    assert feuille.max_column == 26
