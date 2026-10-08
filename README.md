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

## Features

- **Graph engine** – NetworkX-backed directed/undirected graphs
- **Centrality suite** – degree, betweenness, closeness, eigenvector
- **Community detection** – greedy modularity communities
- **Risk scoring** – rule-based flags for high-degree bridges, dense cliques
- **Search & filter** – by node attributes and edge types
- **Import / export** – CSV, JSON, GraphML-friendly dumps
- **Streamlit UI** – interactive exploration
- **Demo mode** – synthetic network generator (no real PII)

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
│   ├── app.py              # Streamlit UI
│   └── graph_engine.py     # Core graph analysis
├── tests/
│   └── test_graph.py
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

```bash
python scripts/generate_demo_data.py
```

Generates a synthetic association network under `data/` for offline demos.

## Running the Application

```bash
streamlit run src/app.py
```

Open http://localhost:8501

## API Usage

This project is UI-first. Core analysis is available programmatically:

```python
from src.graph_engine import GraphEngine
g = GraphEngine()
g.load_csv("data/nodes.csv", "data/edges.csv")
print(g.centrality())
print(g.communities())
```

## Testing

```bash
pytest -v
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
- Risk scores are heuristic, not legal evidence.
- Demo data is synthetic and must not be treated as real investigations.

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
