//! Exhaustive subset search for A386493 on the translated finite square.
//!
//! Contributed by Shmulik Cohen, Sep 08 2026; developed with AI assistance.
//! No SAT dependency. The u128 bitset supports at most 128 domain points,
//! including the 81- and 100-point domains used for D=64 and D=85.

use std::env;
use std::fs;
use std::time::{Duration, Instant};

#[derive(Clone, Copy)]
struct Pt { x: i32, y: i32 }

struct Search {
    n: usize,
    pts: Vec<Pt>,
    compat: Vec<u128>,
    forbidden: Vec<Vec<u128>>,
    selected: Vec<usize>,
    nodes: u64,
    color_calls: u64,
    started: Instant,
    limit: Option<Duration>,
    timed_out: bool,
    witness: Option<Vec<usize>>,
}

fn bit(i: usize) -> u128 { 1u128 << i }

fn json_string(s: &str) -> String { format!("\"{}\"", s.replace('\\', "\\\\").replace('"', "\\\"")) }

impl Search {
    fn expired(&mut self) -> bool {
        if self.nodes & 1023 != 0 { return false; }
        if self.limit.map_or(false, |x| self.started.elapsed() >= x) {
            self.timed_out = true;
            true
        } else { false }
    }

    // Proper greedy coloring of the compatibility graph.  A clique can use
    // at most one vertex per color because each color is made pairwise
    // incompatible.  Prefix triple restrictions are included in edge tests.
    fn coloring_bound(&mut self, candidates: u128) -> usize {
        self.color_calls += 1;
        let mut colors: Vec<Vec<usize>> = Vec::new();
        let mut rest = candidates;
        while rest != 0 {
            let b = rest & (!rest + 1);
            let v = b.trailing_zeros() as usize;
            rest ^= b;
            let mut placed = false;
            for cls in colors.iter_mut() {
                if cls.iter().all(|&w| !self.can_coexist(v, w)) {
                    cls.push(v);
                    placed = true;
                    break;
                }
            }
            if !placed { colors.push(vec![v]); }
        }
        colors.len()
    }

    fn can_coexist(&self, a: usize, b: usize) -> bool {
        if self.compat[a] & bit(b) == 0 { return false; }
        self.selected.iter().all(|&u| self.forbidden[u][a] & bit(b) == 0)
    }

    fn dfs(&mut self, candidates: u128) {
        if self.witness.is_some() || self.timed_out { return; }
        self.nodes += 1;
        if self.expired() { return; }
        let have = self.selected.len();
        if have == self.n {
            self.witness = Some(self.selected.clone());
            return;
        }
        let need = self.n - have;
        if (candidates.count_ones() as usize) < need { return; }
        if have + self.coloring_bound(candidates) < self.n { return; }

        let mut rest = candidates;
        while rest != 0 {
            if self.witness.is_some() || self.timed_out { return; }
            let b = rest & (!rest + 1);
            rest ^= b;
            let v = b.trailing_zeros() as usize;
            // Descendants are strictly later indices, so every subset occurs
            // once and no symmetry assumption is introduced.
            let mut next = rest & self.compat[v];
            for &u in &self.selected { next &= !self.forbidden[u][v]; }
            self.selected.push(v);
            self.dfs(next);
            self.selected.pop();
        }
    }
}

fn isqrt(n: i32) -> i32 {
    let mut x = 0;
    while (x + 1) * (x + 1) <= n { x += 1; }
    x
}

fn main() {
    let args: Vec<String> = env::args().collect();
    let mut n = None; let mut d = None; let mut out = None; let mut timeout = None;
    let mut i = 1;
    while i < args.len() {
        match args[i].as_str() {
            "--n" => { i += 1; n = Some(args[i].parse::<usize>().unwrap()); }
            "--D" => { i += 1; d = Some(args[i].parse::<i32>().unwrap()); }
            "--out" => { i += 1; out = Some(args[i].clone()); }
            "--timeout-sec" => { i += 1; timeout = Some(args[i].parse::<u64>().unwrap()); }
            _ => panic!("unknown argument {}", args[i]),
        }
        i += 1;
    }
    let n = n.expect("--n"); let d = d.expect("--D");
    let side = isqrt(d);
    let mut pts = Vec::new();
    for x in 0..=side { for y in 0..=side { pts.push(Pt { x, y }); } }
    assert!(pts.len() <= 128, "u128 candidate bitset requires <=128 points");
    let m = pts.len();
    let mut compat = vec![0u128; m];
    let mut forbidden = vec![vec![0u128; m]; m];
    let dist = |a: Pt, b: Pt| (a.x - b.x) * (a.x - b.x) + (a.y - b.y) * (a.y - b.y);
    for a in 0..m {
        for b in 0..m {
            if a != b && dist(pts[a], pts[b]) <= d { compat[a] |= bit(b); }
        }
    }
    for a in 0..m { for b in (a + 1)..m { for w in 0..m {
        if w == a || w == b { continue; }
        let bad = dist(pts[a], pts[b]) == dist(pts[a], pts[w])
            || dist(pts[b], pts[a]) == dist(pts[b], pts[w])
            || dist(pts[w], pts[a]) == dist(pts[w], pts[b]);
        if bad { forbidden[a][b] |= bit(w); forbidden[b][a] |= bit(w); }
    }} }
    let started = Instant::now();
    let mut s = Search { n, pts, compat, forbidden, selected: Vec::new(),
        nodes: 0, color_calls: 0, started, limit: timeout.map(Duration::from_secs), timed_out: false, witness: None };
    let all = if m == 128 { u128::MAX } else { (1u128 << m) - 1 };
    s.dfs(all);
    let status = if s.witness.is_some() { "sat" } else if s.timed_out { "timeout" } else { "unsat" };
    let exhaustive = status == "unsat";
    let elapsed = s.started.elapsed().as_secs_f64();
    let points = s.witness.as_ref().map(|ws| ws.iter().map(|&j| format!("[{},{}]", s.pts[j].x, s.pts[j].y)).collect::<Vec<_>>().join(","));
    let result = format!("{{\n  \"status\": {},\n  \"exhaustive\": {},\n  \"n\": {},\n  \"D\": {},\n  \"side\": {},\n  \"points\": [{}],\n  \"nodes\": {},\n  \"coloring_calls\": {},\n  \"elapsed_sec\": {:.6}\n}}\n",
        json_string(status), exhaustive, n, d, side, points.unwrap_or_default(), s.nodes, s.color_calls, elapsed);
    if let Some(path) = out { fs::write(path, &result).unwrap(); }
    print!("{}", result);
}
