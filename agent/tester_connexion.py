"""Test minimal : le modèle répond-il, et appelle-t-il un outil ?

Usage : python agent/tester_connexion.py
Colle la sortie (ou l'erreur) dans le chat. Ne montre JAMAIS ta clé.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import creer_client  # noqa: E402

OUTIL_TEST = [
    {
        "type": "function",
        "function": {
            "name": "get_flood_risk",
            "description": "Risque d'inondation d'une zone.",
            "parameters": {
                "type": "object",
                "properties": {"zone": {"type": "string"}},
                "required": ["zone"],
            },
        },
    }
]

if __name__ == "__main__":
    client, modele, fournisseur = creer_client()
    print(f"Fournisseur : {fournisseur} | modèle : {modele}")

    reponse = client.chat.completions.create(
        model=modele, messages=[{"role": "user", "content": "Dis bonjour en une phrase, en français."}]
    )
    print("Test 1 (texte) :", reponse.choices[0].message.content)

    reponse = client.chat.completions.create(
        model=modele,
        messages=[{"role": "user", "content": "Quel est le risque d'inondation à Bonou ? Utilise l'outil."}],
        tools=OUTIL_TEST,
        tool_choice="auto",
    )
    appels = reponse.choices[0].message.tool_calls
    if appels:
        print("Test 2 (outil) : OK ->", appels[0].function.name, appels[0].function.arguments)
    else:
        print("Test 2 (outil) : AUCUN appel d'outil. Réponse :", reponse.choices[0].message.content)
