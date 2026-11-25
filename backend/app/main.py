from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from neo4j.exceptions import Neo4jError
from pathlib import Path
import json
from app.repositories.graph import GraphRepository
from app.matching.scoring import score_candidates

repo = None
@asynccontextmanager
async def lifespan(app):
    global repo
    repo = GraphRepository()
    yield
    if repo: repo.close()
app = FastAPI(title="Disease Graph Explorer API", description="Disease–phenotype exploration backed by Neo4j.", version="1.0.0", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], allow_methods=["*"], allow_headers=["*"])
class MatchRequest(BaseModel): phenotype_ids: list[str] = Field(min_length=1, max_length=30); limit: int = Field(default=50, ge=1, le=100)
class CompareRequest(BaseModel): disease_ids: list[str] = Field(min_length=2, max_length=5)
class PathRequest(BaseModel): disease_id: str; phenotype_ids: list[str] = Field(min_length=1, max_length=30)

def db():
    if repo is None: raise HTTPException(503, "Database is not initialized")
    try: repo.verify()
    except Exception: raise HTTPException(503, "Neo4j is unavailable. Start the local database and check the configured connection.")
    return repo

@app.get("/api/health")
def health():
    try: db(); return {"status":"ok","database":"connected"}
    except HTTPException as e: return {"status":"unavailable","database":"disconnected","detail":e.detail}
@app.get("/api/stats")
def stats():
    result=db().stats()
    result.update({"dataset":"HPO v2022-12-15"})
    return result
@app.get("/api/sources")
def sources():
    path=Path(__file__).resolve().parents[2]/"data/source_manifest.json"
    return json.loads(path.read_text())
@app.get("/api/phenotypes/search")
def phenotype_search(q: str=Query(min_length=2), limit: int=Query(default=20,ge=1,le=50)):
    return {"items":[x["item"] for x in db().search_phenotypes(q,limit)]}
@app.get("/api/phenotypes/{phenotype_id}")
def phenotype_detail(phenotype_id: str):
    r=db(); item=r.phenotype(phenotype_id)
    if not item: raise HTTPException(404,"Phenotype identifier not found in the loaded catalog")
    item["diseases"]=r.phenotype_diseases(phenotype_id)
    return item
@app.get("/api/diseases/search")
def disease_search(q: str=Query(min_length=2), limit: int=Query(default=20,ge=1,le=50)):
    return {"items":[x["item"] for x in db().search_diseases(q,limit)]}
@app.get("/api/graph/search")
def graph_search(q: str=Query(min_length=2), limit: int=Query(default=20,ge=1,le=40)):
    r=db()
    diseases=[{**x["item"],"kind":"Disease"} for x in r.search_diseases(q,limit)]
    phenotypes=[{**x["item"],"kind":"Phenotype"} for x in r.search_phenotypes(q,limit)]
    items=diseases+phenotypes
    items.sort(key=lambda x:(x.get("name","").casefold()!=q.casefold(), x["kind"]!="Phenotype", x.get("name","").casefold()))
    return {"items":items[:limit]}
@app.get("/api/diseases/{disease_id}")
def disease_detail(disease_id: str):
    r=db(); item=r.disease(disease_id)
    if not item: raise HTTPException(404,"Disease identifier not found")
    item["phenotypes"] = r.disease_phenotypes(disease_id)
    return item
@app.get("/api/diseases/{disease_id}/phenotypes")
def disease_phenotypes(disease_id: str): return {"items":db().disease_phenotypes(disease_id)}
@app.post("/api/match")
def match(request: MatchRequest):
    r=db(); unique=list(dict.fromkeys(request.phenotype_ids))
    found=[pid for pid in unique if (phenotype:=r.phenotype(pid)) and not phenotype.get("obsolete",False)]
    if len(found)!=len(unique): raise HTTPException(422,{"message":"Unknown phenotype identifiers","invalid_ids":sorted(set(unique)-set(found))})
    rows=r.match(found,request.limit)
    profiles={row["disease"]["id"]:r.disease_phenotypes(row["disease"]["id"]) for row in rows}
    candidates=score_candidates(found,rows,{did:[x["phenotype"]["id"] for x in detail] for did,detail in profiles.items()},request.limit)
    ids=[x["disease"]["id"] for x in candidates]
    details={did:profiles[did] for did in ids}
    for item in candidates:
        item["additional_phenotypes"]=[x["phenotype"] for x in details[item["disease"]["id"]] if x["phenotype"]["id"] not in found]
    return {"method":"Jaccard(selected phenotype set, complete documented positive disease profile)","interpretation":"A phenotype match score, not a probability. Missing annotations are unknown.","items":candidates}
@app.post("/api/compare")
def compare(request: CompareRequest):
    r=db(); ids=list(dict.fromkeys(request.disease_ids))
    if len(ids)<2: raise HTTPException(422,"Select at least two distinct diseases")
    diseases=[r.disease(i) for i in ids]
    if any(d is None for d in diseases): raise HTTPException(422,"One or more disease identifiers are unknown")
    grouped={i:set() for i in ids}; names={}
    for row in r.compare(ids): grouped[row["disease_id"]].add(row["phenotype"]["id"]); names[row["phenotype"]["id"]]=row["phenotype"]
    all_ids=set.union(*grouped.values()) if grouped else set()
    return {"diseases":diseases,"shared":[names[i] for i in sorted(set.intersection(*grouped.values()))],"by_disease":{i:[names[p] for p in sorted(grouped[i]-set.intersection(*grouped.values()))] for i in ids},"union_count":len(all_ids),"jaccard":round(len(set.intersection(*grouped.values()))/len(all_ids),4) if all_ids else 0}
@app.get("/api/graph")
def graph(disease_id: str|None=None, phenotype_id: str|None=None, limit: int=Query(default=120,ge=1,le=300)):
    rows=db().graph(disease_id,phenotype_id,limit)
    return rows[0] if rows else {"nodes":[],"edges":[]}
@app.get("/api/graph/nodes/{node_id}")
def node_detail(node_id: str):
    r=db(); rows=r.node_details(node_id)
    if not rows: raise HTTPException(404,"Graph node not found")
    item=rows[0]; labels=item["labels"]; props=item["props"]; details={}
    if "Phenotype" in labels: details["diseases"]=r.phenotype_diseases(node_id)
    elif "Disease" in labels:
        evidence=r.disease_phenotypes(node_id)
        details["phenotype_count"]=len(evidence)
        details["sources"]=[src for src in {x["source"]["id"]:x["source"] for row in evidence for x in row.get("evidence",[]) if x.get("source")}.values()]
    elif "Association" in labels: details["association"]=r.association_details(node_id)
    return {**item,"details":details}
@app.get("/api/graph/neighborhood/{node_id}")
def neighborhood(node_id: str, limit: int=Query(default=80,ge=1,le=150)):
    rows=db().neighborhood(node_id,limit)
    if not rows: raise HTTPException(404,"No neighborhood found for this node")
    return rows[0]
@app.post("/api/graph/path")
def graph_path(request: PathRequest):
    r=db()
    if not r.disease(request.disease_id): raise HTTPException(404,"Disease identifier not found")
    ids=list(dict.fromkeys(request.phenotype_ids))
    invalid=[pid for pid in ids if not (phenotype:=r.phenotype(pid)) or phenotype.get("obsolete",False)]
    if invalid: raise HTTPException(422,{"message":"Unknown or obsolete phenotype identifiers","invalid_ids":invalid})
    return {"paths":r.path(request.disease_id,ids)}
