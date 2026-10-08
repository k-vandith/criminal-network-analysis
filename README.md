# Criminal Network Analysis System

AI-powered graph intelligence platform for analysing criminal networks using **synthetic data only**.

## Problem Statement

Investigators need tools to map relationships among persons, organisations, accounts, vehicles and events, identify central actors, detect communities, and score risk — without relying on real personal data during development and demos.

## Overview

This project builds a NetworkX-based graph, computes centrality metrics, detects communities, flags suspicious relationships, scores entity risk, and visualises the network with Plotly inside a Streamlit dashboard.

## Features

- Entity types: person, organization, location, account, phone, vehicle, event
- Relationship graph construction
- Degree / betweenness / closeness / eigenvector centrality
- Community detection (greedy modularity)
- Heuristic risk scoring
- Suspicious relationship identification
- Entity search and event timeline
- Plotly interactive graph visualisation
- JSON import/export
- Fully offline synthetic demo

## Tech Stack

Python 3.11+, NetworkX, Pandas, Plotly, Streamlit, scikit-learn, pytest

## Installation

### Windows (PowerShell)
```powershell
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Linux / macOS
```bash
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Demo Mode
```bash
python scripts/generate_demo_data.py
streamlit run src/app.py
```

## Testing
```bash
pytest -v
```

## Limitations

- Synthetic data only — no real individuals
- Risk scores are heuristic, not predictive of real-world behaviour
- Designed for research / training demos

## Security / Privacy

No real personal data is used or stored. All entities are fictional.

## License

MIT
