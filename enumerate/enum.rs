//! Independent safe-Rust exhaustive enumerator for detecting matrices.
//!
//! This implementation follows ENUMERATION_PROOF.md rather than wrapping or
//! calling enum.c. It intentionally uses Rust-owned storage and checked CLI
//! parsing, while preserving the same mathematical search and split convention
//! so complete node vectors can be compared between implementations.

use std::env;
use std::process::ExitCode;
use std::time::Instant;

const MAX_Q: usize = 8;
const MAX_N: usize = 20;
const MAX_TYPES: usize = 1 << (MAX_Q - 1);
const TABLE_BITS: u32 = 17;
const TABLE_SIZE: usize = 1 << TABLE_BITS;
const TABLE_MASK: usize = TABLE_SIZE - 1;
const HASH_MULTIPLIER: u64 = 0x9E37_79B9_7F4A_7C15;
const BIAS: u64 = 64;

#[derive(Clone, Copy)]
struct Config {
    q: usize,
    n: usize,
    split: u64,
    part: u64,
    split_depth: usize,
    canon_depth: usize,
    max_solutions: u64,
    use_pivots: bool,
}

impl Config {
    fn parse() -> Result<Self, String> {
        let arguments: Vec<String> = env::args().collect();
        if arguments.len() < 3 {
            return Err(format!(
                "usage: {} q n [--split N --part B] [--maxsol K] [--splitdepth D] [--canondepth D] [--pivots|--no-pivots]",
                arguments.first().map_or("enum-rust", String::as_str)
            ));
        }

        let q = parse_usize("q", &arguments[1])?;
        let n = parse_usize("n", &arguments[2])?;
        let mut config = Self {
            q,
            n,
            split: 1,
            part: 0,
            split_depth: 5,
            canon_depth: n.min(8),
            max_solutions: 3,
            use_pivots: false,
        };

        let mut index = 3;
        while index < arguments.len() {
            let flag = arguments[index].as_str();
            match flag {
                "--pivots" => {
                    config.use_pivots = true;
                    index += 1;
                    continue;
                }
                "--no-pivots" => {
                    config.use_pivots = false;
                    index += 1;
                    continue;
                }
                _ => {}
            }
            let value = arguments
                .get(index + 1)
                .ok_or_else(|| format!("missing value for {flag}"))?;
            match flag {
                "--split" => config.split = parse_u64(flag, value)?,
                "--part" => config.part = parse_u64(flag, value)?,
                "--maxsol" => config.max_solutions = parse_u64(flag, value)?,
                "--report" => {
                    let report = value
                        .parse::<f64>()
                        .map_err(|_| format!("invalid {flag}: {value}"))?;
                    if !report.is_finite() || report <= 0.0 {
                        return Err(format!("invalid {flag}: {value}"));
                    }
                }
                "--splitdepth" => config.split_depth = parse_usize(flag, value)?,
                "--canondepth" => config.canon_depth = parse_usize(flag, value)?,
                _ => return Err(format!("unknown option: {flag}")),
            }
            index += 2;
        }

        if !(2..=MAX_Q).contains(&config.q) || !(2..=MAX_N).contains(&config.n) {
            return Err(format!("require 2<=q<={MAX_Q} and 2<=n<={MAX_N}"));
        }
        if config.split == 0 || config.part >= config.split {
            return Err("partition must satisfy --split >= 1 and 0 <= --part < --split".into());
        }
        if config.max_solutions == 0
            || config.split_depth == 0
            || (config.split > 1 && config.split_depth >= config.n)
            || config.canon_depth > config.n
        {
            return Err(
                "require maxsol>=1, splitdepth>=1 (and <n when split), and 0<=canondepth<=n"
                    .into(),
            );
        }
        Ok(config)
    }
}

fn parse_usize(name: &str, text: &str) -> Result<usize, String> {
    text.parse::<usize>()
        .map_err(|_| format!("invalid {name}: {text}"))
}

