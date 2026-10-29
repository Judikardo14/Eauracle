"""Télécharge l'historique débit + pluie par zone et le met en cache (CSV).

- Débit : Open-Meteo Flood API (GloFAS, réanalyse depuis 1984), SIMULÉ.
- Pluie : Open-Meteo Archive API (réanalyse ERA5), pas des mesures de pluviomètre.

Usage : python data/historique.py
"""

import os
import sys
import time
from datetime import date, timedelta

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ingestion import ZONES  # noqa: E402

URL_DEBIT_HISTORIQUE = "https://flood-api.open-meteo.com/v1/flood"
URL_PLUIE_HISTORIQUE = "https://archive-api.open-meteo.com/v1/archive"
DOSSIER_CACHE = os.environ.get(
    "EAURACLE_CACHE", os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache")
)
ANNEE_DEBUT = 1984
PAS_ANNEES = 5


def telecharger_bloc(url, latitude, longitude, variable, date_debut, date_fin):
    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": variable,
        "start_date": date_debut,
        "end_date": date_fin,
    }
    reponse = requests.get(url, params=parametres, timeout=60)
    reponse.raise_for_status()
    donnees = reponse.json()["daily"]
    return pd.DataFrame({"date": pd.to_datetime(donnees["time"]), variable: donnees[variable]})


def telecharger_serie(url, latitude, longitude, variable, annee_debut, date_fin):
    """Télécharge par blocs de PAS_ANNEES ans pour rester sous les limites de l'API."""
    blocs = []
    annee = annee_debut
    while date(annee, 1, 1) <= date_fin:
        fin_bloc = min(date(annee + PAS_ANNEES - 1, 12, 31), date_fin)
        blocs.append(
            telecharger_bloc(url, latitude, longitude, variable, f"{annee}-01-01", fin_bloc.isoformat())
        )
        annee += PAS_ANNEES
        time.sleep(1)
    return pd.concat(blocs, ignore_index=True)


def construire_historique(nom_zone):
    zone = ZONES[nom_zone]
    date_fin = date.today() - timedelta(days=7)  # l'archive a quelques jours de retard
    debit = telecharger_serie(
        URL_DEBIT_HISTORIQUE, zone["latitude"], zone["longitude"], "river_discharge", ANNEE_DEBUT, date_fin
    ).rename(columns={"river_discharge": "debit"})
    pluie = telecharger_serie(
        URL_PLUIE_HISTORIQUE, zone["latitude"], zone["longitude"], "precipitation_sum", ANNEE_DEBUT, date_fin
    ).rename(columns={"precipitation_sum": "pluie"})
    tableau = debit.merge(pluie, on="date", how="inner").sort_values("date")
    os.makedirs(DOSSIER_CACHE, exist_ok=True)
    tableau.to_csv(os.path.join(DOSSIER_CACHE, f"{nom_zone}.csv"), index=False)
    return tableau


if __name__ == "__main__":
    for nom in ZONES:
        print(f"Téléchargement {nom}...")
        resultat = construire_historique(nom)
        print(f"  {len(resultat)} jours, {resultat['date'].min().date()} -> {resultat['date'].max().date()}")
