"""Emplacement du fichier de configuration.

Deux modes :
    - développement (script Python)      → config.json à la racine du projet ;
    - application packagée (PyInstaller) → config.json dans le dossier de
      données utilisateur de l'OS, le dossier du programme étant en lecture
      seule ou temporaire.
"""

from __future__ import annotations

import os
import sys

APP_NAME = "excel_rule_editor"

RACINE_PROJET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _dossier_donnees() -> str:
    """Dossier où stocker la configuration, adapté au mode d'exécution."""
    if not getattr(sys, "frozen", False):
        return RACINE_PROJET

    if sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")

    dossier = os.path.join(base, APP_NAME)
    os.makedirs(dossier, exist_ok=True)
    return dossier


CONFIG_FILE = os.path.join(_dossier_donnees(), "config.json")
