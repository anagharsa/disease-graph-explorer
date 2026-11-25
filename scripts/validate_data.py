#!/usr/bin/env python3
from pathlib import Path
from datetime import date
import json, re, sys
ROOT=Path(__file__).resolve().parents[1]; RAW=ROOT/'data/raw'
obo=RAW/'hp.obo'; hpoa=RAW/'phenotype.hpoa'
missing=[str(p) for p in (obo,hpoa) if not p.is_file()]
if missing: sys.exit('Missing source file(s): '+', '.join(missing)+'\nRun: python scripts/download_data.py')
manifest=json.loads((ROOT/'data/source_manifest.json').read_text())
if any(d.get('release')!='v2022-12-15' for d in manifest.get('datasets',[])):
    sys.exit('Manifest release is not the pinned HPO v2022-12-15 release.')
obo_header='\n'.join(obo.open(encoding='utf-8').read().splitlines()[:8])
if 'data-version: hp/releases/2022-12-15' not in obo_header:
    sys.exit('hp.obo does not identify the pinned 2022-12-15 ontology version.')
hpoa_header='\n'.join(hpoa.open(encoding='utf-8').read().splitlines()[:8])
date_match=re.search(r'^#date:\s*(\d{4}-\d{2}-\d{2})',hpoa_header,re.M)
if not date_match: sys.exit('phenotype.hpoa has no verifiable #date header.')
annotation_date=date.fromisoformat(date_match.group(1))
expected_annotation_date=next((d.get('file_data_date') for d in manifest.get('datasets',[]) if d.get('local_filename')=='data/raw/phenotype.hpoa'),None)
if annotation_date.isoformat()!=expected_annotation_date: sys.exit(f'phenotype.hpoa date {annotation_date} does not match manifest date {expected_annotation_date}.')
print(f'Pinned source check: hp.obo 2022-12-15; phenotype.hpoa {annotation_date}.')
terms=set(); parents=[]; in_term=False; current={}
def save_term():
    if current.get('id'):
        terms.add(current['id'])
        parents.extend((current['id'],p) for p in current.get('parents',[]))
for line in obo.open(encoding='utf-8'):
    line=line.rstrip('\n')
    if line=='[Term]':
        if in_term: save_term()
        in_term=True; current={}
    elif line.startswith('['):
        if in_term: save_term()
        in_term=False
    elif in_term:
        if line.startswith('id: '): current['id']=line[4:]
        elif line.startswith('is_a: '): current.setdefault('parents',[]).append(line[6:].split()[0])
if in_term: save_term()
association_count=0; bad=[]; diseases=set(); observed=set(); covid_named=[]
for ln,line in enumerate(hpoa.open(encoding='utf-8'),1):
    if not line.strip() or line.startswith('#'): continue
    cols=line.rstrip('\n').split('\t')
    if len(cols)<4: bad.append(ln); continue
    association_count+=1; diseases.add(cols[0]); observed.add(cols[3])
    if re.search(r'covid|sars.?cov.?2',cols[1],re.I): covid_named.append((cols[0],cols[1]))
unknown=observed-terms
print(f'Ontology terms: {len(terms)}; IS_A relationships: {len(parents)}')
print(f'Annotation records: {association_count}; disease identifiers: {len(diseases)}; phenotype identifiers referenced: {len(observed)}')
if bad: print(f'Malformed annotation rows: {len(bad)} (first line numbers: {bad[:10]})')
if unknown: print(f'Annotation phenotype IDs absent from ontology: {len(unknown)} (examples: {sorted(unknown)[:10]})')
named_diseases=sorted(set(covid_named))
direct_profiles=[(did,name) for did,name in named_diseases if re.search(r'^\s*(coronavirus disease|covid-?19|severe acute respiratory syndrome coronavirus)',name,re.I)]
print(f'COVID/SARS text in disease names: {len(covid_named)} rows across {len(named_diseases)} unique ID/name pair(s)')
for did,name in named_diseases: print(f'  {did}\t{name}')
print(f'Dedicated COVID-19/SARS-CoV-2 disease profile name matches: {len(direct_profiles)}')
if bad or unknown: sys.exit(2)