fn parse_u64(name: &str, text: &str) -> Result<u64, String> {
    text.parse::<u64>()
        .map_err(|_| format!("invalid {name}: {text}"))
}

struct HashLayer {
    keys: Box<[u64; TABLE_SIZE]>,
    stamps: Box<[u32; TABLE_SIZE]>,
    generation: u32,
}

impl HashLayer {
    fn new() -> Self {
        let keys = vec![0; TABLE_SIZE]
            .into_boxed_slice()
            .try_into()
            .unwrap_or_else(|_| unreachable!("fixed hash-key allocation length"));
        let stamps = vec![0; TABLE_SIZE]
            .into_boxed_slice()
            .try_into()
            .unwrap_or_else(|_| unreachable!("fixed hash-stamp allocation length"));
        Self {
            keys,
            stamps,
            generation: 0,
        }
    }

    #[inline(always)]
    fn slot(key: u64) -> usize {
        (key.wrapping_mul(HASH_MULTIPLIER) >> (64 - TABLE_BITS)) as usize
    }

    fn rebuild(&mut self, values: &[u64]) -> Result<(), String> {
        if values.len() >= TABLE_SIZE {
            return Err(format!(
                "hash capacity {} reached by {} subset sums",
                TABLE_SIZE,
                values.len()
            ));
        }
        self.generation = self.generation.wrapping_add(1);
        if self.generation == 0 {
            self.stamps.fill(0);
            self.generation = 1;
        }
        let generation = self.generation;
        for &key in values {
            let mut slot = Self::slot(key);
            while self.stamps[slot] == generation && self.keys[slot] != key {
                slot = (slot + 1) & TABLE_MASK;
            }
            self.keys[slot] = key;
            self.stamps[slot] = generation;
        }
        Ok(())
    }

    #[inline(always)]
    fn contains(&self, key: u64) -> bool {
        let mut slot = Self::slot(key);
        while self.stamps[slot] == self.generation {
            if self.keys[slot] == key {
                return true;
            }
            slot = (slot + 1) & TABLE_MASK;
        }
        false
    }
}

struct Search {
    config: Config,
    type_count: usize,
    deltas: [i64; MAX_TYPES],
    permutation_table: Vec<u8>,
    pivot_table: Vec<u8>,
    sums: Vec<u64>,
    tables: Vec<HashLayer>,
    prefix: [u8; MAX_N],
    nodes: [u64; MAX_N + 1],
    split_counter: u64,
    solutions: u64,
    canonical_calls: u64,
    canonical_skips: u64,
}

impl Search {
    fn new(config: Config) -> Result<Self, String> {
        let type_count = 1 << (config.q - 1);
        let mut deltas = [0i64; MAX_TYPES];
        for (type_id, delta) in deltas.iter_mut().enumerate().take(type_count) {
            let mut packed = 1i64;
            for row in 1..config.q {
                let component = 1i64 << (8 * row);
                packed += if type_id & (1 << (row - 1)) == 0 {
                    component
                } else {
                    -component
                };
            }
            *delta = packed;
        }

        let permutation_table = permutation_maps(config.q - 1, type_count);
        let pivot_table = pivot_maps(config.q, type_count);
        let sum_capacity = 1usize
            .checked_shl(config.n as u32)
            .ok_or_else(|| "subset-sum allocation overflow".to_string())?;
        let mut tables = Vec::with_capacity(config.n + 1);
        for _ in 0..=config.n {
            tables.push(HashLayer::new());
        }

        Ok(Self {
            config,
            type_count,
            deltas,
            permutation_table,
            pivot_table,
            sums: vec![0; sum_capacity],
            tables,
            prefix: [0; MAX_N],
            nodes: [0; MAX_N + 1],
            split_counter: 0,
            solutions: 0,
            canonical_calls: 0,
            canonical_skips: 0,
        })
    }

