<p align="center">
  <img src="docs/linklens-mark.svg" alt="LinkLens logo" width="76">
</p>

<h1 align="center">LinkLens</h1>
<p align="center">Local-first, explainable network analysis for relationship data.</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/k-vandith/criminal-network-analysis/tests.yml?branch=main&label=CI" alt="CI status">
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/License-MIT-777777" alt="MIT License">
</p>

LinkLens turns CSV/JSON interaction records into an interactive graph with centrality rankings, communities, timelines, candidate links, and exportable case reports. Analysis runs locally without paid API keys.

## Features

- Import CSV/JSON interactions or separate entity and relationship files.
- Explore connections, communities, timelines, and explainable review signals.
- Export HTML/PDF case reports and use a CSV template.
- Try the built-in fictional sample case.

## Quick start

**Windows (PowerShell)**

\`\`\`powershell
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python run.py
\`\`\`

**macOS / Linux**

\`\`\`bash
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python run.py
\`\`\`

Open [http://127.0.0.1:8501](http://127.0.0.1:8501).

## Input format

A basic interaction CSV can use these columns:

\`\`\`csv
source,target,relationship,date,weight
ENTITY-01,ENTITY-02,phone contact,2025-02-04,2
ENTITY-02,ORG-01,associated with,2025-02-07,1
\`\`\`

Map the source and target columns during import. Relationship, date, weight, and display names are optional. Stable IDs and accurate source records improve the meaning of the analysis.

## Validate

\`\`\`bash
python -m pytest -q
\`\`\`

## Important limitations

- Centrality, communities, suspicious-pattern signals, and candidate links are structural clues—not proof of criminal activity, identity, guilt, or intent.
- Validate imported records and review findings in context; false positives are possible.
- The graph is undirected, so directional or time-dependent relationships may be simplified.
- The sample case is fictional. Use it for demonstrations, not real investigations.
- This local app has no user accounts or role-based access controls. Keep it on a trusted machine; do not expose it directly to untrusted networks.

## License

MIT — see [LICENSE](LICENSE).
