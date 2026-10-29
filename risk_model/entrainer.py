"""Entraîne le modèle de risque LightGBM sur l'historique de toutes les zones.

Découpage temporel (pas aléatoire) :
  entraînement <= 2016, validation 2017-2019, test >= 2020.
Le seuil de crue de chaque zone (centile 95) est calculé sur l'entraînement seul.

Usage : python risk_model/entrainer.py   (après python data/historique.py)
"""

import json
import os
import sys

import lightgbm as lgb
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "data"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from caracteristiques import (  # noqa: E402
    COLONNES_MODELE,
    HORIZON_JOURS,
    construire_cible,
    construire_caracteristiques,
)
from historique import DOSSIER_CACHE  # noqa: E402
from ingestion import ZONES  # noqa: E402

# Modifiables sans toucher au code : $env:EAURACLE_CENTILE = "0.90"
CENTILE_CRUE = float(os.environ.get("EAURACLE_CENTILE", "0.95"))
ANNEE_FIN_ENTRAINEMENT = 2016
ANNEE_FIN_VALIDATION = 2019
CHEMIN_MODELE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modele_risque.txt")
CHEMIN_PARAMETRES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parametres.json")

PARAMETRES_LGBM = {
    "objective": "binary",
    "metric": "auc",
    "learning_rate": 0.05,
    "num_leaves": 31,
    "min_data_in_leaf": 50,
    "feature_fraction": 0.8,
    "bagging_fraction": 0.8,
    "bagging_freq": 1,
    "verbosity": -1,
    "seed": 42,
}


def charger_zone(nom_zone):
    chemin = os.path.join(DOSSIER_CACHE, f"{nom_zone}.csv")
    return pd.read_csv(chemin, parse_dates=["date"])


def preparer_jeu():
    seuils = {}
    morceaux = []
    for nom in ZONES:
        tableau = charger_zone(nom)
        entrainement = tableau[tableau["date"].dt.year <= ANNEE_FIN_ENTRAINEMENT]
        seuil = float(entrainement["debit"].quantile(CENTILE_CRUE))
        seuils[nom] = seuil
        caracteristiques = construire_caracteristiques(tableau, seuil)
        caracteristiques["cible"] = construire_cible(tableau, seuil)
        caracteristiques["zone"] = nom
        morceaux.append(caracteristiques)
    jeu = pd.concat(morceaux, ignore_index=True)
    jeu = jeu.dropna(subset=["cible"])
    # DÉBUT de crue : on ne garde que les jours où le fleuve est encore SOUS le seuil.
    # Sinon la cible est presque toujours vraie dès que le débit est déjà au-dessus
    # (le modèle ne ferait que recopier cette information).
    jeu = jeu[jeu["debit_relatif"] < 1.0]
    return jeu, seuils


def choisir_seuils_niveaux(scores_validation):
    """Niveaux d'alerte par FRÉQUENCE : "moyen" = les 5 % de jours les plus à risque de la validation,
    "élevé" = les 1 % les plus à risque. Un seuil de précision serait instable (peu d'événements)
    et déclencherait des alertes presque tous les jours."""
    seuil_moyen = float(np.quantile(scores_validation, 0.95))
    seuil_eleve = float(np.quantile(scores_validation, 0.99))
    return {"moyen": seuil_moyen, "eleve": max(seuil_eleve, seuil_moyen)}


def main():
    jeu, seuils = preparer_jeu()
    annee = jeu["date"].dt.year
    entrainement = jeu[annee <= ANNEE_FIN_ENTRAINEMENT]
    validation = jeu[(annee > ANNEE_FIN_ENTRAINEMENT) & (annee <= ANNEE_FIN_VALIDATION)]
    test = jeu[annee > ANNEE_FIN_VALIDATION]
    print(f"Lignes : entraînement {len(entrainement)}, validation {len(validation)}, test {len(test)}")

    jeu_entrainement = lgb.Dataset(entrainement[COLONNES_MODELE], entrainement["cible"])
    jeu_validation = lgb.Dataset(validation[COLONNES_MODELE], validation["cible"])
    modele = lgb.train(
        PARAMETRES_LGBM,
        jeu_entrainement,
        num_boost_round=1000,
        valid_sets=[jeu_validation],
        callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)],
    )

    scores = modele.predict(test[COLONNES_MODELE], num_iteration=modele.best_iteration)
    metriques = {
        "centile_crue": CENTILE_CRUE,
        "horizon_jours": HORIZON_JOURS,
        "auc_test": float(roc_auc_score(test["cible"], scores)),
        "precision_moyenne_test": float(average_precision_score(test["cible"], scores)),
        "taux_de_crue_test": float(test["cible"].mean()),
        # Référence naïve : plus le débit est proche du seuil, plus le risque est jugé élevé
        "precision_moyenne_reference_naive": float(
            average_precision_score(test["cible"], test["debit_relatif"].fillna(0))
        ),
        "auc_reference_naive": float(roc_auc_score(test["cible"], test["debit_relatif"].fillna(0))),
        "nombre_debuts_de_crue_test": int(test["cible"].sum()),
        "meilleure_iteration": int(modele.best_iteration),
    }
    scores_validation = modele.predict(validation[COLONNES_MODELE], num_iteration=modele.best_iteration)
    seuils_niveaux = choisir_seuils_niveaux(scores_validation)
    metriques["seuils_niveaux"] = seuils_niveaux
    print(json.dumps(metriques, indent=2, ensure_ascii=False))

    modele.save_model(CHEMIN_MODELE, num_iteration=modele.best_iteration)
    with open(CHEMIN_PARAMETRES, "w", encoding="utf-8") as fichier:
        json.dump(
            {"seuils": seuils, "seuils_niveaux": seuils_niveaux, "metriques": metriques},
            fichier,
            indent=2,
            ensure_ascii=False,
        )
    print(f"Modèle enregistré : {CHEMIN_MODELE}")


if __name__ == "__main__":
    main()