    fn run(&mut self) -> Result<(), String> {
        let mut zero = 0u64;
        for row in 0..self.config.q {
            zero += BIAS << (8 * row);
        }
        self.sums[0] = zero;
        self.sums[1] = zero.wrapping_add_signed(self.deltas[0]);
        self.prefix[0] = 0;

        let mut candidates = [0u8; MAX_TYPES];
        for type_id in 1..self.type_count {
            candidates[type_id - 1] = type_id as u8;
        }
        let candidate_count = self.type_count - 1;
        self.dfs(1, 2, &candidates[..candidate_count])?;
        Ok(())
    }

    fn dfs(&mut self, depth: usize, sum_count: usize, candidates: &[u8]) -> Result<bool, String> {
        self.nodes[depth] = self.nodes[depth]
            .checked_add(1)
            .ok_or_else(|| format!("node counter overflow at depth {depth}"))?;

        if depth == self.config.n {
            self.solutions = self
                .solutions
                .checked_add(1)
                .ok_or_else(|| "solution counter overflow".to_string())?;
            print!("SOLUTION #{}: types", self.solutions);
            for &type_id in &self.prefix[..self.config.n] {
                print!(" {type_id}");
            }
            println!();
            return Ok(self.solutions >= self.config.max_solutions);
        }

        let needed = self.config.n - depth;
        if candidates.len() < needed {
            return Ok(false);
        }

        self.tables[depth].rebuild(&self.sums[..sum_count])?;
        let mut live = [0u8; MAX_TYPES];
        let mut live_count = 0usize;
        {
            let table = &self.tables[depth];
            let sums = &self.sums[..sum_count];
            for &type_id in candidates {
                let delta = self.deltas[type_id as usize];
                let mut legal = true;
                for &sum in sums {
                    if table.contains(sum.wrapping_add_signed(delta)) {
                        legal = false;
                        break;
                    }
                }
                if legal {
                    live[live_count] = type_id;
                    live_count += 1;
                }
            }
        }
        if live_count < needed {
            return Ok(false);
        }

        for index in 0..live_count {
            if live_count - index < needed {
                break;
            }
            let type_id = live[index];
            if depth == self.config.split_depth && self.config.split > 1 {
                let owner = self.split_counter % self.config.split;
                self.split_counter = self
                    .split_counter
                    .checked_add(1)
                    .ok_or_else(|| "split counter overflow".to_string())?;
                if owner != self.config.part {
                    continue;
                }
            }

            self.prefix[depth] = type_id;
            if depth < self.config.canon_depth {
                self.canonical_calls += 1;
                let (accepted, skips) = canonical_prefix(
                    &self.prefix[..=depth],
                    &self.permutation_table,
                    &self.pivot_table,
                    self.type_count,
                    self.config.use_pivots,
                );
                self.canonical_skips += skips;
                if !accepted {
                    continue;
                }
            }

            let delta = self.deltas[type_id as usize];
            {
                let (existing, tail) = self.sums.split_at_mut(sum_count);
                for (destination, &source) in tail[..sum_count].iter_mut().zip(existing.iter()) {
                    *destination = source.wrapping_add_signed(delta);
                }
            }
            if self.dfs(depth + 1, sum_count * 2, &live[index + 1..live_count])? {
                return Ok(true);
            }
        }
        Ok(false)
    }
}

fn permutation_maps(bit_count: usize, type_count: usize) -> Vec<u8> {
    fn visit(
        position: usize,
        permutation: &mut [usize],
        type_count: usize,
        output: &mut Vec<u8>,
    ) {
        if position == permutation.len() {
            let mut map = vec![0u8; type_count];
            for (type_id, image) in map.iter_mut().enumerate() {
                let mut transformed = 0usize;
                for (source, &destination) in permutation.iter().enumerate() {
                    if type_id & (1 << source) != 0 {
                        transformed |= 1 << destination;
                    }
                }
                *image = transformed as u8;
            }
            output.extend_from_slice(&map);
            return;
        }
        for swap_with in position..permutation.len() {
            permutation.swap(position, swap_with);
            visit(position + 1, permutation, type_count, output);
            permutation.swap(position, swap_with);
        }
    }

    let mut permutation: Vec<usize> = (0..bit_count).collect();
    let mut output = Vec::new();
    visit(0, &mut permutation, type_count, &mut output);
    output
}

