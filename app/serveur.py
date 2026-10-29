"""Serveur local de démo Eauracle : sert l'interface (app/) et lance le VRAI agent à la demande.

Usage (depuis le dossier racine eauracle/) :
    python app/serveur.py
puis ouvrir http://localhost:8000

Routes :
    GET  /api/etat    -> statut du lancement en cours + trace partielle (l'interface l'interroge toutes les 0,8 s)
    POST /api/lancer  -> {"zones": ["Bonou", ...], "date": "2002-08-04" ou ""} ; "" = données du jour
Le serveur n'écoute que sur 127.0.0.1 (ta machine) et ne contient aucune clé : elles restent dans .env.
"""

import json
import os
import re
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

DOSSIER_APP = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.dirname(DOSSIER_APP)
sys.path.insert(0, os.path.join(RACINE, "agent"))

import boucle  # noqa: E402
import outils  # noqa: E402

PORT = int(os.environ.get("EAURACLE_PORT", "8000"))
MOTIF_ZONE = re.compile(r"^[A-Za-zÀ-ÿ\- ]{1,40}$")
MOTIF_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

verrou = threading.Lock()
etat = {"statut": "inactif", "erreur": None, "resume": "", "date": None}


def executer_agent(zones, date):
    """Exécute l'agent dans un fil séparé ; la trace se remplit au fur et à mesure."""
    try:
        resume = boucle.lancer_agent(zones, afficher=lambda message: print(message, flush=True))
        etat["resume"] = resume or ""
        boucle.ecrire_journal(resume)
        etat["statut"] = "termine"
    except Exception as erreur:  # on montre la cause dans l'interface au lieu de planter
        etat["erreur"] = f"{type(erreur).__name__}: {erreur}"
        etat["statut"] = "erreur"
        print(f"[serveur] échec de l'agent : {etat['erreur']}", flush=True)


def lire_etat():
    return {
        "statut": etat["statut"],
        "erreur": etat["erreur"],
        "resume": etat["resume"],
        "meta": {"date": etat["date"], "rejeu": bool(etat["date"]), **boucle.meta_execution},
        "trace": list(boucle.trace_agent),
    }


class Gestionnaire(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):  # journal silencieux : on garde le terminal lisible
        pass

    def envoyer_json(self, code, objet):
        corps = json.dumps(objet, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(corps)))
        self.end_headers()
        self.wfile.write(corps)

    def do_GET(self):
        if self.path.split("?")[0] == "/api/etat":
            self.envoyer_json(200, lire_etat())
        else:
            super().do_GET()

    def do_POST(self):
        if self.path != "/api/lancer":
            self.envoyer_json(404, {"erreur": "route inconnue"})
            return
        try:
            longueur = int(self.headers.get("Content-Length", 0))
            demande = json.loads(self.rfile.read(longueur) or "{}")
            zones = [str(zone) for zone in demande.get("zones", [])]
            date = str(demande.get("date") or "")
        except (ValueError, TypeError):
            self.envoyer_json(400, {"erreur": "requête invalide"})
            return
        if not 1 <= len(zones) <= 5 or not all(MOTIF_ZONE.match(zone) for zone in zones):
            self.envoyer_json(400, {"erreur": "zones invalides"})
            return
        if date and not MOTIF_DATE.match(date):
            self.envoyer_json(400, {"erreur": "date invalide (format AAAA-MM-JJ)"})
            return
        with verrou:
            if etat["statut"] == "en_cours":
                self.envoyer_json(409, {"erreur": "un lancement est déjà en cours"})
                return
            etat.update({"statut": "en_cours", "erreur": None, "resume": "", "date": date or None})
            boucle.trace_agent.clear()
            boucle.meta_execution.clear()
            outils.journal_decisions.clear()
            if date:
                os.environ["EAURACLE_DATE_REJEU"] = date
            else:
                os.environ.pop("EAURACLE_DATE_REJEU", None)
        threading.Thread(target=executer_agent, args=(zones, date), daemon=True).start()
        self.envoyer_json(202, {"statut": "en_cours"})


if __name__ == "__main__":
    serveur = ThreadingHTTPServer(("127.0.0.1", PORT), partial(Gestionnaire, directory=DOSSIER_APP))
    print(f"Eauracle : interface sur http://localhost:{PORT}  (Ctrl+C pour arrêter)")
    try:
        serveur.serve_forever()
    except KeyboardInterrupt:
        print("\nServeur arrêté.")
