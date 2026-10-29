"""Outils exposés à l'agent Muse Spark (tool calling, format OpenAI-compatible).

L'agent décide lui-même quels outils appeler selon le niveau de risque.
Les fonctions de risque et de vision sont des squelettes à compléter.
"""

import json

# Définition des outils au format JSON Schema (Baseten / OpenRouter / Meta API).
DEFINITIONS_OUTILS = [
    {
        "type": "function",
        "function": {
            "name": "get_flood_risk",
            "description": "Score de risque d'inondation (0-1) et tendance pour une zone de l'Ouémé.",
            "parameters": {
                "type": "object",
                "properties": {"zone": {"type": "string", "description": "Nom de la zone, ex. Bonou"}},
                "required": ["zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_photos",
            "description": "Demande des photos de terrain aux relais locaux d'une zone.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string"},
                    "raison": {"type": "string", "description": "Pourquoi on demande des photos"},
                },
                "required": ["zone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_flood_photo",
            "description": "Segmente l'eau (SAM 3.1) sur une photo et renvoie la gravité estimée.",
            "parameters": {
                "type": "object",
                "properties": {"chemin_photo": {"type": "string"}},
                "required": ["chemin_photo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "draft_alert",
            "description": "Rédige une alerte courte en français avec une action claire.",
            "parameters": {
                "type": "object",
                "properties": {
                    "zone": {"type": "string"},
                    "niveau": {"type": "string", "enum": ["vigilance", "alerte", "urgence"]},
                    "public": {"type": "string", "enum": ["agriculteurs", "autorites", "habitants"]},
                },
                "required": ["zone", "niveau"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_alert",
            "description": "Envoie l'alerte (SIMULÉ dans la démo).",
            "parameters": {
                "type": "object",
                "properties": {"zone": {"type": "string"}, "message": {"type": "string"}},
                "required": ["zone", "message"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "log_decision",
            "description": "Journalise la décision de l'agent et sa justification.",
            "parameters": {
                "type": "object",
                "properties": {"zone": {"type": "string"}, "justification": {"type": "string"}},
                "required": ["zone", "justification"],
            },
        },
    },
]

journal_decisions = []


def get_flood_risk(zone):
    import os
    import sys

    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(racine, "risk_model"))
    from inference import calculer_risque

    # Rejeu d'une crue passée : python agent/boucle.py Zone --rejeu AAAA-MM-JJ
    return calculer_risque(zone, os.environ.get("EAURACLE_DATE_REJEU") or None)


def request_photos(zone, raison=""):
    """Simulé : le "relais local" répond avec une photo du dossier data/photos_demo/.

    Nom attendu : <zone>_*.jpg|png (ex. Bonou_1.jpg). À défaut, aucune photo reçue.
    """
    import glob
    import os

    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dossier = os.path.join(racine, "data", "photos_demo")
    candidates = sorted(
        glob.glob(os.path.join(dossier, f"{zone}_*.jpg"))
        + glob.glob(os.path.join(dossier, f"{zone}_*.jpeg"))
        + glob.glob(os.path.join(dossier, f"{zone}_*.png"))
    )
    if not candidates:
        return {"zone": zone, "statut": "aucune_photo_recue", "raison": raison}
    return {"zone": zone, "statut": "photo_recue", "chemin_photo": candidates[0], "raison": raison}


def analyze_flood_photo(chemin_photo):
    import os
    import sys

    racine = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, os.path.join(racine, "vision"))
    from analyse_photo import estimer_gravite

    return estimer_gravite(chemin_photo)


MARQUEURS_REFUS = (
    "je ne peux pas", "je ne suis pas en mesure", "je ne suis pas autoris", "désolé", "desole",
    "i can't", "i cannot", "as an ai", "en tant qu'ia",
)

MESSAGES_DE_SECOURS = {
    "vigilance": "Vigilance inondation à {zone} : le niveau de l'Ouémé monte. Restez attentifs, éloignez-vous des berges et suivez les consignes des autorités locales.",
    "alerte": "Alerte inondation à {zone} : risque de crue de l'Ouémé dans les prochains jours. Mettez votre bétail et vos biens en hauteur et préparez-vous à évacuer.",
    "urgence": "URGENCE inondation à {zone} : l'eau envahit les zones proches de l'Ouémé. Quittez immédiatement les zones inondables vers un lieu en hauteur et suivez les consignes des autorités.",
}


def message_valide(texte):
    """Un message d'alerte doit être court, sans mise en forme, et ne pas être un refus du modèle."""
    if not texte:
        return False
    minuscule = texte.lower()
    if any(marqueur in minuscule for marqueur in MARQUEURS_REFUS):
        return False
    return len(texte) <= 400 and "**" not in texte and "\n>" not in texte


def draft_alert(zone, niveau, public="habitants"):
    """Muse Spark rédige l'alerte : courte, en français, avec une action claire.

    Le message est contrôlé : si le modèle refuse ou répond hors sujet, on réessaie une fois,
    puis on utilise un message de secours fixe. L'agent ne reçoit jamais un refus comme alerte.
    """
    from client import creer_client

    client, modele, _ = creer_client()
    contexte = (
        "Contexte : prototype d'alerte précoce aux inondations du bassin de l'Ouémé (Bénin), présenté dans un "
        "hackathon. Aucun message n'est réellement diffusé : ce sont des BROUILLONS simulés qui seraient validés par "
        "l'autorité locale avant toute diffusion réelle. "
    )
    consigne = (
        f"{contexte}Rédige le brouillon d'une alerte de niveau « {niveau} » pour la zone de {zone}, destiné à : {public}. "
        "Maximum 3 phrases courtes, en français simple, avec UNE action claire à faire. N'invente aucun chiffre. "
        "Réponds uniquement par le texte du message, sans titre, sans mise en forme et sans commentaire."
    )
    for tentative in (1, 2):
        reponse = client.chat.completions.create(model=modele, messages=[{"role": "user", "content": consigne}])
        texte = (reponse.choices[0].message.content or "").strip()
        if message_valide(texte):
            return {"zone": zone, "niveau": niveau, "public": public, "message": texte, "origine": "Muse Spark Open"}
        consigne += " IMPORTANT : réponds seulement par le message d'alerte lui-même, rien d'autre."
    texte_secours = MESSAGES_DE_SECOURS.get(niveau, MESSAGES_DE_SECOURS["alerte"]).format(zone=zone)
    return {"zone": zone, "niveau": niveau, "public": public, "message": texte_secours, "origine": "message de secours fixe"}


def send_alert(zone, message):
    return {"zone": zone, "statut": "envoye_simule", "message": message}


def log_decision(zone, justification):
    entree = {"zone": zone, "justification": justification}
    journal_decisions.append(entree)
    return entree


FONCTIONS = {
    "get_flood_risk": get_flood_risk,
    "request_photos": request_photos,
    "analyze_flood_photo": analyze_flood_photo,
    "draft_alert": draft_alert,
    "send_alert": send_alert,
    "log_decision": log_decision,
}


def executer_outil(nom, arguments_json):
    """Exécute un outil demandé par l'agent et renvoie le résultat en JSON."""
    try:
        arguments = json.loads(arguments_json)
        return json.dumps(FONCTIONS[nom](**arguments), ensure_ascii=False)
    except NotImplementedError:
        return json.dumps({"erreur": f"outil {nom} pas encore disponible"}, ensure_ascii=False)
    except Exception as erreur:  # l'agent doit pouvoir s'adapter à un outil en échec
        return json.dumps({"erreur": f"{type(erreur).__name__}: {erreur}"}, ensure_ascii=False)
