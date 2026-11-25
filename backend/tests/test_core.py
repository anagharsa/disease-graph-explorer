import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.matching.scoring import score_candidates
from scripts.ingest_data import parse_obo, parse_hpoa


def test_jaccard_uses_complete_disease_profile():
    rows=[{"disease":{"id":"D1","name":"Example"},"matched_ids":["HP:1","HP:2"],"matched_names":["one","two"]}]
    result=score_candidates(["HP:1","HP:2"],rows,{"D1":["HP:1","HP:2","HP:3"]})[0]
    assert result["score"]==round(2/3,4)
    assert result["matched_ids"]==["HP:1","HP:2"]
    assert result["undocumented_ids"]==[]
    assert result["disease_profile_count"]==3


def test_hpo_obo_parser_preserves_obsolete_terms_and_edges(tmp_path):
    path=tmp_path/'hp.obo'
    path.write_text('[Term]\nid: HP:1\nname: Parent\ndef: "definition" [PMID:1]\n\n[Term]\nid: HP:2\nname: Child\nis_a: HP:1 ! Parent\nis_obsolete: true\n')
    terms,edges=parse_obo(path)
    assert len(terms)==2 and terms[1]["obsolete"] is True
    assert terms[0]["definition"]=='definition'
    assert edges==[{"child":"HP:2","parent":"HP:1"}]


def test_hpoa_parser_normalizes_real_header_case(tmp_path):
    path=tmp_path/'phenotype.hpoa'
    path.write_text('#DatabaseID\tDiseaseName\tQualifier\tHPO_ID\tReference\tEvidence\tOnset\tFrequency\tSex\tAspect\tBiocuration\nOMIM:1\tExample disease\t\tHP:1\tPMID:2\tIEA\t\t\t\tP\tHPO:curator[2022-01-01]\n')
    rows=parse_hpoa(path)
    assert len(rows)==1
    assert rows[0]["disease_id"]=='OMIM:1'
    assert rows[0]["phenotype_id"]=='HP:1'
    assert rows[0]["evidence_code"]=='IEA'
