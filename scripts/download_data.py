#!/usr/bin/env python3
"""Download exact HPO release assets; never follows a moving latest URL."""
from pathlib import Path
from urllib.request import urlopen
from hashlib import sha256
from datetime import datetime, timezone
import json
ROOT=Path(__file__).resolve().parents[1]
RAW=ROOT/'data/raw'; RAW.mkdir(parents=True,exist_ok=True)
RELEASE='v2022-12-15'
ASSETS={
 'hp.obo':f'https://github.com/obophenotype/human-phenotype-ontology/releases/download/{RELEASE}/hp.obo',
 'phenotype.hpoa':f'https://github.com/obophenotype/human-phenotype-ontology/releases/download/{RELEASE}/phenotype.hpoa',
}
manifest=ROOT/'data/source_manifest.json'
old=json.loads(manifest.read_text()) if manifest.exists() else {"datasets":[]}
for filename,url in ASSETS.items():
    out=RAW/filename
    print(f'Downloading {url}')
    with urlopen(url,timeout=90) as response, out.open('wb') as target:
        while block:=response.read(1024*1024): target.write(block)
    entry=next((x for x in old['datasets'] if x['local_filename']==f'data/raw/{filename}'),{})
    entry.update({"name":"Human Phenotype Ontology: ontology" if filename=='hp.obo' else "HPO disease phenotype annotations", "source_url":f'https://github.com/obophenotype/human-phenotype-ontology/releases/tag/{RELEASE}', "asset_url":url, "release":"v2022-12-15", "release_date":"2022-12-16", "file_data_date":"2022-12-20" if filename=='phenotype.hpoa' else "2022-12-15", "retrieval_date":datetime.now(timezone.utc).date().isoformat(), "license":"HPO terms of use: acknowledge HPO, display file date/version, and do not alter source content; see https://human-phenotype-ontology.github.io/license.html", "local_filename":f'data/raw/{filename}', "sha256":sha256(out.read_bytes()).hexdigest(), "historical_verification":"Versioned official GitHub release tag v2022-12-15; release page states December 2022 release and was published 16 Dec 2022. The HPOA file header records its own data date.", "notes":"Exact historical release asset; not an alias for the current release."})
    old['datasets']=[x for x in old['datasets'] if x.get('local_filename')!=entry['local_filename']]+[entry]
manifest.write_text(json.dumps(old,indent=2)+'\n')
print(f'Wrote hashes and retrieval metadata to {manifest}')
