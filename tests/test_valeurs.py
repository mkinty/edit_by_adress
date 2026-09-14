"""Typage de la saisie, dates, et détection des écritures inutiles."""

from datetime import date, datetime

from sna.services.valeurs import (
    analyser_date, est_format_date, formater_date, memes_valeurs, valeur_a_ecrire,
)


# ── Typage ────────────────────────────────────────────────────────
def test_texte_conserve_tel_quel():
    assert valeur_a_ecrire("Vérification RT impossible") == "Vérification RT impossible"


def test_saisie_vide_efface_la_cellule():
    assert valeur_a_ecrire("") is None
    assert valeur_a_ecrire(None) is None


def test_entier_ecrit_comme_entier():
    valeur = valeur_a_ecrire("42")

    assert valeur == 42 and isinstance(valeur, int)


def test_decimal_ecrit_comme_nombre():
    assert valeur_a_ecrire("3,5") == 3.5
    assert valeur_a_ecrire("3.5") == 3.5


def test_espaces_seuls_restent_du_texte():
    assert valeur_a_ecrire(" ") == " "


# ── Comparaison ───────────────────────────────────────────────────
def test_valeurs_identiques():
    assert memes_valeurs("a", "a")
    assert memes_valeurs(None, None)
    assert memes_valeurs(12, 12)


def test_valeurs_differentes():
    assert not memes_valeurs("a", "b")
    assert not memes_valeurs(None, "")
    assert not memes_valeurs("12", 12)  # le type compte : Excel les distingue


# ── Dates ─────────────────────────────────────────────────────────
def test_formats_de_date_acceptes():
    attendu = datetime(2026, 3, 12)

    for saisie in ("12/03/2026", "12-03-2026", "12.03.2026", "2026-03-12", "12/03/26"):
        assert analyser_date(saisie) == attendu, saisie


def test_date_avec_heure():
    assert analyser_date("12/03/2026 08:30") == datetime(2026, 3, 12, 8, 30)


def test_saisie_non_datee():
    assert analyser_date("à revoir") is None
    assert analyser_date("32/13/2026") is None
    assert analyser_date("") is None


def test_objets_dates_acceptes_tels_quels():
    assert analyser_date(datetime(2026, 3, 12, 9, 0)) == datetime(2026, 3, 12, 9, 0)
    assert analyser_date(date(2026, 3, 12)) == datetime(2026, 3, 12)


def test_forme_affichee():
    assert formater_date(datetime(2026, 3, 12)) == "12/03/2026"


def test_colonne_de_dates_ecrit_un_objet_date():
    assert valeur_a_ecrire("12/03/2026", en_date=True) == datetime(2026, 3, 12)


def test_colonne_de_dates_conserve_le_texte_non_date():
    """Un nombre nu n'aurait aucun sens dans une colonne de dates."""
    assert valeur_a_ecrire("42", en_date=True) == "42"
    assert valeur_a_ecrire("à revoir", en_date=True) == "à revoir"


def test_hors_colonne_de_dates_une_date_reste_du_texte():
    assert valeur_a_ecrire("12/03/2026") == "12/03/2026"


def test_reconnaissance_des_formats_d_affichage_de_date():
    assert est_format_date("DD/MM/YYYY") is True
    assert est_format_date("yyyy-mm-dd hh:mm") is True
    assert est_format_date("General") is False
    assert est_format_date("0.00") is False
    assert est_format_date(None) is False
