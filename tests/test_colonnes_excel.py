"""Détection des colonnes et résolution des références."""

from datetime import datetime

from sna.services.colonnes_excel import (
    TYPE_DATE, TYPE_NUM, TYPE_TEXTE,
    detecter_colonnes, index_par_reference, resoudre_colonne, to_num,
)


def test_detecte_les_noms_et_lettres(creer_classeur):
    chemin = creer_classeur({"A": ["rue A"], "B": [3], "Z": ["non"]})

    colonnes = detecter_colonnes(chemin)

    assert [c.nom for c in colonnes] == [
        "Adresse", "Audit - Nb BAL", "ID erreur", "Audit - Street View",
    ]
    assert [c.lettre for c in colonnes] == ["A", "B", "C", "Z"]


def test_deduit_le_type_des_colonnes(creer_classeur):
    chemin = creer_classeur({"A": ["rue A", "rue B"], "B": [3, 7], "Z": ["oui", "non"]})

    types = {c.nom: c.type for c in detecter_colonnes(chemin)}

    assert types["Audit - Nb BAL"] == TYPE_NUM
    assert types["Adresse"] == TYPE_TEXTE
    assert types["Audit - Street View"] == TYPE_TEXTE


def test_ligne_entete_personnalisee(creer_classeur):
    chemin = creer_classeur({"A": ["Libellé", "rue A"]}, entetes={})

    colonnes = detecter_colonnes(chemin, ligne_entete=2)

    assert [c.nom for c in colonnes] == ["Libellé"]


def test_fichier_absent_retourne_liste_vide(tmp_path):
    assert detecter_colonnes(str(tmp_path / "absent.xlsx")) == []


def test_resolution_par_nom_lettre_et_forme_normalisee(creer_classeur):
    chemin = creer_classeur({"Z": ["x"]})
    table = index_par_reference(detecter_colonnes(chemin))

    assert resoudre_colonne("Audit - Street View", table) == 26
    assert resoudre_colonne("audit-streetview", table) == 26
    assert resoudre_colonne("Z", table) == 26


def test_resolution_d_une_lettre_sans_entete(creer_classeur):
    """Une colonne sans en-tête reste adressable par sa lettre."""
    chemin = creer_classeur({"Z": ["x"]})
    table = index_par_reference(detecter_colonnes(chemin))

    assert resoudre_colonne("AA", table) == 27
    assert resoudre_colonne("Colonne inexistante", table) is None
    assert resoudre_colonne("", table) is None


def test_le_nom_d_entete_prime_sur_la_lettre(creer_classeur):
    """Une colonne nommée « Z » placée en A doit gagner sur la lettre Z."""
    chemin = creer_classeur({"A": ["x"]}, entetes={"A": "Z"})
    table = index_par_reference(detecter_colonnes(chemin))

    assert resoudre_colonne("Z", table) == 1


def test_conversion_numerique():
    assert to_num("3,5") == 3.5
    assert to_num(7) == 7.0
    assert to_num("abc") is None
    assert to_num(None) is None
    assert to_num(True) is None  # un booléen n'est pas un nombre exploitable ici


def test_un_id_erreur_n_est_pas_un_nombre():
    """``float("13001_2")`` vaut 130012.0 en Python : le piège est écarté ici."""
    assert to_num("13001_2") is None
    assert to_num("1_0") is None


def test_les_valeurs_non_finies_ne_sont_pas_des_nombres():
    assert to_num("nan") is None
    assert to_num("inf") is None
    assert to_num("-Infinity") is None


def test_une_date_n_est_pas_un_nombre():
    assert to_num(datetime(2026, 3, 12)) is None


def test_colonne_de_dates_detectee_par_l_entete(creer_classeur):
    chemin = creer_classeur({"A": ["12/03/2026"]}, entetes={"A": "Date de visite"})

    assert detecter_colonnes(chemin)[0].type == TYPE_DATE


def test_colonne_de_dates_detectee_par_les_valeurs(creer_classeur):
    chemin = creer_classeur(
        {"A": [datetime(2026, 3, 12), datetime(2026, 4, 1)]}, entetes={"A": "Visite"}
    )

    assert detecter_colonnes(chemin)[0].type == TYPE_DATE


def test_colonne_d_ids_reste_du_texte(creer_classeur):
    chemin = creer_classeur({"C": ["13001_1", "13001_2"]}, entetes={"C": "ID erreur"})

    assert detecter_colonnes(chemin)[0].type == TYPE_TEXTE