/// Row-pivoting maps for the full signed row group O(q,Z) = (Z_2)^q x| S_q.
///
/// Pivot `R` re-selects row `R` as the normalized reference row: the returned
/// table maps each type (a normalized column with row 0 pinned to +1) to its
/// image after moving row `R` into the row-0 slot. Pivot 0 is the identity, so
/// the `q` maps together are exactly what enum.c's `pivottab` applies. Each map
/// is an invertible affine map over GF(2), hence a permutation of the type set,
/// and preserves detectingness, so widening `canonical_prefix` to loop over
/// them only strengthens pruning. See ENUMERATION_PROOF.md section 4.
fn pivot_maps(q: usize, type_count: usize) -> Vec<u8> {
    let bit_count = q - 1;
    let mut output = Vec::with_capacity(q * type_count);
    for type_id in 0..type_count {
        output.push(type_id as u8);
    }
    for reference in 1..q {
        let reference_bit = reference - 1;
        for type_id in 0..type_count {
            let base = (type_id >> reference_bit) & 1;
            let mut image = 0usize;
            let mut out_bit = 0;
            if base != 0 {
                image |= 1 << out_bit;
            }
            out_bit += 1;
            for other in 0..bit_count {
                if other == reference_bit {
                    continue;
                }
                if base ^ ((type_id >> other) & 1) != 0 {
                    image |= 1 << out_bit;
                }
                out_bit += 1;
            }
            output.push(image as u8);
        }
    }
    output
}

#[inline(always)]
fn insertion_sort(values: &mut [u8]) {
    for index in 1..values.len() {
        let value = values[index];
        let mut destination = index;
        while destination > 0 && values[destination - 1] > value {
            values[destination] = values[destination - 1];
            destination -= 1;
        }
        values[destination] = value;
    }
}

fn canonical_prefix(
    prefix: &[u8],
    permutation_table: &[u8],
    pivot_table: &[u8],
    type_count: usize,
    use_pivots: bool,
) -> (bool, u64) {
    let mut lower_bounds = [0u8; MAX_N];
    let mut image = [0u8; MAX_N];
    let mut pivoted = [0u8; MAX_N];
    let mut skipped = 0u64;

    let pivot_count = if use_pivots { pivot_table.len() / type_count } else { 1 };
    for pivot in pivot_table.chunks_exact(type_count).take(pivot_count) {
        for (index, &type_id) in prefix.iter().enumerate() {
            pivoted[index] = pivot[type_id as usize];
        }
        let pivoted = &pivoted[..prefix.len()];

        for &translation in pivoted {
            for (index, &type_id) in pivoted.iter().enumerate() {
                let weight = (type_id ^ translation).count_ones();
                lower_bounds[index] = ((1u16 << weight) - 1) as u8;
            }
            insertion_sort(&mut lower_bounds[..prefix.len()]);

            let mut could_threaten = false;
            for index in 0..prefix.len() {
                if lower_bounds[index] < prefix[index] {
                    could_threaten = true;
                    break;
                }
                if lower_bounds[index] > prefix[index] {
                    break;
                }
            }
            if !could_threaten {
                skipped += 1;
                continue;
            }

            for permutation in permutation_table.chunks_exact(type_count) {
                for (index, &type_id) in pivoted.iter().enumerate() {
                    image[index] = permutation[(type_id ^ translation) as usize];
                }
                insertion_sort(&mut image[..prefix.len()]);
                for index in 0..prefix.len() {
                    if image[index] < prefix[index] {
                        return (false, skipped);
                    }
                    if image[index] > prefix[index] {
                        break;
                    }
                }
            }
        }
    }
    (true, skipped)
}

