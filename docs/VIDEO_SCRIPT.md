# Three-minute demo script

**Language:** English  
**Optional subtitles:** French  
**Recording status:** script only; no video has been recorded.

## 0:00-0:20 — The problem

**Narration**

> In the Ouémé basin in Benin, flood risk changes across places and time. A
> useful warning cannot be only a dashboard number: it needs a decision,
> local evidence and a clear action. Eauracle is an agentic early-warning
> prototype built to connect those pieces while keeping a human authority in
> control.

**On screen**

- Ouémé basin / Benin title card.
- Dashboard warning that discharge is simulated and alerts are drafts.

## 0:20-1:30 — Live demo

### 0:20-0:45 — Calm current data

**Narration**

> First, I run the agent on today's data. The current signal is calm, so the
> agent chooses monitoring instead of creating an alert. The decision and its
> reasoning are logged.

**On screen**

- Select `Today's live data`.
- Click `Run the agent`.
- Show a low-risk zone and the decision trace.

### 0:45-1:20 — Historical replay

**Narration**

> Now I replay 4 August 2002, a historical event, so the behavior is
> reproducible for the demo. Risk rises for Bonou and Porto-Novo. Muse Spark
> Open decides to request field photos. SAM 3.1 segments visible water: on
> the Bonou image it measures the water coverage, and the result is combined
> with the model signal.

**On screen**

- Select `Replay of the August 2002 flood`.
- Select Bonou and Porto-Novo.
- Click `Run the agent`.
- Show the photo, water percentage, confidence and method label.

### 1:20-1:30 — Alert

**Narration**

> The agent drafts a short French alert with one clear action. Sending is
> simulated: the local authority must review it before any real diffusion.

**On screen**

- Show the alert draft and `envoye_simule` / simulated status.
- Show the execution trace.

## 1:30-2:30 — What was built and Meta model usage

**Narration**

> The new implementation has four parts. Open-Meteo provides rainfall and
> GloFAS modelled discharge. A time-split LightGBM model estimates flood
> onset within a configurable horizon. Muse Spark Open, using tool calling,
> decides whether to monitor, request a photo, analyze evidence, draft an
> alert and log the decision. SAM 3.1, through the Meta Model API, measures
> visible water on the photo; Muse vision is an explicitly labelled fallback
> if SAM is unavailable. The local server exposes the agent and the
> English/French dashboard.

**On screen**

- Briefly show `agent/boucle.py`, `agent/outils.py`,
  `vision/segmentation_sam.py`, `app/serveur.py`.
- Show the architecture diagram.
- Show the validation table, including the 2017 miss.

## 2:30-3:00 — Honest impact and next step

**Narration**

> Eauracle is a decision-support prototype, not an autonomous emergency
> system. The discharge is simulated, photos and delivery are simulated, and
> the model can miss events: the validation table shows a 2017 miss. The
> practical next step is to calibrate against station data, work with local
> authorities and replace illustrative images with consented field photos.
> The goal is a clearer, earlier and more accountable warning workflow.

**Real-person clarity quote — leave blank until interviewed**

> “[                                                        ]”

**On screen**

- Human-validation boundary.
- Repository URL and video end card.
