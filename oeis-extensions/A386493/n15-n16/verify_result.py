#!/usr/bin/env python3
"""Replay the two exhaustive exclusions and check both constructions.

Needs Python's standard library and rustc. No SAT solver or Python package.
"""
from itertools import combinations
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import tempfile

HERE=Path(__file__).resolve().parent

def verify_witness(path,n):
    c=json.loads(path.read_text());points=c['points']
    assert len(points)==n
    assert all(len(p)==2 and all(type(x) is int for x in p) for p in points)
    assert len(set(map(tuple,points)))==n
    def d(p,q):return (p[0]-q[0])**2+(p[1]-q[1])**2
    diameter=max(d(p,q) for p,q in combinations(points,2))
    assert diameter==89
    for i,p in enumerate(points):
        ds=[d(p,q) for j,q in enumerate(points) if i!=j]
        assert len(set(ds))==n-1
    for triple in combinations(points,3):
        assert len({d(a,b) for a,b in combinations(triple,2)})==3
    return {'n':n,'squared_diameter':diameter,'distinct':True,'all_apex_distances_distinct':True,'all_triples_checked':True}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--witnesses-only',action='store_true');args=ap.parse_args()
    witnesses=[verify_witness(HERE/'local-D89-seed3864931503.json',15),verify_witness(HERE/'local-n16-D89.json',16)]
    assert {x*x+y*y for x in range(10) for y in range(10) if 85<x*x+y*y<=89}=={89}
    results={'witnesses':witnesses,'no_lattice_squared_distance_86_to_88':True,'exclusions':[]}
    if not args.witnesses_only:
        with tempfile.TemporaryDirectory(prefix='a386493-verify-') as td:
            for name,source,expected_nodes in [('primary','exact_search.rs',11736134),('independent','review-independent.rs',46676991)]:
                binary=Path(td)/name
                subprocess.run(['rustc','-O',str(HERE/source),'-o',str(binary)],check=True,capture_output=True,text=True)
                cmd=[str(binary)]
                if name=='primary':cmd+=['--n','15','--D','85','--timeout-sec','90']
                p=subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=100)
                r=json.loads(p.stdout)
                assert r['status']=='unsat' and r['exhaustive'] is True
                assert r['n']==15 and r['D']==85 and r['nodes']==expected_nodes
                results['exclusions'].append({'name':name,'source_sha256':hashlib.sha256((HERE/source).read_bytes()).hexdigest(),'binary_sha256':hashlib.sha256(binary.read_bytes()).hexdigest(),'command':[name]+cmd[1:],'result':r})
        results.update(status='PASS',conclusion={'a(15)':89,'a(16)':89})
        (HERE/'root-final-verification.json').write_text(json.dumps(results,indent=2)+'\n')
    else:results['status']='WITNESSES-PASS'
    print(json.dumps(results,indent=2))

if __name__=='__main__':main()
