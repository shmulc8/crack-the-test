# A269706: 90 <= a(8) <= 94

Shmulik Cohen, September 2026. Developed with AI assistance.

For the bounded Cartesian grid P8 × P8 × P8, a dominating set needs at
least 90 vertices, and a saved 94-vertex construction covers all 512 vertices.
The exact value is unresolved. This is an OEIS bounds contribution, not an
extension of the exact-term data. Publication priority is not claimed.

## Evidence

- `witness-94.json`: explicit construction, checked directly by Manhattan distance.
- `n8-bound90/README.md`: explanation of the complete lower-bound proof.
- `n8-bound90/verify_global.py`: independent exact-integer proof verification.
- `n8-bound90/verification.json`: recorded PASS for 1,474 corner classes and
  1,237,096 proof nodes; includes a SHA-256 digest for every proof file.
- `PROOF-SHA256SUMS`: proof-file integrity manifest.
- `SHA256SUMS`: integrity manifest for this small repository package.

The two supporting checker directories preserve the original paths and source
bytes. The corner LP metadata describes an earlier bound of 86; the global
checker uses its complete corner partition and the later branching certificates
to establish 90. Search heuristics and unverified timeouts are not proof evidence.

## Reproduce

From this directory, with standard-library Python 3:

```sh
shasum -a 256 -c SHA256SUMS
python3 -B n8-bound90/verify_upper.py
```

For the lower bound, download both archive parts from the
[proof release](https://github.com/shmulc8/crack-the-test/releases/tag/a269706-bounds-90-94-v1).
Concatenate them with `cat A269706-bound90-proofs.tar.gz.part01 A269706-bound90-proofs.tar.gz.part02 > A269706-bound90-proofs.tar.gz`. Check the part and combined digests
in `ARCHIVE.json`, and extract it into this directory:

```sh
tar -xzf /path/to/A269706-bound90-proofs.tar.gz
shasum -a 256 -c PROOF-SHA256SUMS
python3 -B n8-bound90/verify_global.py --workers 4
```

The archive expands to about 11 GB. Verification checks every case and writes
`n8-bound90/verification.json`. A missing or unfinished case prevents global
PASS. No optimization solver or commercial license is required for checking.

## Submission status

Evidence published through the versioned proof release linked above.
Submitted for OEIS editorial review on September 14, 2026:
[submission #25](https://oeis.org/history/view?seq=A269706&v=25).
Status at submission: **proposed, not approved**. The linked OEIS history records subsequent editorial decisions.
