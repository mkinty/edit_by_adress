"""Lecture / écriture de la configuration (dossier racine ET colonnes).

Tout ce qui peut varier d'un poste à l'autre est regroupé dans un unique
``config.json``, modifiable depuis l'interface :

    root_path_be     → dossier racine des fichiers audit
    config_adresses  → colonne des adresses, colonne des ID erreur, ligne
                       d'en-tête et mise en forme, construits par l'utilisateur

Il n'y a pas de configuration métier livrée par défaut : seules des valeurs de
repli structurelles (noms de colonnes usuels) sont utilisées tant que
l'utilisateur n'a rien enregistré.
"""

from __future__ import annotations

import json
import os

from .chemins import CONFIG_FILE
from .models.config_adresses import ConfigAdresses

CLE_RACINE = "root_path_be"
CLE_CONFIG = "config_adresses"

DEFAULT_CFG = {
    CLE_RACINE: "",
    CLE_CONFIG: ConfigAdresses().to_dict(),
}


# ── Fichier de configuration ──────────────────────────────────────
def load_config(config_file: str = CONFIG_FILE) -> dict:
    """Charge la configuration ; complète les clés manquantes par les défauts."""
    if os.path.isfile(config_file):
        try:
            with open(config_file, encoding="utf-8") as f:
                cfg = json.load(f)
            for cle, valeur in DEFAULT_CFG.items():
                cfg.setdefault(cle, valeur)
            return cfg
        except (OSError, json.JSONDecodeError):
            pass
    return json.loads(json.dumps(DEFAULT_CFG))  # copie profonde


def save_config(cfg: dict, config_file: str = CONFIG_FILE) -> bool:
    """Enregistre la configuration. Retourne False si l'écriture a échoué."""
    try:
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return True
    except OSError:
        return False


# ── Racine ────────────────────────────────────────────────────────
def charger_racine(cfg: dict | None = None) -> str:
    """Dossier racine des fichiers audit."""
    cfg = load_config() if cfg is None else cfg
    return str(cfg.get(CLE_RACINE) or "")


def stocker_racine(cfg: dict, racine: str) -> None:
    """Écrit la racine dans le dict de configuration (à sauvegarder ensuite)."""
    cfg[CLE_RACINE] = str(racine).strip()


# ── Colonnes ──────────────────────────────────────────────────────
def charger_config_adresses(cfg: dict) -> ConfigAdresses:
    """Extrait la configuration des colonnes du dict de configuration.

    Ce que l'utilisateur a enregistré est relu **tel quel** ; en l'absence de
    données exploitables, les valeurs de repli (« Adresse », « ID erreur »)
    sont retournées.
    """
    data = cfg.get(CLE_CONFIG)
    if not data:
        return ConfigAdresses()
    try:
        return ConfigAdresses.from_dict(data)
    except Exception:  # noqa: BLE001 — données corrompues → retour aux repères par défaut
        return ConfigAdresses()


def stocker_config_adresses(cfg: dict, config: ConfigAdresses) -> None:
    """Écrit la configuration des colonnes dans le dict (à sauvegarder ensuite)."""
    cfg[CLE_CONFIG] = config.to_dict()
