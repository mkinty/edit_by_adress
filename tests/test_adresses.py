"""Extraction et regroupement des paires (adresse, ID erreur) saisies."""

from sna.services.adresses import (
    SaisieAdresse, extraire_saisies, grouper_par_commune, lignes_incompletes,
    normaliser_adresse,
)


# ── Extraction ────────────────────────────────────────────────────
def test_extrait_une_paire_separee_par_une_tabulation():
    assert extraire_saisies("12 rue de la Paix\t13001_1") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]


def test_extrait_une_paire_separee_par_un_point_virgule():
    assert extraire_saisies("12 rue de la Paix;13001_1") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]


def test_extrait_une_paire_separee_par_une_fleche():
    assert extraire_saisies("12 rue de la Paix -> 13001_1") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]
    assert extraire_saisies("12 rue de la Paix => 13001_1") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]


def test_ordre_id_erreur_puis_adresse_reconnu_automatiquement():
    """Les deux colonnes peuvent être collées dans n'importe quel ordre."""
    assert extraire_saisies("13001_1\t12 rue de la Paix") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]
    assert extraire_saisies("2A004_3;5 place Bellecour") == [
        SaisieAdresse("5 place Bellecour", "2A004_3")
    ]


def test_les_deux_ordres_melanges_dans_le_meme_texte():
    texte = "13001_1\t12 rue de la Paix\n20 avenue Foch\t75020_4"
    assert extraire_saisies(texte) == [
        SaisieAdresse("12 rue de la Paix", "13001_1"),
        SaisieAdresse("20 avenue Foch", "75020_4"),
    ]


def test_aucun_membre_ne_ressemble_a_un_id_garde_l_ordre_par_defaut():
    """Ni l'un ni l'autre ne ressemble à un ID erreur : adresse d'abord, par défaut."""
    assert extraire_saisies("Rue Sans Nom\tCommentaire libre") == [
        SaisieAdresse("Rue Sans Nom", "Commentaire libre")
    ]


def test_ligne_d_entete_copiee_avec_les_donnees_est_ignoree():
    texte = "ID erreur\tAdresse\n13001_1\t12 rue de la Paix"
    assert extraire_saisies(texte) == [SaisieAdresse("12 rue de la Paix", "13001_1")]
    assert lignes_incompletes(texte) == []
    # dans l'autre ordre aussi
    assert extraire_saisies("Adresse;ID erreur\n13001_1;12 rue de la Paix") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]


def test_plusieurs_lignes():
    texte = "12 rue de la Paix\t13001_1\n20 avenue Foch\t75020_4"
    assert extraire_saisies(texte) == [
        SaisieAdresse("12 rue de la Paix", "13001_1"),
        SaisieAdresse("20 avenue Foch", "75020_4"),
    ]


def test_lignes_vides_ignorees():
    assert extraire_saisies("\n\n12 rue de la Paix\t13001_1\n\n") == [
        SaisieAdresse("12 rue de la Paix", "13001_1")
    ]


def test_seul_le_premier_separateur_coupe_la_ligne():
    """La valeur n'est jamais re-coupée, même si elle contient un séparateur."""
    assert extraire_saisies("12 rue A\t13001_1; commentaire") == [
        SaisieAdresse("12 rue A", "13001_1; commentaire")
    ]


# ── Lignes incomplètes ──────────────────────────────────────────────
def test_ligne_sans_separateur_est_incomplete():
    assert lignes_incompletes("12 rue de la Paix") == ["12 rue de la Paix"]
    assert extraire_saisies("12 rue de la Paix") == []


def test_ligne_avec_membre_vide_est_incomplete():
    """Le membre manquant est ignoré ; la ligne reste néanmoins incomplète."""
    assert lignes_incompletes("12 rue de la Paix\t") == ["12 rue de la Paix"]
    assert lignes_incompletes("\t13001_1") == ["13001_1"]


def test_ligne_complete_n_est_pas_signalee_comme_incomplete():
    assert lignes_incompletes("12 rue de la Paix\t13001_1") == []


# ── Normalisation ─────────────────────────────────────────────────
def test_normalisation_tolere_espaces_multiples_et_casse():
    assert normaliser_adresse("  12  rue de la Paix ") == "12 RUE DE LA PAIX"
    assert normaliser_adresse("12 rue de la paix") == "12 RUE DE LA PAIX"
    assert normaliser_adresse(None) == ""


# ── Regroupement par commune ───────────────────────────────────────
def test_groupe_par_code_insee_resolu():
    saisies = [
        SaisieAdresse("12 rue de la Paix", "13001_1"),
        SaisieAdresse("20 avenue Foch", "75020_4"),
        SaisieAdresse("5 place Bellecour", "13001_9"),
    ]
    codes = {
        "12 rue de la Paix": "13001",
        "20 avenue Foch": "75020",
        "5 place Bellecour": "13001",
    }

    groupes, non_resolues = grouper_par_commune(saisies, codes)

    assert groupes == {
        "13001": [SaisieAdresse("12 rue de la Paix", "13001_1"),
                  SaisieAdresse("5 place Bellecour", "13001_9")],
        "75020": [SaisieAdresse("20 avenue Foch", "75020_4")],
    }
    assert non_resolues == []


def test_adresses_sans_code_insee_sont_ecartees():
    saisies = [
        SaisieAdresse("12 rue de la Paix", "13001_1"),
        SaisieAdresse("adresse introuvable", "99999_1"),
    ]
    codes = {"12 rue de la Paix": "13001", "adresse introuvable": None}

    groupes, non_resolues = grouper_par_commune(saisies, codes)

    assert groupes == {"13001": [SaisieAdresse("12 rue de la Paix", "13001_1")]}
    assert non_resolues == [SaisieAdresse("adresse introuvable", "99999_1")]


def test_adresse_absente_du_dictionnaire_est_non_resolue():
    saisies = [SaisieAdresse("adresse non interrogee", "1_1")]

    groupes, non_resolues = grouper_par_commune(saisies, {})

    assert groupes == {}
    assert non_resolues == saisies


def test_ordre_d_apparition_preserve():
    saisies = [
        SaisieAdresse("adresse B", "75020_1"),
        SaisieAdresse("adresse A", "13001_1"),
    ]
    codes = {"adresse B": "75020", "adresse A": "13001"}

    groupes, _ = grouper_par_commune(saisies, codes)

    assert list(groupes) == ["75020", "13001"]
