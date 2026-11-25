import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app import main

class StubRepository:
    def close(self): pass
    def verify(self): pass
    def stats(self): return {"diseases":1,"phenotypes":2,"associations":2,"sources":1,"ontology_relationships":0}
    def phenotype(self,pid): return {"id":pid,"name":pid} if pid in {"HP:1","HP:2"} else None
    def match(self,ids,limit): return [{"disease":{"id":"D:1","name":"Example"},"matched_ids":["HP:1"],"matched_names":["HP:1"]}]
    def disease_phenotypes(self,did,limit=500): return [{"phenotype":{"id":"HP:1","name":"HP:1"},"evidence":[]},{"phenotype":{"id":"HP:3","name":"HP:3"},"evidence":[]}]
    def disease(self,did): return {"id":did,"name":"Example"}
    def compare(self,ids): return []
    def graph(self,*args): return [{"nodes":[],"edges":[]}]
    def node_details(self,node_id): return [{"labels":["Phenotype"],"props":{"id":node_id}}]
    def neighborhood(self,node_id,limit=80): return [{"nodes":[],"edges":[]}]
    def path(self,disease_id,phenotype_ids,limit=5): return [{"pid":phenotype_ids[0],"nodes":[],"edges":[]}]
    def search_phenotypes(self,q,limit=20): return []
    def search_diseases(self,q,limit=20): return []
    def phenotype_diseases(self,pid,limit=100): return []

def test_health_and_matching_validation(monkeypatch):
    monkeypatch.setattr(main,'GraphRepository',StubRepository)
    with TestClient(main.app) as client:
        assert client.get('/api/health').json()['status']=='ok'
        bad=client.post('/api/match',json={'phenotype_ids':['HP:404']})
        assert bad.status_code==422
        empty=client.post('/api/match',json={'phenotype_ids':[]})
        assert empty.status_code==422
        result=client.post('/api/match',json={'phenotype_ids':['HP:1','HP:2']})
        assert result.status_code==200
        candidate=result.json()['items'][0]
        assert candidate['score']==round(1/3,4)
        assert candidate['undocumented_ids']==['HP:2']
        path=client.post('/api/graph/path',json={'disease_id':'D:1','phenotype_ids':['HP:1']})
        assert path.status_code==200 and path.json()['paths'][0]['pid']=='HP:1'
        invalid_path=client.post('/api/graph/path',json={'disease_id':'D:1','phenotype_ids':['HP:404']})
        assert invalid_path.status_code==422

def test_graph_requires_a_search_root_and_docs_are_disabled(monkeypatch):
    monkeypatch.setattr(main,'GraphRepository',StubRepository)
    with TestClient(main.app) as client:
        assert client.get('/api/graph').json()=={'nodes':[],'edges':[]}
        assert client.get('/docs').status_code==404
        assert client.get('/openapi.json').status_code==404
