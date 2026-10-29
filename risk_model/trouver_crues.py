"""Liste les plus grandes crues de l'historique d'une zone et ce que le modèle aurait dit avant.

Usage : python risk_model/trouver_crues.py Bonou
Pour chaque pic annuel, affiche le score du modèle 7, 5 et 3 jours avant, afin de choisir
une date de rejeu pour la démo :  python agent/boucle.py Bonou --rejeu AAAA-MM-JJ

Honnêteté : choisir une date où le modèle réussit est un EXEMPLE ILLUSTRATIF ; dans la démo
et le README, donne aussi les métriques globales (risk_model/parametres.json).
"""

import os
import sys

import pandas as pd

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(RACINE, "data"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from historique import DOSSIER_CACHE  # noqa: E402

DECALAGES_JOURS = (7, 5, 3)


def resume_risque(zone, jour):
    try:
        from inference import calculer_risque

        resultat = calculer_risque(zone, str(jour))
        return f"{resultat['score_risque']:.3f} ({resultat['niveau']})"
    except Exception as erreur:
        return f"? ({type(erreur).__name__})"


if __name__ == "__main__":
    zone = sys.argv[1] if len(sys.argv) > 1 else "Bonou"
    tableau = pd.read_csv(os.path.join(DOSSIER_CACHE, f"{zone}.csv"), parse_dates=["date"])
    manquants = tableau[tableau["debit"].isna()]
    if len(manquants):
        resume = manquants.groupby(manquants["date"].dt.year).size().to_dict()
        print(f"Attention : jours sans débit par année : {resume}\n")
    tableau = tableau.dropna(subset=["debit"])
    tableau["annee"] = tableau["date"].dt.year
    pics = tableau.loc[tableau.groupby("annee")["debit"].idxmax()].nlargest(8, "debit")
    print(f"Plus fortes crues simulées (GloFAS) à {zone} :\n")
    for _, ligne in pics.sort_values("date").iterrows():
        print(f"pic {ligne['date'].date()}  débit {ligne['debit']:.0f} m³/s")
        for decalage in DECALAGES_JOURS:
            jour = (ligne["date"] - pd.Timedelta(days=decalage)).date()
            print(f"   rejeu {jour}  (J-{decalage})  score : {resume_risque(zone, jour)}")
