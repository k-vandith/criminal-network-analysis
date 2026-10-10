# LinkLens

**Local-first network exploration for structured relationship data.** LinkLens turns CSV and JSON interaction records into an interactive graph, explainable structural rankings, community summaries, timelines, and a portable case report. It runs in Python on CPU and does not require paid API keys.

> **Important:** LinkLens produces structural review signals only. Scores and detected patterns are not proof of criminal activity, guilt, identity, or intent. Always validate source records and consider innocent explanations.

## Highlights

- Interactive relationship graph with filters for entity type and relationship type.
- Import a single interaction CSV/JSON file or separate entity and relationship CSVs.
- Column mapping, input validation, record previews, and a downloadable CSV template.
- Key-entity ranking by connection count, bridge position, network influence, and blended review priority.
- Community detection, timeline analysis, candidate missing links, and explainable review signals.
- HTML and PDF case-summary exports, plus a plain-English glossary.
- Fictional sample case with synthetic names and identifiers.
- Local session processing: uploaded records are not sent to an external analysis service.

## Start on Windows

    git clone https://github.com/k-vandith/criminal-network-analysis.git
    cd criminal-network-analysis
    python -m venv .venv
    .venv\Scripts\Activate.ps1
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
    python -m pip install -e .
    python run.py

Open http://localhost:8501.

If PowerShell blocks activation, run Set-ExecutionPolicy with Scope Process and ExecutionPolicy Bypass in that terminal, then activate the environment again.

## Linux / macOS

    git clone https://github.com/k-vandith/criminal-network-analysis.git
    cd criminal-network-analysis
    python3 -m venv .venv
    source .venv/bin/activate
    python -m pip install --upgrade pip
    pip install -r requirements-dev.txt
    python -m pip install -e .
    python run.py

## Input formats

### Interaction table

A CSV needs at least two columns identifying the two sides of each relationship. Suggested headers:

    source,target,relationship,date,weight
    ENTITY-01,ENTITY-02,phone contact,2025-02-04,2
    ENTITY-02,ORG-01,associated with,2025-02-07,1
    ENTITY-01,ORG-01,coordination,2025-02-09,3

During import, map the source and target columns. Date, relationship, weight, and display-name columns are optional. Repeated interactions between the same two IDs are combined into one graph edge with an interaction count and combined weight.

JSON files may contain a list of interaction records, or an object with nodes/entities and edges/relationships arrays.

### Separate entities and relationships

The entity CSV should include a stable entity ID column and may include name/type columns. The relationship CSV should include source and target IDs; relationship type, timestamp, and weight are optional. Endpoints absent from the entity table are kept with type unknown.

## Navigation

- **Overview** — network summary and recommended starting points.
- **Upload & Map Columns** — load a CSV/JSON dataset or pair of CSV files.
- **Network Explorer** — filter relationships, focus on an entity, and inspect direct links.
- **Key Players** — compare structural rankings and read what each measure means.
- **Groups & Communities** — explore detected clusters.
- **Timeline** — chart dated relationships and filter records by date range.
- **Suspicious Patterns** — review heuristic signals and candidate missing links.
- **Case Report** — download a local HTML or PDF summary.
- **Glossary** — plain-English analytical definitions.

## CLI

Validate and summarize an interaction CSV without launching the web UI:

    python -m linklens.cli interactions.csv --source source --target target

## Tests

    python -m pytest -q

App navigation smoke tests use Streamlit AppTest. Run the full suite in the development environment installed from requirements-dev.txt.

## Privacy and limitations

- Files stay in the current application session and are not sent to a third-party analysis API.
- The app has no account system, role-based access controls, or multi-user case storage. Do not expose a running instance to untrusted networks.
- The graph is undirected; some real-world relationships are directional or temporal.
- Community, centrality, bridge, and link-prediction algorithms simplify real activity and can produce false positives.
- Large graphs may require more CPU and memory. The graph display is limited to a manageable visible subset, while summary metrics are computed across the loaded graph.
- Use synthetic records for public demos. Avoid committing sensitive or real case files to the repository.

## Project layout

    src/
      app.py                 Streamlit entry point
      linklens/
        app.py               Workspace and UI
        core.py              Graph import, metrics, communities, review signals
        io.py                CSV/JSON readers and reports
        theme.py             Offline-friendly UI theme
        cli.py               CSV summary command
    tests/
      test_core.py
      test_app_smoke.py

## License

MIT. See LICENSE.
