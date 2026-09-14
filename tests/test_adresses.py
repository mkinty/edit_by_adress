"""Extraction et regroupement des triplets (code INSEE, adresse, ID erreur)."""

from sna.services.adresses import (
    SaisieAdresse, extraire_saisies, grouper_par_commune, lignes_incompletes,
    normaliser_adresse, normaliser_insee,
)


# ── Extraction ────────────────────────────────────────────────────
def test_extrait_un_triplet_separe_par_des_points_virgules():
    assert extraire_saisies("06027;101 CHEMIN DES GROS BUAUX;06027_1164") == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027")
    ]


def test_extrait_un_triplet_avec_espaces_autour_des_separateurs():
    assert extraire_saisies(
        "06027 ; \t101 CHEMIN DES GROS BUAUX 06800 CAGNES SUR MER ; 06027_1164"
    ) == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX 06800 CAGNES SUR MER", "06027_1164", "06027")
    ]


def test_extrait_un_triplet_separe_par_des_tabulations():
    assert extraire_saisies("06027\t101 CHEMIN DES GROS BUAUX\t06027_1164") == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027")
    ]


def test_extrait_un_triplet_separe_par_des_fleches():
    assert extraire_saisies("06027 -> 101 CHEMIN DES GROS BUAUX -> 06027_1164") == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027")
    ]


def test_code_insee_corse():
    assert extraire_saisies("2A004;5 place Bellecour;2A004_3") == [
        SaisieAdresse("5 place Bellecour", "2A004_3", "2A004")
    ]


def test_adresse_contenant_un_point_virgule_reste_intacte():
    """Le 1er séparateur isole l'INSEE, le dernier la valeur : le milieu est intact."""
    assert extraire_saisies("06027;12 rue A; Bat B;06027_1") == [
        SaisieAdresse("12 rue A; Bat B", "06027_1", "06027")
    ]


def test_plusieurs_lignes():
    texte = (
        "06027;101 CHEMIN DES GROS BUAUX;06027_1164\n"
        "75020;20 avenue Foch;75020_4"
    )
    assert extraire_saisies(texte) == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027"),
        SaisieAdresse("20 avenue Foch", "75020_4", "75020"),
    ]


def test_lignes_vides_ignorees():
    texte = "\n\n06027;101 CHEMIN DES GROS BUAUX;06027_1164\n\n"
    assert extraire_saisies(texte) == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027")
    ]


def test_ligne_d_entete_copiee_avec_les_donnees_est_ignoree():
    texte = "Code INSEE;Adresse;ID erreur\n06027;101 CHEMIN DES GROS BUAUX;06027_1164"
    assert extraire_saisies(texte) == [
        SaisieAdresse("101 CHEMIN DES GROS BUAUX", "06027_1164", "06027")
    ]
    assert lignes_incompletes(texte) == []


# ── Lignes incomplètes ──────────────────────────────────────────────
def test_code_insee_invalide_rend_la_ligne_incomplete():
    assert lignes_incompletes("1234;12 rue A;06027_1") == ["1234;12 rue A;06027_1"]
    assert extraire_saisies("1234;12 rue A;06027_1") == []


def test_un_seul_separateur_est_incomplet():
    assert lignes_incompletes("06027;12 rue A") == ["06027;12 rue A"]
    assert extraire_saisies("06027;12 rue A") == []


def test_membre_vide_est_incomplet():
    assert lignes_incompletes("06027;;06027_1") == ["06027;;06027_1"]
    assert lignes_incompletes("06027;12 rue A;") == ["06027;12 rue A;"]


def test_triplet_complet_n_est_pas_signale_comme_incomplet():
    assert lignes_incompletes("06027;12 rue A;06027_1") == []


# ── Normalisation ─────────────────────────────────────────────────
def test_normalisation_adresse_tolere_espaces_multiples_et_casse():
    assert normaliser_adresse("  12  rue de la Paix ") == "12 RUE DE LA PAIX"
    assert normaliser_adresse("12 rue de la paix") == "12 RUE DE LA PAIX"
    assert normaliser_adresse(None) == ""


def test_normalisation_insee_tolere_espaces_et_casse():
    assert normaliser_insee(" 2a004 ") == "2A004"
    assert normaliser_insee(None) == ""


# ── Regroupement par commune ───────────────────────────────────────
def test_groupe_par_code_insee():
    saisies = [
        SaisieAdresse("12 rue de la Paix", "13001_1", "13001"),
        SaisieAdresse("20 avenue Foch", "75020_4", "75020"),
        SaisieAdresse("5 place Bellecour", "13001_9", "13001"),
    ]

    groupes = grouper_par_commune(saisies)

    assert groupes == {
        "13001": [SaisieAdresse("12 rue de la Paix", "13001_1", "13001"),
                  SaisieAdresse("5 place Bellecour", "13001_9", "13001")],
        "75020": [SaisieAdresse("20 avenue Foch", "75020_4", "75020")],
    }


def test_ordre_d_apparition_preserve():
    saisies = [
        SaisieAdresse("adresse B", "75020_1", "75020"),
        SaisieAdresse("adresse A", "13001_1", "13001"),
    ]

    groupes = grouper_par_commune(saisies)

    assert list(groupes) == ["75020", "13001"]
