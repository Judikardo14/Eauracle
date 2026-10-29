"""Score de risque d'inondation pour une zone (utilisé par l'agent).

Deux modes :
- direct : données Open-Meteo du jour ;
- rejeu historique (date_reference donnée) : on rejoue une vraie crue passée à partir du cache
  téléchargé par data/historique.py. À signaler comme "rejeu" dans la démo.
"""

import json
import os
import sys
from datetime import date

import lightgbm as lgb
import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "data"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caracteristiques import COLONNES_MODELE, construire_caracteristiques  # noqa: E402
from historique import DOSSIER_CACHE  # noqa: E402
from ingestion import recuperer_zone  # noqa: E402

DOSSIER_MODELE = os.path.dirname(os.path.abspath(__file__))
SEUILS_PAR_DEFAUT = {"moyen": 0.15, "eleve": 0.40}


def niveau_depuis_score(score, seuils_niveaux=None):
    seuils_niveaux = seuils_niveaux or SEUILS_PAR_DEFAUT
    if score >= seuils_niveaux["eleve"]:
        return "élevé"
    if score >= seuils_niveaux["moyen"]:
        return "moyen"
    return "faible"


def tableau_en_direct(zone):
    donnees = recuperer_zone(zone, jours_passes=40, jours_prevision=1)
    debit = pd.DataFrame(donnees["debit"], columns=["date", "debit"])
    pluie = pd.DataFrame(donnees["pluie"], columns=["date", "pluie"])
    tableau = debit.merge(pluie, on="date", how="inner")
    tableau["date"] = pd.to_datetime(tableau["date"])
    return tableau[tableau["date"] <= pd.Timestamp(date.today())]


def tableau_rejeu(zone, date_reference):
    tableau = pd.read_csv(os.path.join(DOSSIER_CACHE, f"{zone}.csv"), parse_dates=["date"])
    tableau = tableau[tableau["date"] <= pd.Timestamp(date_reference)]
    return tableau.tail(60).reset_index(drop=True)


def calculer_risque(zone, date_reference=None):
    with open(os.path.join(DOSSIER_MODELE, "parametres.json"), encoding="utf-8") as fichier:
        parametres = json.load(fichier)
    seuil = parametres["seuils"][zone]
    seuils_niveaux = parametres.get("seuils_niveaux", SEUILS_PAR_DEFAUT)
    modele = lgb.Booster(model_file=os.path.join(DOSSIER_MODELE, "modele_risque.txt"))

    tableau = tableau_rejeu(zone, date_reference) if date_reference else tableau_en_direct(zone)
    caracteristiques = construire_caracteristiques(tableau, seuil)
    derniere_ligne = caracteristiques.iloc[[-1]]
    debit_relatif = float(derniere_ligne["debit_relatif"].iloc[0])

    if debit_relatif >= 1.0:
        # Le modèle prédit le DÉBUT d'une crue ; si le fleuve est déjà au-dessus du seuil, elle a commencé.
        score, niveau = 1.0, "crue en cours"
    else:
        score = float(modele.predict(derniere_ligne[COLONNES_MODELE])[0])
        niveau = niveau_depuis_score(score, seuils_niveaux)

    return {
        "zone": zone,
        "date": str(derniere_ligne["date"].iloc[0].date()),
        "mode": "rejeu historique" if date_reference else "direct",
        "score_risque": round(score, 3),
        "niveau": niveau,
        "debit_actuel_m3s": round(float(tableau["debit"].iloc[-1]), 1),
        "debit_relatif_au_seuil_crue": round(debit_relatif, 2),
        "variation_3j_relative": round(float(derniere_ligne["variation_3j"].iloc[0]), 3),
        "pluie_7j_mm": round(float(derniere_ligne["pluie_7j"].iloc[0]), 1),
        "source": "GloFAS (simulé) + Open-Meteo",
    }
