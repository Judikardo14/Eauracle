# Prior work (before the hackathon)

Only two things existed before 26 October 2026. Neither is part of the hackathon submission.

| Item | What it is | Status in this repo |
|---|---|---|
| Eauracle idea | Concept that won 1st prize at the UNESCO Water4Future hackathon (idea only, no code at the time) | Concept only; all code is new |
| `Prediction-du-Risque-d-Inondation-ATUT` | LightGBM notebook on the Kaggle Playground S4E5 **synthetic** dataset | Not copied; the risk model here is rewritten from scratch on real regional data |

## New work (26 Oct – 4 Nov 2026)

All implementation in this repository was created for the Meta hackathon:
data ingestion, the regional risk model, Muse Spark agent and tools, SAM 3.1
vision integration, alert generation, execution journaling and the local demo
interface. The public commit history records this work.

The prior ATUT notebook is not used as training data, code or a baseline
implementation here. The current model is trained from the Open-Meteo
historical series described in the README and [docs/VALIDATION.md](docs/VALIDATION.md).
