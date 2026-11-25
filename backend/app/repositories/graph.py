from neo4j import GraphDatabase
from app.core.config import settings

class GraphRepository:
    def __init__(self, driver=None):
        self.driver = driver or GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        self.database = settings.neo4j_database

    def close(self): self.driver.close()
    def verify(self): self.driver.verify_connectivity()
    def read(self, query, **params):
        with self.driver.session(database=self.database) as session:
            return [r.data() for r in session.run(query, **params)]
    def write(self, query, **params):
        with self.driver.session(database=self.database) as session:
            return session.execute_write(lambda tx: [r.data() for r in tx.run(query, **params)])

    def stats(self):
        return self.read("""MATCH (d:Disease) WITH count(d) AS diseases
        MATCH (p:Phenotype) WITH diseases, count(p) AS phenotypes
        MATCH (a:Association) WITH diseases, phenotypes, count(a) AS associations
        MATCH (s:Source) WITH diseases, phenotypes, associations, count(s) AS sources
        MATCH (:Phenotype)-[r:IS_A]->(:Phenotype)
        RETURN diseases, phenotypes, associations, sources, count(r) AS ontology_relationships""")[0]

    def search_phenotypes(self, q, limit=20):
        return self.read("""MATCH (p:Phenotype) WHERE coalesce(p.obsolete,false)=false AND (toLower(p.name) CONTAINS toLower($q)
        OR any(s IN p.synonyms WHERE toLower(s) CONTAINS toLower($q))
        OR toLower(p.id) CONTAINS toLower($q))
        RETURN p {.*, labels: labels(p)} AS item ORDER BY p.name LIMIT $limit""", q=q, limit=limit)
    def search_diseases(self, q, limit=20):
        return self.read("""MATCH (d:Disease) WHERE toLower(d.name) CONTAINS toLower($q) OR toLower(d.id) CONTAINS toLower($q)
        RETURN d {.*} AS item ORDER BY d.name LIMIT $limit""", q=q, limit=limit)
    def phenotype(self, pid):
        rows=self.read("MATCH (p:Phenotype {id:$id}) RETURN p {.*} AS item", id=pid); return rows[0]["item"] if rows else None
    def disease(self, did):
        rows=self.read("MATCH (d:Disease {id:$id}) RETURN d {.*} AS item", id=did); return rows[0]["item"] if rows else None
    def match(self, ids, limit=50):
        return self.read("""MATCH (d:Disease)<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
        WHERE p.id IN $ids AND coalesce(a.negated,false)=false
        WITH DISTINCT d,p
        WITH d, collect(p.id) AS matched_ids, collect(p.name) AS matched_names
        CALL (d) {
          MATCH (d)<-[:FOR_DISEASE]-(all:Association)-[:FOR_PHENOTYPE]->(profile:Phenotype)
          WHERE coalesce(all.negated,false)=false
          RETURN count(DISTINCT profile.id) AS profile_count
        }
        RETURN d {.*} AS disease, matched_ids, matched_names, profile_count
        ORDER BY size(matched_ids) DESC, disease.name LIMIT $limit""", ids=ids, limit=limit)
    def disease_phenotypes(self, did, limit=500):
        return self.read("""MATCH (d:Disease {id:$id})<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
        WHERE coalesce(a.negated,false)=false
        OPTIONAL MATCH (a)-[:SUPPORTED_BY]->(s:Source)
        RETURN p {.*} AS phenotype, collect(DISTINCT {association_id:a.id, evidence_code:a.evidence_code, source_record_id:a.source_record_id, source:s {.*}}) AS evidence
        ORDER BY phenotype.name LIMIT $limit""", id=did, limit=limit)
    def phenotype_diseases(self, pid, limit=100):
        return self.read("""MATCH (d:Disease)<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype {id:$id})
        WHERE coalesce(a.negated,false)=false
        RETURN DISTINCT d {.*} AS disease ORDER BY disease.name LIMIT $limit""", id=pid, limit=limit)
    def compare(self, ids):
        return self.read("""MATCH (d:Disease)<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
        WHERE d.id IN $ids AND coalesce(a.negated,false)=false
        RETURN d.id AS disease_id, p {.*} AS phenotype ORDER BY disease_id, phenotype.name""", ids=ids)
    def graph(self, disease_id=None, phenotype_id=None, limit=160):
        if disease_id:
            return self.read("""MATCH (d:Disease {id:$id})<-[:FOR_DISEASE]-(a:Association)-[:FOR_PHENOTYPE]->(p:Phenotype)
            OPTIONAL MATCH (a)-[:SUPPORTED_BY]->(s:Source)
            WITH d,a,p,s LIMIT $limit
            RETURN collect(DISTINCT d {.*, kind:'Disease'}) + collect(DISTINCT p {.*, kind:'Phenotype'}) + collect(DISTINCT a {.*,kind:'Association'}) + collect(DISTINCT s {.*, kind:'Source'}) AS nodes,
            collect(DISTINCT {source:a.id, target:d.id, type:'FOR_DISEASE'}) + collect(DISTINCT {source:a.id, target:p.id, type:'FOR_PHENOTYPE'}) + collect(DISTINCT {source:a.id,target:s.id,type:'SUPPORTED_BY'}) AS edges""", id=disease_id, limit=limit)
        if phenotype_id:
            return self.read("""MATCH (p:Phenotype {id:$id})<-[:FOR_PHENOTYPE]-(a:Association)-[:FOR_DISEASE]->(d:Disease)
            WITH p,a,d LIMIT $limit
            OPTIONAL MATCH (a)-[:SUPPORTED_BY]->(s:Source)
            RETURN collect(DISTINCT p {.*,kind:'Phenotype'}) + collect(DISTINCT d {.*,kind:'Disease'}) + collect(DISTINCT a {.*,kind:'Association'}) + collect(DISTINCT s {.*,kind:'Source'}) AS nodes,
            collect(DISTINCT {source:a.id,target:p.id,type:'FOR_PHENOTYPE'}) + collect(DISTINCT {source:a.id,target:d.id,type:'FOR_DISEASE'}) + collect(DISTINCT {source:a.id,target:s.id,type:'SUPPORTED_BY'}) AS edges""", id=phenotype_id, limit=limit)
        return [{"nodes": [], "edges": []}]
    def node_details(self, node_id):
        return self.read("""MATCH (n) WHERE n.id=$id
        RETURN labels(n) AS labels, properties(n) AS props LIMIT 1""", id=node_id)
    def association_details(self, association_id):
        rows=self.read("""MATCH (a:Association {id:$id})-[:FOR_DISEASE]->(d:Disease)
        MATCH (a)-[:FOR_PHENOTYPE]->(p:Phenotype)
        OPTIONAL MATCH (a)-[:SUPPORTED_BY]->(s:Source)
        RETURN a {.*} AS association, d {.*} AS disease, p {.*} AS phenotype, s {.*} AS source""", id=association_id)
        return rows[0] if rows else None
    def neighborhood(self, node_id, limit=80):
        return self.read("""MATCH (n {id:$id})-[r]-(m)
        WITH n,r,m LIMIT $limit
        RETURN collect(DISTINCT {id:n.id, name:n.name, kind:labels(n)[0]}) + collect(DISTINCT {id:m.id,name:m.name,kind:labels(m)[0],negated:m.negated,evidence_code:m.evidence_code,source_record_id:m.source_record_id}) AS nodes,
        collect(DISTINCT {source:startNode(r).id,target:endNode(r).id,type:type(r)}) AS edges""", id=node_id, limit=limit)
    def path(self, disease_id, phenotype_ids, limit=5):
        return self.read("""MATCH (d:Disease {id:$disease_id})
        UNWIND $phenotype_ids AS pid
        MATCH (p:Phenotype {id:pid})
        OPTIONAL MATCH path=shortestPath((p)-[*..4]-(d))
        RETURN pid, CASE WHEN path IS NULL THEN [] ELSE [n IN nodes(path) | {id:n.id,name:n.name,kind:labels(n)[0]}] END AS nodes,
        CASE WHEN path IS NULL THEN [] ELSE [r IN relationships(path) | {source:startNode(r).id,target:endNode(r).id,type:type(r)}] END AS edges LIMIT $limit""", disease_id=disease_id, phenotype_ids=phenotype_ids, limit=limit)
