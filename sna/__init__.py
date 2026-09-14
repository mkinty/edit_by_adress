"""Projet SNA — Modification des fichiers audit Excel par adresse.

L'utilisateur saisit des triplets (code INSEE, adresse, nouvel ID erreur) ;
le programme en déduit les communes concernées, ouvre le fichier audit de
chacune, et écrit dans la colonne « ID erreur » des lignes dont l'adresse
correspond la valeur associée.

Le package est volontairement découpé en couches indépendantes :

    sna.chemins           → emplacement du fichier de configuration
    sna.config            → chargement/sauvegarde (dossier racine + colonnes)
    sna.models            → structures de données (configuration, résultat, statut)
    sna.services          → logique métier, sans aucune dépendance à l'interface
    sna.ui                → interface graphique Tkinter (thème, panneau, fenêtre)

Aucun import de l'interface n'est fait ici afin que la couche métier reste
importable et testable sans environnement graphique.
"""

__version__ = "4.0.0"
