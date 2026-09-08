#!/usr/bin/env python3
"""Emit a DIMACS CNF for lattice clouds of size at least n and D diameter."""
import argparse, math
from itertools import combinations
from pysat.card import CardEnc, EncType

ap=argparse.ArgumentParser(); ap.add_argument('--n',type=int,required=True); ap.add_argument('--D',type=int,required=True); ap.add_argument('--out',required=True); a=ap.parse_args()
m=math.isqrt(a.D); pts=[(x,y) for x in range(m+1) for y in range(m+1)]; N=len(pts); clauses=[]
for i,j in combinations(range(N),2):
 d=(pts[i][0]-pts[j][0])**2+(pts[i][1]-pts[j][1])**2
 if d>a.D: clauses.append([-(i+1),-(j+1)])
for i in range(N):
 groups={}
 for j in range(N):
  if i==j: continue
  d=(pts[i][0]-pts[j][0])**2+(pts[i][1]-pts[j][1])**2
  groups.setdefault(d,[]).append(j)
 for js in groups.values():
  for j,k in combinations(js,2): clauses.append([-(i+1),-(j+1),-(k+1)])
card=CardEnc.atleast(lits=list(range(1,N+1)), bound=a.n, top_id=N, encoding=EncType.seqcounter)
clauses.extend(card.clauses); nv=max(card.nv, N)
with open(a.out,'w') as f:
 f.write(f'p cnf {nv} {len(clauses)}\n')
 for c in clauses: f.write(' '.join(map(str,c))+' 0\n')
print(f'points={N} clauses={len(clauses)} vars={nv}')
