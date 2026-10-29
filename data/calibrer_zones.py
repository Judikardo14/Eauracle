"""Calibre les coordonnées des zones sur la vraie cellule de rivière GloFAS.

Pour chaque zone de data/ingestion.py, scanne une grille autour du point
initial et retient la position au débit moyen le plus élevé (= lit principal).

Usage : python data/calibrer_zones.py
Affiche un dictionnaire ZONES à recopier dans data/ingestion.py.
"""

import time

from ingestion import ZONES, recuperer_debit

RAYON_DEGRES = 0.10
PAS_DEGRES = 0.05
JOURS_PASSES = 7


def valeurs_valides(serie):
    return [valeur for _, valeur in serie if valeur is not None]


def calibrer_zone(latitude, longitude):
    """Renvoie (meilleure_lat, meilleure_lon, debit_moyen) autour d'un point."""
    nombre_pas = int(round(RAYON_DEGRES / PAS_DEGRES))
    meilleur = (latitude, longitude, -1.0)
    for i in range(-nombre_pas, nombre_pas + 1):
        for j in range(-nombre_pas, nombre_pas + 1):
            lat_test = round(latitude + i * PAS_DEGRES, 3)
            lon_test = round(longitude + j * PAS_DEGRES, 3)
            try:
                serie = recuperer_debit(lat_test, lon_test, JOURS_PASSES, 1)
            except Exception as erreur:
                print(f"  ({lat_test}, {lon_test}) ignoré : {erreur}")
                continue
            valeurs = valeurs_valides(serie)
            if not valeurs:
                continue
            moyenne = sum(valeurs) / len(valeurs)
            if moyenne > meilleur[2]:
                meilleur = (lat_test, lon_test, moyenne)
            time.sleep(0.2)
    return meilleur


if __name__ == "__main__":
    import sys

    # Usage : python calibrer_zones.py [zone] [rayon_en_degres]
    # Ex. : python calibrer_zones.py Savè 0.3  (zone absente de ZONES : lat/lon ci-dessous)
    ZONES_A_CALIBRER = dict(ZONES)
    ZONES_A_CALIBRER["Savè"] = {"latitude": 8.03, "longitude": 2.48}
    if len(sys.argv) > 1:
        ZONES_A_CALIBRER = {sys.argv[1]: ZONES_A_CALIBRER[sys.argv[1]]}
    if len(sys.argv) > 2:
        RAYON_DEGRES = float(sys.argv[2])
    resultats = {}
    for nom, zone in ZONES_A_CALIBRER.items():
        lat, lon, moyenne = calibrer_zone(zone["latitude"], zone["longitude"])
        print(f"{nom}: ({lat}, {lon}) débit moyen {moyenne:.1f} m³/s")
        resultats[nom] = {"latitude": lat, "longitude": lon}
    print("\nZONES = {")
    for nom, coordonnees in resultats.items():
        print(f'    "{nom}": {coordonnees},')
    print("}")
