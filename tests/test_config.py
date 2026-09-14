"""Persistance de la configuration : racine et colonnes."""

import json

from sna.config import (
    charger_config_adresses, charger_racine, load_config, save_config,
    stocker_config_adresses, stocker_racine,
)
from sna.models.config_adresses import ConfigAdresses


def test_defauts_quand_le_fichier_est_absent(tmp_path):
    cfg = load_config(str(tmp_path / "absent.json"))

    assert charger_racine(cfg) == ""
    assert charger_config_adresses(cfg) == ConfigAdresses()


def test_racine_et_config_persistent(tmp_path):
    fichier = str(tmp_path / "config.json")
    cfg = load_config(fichier)
    config = ConfigAdresses(
        colonne_adresse="Adresse postale", colonne_id="Identifiant erreur", ligne_entete=2,
    )

    stocker_racine(cfg, r"D:\audits")
    stocker_config_adresses(cfg, config)
    assert save_config(cfg, fichier) is True

    relu = load_config(fichier)
    assert charger_racine(relu) == r"D:\audits"
    assert charger_config_adresses(relu) == config


def test_la_config_enregistree_est_relue_telle_quelle(tmp_path):
    fichier = tmp_path / "config.json"
    fichier.write_text(
        json.dumps({
            "root_path_be": "X",
            "config_adresses": {
                "colonne_adresse": "Adresse", "colonne_id": "Audit",
                "ligne_entete": 1, "harmoniser_style": False,
            },
        }),
        encoding="utf-8",
    )

    config = charger_config_adresses(load_config(str(fichier)))

    assert config.colonne_id == "Audit"
    assert config.harmoniser_style is False


def test_json_corrompu_retombe_sur_les_defauts(tmp_path):
    fichier = tmp_path / "config.json"
    fichier.write_text("{ ceci n'est pas du JSON", encoding="utf-8")

    assert charger_racine(load_config(str(fichier))) == ""


def test_config_corrompue_retombe_sur_les_defauts(tmp_path):
    fichier = tmp_path / "config.json"
    fichier.write_text(
        json.dumps({"root_path_be": "X", "config_adresses": "inattendu"}),
        encoding="utf-8",
    )
    cfg = load_config(str(fichier))

    assert charger_config_adresses(cfg) == ConfigAdresses()


def test_cles_manquantes_sont_completees(tmp_path):
    fichier = tmp_path / "config.json"
    fichier.write_text(json.dumps({"root_path_be": "X"}), encoding="utf-8")

    cfg = load_config(str(fichier))

    assert charger_racine(cfg) == "X"
    assert charger_config_adresses(cfg) == ConfigAdresses()
