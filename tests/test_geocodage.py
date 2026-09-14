"""Résolution du code INSEE d'une adresse via l'API Adresse (mockée)."""

import json
import urllib.error

import pytest

from sna.services import geocodage
from sna.services.geocodage import (
    ErreurGeocodage, code_insee_pour_adresse, codes_insee_pour_adresses,
)


class _FausseReponse:
    def __init__(self, donnees: dict):
        self._corps = json.dumps(donnees).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *_exc):
        return False

    def read(self):
        return self._corps


def _reponse_avec_citycode(citycode: str):
    return _FausseReponse({"features": [{"properties": {"citycode": citycode}}]})


def _reponse_sans_resultat():
    return _FausseReponse({"features": []})


# ── Une adresse ───────────────────────────────────────────────────
def test_adresse_vide_ne_fait_aucun_appel(monkeypatch):
    def echoue(*_args, **_kwargs):
        raise AssertionError("ne doit pas être appelé")

    monkeypatch.setattr(geocodage.urllib.request, "urlopen", echoue)

    assert code_insee_pour_adresse("   ") is None


def test_code_insee_retourne_pour_une_adresse_trouvee(monkeypatch):
    monkeypatch.setattr(
        geocodage.urllib.request, "urlopen",
        lambda *a, **k: _reponse_avec_citycode("13001"),
    )

    assert code_insee_pour_adresse("12 rue de la Paix, Marseille") == "13001"


def test_aucun_resultat_retourne_none(monkeypatch):
    monkeypatch.setattr(
        geocodage.urllib.request, "urlopen", lambda *a, **k: _reponse_sans_resultat(),
    )

    assert code_insee_pour_adresse("adresse totalement inconnue") is None


def test_erreur_reseau_leve_erreur_geocodage(monkeypatch):
    def echoue(*_args, **_kwargs):
        raise urllib.error.URLError("pas de réseau")

    monkeypatch.setattr(geocodage.urllib.request, "urlopen", echoue)

    with pytest.raises(ErreurGeocodage):
        code_insee_pour_adresse("12 rue de la Paix")


def test_reponse_illisible_leve_erreur_geocodage(monkeypatch):
    class ReponseInvalide:
        def __enter__(self):
            return self

        def __exit__(self, *_exc):
            return False

        def read(self):
            return b"pas du JSON"

    monkeypatch.setattr(geocodage.urllib.request, "urlopen", lambda *a, **k: ReponseInvalide())

    with pytest.raises(ErreurGeocodage):
        code_insee_pour_adresse("12 rue de la Paix")


# ── Plusieurs adresses ──────────────────────────────────────────────
def test_resout_plusieurs_adresses(monkeypatch):
    codes = {"12 rue de la Paix": "13001", "20 avenue Foch": "75020", "inconnue": None}
    monkeypatch.setattr(
        geocodage, "code_insee_pour_adresse", lambda a, timeout=8.0: codes[a]
    )

    resultat = codes_insee_pour_adresses(list(codes))

    assert resultat == codes


def test_adresses_vides_ou_en_double_dedupliquees(monkeypatch):
    appels = []

    def resoudre(adresse, timeout=8.0):
        appels.append(adresse)
        return "13001"

    monkeypatch.setattr(geocodage, "code_insee_pour_adresse", resoudre)

    resultat = codes_insee_pour_adresses(["a", "a", "  ", "b"])

    assert resultat == {"a": "13001", "b": "13001"}
    assert sorted(appels) == ["a", "b"]


def test_liste_vide_ne_fait_aucun_appel(monkeypatch):
    def echoue(*_args, **_kwargs):
        raise AssertionError("ne doit pas être appelé")

    monkeypatch.setattr(geocodage, "code_insee_pour_adresse", echoue)

    assert codes_insee_pour_adresses([]) == {}
