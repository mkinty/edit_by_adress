"""
Point d'entrée — Modification des fichiers Excel par adresse (Projet SNA)

Lance l'interface graphique : l'utilisateur y colle des triplets
(code INSEE, adresse, nouvel ID erreur), le programme en déduit les communes
concernées, ouvre leur fichier audit et écrit dans la colonne « ID erreur »
des lignes dont l'adresse correspond la valeur associée.

Usage :
    python main.py
"""

from sna.ui.application import Application


def main() -> None:
    Application().mainloop()


if __name__ == "__main__":
    main()
