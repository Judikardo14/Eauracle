# Eauracle

**Eauracle** is an agentic early-warning prototype for flood risk in the Ouémé basin (Benin).  
Built for the **Meta Global AI Developer Hackathon (Indie track)**.

The system combines:
- hydrometeorological signals (river discharge + rainfall),
- a calibrated risk model (LightGBM),
- an LLM agent with tool calling (Muse Spark),
- image-based flood verification (SAM 3.1 + Muse vision),
- simulated alert drafting and delivery in French.

---

## 1) What the agent does

For each monitored zone, the agent follows this flow:
1. Compute flood risk (`get_flood_risk`).
2. If risk is low: continue monitoring and log decision.
3. If risk is medium/high: request local photos (`request_photos`), analyze flood severity (`analyze_flood_photo`).
4. Draft a short actionable alert (`draft_alert`) with level:
   - `vigilance`
   - `alerte`
   - `urgence` (only if confirmed by photo or ongoing flood condition)
5. Send alert in **simulated mode** (`send_alert`) and log rationale (`log_decision`).

All alerts are demo drafts and should be human-validated by local authorities before real-world use.

---

## 2) Data sources and monitored zones

### Sources
- **River discharge**: Open-Meteo Flood API (GloFAS model)  
  ⚠️ Simulated/modelled discharge, not gauge station measurements.
- **Rainfall (live mode)**: Open-Meteo Forecast API.
- **Rainfall (historical training)**: Open-Meteo Archive API (ERA5 reanalysis).

### Monitored zones (Ouémé basin)
- Betérou (9.10, 2.26)
- Bonou (6.83, 2.45)
- Adjohoun (6.60, 2.48)
- Dangbo (6.50, 2.48)
- Porto-Novo (6.44, 2.73)

`Savè` was removed from active monitoring because no valid river cell was found in calibration.

### Known data gap
- In local checks, **Bonou discharge contains missing values from 1984 to 1996** in the downloaded historical series.  
  As a result, effective model training for that zone starts later (roughly from 1997).

---

## 3) Project structure

- `data/`
  - `ingestion.py`: live discharge/rain retrieval by zone
  - `historique.py`: historical cache builder (1984 -> today-7d)
  - `calibrer_zones.py`: calibration helper (not part of normal run)
- `risk_model/`
  - `caracteristiques.py`: feature engineering + prediction target horizon
  - `entrainer.py`: LightGBM training / validation / test and thresholds
  - `inference.py`: live or replay risk inference
  - `trouver_crues.py`: identify major flood peaks and replay candidates
- `agent/`
  - `client.py`: Baseten/Meta OpenAI-compatible client
  - `outils.py`: all agent tools
  - `boucle.py`: agent tool-calling loop
  - `tester_connexion.py`: connectivity smoke test
- `vision/`
  - `segmentation_sam.py`: SAM 3.1 water segmentation
  - `analyse_photo.py`: SAM + Muse vision fallback pipeline
- `app/`, `alerts/`, `docs/`: demo interface/docs work in progress

---

## 4) Setup

### Requirements
- Python 3.x
- Internet access for APIs
- API key(s) for at least one model provider

Install dependencies:

```bash
pip install -r requirements.txt
```

### Environment variables

Copy `.env.example` to `.env` and set your keys:

```env
BASETEN_API_KEY=...
# META_API_KEY=...
# EAURACLE_FOURNISSEUR=baseten
# EAURACLE_MODELE=...
```

Supported providers in `agent/client.py`:
- `baseten` (default): `meta-models/muse-spark-open-1026`
- `meta`: `muse-spark-1.1`

---

## 5) Quick start

From repository root:

```bash
python agent/tester_connexion.py
python data/historique.py
```

Set training configuration (PowerShell example):

```powershell
$env:EAURACLE_CENTILE = "0.90"
$env:EAURACLE_HORIZON = "5"
```

Train risk model:

```bash
python risk_model/entrainer.py
```

Find replay dates for major floods:

```bash
python risk_model/trouver_crues.py Bonou
```

Run agent in historical replay mode:

```bash
python agent/boucle.py Bonou Porto-Novo --rejeu 2002-08-04
```

Run agent in live mode:

```bash
python agent/boucle.py Bonou Porto-Novo
```

---

## 6) Model objective and reported metrics

### Objective
Predict **flood onset within the next N days** (default horizon from `EAURACLE_HORIZON`) while the river is still below its flood threshold.

### Training split
- Train: years <= 2016
- Validation: 2017-2019
- Test: >= 2020

### Reported test snapshot (from local project recap)
- AUC: **0.962**
- Naive baseline AUC (relative discharge only): **0.960**
- Average precision: **0.361**
- Naive baseline average precision: **0.310**
- Number of flood-onset positives in test: **210**

Interpretation: useful signal, but only a modest gain versus baseline; agent decisions also rely on rainfall trends and photo evidence.

---

## 7) Honesty and safety notes

- Discharge comes from a simulation model (GloFAS), not station measurements.
- Alert sending is simulated (`envoye_simule`), not connected to real emergency channels.
- Local relay photos in the demo are illustrative; verify rights before public reuse.
- SAM severity thresholds (10% / 30% water coverage) are heuristic and should be calibrated.
- If SAM fails, the pipeline falls back to Muse vision estimation and explicitly states the method.
- This prototype supports decision assistance, not autonomous civil-protection action.

---

## 8) What is new vs prior work

See [PRIOR_WORK.md](PRIOR_WORK.md).  
In summary: only the concept existed before the hackathon; this repository’s implementation is new work.
