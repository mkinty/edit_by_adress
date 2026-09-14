"""Fenêtre principale de l'application (Tkinter).

Rôle strictement limité à l'affichage et à l'interaction :
    - paramétrage du dossier racine et des colonnes utilisées ;
    - collecte des paires (adresse, ID erreur) saisies par l'utilisateur ;
    - résolution des codes INSEE des adresses (API Adresse, data.gouv.fr) et
      regroupement par commune ;
    - déclenchement du traitement dans un thread de fond ;
    - restitution de la progression et du journal.

Toute la logique métier est déléguée à ``sna.services``. Les mises à jour de
l'interface déclenchées depuis le thread de fond sont replacées sur le thread
principal via ``self.after`` (Tkinter n'étant pas thread-safe).
"""

from __future__ import annotations

import os
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ..config import (
    charger_config_adresses, charger_racine, load_config, save_config,
    stocker_config_adresses, stocker_racine,
)
from ..models.base import ResultatCommune, Statut
from ..models.config_adresses import ConfigAdresses
from ..services.adresses import (
    SaisieAdresse, extraire_saisies, grouper_par_commune, lignes_incompletes,
)
from ..services.fichiers import trouver_fichier_exemple
from ..services.geocodage import ErreurGeocodage, codes_insee_pour_adresses
from ..services.traitement import traiter_communes
from .panneau_config import PanneauConfig
from .theme import STYLE_STATUT, Couleurs, Polices

SEPARATEUR = "─" * 60

# Période de vidage de la file du journal, en millisecondes.
PERIODE_JOURNAL = 120


