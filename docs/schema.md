# Neo4j schema and queries

## Model

`Disease`, `Phenotype`, `Source`, and `Association` are separate labels. Every HPOA source row is represented as an `Association` node with its own stable row hash, source line identifier, qualifier, evidence code, reference, onset/frequency/sex qualifiers, aspect, and biocuration data. This preserves distinct evidence rows that would be lost if disease–phenotype pairs were collapsed into one relationship.

Directed relationships:

- Association → Disease: `FOR_DISEASE`
- Association → Phenotype: `FOR_PHENOTYPE`
- Association → Source: `SUPPORTED_BY`
- Child Phenotype → parent Phenotype: `IS_A`

The source nodes identify the exact ontology or annotation release, URL, release date, and terms. The current HPOA source does not provide confidence scores; none are invented.

## Constraints and indexes

The ingestion command creates uniqueness constraints for each stable `id` on Disease, Phenotype, Source, and Association, plus indexes on disease and phenotype names. Nodes and edges are created with parameterized `MERGE` statements in transactional batches. Re-running the import is idempotent.

## Representative matching Cypher

```cypher
MATCH (d:Disease)<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
WHERE p.id IN $ids AND coalesce(a.negated, false) = false
WITH DISTINCT d, p
WITH d, collect(p.id) AS matched_ids, collect(p.name) AS matched_names
CALL {
  WITH d
  MATCH (d)<-[:FOR_DISEASE]-(all:Association)-[:FOR_PHENOTYPE]->(profile:Phenotype)
  WHERE coalesce(all.negated, false) = false
  RETURN count(DISTINCT profile.id) AS profile_count
}
RETURN d {.*} AS disease, matched_ids, matched_names, profile_count
ORDER BY size(matched_ids) DESC, disease.name
LIMIT $limit
```

The matching service uses the complete positive profile count for exact Jaccard denominators. The UI then retrieves at most 500 phenotype/evidence details per disease for display.

## Neighborhood and path bounds

Neighborhood queries return at most the requested (API-capped) number of adjacent relationships. The path endpoint asks Neo4j for a shortest path of up to four edges from each selected HPO term to a disease. A path is the actual graph route and may pass through an Association node; the disease-to-phenotype direct association is represented by that evidence node and two relationships, not mislabeled as a direct edge.
