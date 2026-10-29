"""Ingestion des données hydro-météo pour le bassin de l'Ouémé (Bénin).

Sources (réelles, gratuites, sans clé) :
- Débit des rivières : Open-Meteo Flood API (modèle GloFAS, Copernicus)
- Précipitations : Open-Meteo Forecast API (pluie passée + prévision)

NOTE HONNÊTETÉ : le débit GloFAS est un débit SIMULÉ (modèle), pas une mesure
de station. À indiquer clairement dans la démo et le README.
"""

import requests

URL_DEBIT = "https://flood-api.open-meteo.com/v1/flood"
URL_PLUIE = "https://api.open-meteo.com/v1/forecast"

# Zones de surveillance le long de l'Ouémé, du nord vers l'embouchure.
# Coordonnées approximatives : GloFAS "accroche" la cellule de rivière la plus
# proche, mais à vérifier (le débit doit être non nul).
ZONES = {
    "Betérou": {"latitude": 9.10, "longitude": 2.26},
    # Savè retiré : aucune cellule de rivière trouvée (0,4 m³/s). À rescanner :
    # python calibrer_zones.py Savè 0.3
    "Bonou": {"latitude": 6.83, "longitude": 2.45},
    "Adjohoun": {"latitude": 6.60, "longitude": 2.48},
    "Dangbo": {"latitude": 6.50, "longitude": 2.48},
    "Porto-Novo": {"latitude": 6.44, "longitude": 2.73},
}


def recuperer_debit(latitude, longitude, jours_passes=30, jours_prevision=7):
    """Série journalière du débit (m³/s) : passé récent + prévision."""
    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "river_discharge",
        "past_days": jours_passes,
        "forecast_days": jours_prevision,
    }
    reponse = requests.get(URL_DEBIT, params=parametres, timeout=30)
    reponse.raise_for_status()
    donnees = reponse.json()["daily"]
    return list(zip(donnees["time"], donnees["river_discharge"]))


def recuperer_pluie(latitude, longitude, jours_passes=30, jours_prevision=7):
    """Série journalière des précipitations (mm) : passé récent + prévision."""
    parametres = {
        "latitude": latitude,
        "longitude": longitude,
        "daily": "precipitation_sum",
        "past_days": jours_passes,
        "forecast_days": jours_prevision,
        "timezone": "Africa/Porto-Novo",
    }
    reponse = requests.get(URL_PLUIE, params=parametres, timeout=30)
    reponse.raise_for_status()
    donnees = reponse.json()["daily"]
    return list(zip(donnees["time"], donnees["precipitation_sum"]))


def recuperer_zone(nom_zone, jours_passes=30, jours_prevision=7):
    """Débit + pluie pour une zone nommée de ZONES."""
    zone = ZONES[nom_zone]
    return {
        "zone": nom_zone,
        "debit": recuperer_debit(zone["latitude"], zone["longitude"], jours_passes, jours_prevision),
        "pluie": recuperer_pluie(zone["latitude"], zone["longitude"], jours_passes, jours_prevision),
    }


if __name__ == "__main__":
    for nom in ZONES:
        resultat = recuperer_zone(nom, jours_passes=3, jours_prevision=3)
        print(nom, resultat["debit"][:3], resultat["pluie"][:3])
