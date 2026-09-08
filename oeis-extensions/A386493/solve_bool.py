#!/usr/bin/env python3
"""Complete finite Boolean encoding over the translated bounding square."""
import argparse, json, math, time
from itertools import combinations
from z3 import Bool, If, Solver, Sum, sat, unknown

ap = argparse.ArgumentParser(); ap.add_argument('--n',type=int,required=True); ap.add_argument('--D',type=int,required=True); ap.add_argument('--timeout-ms',type=int,default=300000); ap.add_argument('--out',required=True); a=ap.parse_args()
t0=time.time(); m=math.isqrt(a.D); pts=[(x,y) for x in range(m+1) for y in range(m+1)]; N=len(pts)
s=Solver(); s.set(timeout=a.timeout_ms); z=[Bool(f'p{i}') for i in range(N)]; s.add(Sum([If(v,1,0) for v in z])==a.n)
for i,j in combinations(range(N),2):
 d=(pts[i][0]-pts[j][0])**2+(pts[i][1]-pts[j][1])**2
 if d>a.D: s.add(z[i]+z[j] <= 1)
for i in range(N):
 groups={}
 for j in range(N):
  if j==i: continue
  d=(pts[i][0]-pts[j][0])**2+(pts[i][1]-pts[j][1])**2
  groups.setdefault(d,[]).append(j)
 for js in groups.values():
  for j,k in combinations(js,2): s.add(z[i]+z[j]+z[k] <= 2)
r=s.check(); out={'status':'sat' if r==sat else 'unsat' if r!=unknown else 'unknown','n':a.n,'D':a.D,'squared_diameter':a.D,'seconds':time.time()-t0}
if r==sat: out['points']=[list(pts[i]) for i,v in enumerate(z) if s.model().eval(v)]
json.dump(out,open(a.out,'w'),indent=2); print(json.dumps(out),flush=True)
