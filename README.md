# Criminal Network Analysis System

Graph-based analysis platform for exploring relationships, centrality, communities, and risk in criminal association networks. Built for investigators and analysts working with structured relationship data.

## Problem Statement

Law-enforcement and compliance teams need to map associations between persons, organisations, locations, and events. Manual spreadsheets do not scale; analysts need centrality measures, community detection, path finding, and risk scoring on interactive graphs — offline and without sending data to third-party SaaS.

## Overview

This project provides:

- Import of nodes and edges from CSV / JSON
- Interactive graph visualisation (Streamlit + Plotly)
- Degree, betweenness, closeness, and eigenvector centrality
- Community detection (greedy modularity)
- Suspicious-pattern heuristics and risk scores
- Export of subgraphs and analysis reports
- Fully offline demo mode with synthetic data

## Features (V3 intelligence workspace)

The UI is a desktop investigation workspace, not a tabbed dashboard:

- Left navigation rail: Overview, Network, Investigate, Entities, Signals, Timeline, Cases, Reports, Settings
- Command search across entity name, ID, type, and relationship type
- Central network map with risk, community, and type color modes, labels, hop focus, and path highlight
- Right-side entity intelligence panel driven by the selected entity
- Signal center for bridge candidates, anomalies, suspicious links, and potential links
- Community cards that filter the map
- Local JSON case files (`data/cases/cases.json`)
- Report builder for local HTML and PDF
- Analytical priority is a heuristic review signal, not legal evidence

## Previous feature set still in the engine

- **Dark analyst console** – overview metrics, priority queue, and filtered workspace
- **Graph engine** – NetworkX weighted undirected graph (`CriminalNetworkGraph`)
- **Centrality suite** – degree, weighted betweenness, closeness, eigenvector (numpy fallback)
- **Analytical priority** – explainable composite heuristic (not a finding of guilt)
- **Bridge candidates** – entities linking different communities
- **Anomaly candidates** – degree and weighted-degree z-score signals for review
- **Community summaries** – size, density, dominant type, core entity
- **Entity investigation** – profile, reasons, neighbors, shortest relationship path
- **Link prediction** and suspicious-relationship heuristics
- **Timeline** for synthetic event entities
- **Local HTML / PDF reports** (PDF falls back to HTML if ReportLab is missing)
- **Demo mode** – synthetic network generator only (no real persons)

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Streamlit  │────▶│ Graph Engine │────▶│  NetworkX   │
│     UI      │     │  (analysis)  │     │  + metrics  │
└─────────────┘     └──────┬───────┘     └─────────────┘
                           │
                    ┌──────▼───────┐
                    │  CSV / JSON  │
                    │  data layer  │
                    └──────────────┘
```

## Tech Stack

- Python 3.11+
- NetworkX
- Streamlit + Plotly
- Pandas / NumPy
- scikit-learn (optional clustering helpers)
- pytest

## Repository Structure

```
criminal-network-analysis/
├── README.md
├── requirements.txt
├── .gitignore
├── src/
│   ├── app.py              # Streamlit intelligence console
│   ├── graph_engine.py     # Core graph analysis
│   └── graph_features.py   # Analyst features (monkey-patched)
├── tests/
│   ├── test_graph.py
│   └── test_advanced_features.py
├── data/
├── scripts/
│   ├── setup_env.py
│   ├── setup.sh
│   ├── setup.ps1
│   └── generate_demo_data.py
└── docs/
```

## System Requirements

| Mode   | CPU        | RAM  | Disk | GPU        |
|--------|------------|------|------|------------|
| Demo   | Any modern | 2 GB | 1 GB | Not needed |

## Installation

### Recommended (all platforms) — automated bootstrap

Handles missing `ensurepip`, symlink restrictions, and installs dependencies into `.venv`:

```bash
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python3 scripts/setup_env.py    # or:  python scripts/setup_env.py
```

Then activate:

```bash
# Linux / macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

### Manual setup

#### Windows (PowerShell)

```powershell
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python -m venv .venv --copies
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### Linux / macOS

```bash
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
# If venv fails with ensurepip errors:
#   sudo apt install python3-venv python3-pip
python3 -m venv .venv --copies
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### Why `--copies`?

Some environments cannot create symlinks inside a venv (`Operation not permitted` on `lib64 → lib`). Using `--copies` avoids that. `scripts/setup_env.py` tries `--copies` first automatically.

## Environment Variables

Optional. Defaults work for demo mode. See `.env.example` if present.

## Dataset / Demo Mode

Synthetic data only. Do not load real case files into a public clone.

### Windows (PowerShell)

```powershell
cd criminal-network-analysis
.venv\Scripts\Activate.ps1
python scripts/generate_demo_data.py
python -m pytest -q
streamlit run src/app.py
```

### Linux / macOS

```bash
cd criminal-network-analysis
source .venv/bin/activate
python scripts/generate_demo_data.py
python -m pytest -q
streamlit run src/app.py
```

Generates `data/sample/synthetic_network.json` for offline demos. Open http://localhost:8501

## API Usage

This project is UI-first. Core analysis is available programmatically:

```python
from src.graph_engine import CriminalNetworkGraph
import src.graph_features  # registers analyst methods

g = CriminalNetworkGraph()
g.import_json("data/sample/synthetic_network.json")
print(g.centrality_analysis())
print(g.key_player_ranking(10))
print(g.bridge_entities())
```

`kingpin_score` is the historical column name for **analytical priority**. It is a heuristic, not evidence.

## Testing

```bash
python -m pytest -q
```

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError: src` | Run from project root with `PYTHONPATH=.` |
| `venv` / ensurepip fails | Run `python3 scripts/setup_env.py` or install `python3-venv` |
| `Operation not permitted` on lib64 | Use `python3 -m venv .venv --copies` |
| Plotly blank chart | Ensure browser allows WebGL; update plotly |

## Limitations

- Designed for moderate-size graphs (thousands of nodes), not billion-edge graphs.
- Analytical risk and analytical priority are heuristics. They are **not** proof of guilt, not a legal finding, and not evidence.
- The system is an offline synthetic demonstration. It does not harvest external data and must not be loaded with real-person case data in a public repository.
- Community detection, bridge ratios, anomaly z-scores, and link scores are signals for analyst review only.
- The graph is undirected. Betweenness uses edge `weight`. Eigenvector falls back to a NumPy solver, then zeros, if power iteration does not converge.

## Security / Privacy

- No network calls required for core analysis.
- Do not commit real case data; use synthetic demos for public repos.
- Designed for defensive investigative analytics only.

## Future Improvements

- GraphML / Neo4j connectors
- Temporal edge analysis
- Role-based access for multi-analyst deployments

## License

MIT
