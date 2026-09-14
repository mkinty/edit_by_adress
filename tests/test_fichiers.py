"""Localisation des fichiers audit sous la racine."""

from sna.services.fichiers import (
    lister_communes, trouver_fichier_audit, trouver_fichier_exemple,
)


def _creer_audit(racine, departement, commune, nom="audit_{c}.xlsx"):
    dossier = racine / departement / commune
    dossier.mkdir(parents=True, exist_ok=True)
    fichier = dossier / nom.format(c=commune)
    fichier.write_text("x")
    return fichier


def test_trouve_le_fichier_audit(tmp_path):
    fichier = _creer_audit(tmp_path, "Dep13", "13001")
    (tmp_path / "Dep13" / "13001" / "autre.xlsx").write_text("x")

    assert trouver_fichier_audit(str(tmp_path), "13001") == str(fichier)


def test_dossier_commune_absent(tmp_path):
    assert trouver_fichier_audit(str(tmp_path), "99999") is None


def test_aucun_fichier_audit(tmp_path):
    dossier = tmp_path / "Dep13" / "13001"
    dossier.mkdir(parents=True)
    (dossier / "rapport.xlsx").write_text("x")

    assert trouver_fichier_audit(str(tmp_path), "13001") is None


def test_code_insensible_a_la_casse_et_espaces(tmp_path):
    fichier = _creer_audit(tmp_path, "Dep2A", "2A004")

    assert trouver_fichier_audit(str(tmp_path), " 2a004 ") == str(fichier)


def test_liste_les_communes_de_tous_les_departements(tmp_path):
    _creer_audit(tmp_path, "Dep13", "13001")
    _creer_audit(tmp_path, "Dep75", "75020")
    (tmp_path / "hors_arborescence").mkdir()

    assert lister_communes(str(tmp_path)) == ["13001", "75020"]


def test_fichier_exemple_pour_les_menus_deroulants(tmp_path):
    fichier = _creer_audit(tmp_path, "Dep13", "13001")
    _creer_audit(tmp_path, "Dep75", "75020")

    assert trouver_fichier_exemple(str(tmp_path)) == str(fichier)


def test_fichier_exemple_absent(tmp_path):
    (tmp_path / "Dep13" / "13001").mkdir(parents=True)

    assert trouver_fichier_exemple(str(tmp_path)) is None


def test_racine_inexistante_ne_leve_pas(tmp_path):
    absent = str(tmp_path / "nulle_part")

    assert lister_communes(absent) == []
    assert trouver_fichier_exemple(absent) is None
