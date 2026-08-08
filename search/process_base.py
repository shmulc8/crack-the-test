#!/usr/bin/env python3
"""Post-process one W28 base's extend log: materialize sibling 15x29s and
   extend-scan each for a 15x30 record. usage: process_base.py <basefile> <extlog>"""
import os, re, subprocess, sys

if len(sys.argv) != 3:
    raise SystemExit(__doc__)
base, extlog = sys.argv[1], sys.argv[2]
D = os.path.dirname(os.path.abspath(base)).rsplit("/pairbases", 1)[0]
tag = os.path.basename(base).replace(".txt", "")
pname, c = tag.rsplit("_d", 1)
c = int(c)
ppath = f"{D}/{pname}.txt" if os.path.exists(f"{D}/{pname}.txt") else f"{D}/fresh29/{pname}.txt"
prows = [l.strip() for l in open(ppath) if l.strip() and not l.startswith("#")]
pcol = "".join(r[c] for r in prows)
npcol = pcol.translate(str.maketrans("+-", "-+"))
brows = [l.strip() for l in open(base) if l.strip()]

def run(args):
    return subprocess.run(args, capture_output=True, text=True, check=True).stdout

zeros = re.findall(r"^ZERO .* col=([+-]+)$", open(extlog).read(), re.M)
fresh = [z for z in zeros if z != pcol and z != npcol]
# canonical: a column and its negation give sign-equivalent siblings
seen, uniq = set(), []
for z in fresh:
    k = min(z, z.translate(str.maketrans("+-", "-+")))
    if k not in seen:
        seen.add(k); uniq.append(z)
print(f"{tag}: {len(zeros)} zero-cols, {len(uniq)} novel siblings", flush=True)
import hashlib
CAP = 30
if len(uniq) > CAP:
    uniq.sort(key=lambda z: hashlib.md5((tag + z).encode()).hexdigest())
    print(f"  sampling {CAP}/{len(uniq)} siblings", flush=True)
    uniq = uniq[:CAP]
os.makedirs(f"{D}/siblings", exist_ok=True)
for z in uniq:
    sib = f"{D}/siblings/sib_{tag}_{z.replace('+','p').replace('-','m')}.txt"
    open(sib, "w").write("\n".join(r + z[i] for i, r in enumerate(brows)) + "\n")
    if "nulls=0" not in run([f"{D}/sa3", "count", sib, "29"]):
        print(f"  WARN sibling not zero-null: {sib}", flush=True)
        continue
    ext = run([f"{D}/sa3", "extend", "29", sib, "0", "32768", "0"])
    hits = re.findall(r"^ZERO .* col=([+-]+)$", ext, re.M)
    print(f"  sibling {os.path.basename(sib)}: {len(hits)} zero-cols at n=29", flush=True)
    srows = [l.strip() for l in open(sib)]
    for h in hits:
        cand = sib.replace("sib_", "cand30_").replace(".txt", f"_{h.replace('+','p').replace('-','m')}.txt")
        open(cand, "w").write("\n".join(r + h[i] for i, r in enumerate(srows)) + "\n")
        if "nulls=0" in run([f"{D}/sa3", "count", cand, "30"]):
            rec = f"{D}/RECORD_15x30_{tag}.txt"
            open(rec, "w").write(open(cand).read())
            print(f"!!!!! VERIFIED 15x30 RECORD: {rec} !!!!!", flush=True)
            with open(f"{D}/rescue.log", "a") as f:
                f.write(f"!!!!! VERIFIED 15x30: {rec} !!!!!\n")
