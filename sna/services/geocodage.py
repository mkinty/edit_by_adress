"""Résolution du code INSEE d'une adresse via l'API Adresse (BAN, data.gouv.fr).

Une adresse saisie par l'utilisateur ne porte pas de code INSEE en elle-même —
contrairement à l'ancien ID erreur, qui l'incluait en préfixe (``13001_1``) —
il faut l'interroger auprès d'un service de géocodage. Le programme utilise
l'API Adresse officielle (https://api-adresse.data.gouv.fr), gratuite et sans
clé, qui retourne notamment le ``citycode`` (code INSEE) de la commune la plus
probable pour une adresse en texte libre.

Une adresse introuvable ou trop ambiguë n'est pas une erreur fatale : le code
INSEE correspondant vaut simplement ``None``, à charge de l'appelant de la
signaler comme non résolue.
"""

from __future__ import annotations

from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
import json
import urllib.error
import urllib.parse
import urllib.request

URL_RECHERCHE = "https://api-adresse.data.gouv.fr/search/"
DELAI_DEFAUT = 8.0
PARALLELISME = 8


class ErreurGeocodage(Exception):
    """La requête vers l'API Adresse a échoué (réseau, service indisponible…).

    Distincte d'une adresse simplement non trouvée, qui retourne ``None``
    sans lever d'exception.
    """


def code_insee_pour_adresse(adresse: str, timeout: float = DELAI_DEFAUT) -> str | None:
    """Code INSEE de la commune la plus probable pour une adresse.

    Args:
        adresse: adresse en texte libre (numéro, rue, ville…).
        timeout: délai maximal de la requête HTTP, en secondes.

    Returns:
        Le code INSEE (``citycode``) du meilleur résultat, ou ``None`` si
        l'adresse ne trouve aucune correspondance.

    Raises:
        ErreurGeocodage: si la requête elle-même échoue (réseau, service HTTP
            en erreur, réponse illisible).
    """
    adresse = adresse.strip()
    if not adresse:
        return None

    parametres = urllib.parse.urlencode({"q": adresse, "limit": 1, "autocomplete": 0})
    requete = urllib.request.Request(f"{URL_RECHERCHE}?{parametres}")
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise ErreurGeocodage(f"géocodage de « {adresse} » impossible : {exc}") from exc

    resultats = donnees.get("features") or []
    if not resultats:
        return None
    return resultats[0].get("properties", {}).get("citycode") or None


def codes_insee_pour_adresses(
    adresses: Iterable[str], timeout: float = DELAI_DEFAUT,
) -> dict[str, str | None]:
    """Résout plusieurs adresses en parallèle (jusqu'à ``PARALLELISME`` à la fois).

    Args:
        adresses: adresses à résoudre (les doublons sont dédoublonnés).
        timeout: délai maximal de chaque requête HTTP, en secondes.

    Returns:
        ``{adresse: code_insee | None}`` — une entrée par adresse fournie,
        ``None`` quand l'adresse ne trouve aucune correspondance.

    Raises:
        ErreurGeocodage: si l'une des requêtes échoue.
    """
    uniques = list(dict.fromkeys(a.strip() for a in adresses if a.strip()))
    if not uniques:
        return {}

    with ThreadPoolExecutor(max_workers=min(PARALLELISME, len(uniques))) as executeur:
        resultats = list(
            executeur.map(lambda a: code_insee_pour_adresse(a, timeout), uniques)
        )

    return dict(zip(uniques, resultats))
