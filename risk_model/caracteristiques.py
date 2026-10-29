"""Caractéristiques et cible du modèle de risque d'inondation.

Cible : "crue dans les HORIZON_JOURS prochains jours", c'est-à-dire un débit
futur supérieur au seuil de la zone (centile 95 calculé sur les années
d'entraînement uniquement, pour éviter toute fuite d'information).
"""

import os

import numpy as np
import pandas as pd

# Modifiable sans toucher au code : $env:EAURACLE_HORIZON = "5"
HORIZON_JOURS = int(os.environ.get("EAURACLE_HORIZON", "3"))
FENETRES_PLUIE = [1, 3, 7, 14, 30]
FENETRES_DEBIT = [3, 7, 14]

COLONNES_MODELE = (
    ["debit_relatif", "variation_1j", "variation_3j", "rapport_debit_moy30", "jour_sin", "jour_cos"]
    + [f"pluie_{f}j" for f in FENETRES_PLUIE]
    + [f"debit_moy_rel_{f}j" for f in FENETRES_DEBIT]
    + [f"debit_max_rel_{f}j" for f in FENETRES_DEBIT]
)


def construire_caracteristiques(tableau, seuil):
    """tableau : colonnes date, debit, pluie. Ne regarde que le passé (jusqu'à la date du jour)."""
    donnees = tableau.sort_values("date").reset_index(drop=True)
    debit = donnees["debit"].astype(float)
    pluie = donnees["pluie"].astype(float)
    resultat = pd.DataFrame({"date": donnees["date"]})

    resultat["debit_relatif"] = debit / seuil
    resultat["variation_1j"] = debit.diff(1) / seuil
    resultat["variation_3j"] = debit.diff(3) / seuil
    moyenne_30j = debit.rolling(30, min_periods=30).mean()
    resultat["rapport_debit_moy30"] = debit / (moyenne_30j + 1e-6)

    jour_annee = donnees["date"].dt.dayofyear
    resultat["jour_sin"] = np.sin(2 * np.pi * jour_annee / 365.25)
    resultat["jour_cos"] = np.cos(2 * np.pi * jour_annee / 365.25)

    for fenetre in FENETRES_PLUIE:
        resultat[f"pluie_{fenetre}j"] = pluie.rolling(fenetre, min_periods=fenetre).sum()
    for fenetre in FENETRES_DEBIT:
        resultat[f"debit_moy_rel_{fenetre}j"] = debit.rolling(fenetre, min_periods=fenetre).mean() / seuil
        resultat[f"debit_max_rel_{fenetre}j"] = debit.rolling(fenetre, min_periods=fenetre).max() / seuil
    return resultat


def construire_cible(tableau, seuil):
    """1 si le débit max des jours t+1..t+HORIZON_JOURS dépasse le seuil, sinon 0 (NaN en fin de série)."""
    donnees = tableau.sort_values("date").reset_index(drop=True)
    debit = donnees["debit"].astype(float)
    futur_max = debit[::-1].rolling(HORIZON_JOURS, min_periods=HORIZON_JOURS).max()[::-1].shift(-1)
    cible = (futur_max > seuil).astype(float)
    cible[futur_max.isna()] = np.nan
    return cible
