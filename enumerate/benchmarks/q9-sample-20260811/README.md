# Bounded 9x16 frontier pilot (2026-08-11)

This directory is a deliberately bounded feasibility experiment, not a
nonexistence proof and not a runtime estimate for the complete 9x16 search.

The exact command was run from `enumerate/`:

```sh
./frontier_run.py ./enum 9 16 \
  --frontier-depth 6 --sample 8 --seed 20260811 --workers 4 \
  --unit-timeout 60 --report-seconds 30 --source enum.c \
  --output benchmarks/q9-sample-20260811
```

The portable enumerator produced 66,547 canonical depth-six prefixes, with
node vector `[0,1,7,26,286,3510,66547]` through that depth. The driver then
selected eight prefixes uniformly without replacement using the recorded seed.

Seven sampled subtrees completed. One prefix, `0,1,6,25,42,61`, did not finish
within the declared 60-second limit. Its retained 30-second progress report
already contained hundreds of thousands of deeper nodes, while several of the
completed samples contained only a few nodes. This directly demonstrates the
heavy-tailed workload discussed in the manuscript.

`summary.json` therefore says `estimate_available: false`. Averaging only the
seven completed units would exclude the most expensive observed branch and
produce a downward-biased estimate. No such estimate is claimed here.

The bundle retains the full frontier, selected units, individual logs, progress,
environment, and source/binary/driver manifests. To retry only the incomplete
unit with a larger limit, use the same command with a larger `--unit-timeout`
and add `--resume`. A complete mathematical verdict would require running every
frontier unit, not merely completing this sample.
