#!/usr/bin/env python3
"""Run or sample canonical frontier units with retained, resumable evidence.

The enumerator first emits every canonical prefix at a chosen depth.  This
driver then assigns those independent subtrees to a dynamic worker pool.  A
uniform deterministic sample can be used for a bounded runtime estimate; omit
--sample to drain the complete frontier.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import random
import re
import subprocess
import sys
import tempfile
from typing import Any


FRONTIER_RE = re.compile(r"^FRONTIER ([0-9]+(?:,[0-9]+)*)$")
NODES_RE = re.compile(r"nodes/depth: \[([0-9,]+)\].*\btotal=([0-9]+)\b")
DONE_RE = re.compile(r"DONE in ([0-9.]+)s")
SOLUTIONS_RE = re.compile(r"^solutions found: ([0-9]+)$", re.MULTILINE)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_json(path: Path, value: Any) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, delete=False
    ) as stream:
        json.dump(value, stream, indent=2, sort_keys=True)
        stream.write("\n")
        temporary = Path(stream.name)
    os.replace(temporary, path)


def parse_frontier_log(path: Path, depth: int) -> tuple[list[str], list[int]]:
    prefixes: list[str] = []
    node_vector: list[int] | None = None
    with path.open(encoding="utf-8") as stream:
        for raw_line in stream:
            line = raw_line.rstrip("\n")
            match = FRONTIER_RE.fullmatch(line)
            if match:
                prefix = match.group(1)
                if len(prefix.split(",")) != depth:
                    raise ValueError(f"frontier prefix has wrong depth: {prefix}")
                prefixes.append(prefix)
            node_match = NODES_RE.search(line)
            if node_match:
                node_vector = [int(value) for value in node_match.group(1).split(",")]
    if not prefixes:
        raise ValueError("enumerator emitted no frontier prefixes")
    if node_vector is None or len(node_vector) <= depth:
        raise ValueError("frontier log has no complete node vector")
    if node_vector[depth] != len(prefixes):
        raise ValueError(
            f"frontier count mismatch: vector={node_vector[depth]} lines={len(prefixes)}"
        )
    return prefixes, node_vector


def create_frontier(
    binary: Path, q: int, n: int, depth: int, output: Path
) -> tuple[list[str], list[int]]:
    log_path = output / "frontier-generation.log"
    command = [
        str(binary),
        str(q),
        str(n),
        "--dumpdepth",
        str(depth),
        "--maxsol",
        "1",
        "--report",
        "1000000000",
    ]
    with log_path.open("w", encoding="utf-8") as stream:
        result = subprocess.run(
            command,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            text=True,
        )
    if result.returncode != 0:
        raise RuntimeError(f"frontier generation failed with exit {result.returncode}")
    return parse_frontier_log(log_path, depth)


def select_units(prefixes: list[str], sample: int | None, seed: int) -> list[dict[str, Any]]:
    if sample is None:
        indices = list(range(len(prefixes)))
    else:
        if sample > len(prefixes):
            raise ValueError(f"sample {sample} exceeds frontier size {len(prefixes)}")
        indices = sorted(random.Random(seed).sample(range(len(prefixes)), sample))
    return [
        {"unit_id": position, "frontier_index": index, "prefix": prefixes[index]}
        for position, index in enumerate(indices)
    ]


def write_units(path: Path, units: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        stream.write("unit_id\tfrontier_index\tprefix\n")
        for unit in units:
            stream.write(
                f"{unit['unit_id']}\t{unit['frontier_index']}\t{unit['prefix']}\n"
            )


def read_units(path: Path) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as stream:
        header = stream.readline().rstrip("\n")
        if header != "unit_id\tfrontier_index\tprefix":
            raise ValueError("unexpected units.tsv header")
        for line in stream:
            unit_id, frontier_index, prefix = line.rstrip("\n").split("\t")
            units.append(
                {
                    "unit_id": int(unit_id),
                    "frontier_index": int(frontier_index),
                    "prefix": prefix,
                }
            )
    return units


def parse_unit_log(path: Path, depth: int, returncode: int, timed_out: bool) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    if timed_out:
        return {"status": "timeout", "returncode": returncode}
    node_match = NODES_RE.search(text)
    done_match = DONE_RE.search(text)
    solution_match = SOLUTIONS_RE.search(text)
    if returncode != 0 or not node_match or not done_match or not solution_match:
        return {"status": "error", "returncode": returncode}
    total_nodes = int(node_match.group(2))
    solutions = int(solution_match.group(1))
    if total_nodes < depth:
        return {"status": "error", "returncode": returncode}
    return {
        "status": "solution" if solutions else "complete",
        "returncode": returncode,
        "elapsed_seconds": float(done_match.group(1)),
        "total_nodes": total_nodes,
        "subtree_nodes": total_nodes - (depth - 1),
        "solutions": solutions,
    }


def run_unit(
    binary: Path,
    q: int,
    n: int,
    depth: int,
    output: Path,
    unit: dict[str, Any],
    timeout: float | None,
    attempt: int,
    report_seconds: float,
) -> tuple[str, dict[str, Any]]:
    key = str(unit["unit_id"])
    suffix = "" if attempt == 1 else f"-attempt-{attempt:02d}"
    log_path = output / "units" / f"unit-{unit['unit_id']:06d}{suffix}.log"
    command = [
        str(binary),
        str(q),
        str(n),
        "--maxsol",
        "1",
        "--report",
        str(report_seconds),
        "--prefix",
        str(unit["prefix"]),
    ]
    timed_out = False
    returncode = -1
    with log_path.open("w", encoding="utf-8") as stream:
        try:
            result = subprocess.run(
                command,
                stdout=stream,
                stderr=subprocess.STDOUT,
                check=False,
                text=True,
                timeout=timeout,
            )
            returncode = result.returncode
        except subprocess.TimeoutExpired:
            timed_out = True
            stream.write(f"\nDRIVER TIMEOUT after {timeout} seconds\n")
    parsed = parse_unit_log(log_path, depth, returncode, timed_out)
    parsed.update(
        {
            "attempt": attempt,
            "frontier_index": unit["frontier_index"],
            "prefix": unit["prefix"],
            "log": str(log_path.relative_to(output)),
        }
    )
    return key, parsed


def summarize(
    manifest: dict[str, Any], progress: dict[str, dict[str, Any]], node_vector: list[int]
) -> dict[str, Any]:
    statuses: dict[str, int] = {}
    for result in progress.values():
        status = result["status"]
        statuses[status] = statuses.get(status, 0) + 1
    summary: dict[str, Any] = {
        "selected_units": manifest["selected_units"],
        "finished_units": len(progress),
        "statuses": statuses,
    }
    completed = [result for result in progress.values() if result["status"] == "complete"]
    if len(completed) != manifest["selected_units"]:
        summary["estimate_available"] = False
        summary["estimate_reason"] = "every sampled unit must finish without finding a solution"
        return summary

    subtree_values = [float(result["subtree_nodes"]) for result in completed]
    elapsed_values = [float(result["elapsed_seconds"]) for result in completed]
    frontier_size = int(manifest["frontier_size"])
    shallow_nodes = sum(node_vector[: manifest["frontier_depth"]])
    mean_nodes = sum(subtree_values) / len(subtree_values)
    mean_seconds = sum(elapsed_values) / len(elapsed_values)
    summary.update(
        {
            "estimate_available": True,
            "shallow_nodes": shallow_nodes,
            "mean_subtree_nodes": mean_nodes,
            "estimated_total_nodes": shallow_nodes + frontier_size * mean_nodes,
            "mean_unit_seconds": mean_seconds,
            "estimated_single_process_hours": frontier_size * mean_seconds / 3600.0,
        }
    )
    if manifest["sample"] is None:
        summary["mode"] = "complete-frontier"
        summary["exact_total_nodes"] = int(shallow_nodes + sum(subtree_values))
    else:
        summary["mode"] = "uniform-frontier-sample"
    if len(subtree_values) >= 2:
        variance = sum((value - mean_nodes) ** 2 for value in subtree_values) / (
            len(subtree_values) - 1
        )
        finite_population = math.sqrt(
            max(0.0, (frontier_size - len(subtree_values)) / (frontier_size - 1))
        )
        margin = 1.96 * math.sqrt(variance / len(subtree_values)) * finite_population
        summary["estimated_total_nodes_95pct_normal_interval"] = [
            shallow_nodes + frontier_size * max(0.0, mean_nodes - margin),
            shallow_nodes + frontier_size * (mean_nodes + margin),
        ]
        summary["interval_warning"] = (
            "Normal-approximation sampling interval; a heavy-tailed frontier may require a larger sample."
        )
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path, help="compiled enumerate/enum binary")
    parser.add_argument("q", type=int)
    parser.add_argument("n", type=int)
    parser.add_argument("--frontier-depth", type=int, default=6)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--sample", type=int, help="uniform sample size; omit for a full run")
    parser.add_argument("--seed", type=int, default=20260811)
    parser.add_argument("--unit-timeout", type=float, help="seconds per unit; timed-out samples are not estimated")
    parser.add_argument("--report-seconds", type=float, default=60.0, help="enumerator progress interval")
    parser.add_argument("--source", type=Path, help="enumerator source to include in the manifest")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if not 2 <= args.q <= 9 or not 2 <= args.n <= 20:
        parser.error("require 2<=q<=9 and 2<=n<=20")
    if not 1 <= args.frontier_depth < args.n:
        parser.error("require 1<=frontier-depth<n")
    if args.workers < 1:
        parser.error("workers must be positive")
    if args.sample is not None and args.sample < 1:
        parser.error("sample must be positive")
    if args.unit_timeout is not None and args.unit_timeout <= 0:
        parser.error("unit-timeout must be positive")
    if args.report_seconds <= 0:
        parser.error("report-seconds must be positive")
    return args


def main() -> int:
    args = parse_args()
    binary = args.binary.resolve(strict=True)
    if not binary.is_file() or not os.access(binary, os.X_OK):
        raise SystemExit(f"enumerator is not executable: {binary}")
    source = args.source.resolve(strict=True) if args.source else None
    driver = Path(__file__).resolve(strict=True)
    output = args.output.resolve()
    manifest_path = output / "manifest.json"
    progress_path = output / "progress.json"
    summary_path = output / "summary.json"

    if args.resume:
        if not output.is_dir() or not manifest_path.is_file():
            raise SystemExit("--resume requires an existing output directory with manifest.json")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected = {
            "q": args.q,
            "n": args.n,
            "frontier_depth": args.frontier_depth,
            "workers": args.workers,
            "sample": args.sample,
            "seed": args.seed,
            "report_seconds": args.report_seconds,
            "binary_sha256": sha256_file(binary),
            "driver_sha256": sha256_file(driver),
        }
        for key, value in expected.items():
            if manifest.get(key) != value:
                raise SystemExit(f"resume mismatch for {key}: {manifest.get(key)!r} != {value!r}")
        units = read_units(output / "units.tsv")
        _, node_vector = parse_frontier_log(output / "frontier-generation.log", args.frontier_depth)
        progress = json.loads(progress_path.read_text(encoding="utf-8")) if progress_path.is_file() else {}
        manifest.setdefault("attempts", []).append(
            {
                "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                "workers": args.workers,
                "unit_timeout": args.unit_timeout,
                "resume": True,
            }
        )
        atomic_json(manifest_path, manifest)
    else:
        if output.exists():
            raise SystemExit(f"refusing to overwrite existing output directory: {output}")
        (output / "units").mkdir(parents=True)
        prefixes, node_vector = create_frontier(binary, args.q, args.n, args.frontier_depth, output)
        units = select_units(prefixes, args.sample, args.seed)
        write_units(output / "units.tsv", units)
        manifest = {
            "format": 1,
            "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "q": args.q,
            "n": args.n,
            "frontier_depth": args.frontier_depth,
            "frontier_size": len(prefixes),
            "workers": args.workers,
            "sample": args.sample,
            "selected_units": len(units),
            "seed": args.seed,
            "unit_timeout": args.unit_timeout,
            "report_seconds": args.report_seconds,
            "binary": str(args.binary),
            "binary_sha256": sha256_file(binary),
            "source": str(args.source) if source else None,
            "source_sha256": sha256_file(source) if source else None,
            "driver": Path(__file__).name,
            "driver_sha256": sha256_file(driver),
            "platform": platform.platform(),
            "machine": platform.machine(),
            "python": sys.version,
            "frontier_node_vector": node_vector,
            "attempts": [
                {
                    "started_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
                    "workers": args.workers,
                    "unit_timeout": args.unit_timeout,
                    "resume": False,
                }
            ],
        }
        atomic_json(manifest_path, manifest)
        progress: dict[str, dict[str, Any]] = {}
        atomic_json(progress_path, progress)

    terminal_statuses = {"complete", "solution"}
    pending = [
        unit
        for unit in units
        if progress.get(str(unit["unit_id"]), {}).get("status") not in terminal_statuses
    ]
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(
                run_unit,
                binary,
                args.q,
                args.n,
                args.frontier_depth,
                output,
                unit,
                args.unit_timeout,
                int(progress.get(str(unit["unit_id"]), {}).get("attempt", 1))
                + (1 if str(unit["unit_id"]) in progress else 0),
                args.report_seconds,
            ): unit
            for unit in pending
        }
        for future in concurrent.futures.as_completed(futures):
            key, result = future.result()
            previous = progress.get(key)
            if previous:
                history = list(previous.get("previous_attempts", []))
                previous_copy = dict(previous)
                previous_copy.pop("previous_attempts", None)
                history.append(previous_copy)
                result["previous_attempts"] = history
            progress[key] = result
            atomic_json(progress_path, progress)
            print(
                f"unit {key}: {result['status']} "
                f"({len(progress)}/{manifest['selected_units']})",
                flush=True,
            )

    summary = summarize(manifest, progress, node_vector)
    atomic_json(summary_path, summary)
    print(json.dumps(summary, indent=2, sort_keys=True))
    if summary.get("estimate_available") or summary.get("statuses", {}).get("solution", 0):
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
