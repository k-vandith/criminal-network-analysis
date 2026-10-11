<p align="center">
  <img src="assets/linklens-logo.svg" alt="LinkLens logo" width="76">
</p>

<h1 align="center">LinkLens</h1>
<p align="center">Local-first network exploration and explainable structural analytics for CSV/JSON relationship data.</p>

<p align="center">
  <a href="https://github.com/k-vandith/criminal-network-analysis/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/k-vandith/criminal-network-analysis/tests.yml?branch=main&label=tests" alt="Tests"></a>
  <img src="https://img.shields.io/badge/Python-3.11%2B-3776AB" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/License-MIT-777777" alt="MIT License">
</p>

## What it does
- Explore relationship graphs and rank entities by connections, bridges, and network structure.
- Review communities, timelines, heuristic patterns, and candidate missing links.
- Import CSV/JSON with column mapping and validation; export HTML/PDF case reports.
- Process cases locally without a paid analysis API.

## Data flow
\`\`\`mermaid
flowchart LR
  A[CSV / JSON] --> B[Validate and map]
  B --> C[NetworkX graph]
  C --> D[Explore, rank, group, timeline]
  D --> E[HTML / PDF report]
\`\`\`

## Quick start
\`\`\`bash
git clone https://github.com/k-vandith/criminal-network-analysis.git
cd criminal-network-analysis
python -m venv .venv
\`\`\`

Activate the environment, then install and run:

- **Windows PowerShell:** \`.venv\\Scripts\\Activate.ps1\`
- **macOS/Linux:** \`source .venv/bin/activate\`

\`\`\`bash
python -m pip install -r requirements-dev.txt
python -m pip install -e .
python run.py
\`\`\`

Open [http://127.0.0.1:8501](http://127.0.0.1:8501).

## Input example
Map \`source\` and \`target\` to the two endpoint IDs. Other columns are optional.

\`\`\`csv
source,target,relationship,date,weight
ENTITY-01,ENTITY-02,contact,2025-02-04,2
ENTITY-02,ORG-01,associated-with,2025-02-07,1
\`\`\`

## Tests
\`\`\`bash
python -m pytest -q
\`\`\`

## Important limitations
- Rankings and detected patterns are structural review signals—not proof of criminal activity, guilt, identity, or intent.
- Candidate missing links do not establish that a relationship exists. Verify findings against reliable source records.
- Relationship-only imports leave entity types as \`unknown\` unless type information is supplied.
- The app has no user authentication or multi-user access controls. Keep it on your local machine; do not expose it to untrusted networks.

## License
MIT — see [LICENSE](LICENSE).