class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.racine = charger_racine(self.cfg)
        self.config_adresses = charger_config_adresses(self.cfg)

        self.title("Modification des fichiers Excel par adresse — Projet SNA")
        self.geometry("860x740")
        self.minsize(760, 640)
        self.configure(bg=Couleurs.FOND)

        self.var_racine = tk.StringVar(value=self.racine)
        self.var_simulation = tk.BooleanVar(value=False)
        self.file_journal: queue.Queue[tuple[str, str]] = queue.Queue()

        self._construire_ui()
        self._maj_resume_config()
        self._vider_journal()

    # ── Construction de l'interface ───────────────────────────────
    def _construire_ui(self) -> None:
        entete = tk.Frame(self, bg=Couleurs.FOND_HEADER, pady=12)
        entete.pack(fill="x")
        tk.Label(
            entete, text="  🛠️  Modification des fichiers Excel par adresse",
            font=Polices.TITRE, bg=Couleurs.FOND_HEADER, fg=Couleurs.TEXTE,
        ).pack(side="left")

        corps = tk.Frame(self, bg=Couleurs.FOND)
        corps.pack(fill="both", expand=True, padx=20, pady=14)

        self._construire_configuration(corps)
        self._construire_saisie(corps)
        self._construire_progression(corps)
        self._construire_journal(corps)

    def _construire_configuration(self, parent) -> None:
        """Dossier racine + accès à la configuration des colonnes."""
        carte = tk.Frame(
            parent, bg=Couleurs.FOND_CARTE,
            highlightbackground=Couleurs.BORDURE, highlightthickness=1,
        )
        carte.pack(fill="x", pady=(0, 12))

        ligne = tk.Frame(carte, bg=Couleurs.FOND_CARTE)
        ligne.pack(fill="x", padx=12, pady=(10, 6))
        tk.Label(
            ligne, text="Dossier racine :", bg=Couleurs.FOND_CARTE,
            fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.LABEL, width=14, anchor="w",
        ).pack(side="left")
        tk.Entry(
            ligne, textvariable=self.var_racine, font=Polices.LABEL,
            bg=Couleurs.FOND_JOURNAL, fg=Couleurs.TEXTE, insertbackground=Couleurs.BLANC,
            relief="flat", bd=6,
        ).pack(side="left", fill="x", expand=True)
        tk.Button(
            ligne, text="📁", command=self._parcourir_racine, bg=Couleurs.FOND_PANNEAU2,
            fg=Couleurs.BLEU_CLAIR, font=Polices.LABEL, relief="flat", cursor="hand2",
            padx=8,
        ).pack(side="left", padx=(6, 0))
        tk.Button(
            ligne, text="Enregistrer", command=self._enregistrer_racine,
            bg=Couleurs.FOND_PANNEAU2, fg=Couleurs.VERT, font=Polices.BOUTON_PETIT,
            relief="flat", cursor="hand2", padx=10,
        ).pack(side="left", padx=(6, 0))

        options = tk.Frame(carte, bg=Couleurs.FOND_CARTE)
        options.pack(fill="x", padx=12, pady=(0, 10))
        tk.Button(
            options, text="⚙️  Configuration", command=self._ouvrir_config,
            bg=Couleurs.FOND_PANNEAU2, fg=Couleurs.BLEU_CLAIR, font=Polices.BOUTON_PETIT,
            relief="flat", cursor="hand2", padx=12, pady=5,
        ).pack(side="left")
        self.lbl_config = tk.Label(
            options, text="", bg=Couleurs.FOND_CARTE, fg=Couleurs.TEXTE_SECONDAIRE,
            font=Polices.PETIT,
        )
        self.lbl_config.pack(side="left", padx=10)
        tk.Checkbutton(
            options, text="Simulation (aucune écriture)", variable=self.var_simulation,
            bg=Couleurs.FOND_CARTE, fg=Couleurs.AMBRE, font=Polices.PETIT,
            activebackground=Couleurs.FOND_CARTE, activeforeground=Couleurs.AMBRE,
            selectcolor=Couleurs.FOND_PANNEAU2, cursor="hand2",
        ).pack(side="right")

    def _construire_saisie(self, parent) -> None:
        tk.Label(
            parent,
            text="Collez vos adresses, une par ligne "
                 "(adresse [Tab ou ; ou ->] nouvel ID erreur) :",
            bg=Couleurs.FOND, fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.LABEL,
        ).pack(anchor="w", pady=(0, 4))
        self.txt_adresses = tk.Text(
            parent, height=6, bg=Couleurs.FOND_CHAMP, fg=Couleurs.BLANC,
            font=Polices.CORPS, relief="flat", insertbackground=Couleurs.BLANC, bd=6,
        )
        self.txt_adresses.pack(fill="x", pady=(0, 2))
        self.txt_adresses.bind("<KeyRelease>", lambda e: self._maj_apercu())
        self.txt_adresses.focus()

        self.lbl_apercu = tk.Label(
            parent, text="", bg=Couleurs.FOND, fg=Couleurs.TEXTE_SECONDAIRE,
            font=Polices.PETIT, anchor="w",
        )
        self.lbl_apercu.pack(fill="x", pady=(0, 8))

        self.btn = tk.Button(
            parent, text="🛠️  Appliquer les modifications", command=self._lancer,
            bg=Couleurs.BLEU, fg=Couleurs.BLANC, font=Polices.BOUTON,
            relief="flat", cursor="hand2", pady=10,
        )
        self.btn.pack(fill="x", pady=(0, 8))

    def _construire_progression(self, parent) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(
            "exp.Horizontal.TProgressbar", troughcolor=Couleurs.FOND_CHAMP,
            background=Couleurs.BLEU, darkcolor=Couleurs.BLEU,
            lightcolor=Couleurs.BLEU, bordercolor=Couleurs.FOND_CHAMP,
        )
        self.progress = ttk.Progressbar(
            parent, style="exp.Horizontal.TProgressbar", mode="determinate"
        )
        self.progress.pack(fill="x", pady=(0, 2))
        self.lbl_prog = tk.Label(
            parent, text="", bg=Couleurs.FOND, fg=Couleurs.TEXTE_SECONDAIRE,
            font=Polices.LABEL,
        )
        self.lbl_prog.pack(anchor="w", pady=(0, 6))

    def _construire_journal(self, parent) -> None:
        tk.Label(
            parent, text="Journal :", bg=Couleurs.FOND,
            fg=Couleurs.TEXTE_SECONDAIRE, font=Polices.LABEL_GRAS,
        ).pack(anchor="w")
        self.txt_log = tk.Text(
            parent, height=10, bg=Couleurs.FOND_JOURNAL, fg=Couleurs.SUCCES,
            font=Polices.JOURNAL, relief="flat", state="disabled",
        )
        self.txt_log.pack(fill="both", expand=True, pady=(2, 0))

    # ── Saisie ────────────────────────────────────────────────────
    def _saisie(self) -> str:
        return self.txt_adresses.get("1.0", tk.END)

    def _maj_apercu(self) -> None:
        """Compte, à la volée, ce que le programme a compris de la saisie.

        Les communes ne sont connues qu'après résolution des codes INSEE
        (appel réseau), qui n'a lieu qu'au lancement du traitement : cet
        aperçu se limite donc aux paires reconnues dans le texte.
        """
        texte = self._saisie()
        saisies = extraire_saisies(texte)
        incompletes = lignes_incompletes(texte)

        if not saisies and not incompletes:
            self.lbl_apercu.config(text="", fg=Couleurs.TEXTE_SECONDAIRE)
            return

        message = f"{len(saisies)} adresse(s) reconnue(s)"
        couleur = Couleurs.VERT if saisies else Couleurs.AVERTISSEMENT
        if incompletes:
            message += (
                f"  ·  {len(incompletes)} ligne(s) incomplète(s) ignorée(s) "
                "(adresse ou ID erreur manquant)"
            )
            couleur = Couleurs.AVERTISSEMENT
        self.lbl_apercu.config(text=message, fg=couleur)

    # ── Configuration ─────────────────────────────────────────────
    def _parcourir_racine(self) -> None:
        depart = self.var_racine.get() if os.path.isdir(self.var_racine.get()) else None
        chemin = filedialog.askdirectory(title="Dossier racine des audits", initialdir=depart)
        if chemin:
            self.var_racine.set(os.path.normpath(chemin))
            self._enregistrer_racine()

    def _enregistrer_racine(self) -> None:
        racine = self.var_racine.get().strip()
        if not racine:
            messagebox.showwarning("Dossier racine", "Indiquez un dossier racine.")
            return

        self.racine = racine
        stocker_racine(self.cfg, racine)
        if not save_config(self.cfg):
            messagebox.showwarning(
                "Configuration", "Le dossier racine n'a pas pu être enregistré "
                "(fichier de configuration inaccessible)."
            )
            return

        if os.path.isdir(racine):
            self._journaliser(f"📂 Dossier racine : {racine}", Couleurs.INFO)
        else:
            self._journaliser(f"⚠️ Dossier racine introuvable : {racine}", Couleurs.AVERTISSEMENT)
        self._maj_resume_config()

    def _ouvrir_config(self) -> None:
        PanneauConfig(
            self, self.config_adresses, on_save=self._appliquer_config,
            fichier_exemple=self._fichier_exemple(),
        )

    def _fichier_exemple(self) -> str:
        """Premier audit trouvé sous la racine, pour peupler les menus déroulants."""
        return trouver_fichier_exemple(self.var_racine.get().strip()) or ""

    def _appliquer_config(self, config: ConfigAdresses) -> None:
        self.config_adresses = config
        stocker_config_adresses(self.cfg, config)
        save_config(self.cfg)
        self._maj_resume_config()
        self._journaliser("⚙️ Configuration mise à jour", Couleurs.INFO)

    def _maj_resume_config(self) -> None:
        config = self.config_adresses
        self.lbl_config.config(
            text=(
                f"« {config.colonne_adresse} » → « {config.colonne_id} »"
                f"  ·  en-tête ligne {config.ligne_entete}"
            ),
            fg=Couleurs.VERT,
        )

    # ── Traitement ────────────────────────────────────────────────
    def _lancer(self) -> None:
        """Valide la saisie, demande confirmation, puis lance le traitement."""
        texte = self._saisie()
        saisies = extraire_saisies(texte)
        if not saisies:
            messagebox.showwarning(
                "Erreur",
                "Aucune adresse valide détectée.\n\n"
                "Format attendu, une ligne par adresse : adresse, une tabulation, "
                "un point-virgule ou « -> », puis le nouvel ID erreur.",
            )
            return

        racine = self.var_racine.get().strip()
        if not os.path.isdir(racine):
            messagebox.showwarning("Dossier racine", f"Dossier introuvable :\n{racine}")
            return

        incompletes = lignes_incompletes(texte)
        if incompletes and not messagebox.askyesno(
            "Lignes incomplètes",
            f"{len(incompletes)} ligne(s) n'ont pas pu être comprises (adresse ou "
            f"ID erreur manquant) et seront ignorées.\n\nContinuer ?",
        ):
            return

        simulation = self.var_simulation.get()
        avertissement = (
            "🔍 Mode simulation : aucun fichier ne sera modifié."
            if simulation
            else "⚠️ Les fichiers d'origine seront modifiés."
        )
        if not messagebox.askyesno(
            "Confirmation",
            f"Rechercher la commune de {len(saisies)} adresse(s) via l'API Adresse, "
            f"puis écrire leur valeur dans la colonne « {self.config_adresses.colonne_id} » "
            f"(lignes sélectionnées via « {self.config_adresses.colonne_adresse} ») ?"
            f"\n\n{avertissement}",
        ):
            return

        self._reinitialiser_journal()
        self.btn.config(state="disabled")
        threading.Thread(
            target=self._executer, args=(saisies, racine, simulation), daemon=True
        ).start()

    def _executer(self, saisies: list[SaisieAdresse], racine: str, simulation: bool) -> None:
        """Exécuté dans un thread de fond : résout les adresses puis traite les communes.

        Chaque étape est journalisée au fil de l'eau — résolution des codes
        INSEE, recherche du fichier, analyse, chargement, écriture,
        enregistrement — afin que l'utilisateur voie l'avancement au lieu
        d'attendre devant un journal figé.
        """
        mode = " (simulation)" if simulation else ""
        depart = time.perf_counter()

        self._journaliser(f"🚀 {len(saisies)} adresse(s){mode}", Couleurs.INFO)
        self._journaliser(f"📂 Racine : {racine}", Couleurs.TEXTE_SECONDAIRE)
        self._journaliser(
            "🌐 Résolution des codes INSEE via l'API Adresse (data.gouv.fr)…",
            Couleurs.TEXTE_SECONDAIRE,
        )

        try:
            codes = codes_insee_pour_adresses({s.adresse for s in saisies})
        except ErreurGeocodage as exc:
            self._journaliser(f"❌ Résolution des adresses impossible : {exc}", Couleurs.ERREUR)
            self.after(0, self._terminer, 0, 0, 0, 0, simulation)
            return

        groupes, non_resolues = grouper_par_commune(saisies, codes)
        if non_resolues:
            self._journaliser(
                f"⚠️ {len(non_resolues)} adresse(s) sans commune identifiée : "
                + ", ".join(s.adresse for s in non_resolues[:5])
                + ("…" if len(non_resolues) > 5 else ""),
                Couleurs.AVERTISSEMENT,
            )

        if not groupes:
            self._journaliser("❌ Aucune commune identifiée — rien à traiter", Couleurs.ERREUR)
            self.after(0, self._terminer, 0, 0, 0, len(non_resolues), simulation)
            return

        self._journaliser(
            f"🔎 Filtre : colonne « {self.config_adresses.colonne_adresse} » "
            f"→ écriture dans « {self.config_adresses.colonne_id} »"
            + ("  ·  mise en forme reprise de la colonne" if self.config_adresses.harmoniser_style else ""),
            Couleurs.TEXTE_SECONDAIRE,
        )
        self._journaliser(SEPARATEUR, Couleurs.SEPARATEUR)

        resultats = traiter_communes(
            groupes, self.config_adresses, racine, simuler=simulation,
            on_progression=self._progresser,
            on_resultat=self._afficher_resultat,
            on_etape=self._afficher_etape,
        )

        duree = time.perf_counter() - depart
        n_ok = sum(1 for r in resultats if r.statut is Statut.SUCCES)
        total_modifs = sum(r.nb_modifications for r in resultats)
        total_absentes = sum(len(r.adresses_absentes) for r in resultats) + len(non_resolues)
        self._journaliser(SEPARATEUR, Couleurs.SEPARATEUR)
        self._journaliser(
            f"🎉 {n_ok}/{len(groupes)} fichier(s) traité(s) — "
            f"{total_modifs} modification(s) au total{mode} — "
            f"{duree:.1f} s".replace(".", ","),
            Couleurs.SUCCES,
        )
        if total_absentes:
            self._journaliser(
                f"⚠️ {total_absentes} adresse(s) introuvable(s)",
                Couleurs.AVERTISSEMENT,
            )
        self.after(
            0, self._terminer, n_ok, len(groupes), total_modifs, total_absentes, simulation
        )

    def _terminer(
        self, n_ok: int, total: int, total_modifs: int, total_absentes: int, simulation: bool
    ) -> None:
        """Réactive l'interface et affiche le bilan (thread principal)."""
        self.btn.config(state="normal")
        suffixe = "\n\n(simulation : aucun fichier modifié)" if simulation else ""
        if total_absentes:
            suffixe = (
                f"\n\n⚠️ {total_absentes} adresse(s) introuvable(s) — voir le journal."
                + suffixe
            )
        if n_ok:
            messagebox.showinfo(
                "Terminé",
                f"✅ {n_ok}/{total} fichier(s) traité(s).\n"
                f"{total_modifs} modification(s) au total.{suffixe}",
            )
        else:
            messagebox.showwarning("Terminé", "Aucun fichier traité. Voir le journal.")

    # ── Callbacks du traitement (appelés depuis le thread de fond) ──
    def _afficher_etape(self, commune: str, message: str) -> None:
        """Trace une étape interne au traitement d'une commune."""
        self._journaliser(f"   · {commune} — {message}", Couleurs.TEXTE_SECONDAIRE)

    def _afficher_resultat(self, resultat: ResultatCommune) -> None:
        couleur, icone = STYLE_STATUT[resultat.statut]
        if resultat.statut is Statut.SUCCES:
            texte = (
                f"{icone} {resultat.commune} — {resultat.nb_modifications} modification(s) "
                f"sur {resultat.nb_lignes} ligne(s) · {resultat.resume_adresses()} · "
                f"{resultat.resume_duree()}"
            )
            if resultat.adresses_absentes:
                couleur = Couleurs.AVERTISSEMENT
                texte += "\n   ↳ introuvables : " + ", ".join(resultat.adresses_absentes[:8])
                if len(resultat.adresses_absentes) > 8:
                    texte += f" … (+{len(resultat.adresses_absentes) - 8})"
        else:
            texte = f"{icone} {resultat.commune} — {resultat.message}"
        self._journaliser(texte, couleur)

    # ── Mises à jour de l'interface (repliées sur le thread principal) ──
    def _journaliser(self, message: str, couleur: str = Couleurs.SUCCES) -> None:
        """Empile une ligne de journal depuis n'importe quel thread.

        Les messages transitent par une file vidée périodiquement sur le thread
        principal : un traitement bavard (points d'avancement toutes les 20 000
        lignes) ne noie donc pas la boucle d'événements Tk sous les rappels.
        """
        self.file_journal.put((message, couleur))

    def _vider_journal(self) -> None:
        """Vide la file dans la zone de journal (thread principal, périodique)."""
        lignes = []
        try:
            while True:
                lignes.append(self.file_journal.get_nowait())
        except queue.Empty:
            pass

        if lignes:
            self.txt_log.config(state="normal")
            for message, couleur in lignes:
                tag = f"c{couleur.replace('#', '')}"
                self.txt_log.tag_config(tag, foreground=couleur)
                self.txt_log.insert(tk.END, message + "\n", tag)
            self.txt_log.see(tk.END)
            self.txt_log.config(state="disabled")

        self.after(PERIODE_JOURNAL, self._vider_journal)

    def _progresser(self, fait: int, total: int, libelle: str = "") -> None:
        self.after(0, self._progresser_ui, fait, total, libelle)

    def _progresser_ui(self, fait: int, total: int, libelle: str) -> None:
        self.progress["maximum"] = max(total, 1)
        self.progress["value"] = fait
        self.lbl_prog.config(text=f"{fait}/{total} — {libelle}")

    def _reinitialiser_journal(self) -> None:
        while not self.file_journal.empty():
            self.file_journal.get_nowait()
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.config(state="disabled")
