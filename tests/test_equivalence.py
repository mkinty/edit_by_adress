"""Équivalence avec une implémentation de référence de la spécification.

Le moteur optimisé (résolution des colonnes une seule fois, écriture
conditionnelle, exclusion des lignes fantômes) doit produire **exactement** le
même classeur qu'une transcription naïve et directe de la règle métier :

    pour chaque ligne de données,
        si la colonne « Adresse » porte une adresse demandée,
            la colonne « ID erreur » reçoit la valeur associée à cette adresse.

Ce test rejoue cette version naïve sur une matrice de cas et compare les deux
classeurs **cellule par cellule**, ainsi que le nombre de modifications.
"""

import pytest
from openpyxl import Workbook, load_workbook

from sna.models.config_adresses import ConfigAdresses
from sna.services.adresses import SaisieAdresse, normaliser_adresse
from sna.services.excel import appliquer_adresses

COLONNE_ADRESSE = "A"
COLONNE_ID = "C"
ENTETES = {"A": "Adresse", "B": "Nb", "C": "ID erreur"}

# (adresses du fichier, valeurs déjà en place dans ID erreur, saisies [(adresse, valeur)])
CAS = [
    # Cas nominal : deux lignes sur trois sont visées.
    (["a", "b", "c"], ["x", "y", "z"], [("a", "1"), ("c", "3")]),
    # Aucune adresse demandée n'est présente dans le fichier.
    (["a"], ["x"], [("z", "9")]),
    # Valeur déjà en place : aucune écriture ne doit être comptée.
    (["a"], ["1"], [("a", "1")]),
    # Adresse dupliquée dans le fichier : les deux lignes sont écrites.
    (["a", "a"], ["x", "y"], [("a", "9")]),
    # Valeur numérique : écrite comme un nombre.
    (["a"], ["x"], [("a", "42")]),
    # Cellules ID erreur d'origine vides ou numériques.
    (["a", "b"], [None, 12], [("a", "1"), ("b", "2")]),
    # Adresses du fichier avec espaces et casse différentes.
    ([" a  b ", "c d"], ["x", "y"], [("A B", "1")]),
    # Colonne Adresse partiellement vide.
    ([None, "a", ""], ["x", "y", "z"], [("a", "1")]),
    # Fichier sans aucune ligne de données.
    ([], [], [("a", "1")]),
    # Deux adresses différentes visant la même commune, valeurs distinctes.
    (["a", "b"], ["x", "y"], [("a", "1"), ("b", "2")]),
    # Adresse dupliquée dans le fichier ET dans la saisie : distribution
    # positionnelle (1re ligne → 1re valeur, 2e ligne → 2e valeur).
    (["a", "a", "a"], ["x", "y", "z"], [("a", "1"), ("a", "2")]),
]


def _ecrire(chemin, adresses, valeurs_id):
    wb = Workbook()
    ws = wb.active
    for lettre, libelle in ENTETES.items():
        ws[f"{lettre}1"] = libelle
    for i, adresse in enumerate(adresses, start=2):
        ws[f"{COLONNE_ADRESSE}{i}"] = adresse
    for i, valeur in enumerate(valeurs_id, start=2):
        ws[f"{COLONNE_ID}{i}"] = valeur
    wb.save(chemin)


def _implementation_reference(chemin, saisies):
    """Transcription directe de la règle métier, sans aucune optimisation."""
    attendues: dict[str, list[str]] = {}
    for a, v in saisies:
        attendues.setdefault(normaliser_adresse(a), []).append(v)
    compteurs: dict[str, int] = {}

    classeur = load_workbook(chemin)
    feuille = classeur.active
    nb = 0
    try:
        for ligne in range(2, feuille.max_row + 1):
            brut = feuille[f"{COLONNE_ADRESSE}{ligne}"].value
            cle = normaliser_adresse(brut)
            valeurs = attendues.get(cle)
            if not valeurs:
                continue
            index = compteurs.get(cle, 0)
            compteurs[cle] = index + 1
            valeur = valeurs[min(index, len(valeurs) - 1)]

            cellule = feuille[f"{COLONNE_ID}{ligne}"]
            nouvelle = _typer(valeur)
            if cellule.value == nouvelle and type(cellule.value) is type(nouvelle):
                continue
            cellule.value = nouvelle
            nb += 1
        if nb:
            classeur.save(chemin)
        return nb
    finally:
        classeur.close()


def _typer(valeur: str):
    if valeur == "":
        return None
    return int(valeur) if valeur.isdigit() else valeur


def _toutes_les_cellules(chemin):
    ws = load_workbook(chemin).active
    return [
        [ws.cell(ligne, colonne).value for colonne in range(1, 27)]
        for ligne in range(1, (ws.max_row or 1) + 1)
    ]


def _saisies(paires):
    return [SaisieAdresse(a, v) for a, v in paires]


@pytest.mark.parametrize("adresses,valeurs_id,saisies", CAS)
def test_meme_resultat_que_l_implementation_de_reference(
    tmp_path, adresses, valeurs_id, saisies
):
    reference = str(tmp_path / "reference.xlsx")
    moteur = str(tmp_path / "moteur.xlsx")
    _ecrire(reference, adresses, valeurs_id)
    _ecrire(moteur, adresses, valeurs_id)

    config = ConfigAdresses(colonne_adresse="Adresse", colonne_id="ID erreur", ligne_entete=1)

    nb_reference = _implementation_reference(reference, saisies)
    bilan = appliquer_adresses(moteur, config, _saisies(saisies))

    assert bilan.nb_modifications == nb_reference
    assert _toutes_les_cellules(moteur) == _toutes_les_cellules(reference)


# ── Équivalence des deux chemins de lecture ───────────────────────
@pytest.mark.parametrize("adresses,valeurs_id,saisies", CAS)
def test_lecture_rapide_et_openpyxl_donnent_le_meme_resultat(
    tmp_path, monkeypatch, adresses, valeurs_id, saisies
):
    """Le repli openpyxl doit produire exactement le même classeur.

    Le repérage rapide lit le XML directement ; c'est un chemin distinct de
    celui d'openpyxl, avec ses propres pièges (entités, chaînes partagées).
    Cette comparaison croisée est le garde-fou de cette optimisation.
    """
    from sna.services import excel as module_excel
    from sna.services.lecture_rapide import LectureImpossible

    rapide = str(tmp_path / "rapide.xlsx")
    repli = str(tmp_path / "repli.xlsx")
    _ecrire(rapide, adresses, valeurs_id)
    _ecrire(repli, adresses, valeurs_id)

    config = ConfigAdresses(colonne_adresse="Adresse", colonne_id="ID erreur", ligne_entete=1)

    bilan_rapide = appliquer_adresses(rapide, config, _saisies(saisies))

    def refuser(*_args, **_kwargs):
        raise LectureImpossible("repli forcé")

    monkeypatch.setattr(module_excel, "lire_entetes", refuser)
    bilan_repli = appliquer_adresses(repli, config, _saisies(saisies))

    assert bilan_repli.nb_modifications == bilan_rapide.nb_modifications
    assert bilan_repli.adresses_trouvees == bilan_rapide.adresses_trouvees
    assert bilan_repli.nb_lignes == bilan_rapide.nb_lignes
    assert _toutes_les_cellules(repli) == _toutes_les_cellules(rapide)
