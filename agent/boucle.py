"""Boucle de l'agent Eauracle : le modèle décide quels outils appeler selon le risque.

Usage : python agent/boucle.py [zone1 zone2 ...] [--rejeu AAAA-MM-JJ]
Chaque exécution est enregistrée dans app/journal.json (lu par l'interface de démo).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from client import creer_client  # noqa: E402
from outils import DEFINITIONS_OUTILS, executer_outil, journal_decisions  # noqa: E402

CHEMIN_JOURNAL = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "app", "journal.json")

# Trace complète de l'exécution : un élément par appel d'outil (lue par l'interface).
trace_agent = []
meta_execution = {}

INSTRUCTIONS_SYSTEME = """Tu es Eauracle, un agent d'alerte précoce pour les inondations du bassin de l'Ouémé (Bénin).
Pour CHAQUE zone fournie, suis cette démarche :
1. Appelle get_flood_risk pour obtenir le risque.
2. Risque faible : surveillance seulement. Journalise ta décision avec log_decision, aucune alerte.
3. Risque moyen ou élevé : appelle request_photos, puis analyze_flood_photo sur la photo reçue,
   et recoupe la gravité visuelle avec le score de risque.
4. Si la photo est indisponible ou l'analyse échoue, décide avec le score seul et dis-le dans ta justification.
5. Décide du niveau (vigilance, alerte ou urgence), appelle draft_alert puis send_alert avec le message EXACT renvoyé par draft_alert.
   Règle de prudence : le niveau "urgence" exige une confirmation (photo avec gravité élevée, ou niveau "crue en cours").
   Sans photo, le niveau maximal est "alerte".
6. Termine chaque zone par log_decision avec une justification factuelle courte.
Règles : ne jamais inventer de chiffres ; n'utilise que les résultats des outils. Le débit est SIMULÉ (GloFAS) :
ne le présente pas comme une mesure de station. Réponse finale : un résumé court, en français, une ligne par zone."""


def enregistrer_trace(numero, nom, arguments_json, resultat_json):
    """Ajoute un appel d'outil à la trace (arguments et résultat convertis en objets JSON)."""
    try:
        arguments = json.loads(arguments_json or "{}")
    except ValueError:
        arguments = {"brut": arguments_json}
    try:
        resultat = json.loads(resultat_json)
    except ValueError:
        resultat = {"brut": resultat_json}
    trace_agent.append({"tour": numero, "outil": nom, "arguments": arguments, "resultat": resultat})


def ecrire_journal(resume):
    """Écrit app/journal.json : méta-données, trace, résumé et décisions."""
    contenu = {
        "meta": {
            "date": os.environ.get("EAURACLE_DATE_REJEU") or None,
            "rejeu": bool(os.environ.get("EAURACLE_DATE_REJEU")),
            **meta_execution,
        },
        "trace": trace_agent,
        "resume": resume,
        "decisions": journal_decisions,
    }
    os.makedirs(os.path.dirname(CHEMIN_JOURNAL), exist_ok=True)
    with open(CHEMIN_JOURNAL, "w", encoding="utf-8") as fichier:
        json.dump(contenu, fichier, indent=2, ensure_ascii=False)
    print(f"[agent] journal enregistré : {CHEMIN_JOURNAL}")


def lancer_agent(zones, client=None, modele=None, iterations_max=20, afficher=print):
    """Fait tourner l'agent sur une liste de zones et renvoie son résumé final."""
    if client is None:
        client, modele, fournisseur = creer_client()
        afficher(f"[agent] fournisseur={fournisseur} modèle={modele}")
        meta_execution.update({"fournisseur": fournisseur, "modele": modele})

    messages = [
        {"role": "system", "content": INSTRUCTIONS_SYSTEME},
        {"role": "user", "content": "Analyse ces zones et agis : " + ", ".join(zones)},
    ]
    for numero in range(1, iterations_max + 1):
        reponse = client.chat.completions.create(
            model=modele, messages=messages, tools=DEFINITIONS_OUTILS, tool_choice="auto"
        )
        message = reponse.choices[0].message
        appels = message.tool_calls or []
        entree = {"role": "assistant", "content": message.content or ""}
        if appels:
            entree["tool_calls"] = [
                {
                    "id": appel.id,
                    "type": "function",
                    "function": {"name": appel.function.name, "arguments": appel.function.arguments},
                }
                for appel in appels
            ]
        messages.append(entree)

        if not appels:
            return message.content

        for appel in appels:
            afficher(f"[agent] tour {numero} -> {appel.function.name}({appel.function.arguments})")
            resultat = executer_outil(appel.function.name, appel.function.arguments)
            afficher(f"[outil]  {resultat[:300]}")
            enregistrer_trace(numero, appel.function.name, appel.function.arguments, resultat)
            messages.append({"role": "tool", "tool_call_id": appel.id, "content": resultat})
    return "Arrêt : nombre maximal d'itérations atteint."


if __name__ == "__main__":
    arguments = sys.argv[1:]
    if "--rejeu" in arguments:
        position = arguments.index("--rejeu")
        os.environ["EAURACLE_DATE_REJEU"] = arguments[position + 1]
        print(f"[agent] REJEU HISTORIQUE au {arguments[position + 1]} (pas des données du jour)")
        arguments = arguments[:position] + arguments[position + 2:]
    zones_a_analyser = arguments or ["Bonou", "Porto-Novo"]
    resume = lancer_agent(zones_a_analyser)
    print("\n=== RÉSUMÉ DE L'AGENT ===\n" + str(resume))
    print("\n=== JOURNAL DES DÉCISIONS ===")
    print(json.dumps(journal_decisions, indent=2, ensure_ascii=False))
    ecrire_journal(resume)