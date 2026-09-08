#!/usr/bin/env python3
"""Reproduce A386493(13..16) = 65,65,89,89. Python stdlib + rustc only."""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent
def require(condition,message):
    if not condition: raise RuntimeError(message)

def check_witness(c,n,D):
    require(c['n']==n and c['D']==D,'Wrong witness metadata')
    p=c['points']
    require(len(p)==n and all(len(q)==2 and all(type(x) is int for x in q) for q in p),'Invalid coordinates')
    require(len(set(map(tuple,p)))==n,'Repeated point')
    def dist(a,b):return (a[0]-b[0])**2+(a[1]-b[1])**2
    require(max(dist(a,b) for a,b in combinations(p,2))==D,'Wrong squared diameter')
    for i,a in enumerate(p):
        ds=[dist(a,b) for j,b in enumerate(p) if i!=j]
        require(len(set(ds))==n-1,'Equal distances at one apex')
    for triple in combinations(p,3):
        require(len({dist(a,b) for a,b in combinations(triple,2)})==3,'Isosceles or midpoint triple')
    return {'n':n,'squared_diameter':D,'status':'PASS'}

def main():
    witnesses=json.loads((HERE/'witnesses.json').read_text())
    require(len(witnesses)==4,'Expected four witnesses')
    results={'witnesses':[check_witness(c,n,D) for c,(n,D) in zip(witnesses,[(13,65),(14,65),(15,89),(16,89)])],'exclusions':[]}
    require({x*x+y*y for x in range(10) for y in range(10) if 85<x*x+y*y<=89}=={89},'Unexpected squared distance')
    with tempfile.TemporaryDirectory(prefix='a386493-') as td:
        for source in ['exact_search.rs','independent85.rs']:
            binary=Path(td)/source.removesuffix('.rs')
            subprocess.run(['rustc','-O',str(HERE/source),'-o',str(binary)],check=True,capture_output=True,text=True)
            cases=[(13,64,789000),(15,85,11736134)] if source=='exact_search.rs' else [(15,85,46676991)]
            for n,D,nodes in cases:
                args=['--n',str(n),'--D',str(D),'--timeout-sec','90'] if source=='exact_search.rs' else []
                p=subprocess.run([str(binary)]+args,check=True,capture_output=True,text=True,timeout=100)
                r=json.loads(p.stdout)
                require(r['status']=='unsat' and r['exhaustive'] is True,'Search did not complete an exclusion')
                require((r['n'],r['D'],r['nodes'])==(n,D,nodes),'Unexpected exhaustive result')
                results['exclusions'].append({'source':source,'source_sha256':hashlib.sha256((HERE/source).read_bytes()).hexdigest(),'result':r})
    results.update(status='PASS',conclusion={'a(13)':65,'a(14)':65,'a(15)':89,'a(16)':89})
    (HERE/'verification.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
