"""Modèle de configuration de la modification par adresse."""

from sna.models.config_adresses import (
    COLONNE_ADRESSE_DEFAUT, COLONNE_ID_DEFAUT, ConfigAdresses,
)


def test_valeurs_par_defaut():
    config = ConfigAdresses()

    assert config.colonne_adresse == COLONNE_ADRESSE_DEFAUT == "Adresse"
    assert config.colonne_id == COLONNE_ID_DEFAUT == "ID erreur"
    assert config.ligne_entete == 1
    assert config.harmoniser_style is True


def test_serialisation_aller_retour():
    avant = ConfigAdresses(
        colonne_adresse="Adresse postale",
        colonne_id="Identifiant erreur",
        ligne_entete=3,
        harmoniser_style=False,
    )

    assert ConfigAdresses.from_dict(avant.to_dict()) == avant


def test_cles_manquantes_reprennent_les_defauts():
    config = ConfigAdresses.from_dict({})

    assert config == ConfigAdresses()


def test_valeurs_vides_reprennent_les_defauts():
    config = ConfigAdresses.from_dict({
        "colonne_adresse": "", "colonne_id": "", "ligne_entete": None,
    })

    assert config.colonne_adresse == COLONNE_ADRESSE_DEFAUT
    assert config.colonne_id == COLONNE_ID_DEFAUT
    assert config.ligne_entete == 1
