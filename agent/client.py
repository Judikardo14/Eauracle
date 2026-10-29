"""Client LLM de l'agent. Les clés restent dans des variables d'environnement.

Variables :
  EAURACLE_FOURNISSEUR = baseten (défaut) | meta
  BASETEN_API_KEY      clé Baseten  (Muse Spark Open)
  META_API_KEY         clé Meta Model API (Muse Spark)
  EAURACLE_MODELE      (optionnel) force le nom du modèle

Windows PowerShell :  $env:BASETEN_API_KEY = "ta_cle"
"""

import os

from openai import OpenAI


def charger_fichier_env():
    """Lit eauracle/.env (ignoré par git) et remplit les variables absentes."""
    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    chemin = os.path.join(racine, ".env")
    if not os.path.exists(chemin):
        return
    with open(chemin, encoding="utf-8") as fichier:
        for ligne in fichier:
            ligne = ligne.strip()
            if not ligne or ligne.startswith("#") or "=" not in ligne:
                continue
            nom, valeur = ligne.split("=", 1)
            os.environ.setdefault(nom.strip(), valeur.strip().strip('"').strip("'"))


charger_fichier_env()

FOURNISSEURS = {
    "baseten": {
        "url_base": "https://inference.baseten.co/v1",
        "variable_cle": "BASETEN_API_KEY",
        "modele": "meta-models/muse-spark-open-1026",
    },
    "meta": {
        "url_base": "https://api.meta.ai/v1",
        "variable_cle": "META_API_KEY",
        "modele": "muse-spark-1.1",
    },
}


def creer_client():
    """Renvoie (client, nom_du_modele, nom_du_fournisseur)."""
    fournisseur = os.environ.get("EAURACLE_FOURNISSEUR", "baseten").lower()
    configuration = FOURNISSEURS[fournisseur]
    cle = os.environ.get(configuration["variable_cle"])
    if not cle and fournisseur == "meta":
        cle = os.environ.get("MODEL_API_KEY")  # nom utilisé dans la doc Meta
    if not cle:
        raise RuntimeError(f"Variable d'environnement {configuration['variable_cle']} manquante.")
    # Connexion parfois lente : délai généreux et plusieurs nouvelles tentatives automatiques.
    client = OpenAI(api_key=cle, base_url=configuration["url_base"], timeout=120.0, max_retries=6)
    modele = os.environ.get("EAURACLE_MODELE", configuration["modele"])
    return client, modele, fournisseur
