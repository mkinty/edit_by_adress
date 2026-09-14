"""Valeurs écrites dans les cellules : typage de la saisie, dates, mise en forme.

Ce module ne dépend que d'openpyxl pour la recopie de style ; le typage lui-même
raisonne sur des valeurs Python et reste testable sans fichier Excel.

Trois responsabilités :
    - convertir la saisie utilisateur en valeur de cellule (texte, nombre, date) ;
    - éviter les écritures inutiles (valeur déjà en place) ;
    - donner à la cellule écrite la **même forme** que les valeurs déjà
      présentes dans sa colonne (police, taille, alignement, format d'affichage).
"""

from __future__ import annotations

from copy import copy
from datetime import date, datetime
from typing import Any

from .colonnes_excel import to_num

# Formats acceptés en saisie, du plus courant au plus rare.
FORMATS_DATE = (
    "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%d/%m/%y",
    "%Y-%m-%d", "%Y/%m/%d",
    "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M",
)

# Format d'affichage appliqué à une date écrite dans une colonne sans format.
FORMAT_DATE_DEFAUT = "DD/MM/YYYY"

# Format d'une cellule qui n'a reçu aucune mise en forme particulière.
_FORMAT_GENERAL = "General"


# ── Dates ─────────────────────────────────────────────────────────
def analyser_date(valeur) -> datetime | None:
    """Interprète une saisie comme une date, ou retourne ``None``.

    Accepte les séparateurs ``/``, ``-`` et ``.``, l'année sur 2 ou 4 chiffres,
    l'ordre français comme l'ordre ISO, avec ou sans heure.
    """
    if isinstance(valeur, datetime):
        return valeur
    if isinstance(valeur, date):
        return datetime(valeur.year, valeur.month, valeur.day)

    texte = "" if valeur is None else str(valeur).strip()
    if not texte:
        return None
    for forme in FORMATS_DATE:
        try:
            return datetime.strptime(texte, forme)
        except ValueError:
            continue
    return None


def formater_date(moment: datetime | date) -> str:
    """Forme canonique affichée dans l'interface (``JJ/MM/AAAA``)."""
    return moment.strftime("%d/%m/%Y")


def est_format_date(number_format: str | None) -> bool:
    """Vrai si un format de nombre Excel affiche une date ou une heure.

    Heuristique volontairement large : un format contenant un jour, un mois,
    une année ou une heure est traité comme un format de date.
    """
    if not number_format or number_format == _FORMAT_GENERAL:
        return False
    return any(marque in number_format.lower() for marque in ("y", "d", "h", "m/", "mm/"))


# ── Typage de la saisie ───────────────────────────────────────────
def valeur_a_ecrire(valeur: str, en_date: bool = False) -> Any:
    """Convertit la saisie utilisateur en valeur de cellule.

    - saisie vide → ``None``, la cellule est effacée ;
    - colonne de dates (``en_date``) → objet ``datetime`` si la saisie est une
      date ; sinon le texte est conservé tel quel, jamais transformé en nombre
      (un nombre nu n'aurait aucun sens dans une colonne de dates) ;
    - saisie numérique → nombre (sans quoi Excel afficherait un texte marqué
      d'un triangle d'avertissement) ;
    - sinon → texte inchangé.
    """
    texte = "" if valeur is None else str(valeur)
    if texte == "":
        return None

    if en_date:
        moment = analyser_date(texte)
        return moment if moment is not None else texte

    nombre = to_num(texte)
    if nombre is None:
        return texte
    entier = nombre.is_integer() and "." not in texte and "," not in texte
    return int(nombre) if entier else nombre


def memes_valeurs(a: Any, b: Any) -> bool:
    """Égalité stricte utilisée pour savoir si une écriture change la cellule.

    Évite de réécrire (et donc de sauvegarder) un fichier lorsque la
    modification inscrit une valeur déjà présente. La comparaison tient compte du type :
    ``12`` et ``"12"`` sont considérés différents, car Excel les affiche et les
    trie différemment.
    """
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return type(a) is type(b) and a == b


# ── Mise en forme ─────────────────────────────────────────────────
def harmoniser_forme(cellule, modele, police_secours=None) -> None:
    """Donne à ``cellule`` la forme des valeurs déjà présentes dans le classeur.

    Sont repris du modèle la **police** (nom, taille, gras, italique, couleur),
    l'**alignement** et le **format d'affichage**. Le fond et les bordures de la
    cellule écrite sont volontairement laissés intacts : ils servent souvent à
    signaler une anomalie ligne par ligne, et les recopier écraserait cette
    information.

    ``police_secours`` sert quand la colonne visée est **entièrement vide** —
    cas normal des colonnes Audit, Date audit, Auditeur et Validation finale,
    qu'on remplit précisément parce qu'elles ne le sont pas. Sans elle, la
    valeur écrite garderait la police par défaut d'openpyxl (Calibri 11) et
    détonnerait dans un classeur composé en Calibri 10.
    """
    if modele is not None:
        cellule.font = copy(modele.font)
        cellule.alignment = copy(modele.alignment)
        cellule.number_format = modele.number_format
    elif police_secours is not None:
        cellule.font = copy(police_secours)


def assurer_format_date(cellule, format_reference: str | None) -> None:
    """Garantit qu'une date écrite s'affiche comme une date, pas comme un nombre.

    ``format_reference`` est le format que la colonne impose réellement : celui
    du modèle de mise en forme, ou celui que portait la cellule avant écriture.
    S'il affiche déjà une date, il est conservé — un classeur qui affiche
    « 12 mars 2026 » doit continuer de le faire. Sinon, le format français par
    défaut est appliqué : openpyxl retomberait autrement sur un format ISO avec
    heure (``yyyy-mm-dd h:mm:ss``), inattendu dans un livrable.
    """
    if not est_format_date(format_reference):
        cellule.number_format = FORMAT_DATE_DEFAUT
