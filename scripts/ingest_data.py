#!/usr/bin/env python3
"""Idempotently import the versioned HPO OBO + HPOA assets into Neo4j."""
from pathlib import Path
import hashlib, json, re, sys
from datetime import date
from neo4j import GraphDatabase
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'

def parse_obo(path):
    terms=[]; parents=[]; current=None
    def save():
        if current and current.get('id') and current.get('name'):
            terms.append({"id":current['id'],"name":current['name'],"definition":current.get('definition'),"synonyms":current.get('synonyms',[]),"obsolete":bool(current.get('obsolete',False))})
            parents.extend({"child":current['id'],"parent":p} for p in current.get('parents',[]))
    for line in path.open(encoding='utf-8'):
        line=line.rstrip('\n')
        if line=='[Term]': save(); current={}
        elif line.startswith('['): save(); current=None
        elif current is not None:
            if line.startswith('id: '): current['id']=line[4:]
            elif line.startswith('name: '): current['name']=line[6:]
            elif line.startswith('def: '):
                match=re.match(r'def: "(.*?)"\s+\[',line)
                if match: current['definition']=match.group(1)
            elif line.startswith('synonym: '):
                m=re.match(r'synonym: \"(.*?)\"',line)
                if m: current.setdefault('synonyms',[]).append(m.group(1))
            elif line.startswith('is_a: '): current.setdefault('parents',[]).append(line[6:].split()[0])
            elif line=='is_obsolete: true': current['obsolete']=True
    save(); return terms,parents

def parse_hpoa(path):
    rows=[]; header=None
    for lineno,line in enumerate(path.open(encoding='utf-8'),1):
        if not line.strip(): continue
        if line.startswith('#'):
            label=line.lstrip('#').rstrip('\n').split('\t')
            keymap={'databaseid':'database_id','diseaseid':'disease_id','diseasename':'disease_name','hpoid':'hpo_id','evidence':'evidence','reference':'reference','qualifier':'qualifier','onset':'onset','frequency':'frequency','sex':'sex','aspect':'aspect','modifier':'modifier','biocuration':'biocuration'}
            normalized=[keymap.get(re.sub(r'[^a-z0-9]','',x.lower()),x.lower()) for x in label]
            if 'database_id' in normalized or 'disease_id' in normalized: header=normalized
            continue
        cols=line.rstrip('\n').split('\t')
        if header and len(cols)<len(header): continue
        data=dict(zip(header or ['database_id','disease_name','qualifier','hpo_id','reference','evidence','onset','frequency','sex','modifier','aspect','biocuration'],cols))
        did=data.get('database_id') or data.get('disease_id'); pid=data.get('hpo_id') or data.get('HPO_ID')
        if not did or not pid: continue
        disease_id=did.strip()
        aid=hashlib.sha256((line.rstrip('\n')+'\t'+str(lineno)).encode()).hexdigest()
        rows.append({"id":aid,"disease_id":disease_id,"disease_name":data.get('disease_name','').strip() or disease_id,"phenotype_id":pid.strip(),"negated":data.get('qualifier','').strip().upper()=='NOT',"reference":data.get('reference','').strip(),"evidence_code":data.get('evidence','').strip(),"onset":data.get('onset','').strip(),"frequency":data.get('frequency','').strip(),"sex":data.get('sex','').strip(),"aspect":data.get('aspect','').strip(),"biocuration":data.get('biocuration','').strip(),"source_record_id":f'{lineno}'})
    return rows

