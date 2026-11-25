# Disease Graph Explorer NoSQL demonstration (5–7 minutes)

Before class, start Neo4j, acquire the exact HPO v2022-12-15 release, validate it, ingest it, and confirm `/api/health` returns `ok`. The UI and statistics use live database records. This walkthrough derives examples from the current graph and does not assume a particular disease or phenotype exists.

## 0:00–0:45 — Source and actual database counts

1. Open `http://127.0.0.1:5173`.
2. Point out disease, phenotype, association, source, and ontology-link counts, which the API reads from Neo4j.
3. Open **Sources & method** and show the release tag, license acknowledgement, and known COVID-19 coverage limitation.

For direct live counts in Neo4j Browser:

```cypher
MATCH (d:Disease) WITH count(d) AS diseases
MATCH (p:Phenotype) WITH diseases, count(p) AS phenotypes
MATCH (a:Association) WITH diseases, phenotypes, count(a) AS associations
MATCH (s:Source) WITH diseases, phenotypes, associations, count(s) AS sources
MATCH (:Phenotype)-[r:IS_A]->(:Phenotype)
RETURN diseases, phenotypes, associations, sources, count(r) AS ontology_relationships;
```

## 0:45–2:00 — Select real phenotype terms

1. Open **Phenotype matching**.
2. Type a term fragment from the loaded catalog and choose several returned records; the autocomplete comes from Neo4j.
3. Click **Run disease match**.
4. Explain the selected IDs, each candidate's matched terms, undocumented selected terms, additional annotated phenotypes, and the Jaccard score.
5. Remind the audience that an unrecorded association is unknown, and the score is not a probability.

To find an actual example candidate with multiple associations in Neo4j Browser:

```cypher
MATCH (d:Disease)<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
WHERE coalesce(a.negated,false)=false
WITH d, collect(DISTINCT p) AS ps
WHERE size(ps) >= 3
RETURN d.id AS disease_id, d.name AS disease,
       [p IN ps[0..5] | {id:p.id, name:p.name}] AS sample_phenotypes
ORDER BY disease LIMIT 1;
```

Use returned terms to run a matching query in the UI. It is dynamically derived from the ingested corpus.

## 2:00–3:30 — Open a real graph and expand it

1. Click **Explore graph** on a candidate.
2. Point out the disease, phenotype, Association, and Source node styles; pan, zoom, drag, or use Fit graph.
3. Click an Association node to inspect the source row and available evidence/reference metadata.
4. Click **Expand neighborhood**. This requests a bounded backend route to Neo4j; it merges new nodes/edges without duplicates.

Underlying query shape:

```cypher
MATCH (n {id:$id})-[r]-(m)
WITH n,r,m LIMIT $limit
RETURN n, r, m;
```

The API query also returns stable IDs and relationship types for Cytoscape.

## 3:30–4:20 — Highlight relationship paths

Return to matching and select a candidate graph from its result, with the original phenotype set still selected. Choose **Highlight phenotype paths**. The API asks Neo4j for actual shortest paths up to four edges. An evidence-backed disease–phenotype route goes through an Association node; the UI distinguishes it from a direct disease→phenotype edge. If no path exists, the UI says so.

## 4:20–5:45 — Compare disease profiles

1. Return to the matching results and tick two or more candidate checkboxes.
2. Open **Disease detail & compare** and run comparison.
3. Show shared and disease-specific documented terms and the profile Jaccard overlap.

## 5:45–6:30 — NoSQL explanation

Neo4j represents evidence provenance and ontology relationships as traversable graph structure. The same HPO term can connect many disease profiles, and an Association node preserves the evidence row between the disease, term, and source. Cypher can expand bounded neighborhoods and find actual paths without loading the whole graph into the browser or simulating graph traversal in Python.
