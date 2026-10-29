"""Vérification terrain : estime la gravité d'une inondation à partir d'une photo.

Étape 1 (ici) : Muse Spark Open (entrée image) estime la part d'eau visible et la gravité.
Étape 2 (plus tard, si l'accès existe) : SAM 3.1 segmente l'eau pour MESURER la part d'eau.

Honnêteté : tant que SAM 3.1 n'est pas branché, la part d'eau est une ESTIMATION du modèle,
pas une mesure par segmentation. Le champ "methode" l'indique.
"""

import base64
import json
import mimetypes
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent"))

CONSIGNE = (
    "Tu analyses une photo envoyée par un relais local pendant une possible inondation au Bénin. "
    "Décris uniquement ce qui est visible. Réponds par UN SEUL objet JSON, sans autre texte, avec les clés : "
    '"eau_visible" (true/false), "part_eau_estimee_pct" (entier 0-100, part de la scène couverte par de l\'eau), '
    '"gravite" ("faible", "moyenne" ou "elevee"), "indices" (liste de 2 à 4 courtes observations), '
    '"confiance" (nombre entre 0 et 1). Si l\'image est floue ou ne montre pas d\'eau, dis-le et baisse la confiance.'
)


def photo_vers_url_donnees(chemin_photo):
    type_mime = mimetypes.guess_type(chemin_photo)[0] or "image/jpeg"
    with open(chemin_photo, "rb") as fichier:
        contenu = base64.b64encode(fichier.read()).decode("ascii")
    return f"data:{type_mime};base64,{contenu}"


def extraire_json(texte):
    """Récupère le premier objet JSON d'une réponse (le modèle peut ajouter du texte autour)."""
    correspondance = re.search(r"\{.*\}", texte or "", re.DOTALL)
    if not correspondance:
        raise ValueError("aucun JSON dans la réponse du modèle")
    return json.loads(correspondance.group(0))


def decrire_avec_muse(chemin_photo, client=None, modele=None):
    if client is None:
        from client import creer_client

        client, modele, _ = creer_client()

    reponse = client.chat.completions.create(
        model=modele,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": CONSIGNE},
                    {"type": "image_url", "image_url": {"url": photo_vers_url_donnees(chemin_photo)}},
                ],
            }
        ],
    )
    resultat = extraire_json(reponse.choices[0].message.content)
    resultat["methode"] = "estimation par Muse Spark Open (vision), pas de segmentation"
    resultat["photo"] = os.path.basename(chemin_photo)
    return resultat


def estimer_gravite(chemin_photo, client=None, modele=None):
    """Mesure l'eau avec SAM 3.1 puis décrit la scène avec Muse Spark Open.

    Si SAM est indisponible (clé absente, erreur), repli sur l'estimation de Muse seule,
    clairement signalé dans "methode". L'agent reçoit toujours un résultat exploitable.
    """
    if not os.path.exists(chemin_photo):
        return {"erreur": f"photo introuvable : {chemin_photo}"}
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    problemes = []

    mesure = None
    try:
        from segmentation_sam import mesurer_eau

        mesure = mesurer_eau(chemin_photo)
    except Exception as erreur:
        problemes.append(f"SAM indisponible ({type(erreur).__name__}: {erreur})")

    description = None
    try:
        description = decrire_avec_muse(chemin_photo, client, modele)
    except Exception as erreur:
        problemes.append(f"Muse vision indisponible ({type(erreur).__name__}: {erreur})")

    if mesure is None and description is None:
        return {"erreur": "analyse impossible", "problemes": problemes}

    resultat = {"photo": os.path.basename(chemin_photo)}
    if mesure is not None:
        resultat.update(
            part_eau_mesuree_pct=mesure["part_eau_mesuree_pct"],
            regions_detectees=mesure["regions_detectees"],
            confiance_sam=mesure["confiance_moyenne"],
            gravite=mesure["gravite"],
            methode=mesure["methode"],
        )
        if description is not None:
            resultat["description_muse"] = description.get("indices", [])
            resultat["gravite_estimee_par_muse"] = description.get("gravite")
    else:
        resultat.update(description)
    if problemes:
        resultat["problemes"] = problemes
    return resultat