def main():
    for filename in ('hp.obo','phenotype.hpoa'):
        if not (RAW/filename).exists(): sys.exit(f'Missing {RAW/filename}; run python scripts/download_data.py first')
    manifest=json.loads((ROOT/'data/source_manifest.json').read_text())
    if any(d.get('release')!='v2022-12-15' for d in manifest.get('datasets',[])):
        sys.exit('Source manifest must pin HPO v2022-12-15 before ingestion.')
    obo_header='\n'.join((RAW/'hp.obo').open(encoding='utf-8').read().splitlines()[:8])
    if 'data-version: hp/releases/2022-12-15' not in obo_header: sys.exit('hp.obo is not the pinned v2022-12-15 release.')
    hpoa_header='\n'.join((RAW/'phenotype.hpoa').open(encoding='utf-8').read().splitlines()[:8])
    date_match=re.search(r'^#date:\s*(\d{4}-\d{2}-\d{2})',hpoa_header,re.M)
    expected_annotation_date=next((d.get('file_data_date') for d in manifest.get('datasets',[]) if d.get('local_filename')=='data/raw/phenotype.hpoa'),None)
    if not date_match or date_match.group(1)!=expected_annotation_date:
        sys.exit('HPOA source date is missing or does not match the pinned manifest.')
    terms,parents=parse_obo(RAW/'hp.obo'); annotations=parse_hpoa(RAW/'phenotype.hpoa')
    termids={t['id'] for t in terms}; bad=[a for a in annotations if a['phenotype_id'] not in termids]
    if bad: print(f'WARNING: skipping {len(bad)} annotation rows with phenotype IDs absent from ontology')
    annotations=[a for a in annotations if a['phenotype_id'] in termids]
    srcs=[{"id":"HPO:hp.obo:v2022-12-15","name":"HPO ontology hp.obo","url":"https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2022-12-15","release":"v2022-12-15","release_date":"2022-12-16","file_data_date":"2022-12-15","license":"HPO terms of use"},{"id":"HPO:phenotype.hpoa:v2022-12-15","name":"HPO disease annotations phenotype.hpoa","url":"https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2022-12-15","release":"v2022-12-15","release_date":"2022-12-16","file_data_date":"2022-12-20","license":"HPO terms of use"}]
    for a in annotations: a['source_id']=srcs[1]['id']
    source_meta={s['id']:s for s in srcs}
    for a in annotations: a['source']=source_meta[a['source_id']]
    uri='bolt://localhost:7687'; user='neo4j'; password=None
    from dotenv import load_dotenv; load_dotenv(ROOT/'.env')
    import os
    uri=os.getenv('NEO4J_URI',uri); user=os.getenv('NEO4J_USER',user); password=os.getenv('NEO4J_PASSWORD',password); database=os.getenv('NEO4J_DATABASE','neo4j')
    if not password: sys.exit('Set NEO4J_PASSWORD in the project .env before ingestion.')
    try: driver=GraphDatabase.driver(uri,auth=(user,password)); driver.verify_connectivity()
    except Exception as e: sys.exit(f'Cannot connect to Neo4j at {uri}: {e}. Start Neo4j and check .env.')
    with driver.session(database=database) as s:
        for constraint in ["CREATE CONSTRAINT disease_id IF NOT EXISTS FOR (n:Disease) REQUIRE n.id IS UNIQUE","CREATE CONSTRAINT phenotype_id IF NOT EXISTS FOR (n:Phenotype) REQUIRE n.id IS UNIQUE","CREATE CONSTRAINT source_id IF NOT EXISTS FOR (n:Source) REQUIRE n.id IS UNIQUE","CREATE CONSTRAINT association_id IF NOT EXISTS FOR (n:Association) REQUIRE n.id IS UNIQUE"]: s.run(constraint).consume()
        s.run("CREATE INDEX disease_name IF NOT EXISTS FOR (n:Disease) ON (n.name)").consume(); s.run("CREATE INDEX phenotype_name IF NOT EXISTS FOR (n:Phenotype) ON (n.name)").consume()
        s.execute_write(lambda tx: tx.run("UNWIND $rows AS row MERGE (p:Phenotype {id:row.id}) SET p.name=row.name,p.definition=row.definition,p.synonyms=row.synonyms,p.obsolete=row.obsolete",rows=terms).consume())
        s.execute_write(lambda tx: tx.run("UNWIND $rows AS row MATCH (c:Phenotype {id:row.child}) MATCH (p:Phenotype {id:row.parent}) MERGE (c)-[:IS_A]->(p)",rows=parents).consume())
        s.execute_write(lambda tx: tx.run("UNWIND $rows AS row MERGE (s:Source {id:row.id}) SET s += row",rows=srcs).consume())
        # Chunk transactions keep memory bounded and are safely repeatable.
        for off in range(0,len(annotations),1000):
            batch=annotations[off:off+1000]
            s.execute_write(lambda tx: tx.run("""UNWIND $rows AS row MERGE (d:Disease {id:row.disease_id}) ON CREATE SET d.name=row.disease_name
            MERGE (p:Phenotype {id:row.phenotype_id}) MERGE (a:Association {id:row.id}) SET a.disease_id=row.disease_id,a.phenotype_id=row.phenotype_id,a.negated=row.negated,a.reference=row.reference,a.evidence_code=row.evidence_code,a.onset=row.onset,a.frequency=row.frequency,a.sex=row.sex,a.aspect=row.aspect,a.biocuration=row.biocuration,a.source_record_id=row.source_record_id
            MERGE (a)-[:FOR_DISEASE]->(d) MERGE (a)-[:FOR_PHENOTYPE]->(p) WITH a,row MATCH (src:Source {id:row.source_id}) MERGE (a)-[:SUPPORTED_BY]->(src)""",rows=batch).consume())
        db_counts={name:s.run(query).single()["count"] for name,query in {
            "disease_nodes":"MATCH (n:Disease) RETURN count(n) AS count",
            "phenotype_nodes":"MATCH (n:Phenotype) RETURN count(n) AS count",
            "association_nodes":"MATCH (n:Association) RETURN count(n) AS count",
            "source_nodes":"MATCH (n:Source) RETURN count(n) AS count",
            "ontology_relationships":"MATCH (:Phenotype)-[r:IS_A]->(:Phenotype) RETURN count(r) AS count"
        }.items()}
    driver.close()
    covid_rows=[a for a in annotations if re.search(r'covid|sars.?cov.?2',a['disease_name'],re.I)]
    stats={"release":"v2022-12-15","annotation_file_data_date":"2022-12-20","ontology_terms_parsed":len(terms),"ontology_edges_parsed":len(parents),"annotation_records_parsed":len(annotations),"skipped_missing_phenotype":len(bad),"covid_named_annotation_rows":len(covid_rows),"covid_named_disease_names":sorted({a['disease_name'] for a in covid_rows}),"dedicated_covid_infection_profile_verified":False,**db_counts}
    (ROOT/'data/processed/ingestion_summary.json').write_text(json.dumps(stats,indent=2)+'\n'); print(json.dumps(stats,indent=2))
if __name__=='__main__': main()