fn execute() -> Result<(), String> {
    let config = Config::parse()?;
    let mut search = Search::new(config)?;
    println!(
        "rust q={} n={}: {} types, {} perms, split {}/{} (depth {}), canon<={}{}",
        config.q,
        config.n,
        search.type_count,
        search.permutation_table.len() / search.type_count,
        config.part,
        config.split,
        config.split_depth,
        config.canon_depth,
        if config.use_pivots { ", pivots=on" } else { "" }
    );
    let started = Instant::now();
    search.run()?;
    let elapsed = started.elapsed().as_secs_f64();
    let total: u64 = search.nodes.iter().sum();
    print!("DONE in {elapsed:.2}s  nodes/depth: [");
    for depth in 0..=config.n {
        if depth != 0 {
            print!(",");
        }
        print!("{}", search.nodes[depth]);
    }
    println!(
        "]  total={}  rate={:.0} nodes/s  canon={} skipped={}",
        total,
        total as f64 / elapsed.max(f64::EPSILON),
        search.canonical_calls,
        search.canonical_skips
    );
    println!("solutions found: {}", search.solutions);
    if search.solutions == 0 && config.split == 1 {
        println!("*** NO {}x{} DETECTING MATRIX EXISTS ***", config.q, config.n);
    } else if search.solutions == 0 {
        println!(
            "*** no solutions in {}x{} partition {}/{} ***",
            config.q, config.n, config.part, config.split
        );
    }
    Ok(())
}

fn main() -> ExitCode {
    match execute() {
        Ok(()) => ExitCode::SUCCESS,
        Err(error) => {
            eprintln!("error: {error}");
            ExitCode::FAILURE
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn permutation_count_is_factorial() {
        assert_eq!(permutation_maps(3, 8).len(), 6 * 8);
        assert_eq!(permutation_maps(7, 128).len(), 5040 * 128);
    }

    #[test]
    fn canonicalization_accepts_the_orbit_minimum() {
        let maps = permutation_maps(3, 8);
        let pivots = pivot_maps(4, 8);
        assert_eq!(canonical_prefix(&[0, 1, 2, 4], &maps, &pivots, 8, false).0, true);
        assert_eq!(canonical_prefix(&[0, 1, 2, 6], &maps, &pivots, 8, false).0, false);
    }

    #[test]
    fn pivot_maps_are_permutations_with_identity_first() {
        for q in 2..=MAX_Q {
            let type_count = 1 << (q - 1);
            let table = pivot_maps(q, type_count);
            assert_eq!(table.len(), q * type_count);
            for (pivot, map) in table.chunks_exact(type_count).enumerate() {
                let mut seen = vec![false; type_count];
                for &image in map {
                    assert!((image as usize) < type_count);
                    assert!(!seen[image as usize], "pivot {pivot} is not injective");
                    seen[image as usize] = true;
                }
                if pivot == 0 {
                    assert!(map.iter().enumerate().all(|(i, &image)| image as usize == i));
                }
            }
        }
    }

    #[test]
    fn pivots_never_accept_a_prefix_the_baseline_rejects() {
        // Enlarging the group can only reject more prefixes, never fewer.
        let maps = permutation_maps(4, 16);
        let pivots = pivot_maps(5, 16);
        for a in 1..16u8 {
            for b in a + 1..16 {
                let prefix = [0u8, a, b];
                let baseline = canonical_prefix(&prefix, &maps, &pivots, 16, false).0;
                let pivoted = canonical_prefix(&prefix, &maps, &pivots, 16, true).0;
                if pivoted {
                    assert!(baseline, "pivots accepted {prefix:?} but baseline rejected it");
                }
            }
        }
    }
}
