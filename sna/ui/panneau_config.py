"""Panneau « Configuration » — colonnes utilisées pour la modification par adresse.

Une seule opération est possible : pour chaque ligne dont la colonne
« Adresse » correspond à l'une des adresses saisies, écrire dans la colonne
« ID erreur » la valeur qui lui est associée dans la saisie. Ce panneau ne
fait donc que désigner :

    - la colonne comparée aux adresses saisies ;
    - la colonne écrite avec la valeur d'ID erreur ;
    - la ligne d'en-tête du classeur ;
    - si la mise en forme (police, format) de la colonne écrite doit être
      reprise des valeurs déjà présentes dans cette colonne.

Les colonnes sont détectées automatiquement dans un fichier audit de la racine
(``<racine>/Dep<XX>/<insee>/audit_*.xlsx``) pour peupler les menus déroulants ;
un autre fichier peut être choisi manuellement.

À l'enregistrement, la configuration reconstruite est renvoyée via ``on_save``.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..models.config_adresses import COLONNE_ADRESSE_DEFAUT, COLONNE_ID_DEFAUT, ConfigAdresses
from ..services.colonnes_excel import detecter_colonnes, normaliser
from .theme import Couleurs, Polices


class PanneauConfig(tk.Toplevel):
    def __init__(
        self,
        parent,
        config: ConfigAdresses,
        on_save,
        fichier_exemple: str = "",
    ):
        super().__init__(parent)
        self.title("⚙️ Configuration — modification par adresse")
        self.geometry("620x420")
        self.configure(bg=Couleurs.FOND)
        self.transient(parent)
        self.on_save = on_save

        self.colonnes = []           # list[Colonne]
        self.noms: list[str] = []    # libellés proposés dans les menus déroulants
        self.info = {}               # référence normalisée -> Colonne
        self.fichier_colonnes = ""

        self.var_colonne_adresse = tk.StringVar(
            value=config.colonne_adresse or COLONNE_ADRESSE_DEFAUT
        )
        self.var_colonne_id = tk.StringVar(value=config.colonne_id or COLONNE_ID_DEFAUT)
        self.var_entete = tk.StringVar(value=str(config.ligne_entete))
        self.var_style = tk.BooleanVar(value=config.harmoniser_style)

        self._construire()
        if fichier_exemple:
            self._charger_colonnes(fichier_exemple, silencieux=True)

    # ── Construction de la fenêtre ────────────────────────────────
    def _construire(self) -> None:
        entete = tk.Frame(self, bg=Couleurs.FOND_PANNEAU)
        entete.pack(fill="x")
        tk.Label(
            entete, text="⚙️  Configuration", font=Polices.TITRE,
            bg=Couleurs.FOND_PANNEAU, fg=Couleurs.TEXTE,
        ).pack(anchor="w", padx=20, pady=(12, 0))
        tk.Label(
            entete,
            text="Les lignes modifiées sont celles dont l'adresse a été saisie ;\n"
                 "la valeur écrite dans « ID erreur » est celle associée à cette "
                 "adresse dans la saisie.",
            font=Polices.LABEL, bg=Couleurs.FOND_PANNEAU, fg=Couleurs.TEXTE_SECONDAIRE,
            justify="left",
        ).pack(anchor="w", padx=20, pady=(4, 0))

        corps = tk.Frame(self, bg=Couleurs.FOND)
        corps.pack(fill="both", expand=True, padx=20, pady=16)

        self._ligne_colonne(
            corps, "Colonne « Adresse » :", self.var_colonne_adresse, "combo_adresse",
        )
        self._ligne_colonne(
            corps, "Colonne « ID erreur » :", self.var_colonne_id, "combo_id",
        )

        reperes = tk.Frame(corps, bg=Couleurs.FOND)
        reperes.pack(fill="x", pady=(4, 12))
        tk.Label(
            reperes, text="Ligne d'en-tête :", bg=Couleurs.FOND,
            fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.LABEL,
        ).pack(side="left")
        tk.Entry(
            reperes, textvariable=self.var_entete, width=4, justify="center",
            bg=Couleurs.FOND_JOURNAL, fg=Couleurs.TEXTE, font=Polices.LABEL,
            relief="flat", bd=4, insertbackground=Couleurs.BLANC,
        ).pack(side="left", padx=6)
        tk.Checkbutton(
            reperes, text="Reprendre la mise en forme de la colonne (police, format)",
            variable=self.var_style, bg=Couleurs.FOND,
            fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.PETIT,
            activebackground=Couleurs.FOND, activeforeground=Couleurs.TEXTE,
            selectcolor=Couleurs.FOND_PANNEAU2, cursor="hand2",
        ).pack(side="left", padx=(16, 0))

        barre = tk.Frame(corps, bg=Couleurs.FOND)
        barre.pack(fill="x", pady=(0, 12))
        tk.Button(
            barre, text="📄 Colonnes depuis un autre fichier…", command=self._parcourir,
            bg=Couleurs.FOND_PANNEAU2, fg=Couleurs.BLEU_CLAIR, font=Polices.BOUTON_PETIT,
            relief="flat", cursor="hand2", padx=10, pady=4,
        ).pack(side="left")
        self.lbl_colonnes = tk.Label(
            barre, text="aucune colonne détectée — saisie libre possible",
            bg=Couleurs.FOND, fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.PETIT,
        )
        self.lbl_colonnes.pack(side="left", padx=10)

        # Barre d'actions
        pied = tk.Frame(self, bg=Couleurs.FOND_PANNEAU)
        pied.pack(fill="x", side="bottom")
        tk.Button(
            pied, text="💾 Enregistrer", command=self._enregistrer,
            bg=Couleurs.VERT, fg="#062017", font=Polices.BOUTON_PETIT,
            relief="flat", cursor="hand2", padx=18, pady=8,
        ).pack(side="right", padx=16, pady=10)
        tk.Button(
            pied, text="Annuler", command=self.destroy,
            bg=Couleurs.FOND_PANNEAU2, fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.LABEL,
            relief="flat", cursor="hand2", padx=14, pady=8,
        ).pack(side="right", pady=10)

    def _ligne_colonne(self, parent, libelle: str, variable: tk.StringVar, attribut: str) -> None:
        ligne = tk.Frame(parent, bg=Couleurs.FOND)
        ligne.pack(fill="x", pady=6)
        tk.Label(
            ligne, text=libelle, bg=Couleurs.FOND, fg=Couleurs.TEXTE_SECONDAIRE,
            font=Polices.LABEL, width=18, anchor="w",
        ).pack(side="left")
        combo = ttk.Combobox(
            ligne, textvariable=variable, values=self.noms, font=Polices.LABEL, width=30,
        )
        combo.pack(side="left", padx=6)
        badge = tk.Label(
            ligne, text="", bg=Couleurs.FOND, fg=Couleurs.TEXTE_TERTIAIRE, font=Polices.PETIT,
        )
        badge.pack(side="left", padx=6)
        combo.bind("<<ComboboxSelected>>", lambda e: self._rafraichir_badges())
        setattr(self, attribut, combo)
        setattr(self, f"lbl_{attribut}", badge)

    # ── Colonnes ──────────────────────────────────────────────────
    def _parcourir(self) -> None:
        chemin = filedialog.askopenfilename(
            title="Fichier Excel de référence", filetypes=[("Classeur Excel", "*.xlsx")],
            parent=self,
        )
        if chemin:
            self._charger_colonnes(chemin)

    def _charger_colonnes(self, chemin: str, silencieux: bool = False) -> None:
        try:
            colonnes = detecter_colonnes(chemin, ligne_entete=_entier(self.var_entete.get(), 1))
        except Exception as exc:  # noqa: BLE001 — fichier verrouillé, corrompu…
            if not silencieux:
                messagebox.showerror("Colonnes", str(exc), parent=self)
            return

        if not colonnes:
            if not silencieux:
                messagebox.showwarning(
                    "Colonnes", "Aucune colonne détectée dans ce fichier.", parent=self
                )
            return

        self.colonnes = colonnes
        self.noms = [c.nom for c in colonnes]
        self.info = {normaliser(c.nom): c for c in colonnes}
        self.info.update({c.lettre.casefold(): c for c in colonnes})
        self.fichier_colonnes = chemin
        self.combo_adresse.config(values=self.noms)
        self.combo_id.config(values=self.noms)
        self.lbl_colonnes.config(
            text=f"{len(colonnes)} colonnes détectées — {_raccourcir(chemin)}",
            fg=Couleurs.VERT,
        )
        self._rafraichir_badges()

    def _colonne(self, reference: str):
        return self.info.get(normaliser(reference))

    def _badge(self, reference: str) -> str:
        colonne = self._colonne(reference)
        if colonne is None:
            return ""
        return f"[{colonne.lettre} · {colonne.type}]"

    def _rafraichir_badges(self) -> None:
        self.lbl_combo_adresse.config(text=self._badge(self.var_colonne_adresse.get()))
        self.lbl_combo_id.config(text=self._badge(self.var_colonne_id.get()))

    # ── Enregistrement ────────────────────────────────────────────
    def _enregistrer(self) -> None:
        colonne_adresse = self.var_colonne_adresse.get().strip()
        colonne_id = self.var_colonne_id.get().strip()

        if not colonne_adresse:
            messagebox.showerror(
                "Colonne des adresses",
                "Indiquez la colonne comparée aux adresses saisies : c'est elle qui "
                "sélectionne les lignes à modifier.",
                parent=self,
            )
            return
        if not colonne_id:
            messagebox.showerror(
                "Colonne des ID erreur",
                "Indiquez la colonne dans laquelle écrire la valeur d'ID erreur.",
                parent=self,
            )
            return
        if normaliser(colonne_adresse) == normaliser(colonne_id) and not messagebox.askyesno(
            "Même colonne",
            "La colonne des adresses et celle des ID erreur sont identiques : "
            "la valeur d'adresse serait remplacée par l'ID erreur.\n\n"
            "Enregistrer quand même ?",
            parent=self,
        ):
            return

        config = ConfigAdresses(
            colonne_adresse=colonne_adresse,
            colonne_id=colonne_id,
            ligne_entete=_entier(self.var_entete.get(), 1),
            harmoniser_style=self.var_style.get(),
        )
        self.on_save(config)
        self.destroy()


# ── Helpers module ────────────────────────────────────────────────
def _entier(valeur: str, defaut: int) -> int:
    try:
        return max(1, int(str(valeur).strip()))
    except (TypeError, ValueError):
        return defaut


def _raccourcir(chemin: str, longueur: int = 60) -> str:
    return chemin if len(chemin) <= longueur else "…" + chemin[-longueur:]
