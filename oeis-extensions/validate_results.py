"""Recheck the headline constructions without importing any solver."""
import json
from pathlib import Path
from verify_witness import verify

root=Path(__file__).resolve().parent
cases=[
    ('A386493','runs/bool-n13-D65.json'),
    ('A386493','runs/bool-n14-D65.json'),
    ('A279404','logs/n19-k11.json'),
    ('A279404','logs/n20-k11.json'),
]
results=[]
for sequence,relative in cases:
    data=json.loads((root/sequence/relative).read_text())
    result=verify(sequence,data)
    results.append({'source':f'{sequence}/{relative}',**result})
    print(json.dumps(result,sort_keys=True))
(root/'independent-validation.json').write_text(json.dumps(results,indent=2)+'\n')
