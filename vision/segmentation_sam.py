"""Mesure de la part d'eau sur une photo avec SAM 3.1 (Meta Model API).

Doc : https://dev.meta.ai/docs/sam/segmenting
- POST https://api.meta.ai/v1/responses, modèle "sam-3.1", invite texte courte + image.
- Réponse en jetons texte (boîtes + masques), décodés avec le paquet `meta-sam-parser`.

Un masque est LOCAL à sa boîte : on convertit sa couverture en pixels de la photo,
puis on divise par la surface totale. Les masques qui se chevauchent peuvent compter
deux fois : le résultat est plafonné à 100 %.
"""

import asyncio
import base64
import mimetypes
import os

from meta_sam_parser import decode_mask_to_raster, image_segmentation_format, parse_responses_stream
from openai import AsyncOpenAI
from PIL import Image

URL_BASE_META = "https://api.meta.ai/v1"
MODELE_SAM = "sam-3.1"
INVITE_PAR_DEFAUT = "flood water"

# Seuils de gravité sur la part d'eau mesurée : HEURISTIQUE à calibrer, pas une norme.
SEUIL_MOYENNE_PCT = 10.0
SEUIL_ELEVEE_PCT = 30.0


def gravite_depuis_part_eau(part_eau_pct):
    if part_eau_pct >= SEUIL_ELEVEE_PCT:
        return "elevee"
    if part_eau_pct >= SEUIL_MOYENNE_PCT:
        return "moyenne"
    return "faible"


def photo_vers_url_donnees(chemin_photo):
    type_mime = mimetypes.guess_type(chemin_photo)[0] or "image/jpeg"
    with open(chemin_photo, "rb") as fichier:
        contenu = base64.b64encode(fichier.read()).decode("ascii")
    return f"data:{type_mime};base64,{contenu}"


def surface_eau_pixels(enregistrement):
    """Surface d'eau (pixels de la photo) d'un enregistrement de masque."""
    masque = enregistrement.mask
    trame = decode_mask_to_raster(masque)
    couverture = sum(trame) / (masque.width * masque.height)
    limites = enregistrement.bounds
    surface_boite = max(limites.right - limites.left, 0) * max(limites.bottom - limites.top, 0)
    return couverture * surface_boite


async def mesurer_eau_async(chemin_photo, invite=INVITE_PAR_DEFAUT, client=None, cle=None):
    with Image.open(chemin_photo) as image:
        largeur, hauteur = image.size
    if client is None:
        client = AsyncOpenAI(api_key=cle, base_url=URL_BASE_META)

    flux = await client.responses.create(
        model=MODELE_SAM,
        input=[
            {
                "type": "message",
                "role": "user",
                "content": [
                    {"type": "input_text", "text": invite},
                    {"type": "input_image", "image_url": photo_vers_url_donnees(chemin_photo)},
                ],
            }
        ],
        metadata={"mask_encoding": "one_bit", "include_confidence": "true"},
        stream=True,
    )
    analyse = parse_responses_stream(flux, image_segmentation_format())
    resultat = await analyse.final_result()

    masques = [r for r in resultat.records if getattr(r, "kind", None) == "mask"]
    surface_totale = largeur * hauteur
    surface_eau = sum(surface_eau_pixels(r) for r in masques)
    part_eau_pct = round(min(100.0, 100.0 * surface_eau / surface_totale), 1)
    confiances = [r.confidence for r in masques if r.confidence is not None]
    return {
        "invite": invite,
        "regions_detectees": len(masques),
        "part_eau_mesuree_pct": part_eau_pct,
        "gravite": gravite_depuis_part_eau(part_eau_pct),
        "confiance_moyenne": round(sum(confiances) / len(confiances), 2) if confiances else None,
        "methode": "segmentation SAM 3.1 (masques) ; seuils de gravité heuristiques",
    }


def mesurer_eau(chemin_photo, invite=INVITE_PAR_DEFAUT, client=None, cle=None):
    """Version synchrone pour l'agent."""
    if cle is None and client is None:
        cle = os.environ.get("META_API_KEY") or os.environ.get("MODEL_API_KEY")
        if not cle:
            raise RuntimeError("Clé Meta manquante (META_API_KEY ou MODEL_API_KEY).")
    return asyncio.run(mesurer_eau_async(chemin_photo, invite, client, cle))
