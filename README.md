# Disease Graph Explorer

A local web app for exploring documented links between diseases and their phenotypes. Search a set of phenotype terms, see overlapping disease profiles, compare candidates, and explore the evidence in a graph.

## Neo4j

Neo4j is the graph database. Diseases, phenotype terms, evidence records, and data sources are stored as connected nodes. Cypher queries find matches, expand graph neighborhoods, inspect evidence, and trace paths between diseases and phenotypes.

The matching score is based on annotation overlap. It is for research and learning, not a diagnosis or clinical probability.

## Features

- Search HPO terms by name or identifier and match them to disease profiles.
- Inspect matched, undocumented, and other documented phenotypes.
- View disease details and compare profiles.
- Explore the graph, expand connected nodes, inspect evidence sources, and highlight paths.
- Export matching results as JSON.

## Data

The project uses Human Phenotype Ontology (HPO) terms from `hp.obo` and disease–phenotype annotations from `phenotype.hpoa`, both from the HPO `v2022-12-15` release. The annotations include disease profiles with identifiers from sources such as OMIM, Orphanet, and DECIPHER.

The files come from the [official HPO release](https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2022-12-15). The data download and import scripts are in `scripts/`. The raw data files are not included in the repository; download and import them before running a fresh copy of the app.

## Technology

Neo4j Community, Cypher, FastAPI, React, TypeScript, Vite, and Cytoscape.js.

## Run locally

You need Python 3.10 or newer, Node.js 20.19 or newer, and Neo4j Community 5.26 (or Docker Compose).

1. Copy `.env.example` to `.env` and set a local Neo4j password.
2. Start Neo4j: `docker compose up -d neo4j`.
3. From the project folder, set up Python and load the HPO data:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install -r backend/requirements.txt
   python scripts/download_data.py
   python scripts/validate_data.py
   python scripts/ingest_data.py
   ```

4. In a separate terminal, start the API from the project folder:

   ```bash
   source .venv/bin/activate
   uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8001
   ```

5. Copy `frontend/.env.example` to `frontend/.env.local`. Then run the frontend:

   ```bash
   cd frontend
   npm install
   npm run dev
   ```

6. Open <http://127.0.0.1:5173>.
