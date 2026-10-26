//! Exhaustive search for q x n detecting matrices: q x n sign matrices with no
//! nonzero z in {-1,0,1}^n such that Wz = 0.
//!
//! Row 0 is normalised to all +1, so a column is one of 2^(q-1) types and the
//! search walks strictly increasing type sequences, as in `../enum.c`. On top of
//! that search this engine applies, at every node:
//!
//! - full-depth isomorph rejection: a prefix is kept only if it is lex-least in
//!   its orbit, decided by a minimal-image partition backtrack over bit
//!   permutations instead of a loop over all (q-1)! permutations;
//! - a compatibility-graph bound: the n - depth columns still needed must be
//!   pairwise compatible (a and b are compatible iff a + b and a - b lie
//!   outside T(S), the set of ternary combinations of the chosen columns), so a
//!   node whose live candidates contain no clique of that size is dead;
//! - meet-in-the-middle membership: T(S) = T(P) + T(R) for the first `anchor`
//!   columns P, so v is in T(S) iff v - r is in a hash of T(P) for some r in
//!   T(R), costing 3^|R| probes instead of 2^|S|.
//!
//! The tree above `pardepth` is distributed with rayon work stealing. Node
//! counts do not depend on scheduling, so they are comparable with `enum2.c`.

use clap::Parser;
use rayon::prelude::*;
use std::cell::RefCell;
use std::io::Write;
use std::sync::atomic::{AtomicBool, AtomicU64, AtomicUsize, Ordering::Relaxed};
use std::sync::Mutex;
use std::time::{Duration, Instant};

const MAXN: usize = 20;
const LOGT: u32 = 16;
const TSIZE: usize = 1 << LOGT;
const BIAS: u64 = 64;
const FLUSH_EVERY: u64 = 1 << 16;

#[derive(Parser)]
#[command(about = "Decide whether a q x n detecting matrix exists")]
struct Args {
    q: usize,
    n: usize,
    /// stop after this many solutions
    #[arg(long, default_value_t = 1)]
    maxsol: usize,
    /// meet-in-the-middle anchor depth (1..=9)
    #[arg(long, default_value_t = 7)]
    mitm: usize,
    /// apply the compatibility-graph clique bound from this depth
    #[arg(long, default_value_t = 6)]
    clique: usize,
    /// lex-min isomorph rejection up to this depth (default n)
    #[arg(long)]
    canondepth: Option<usize>,
    /// include the row-pivot symmetries in the isomorph rejection
    #[arg(long)]
    pivots: bool,
    /// distribute subtrees rooted above this depth across threads
    #[arg(long, default_value_t = 7)]
    pardepth: usize,
    /// force the first types, e.g. 0,3,5,56,90,188
    #[arg(long, value_delimiter = ',')]
    prefix: Vec<usize>,
    /// progress interval in seconds
    #[arg(long, default_value_t = 60.0)]
    report: f64,
    #[arg(long)]
    threads: Option<usize>,
}

struct Cfg {
    q: usize,
    n: usize,
    nt: usize,
    delta: Vec<i64>,
    zero: u64,
    anchor: usize,
    clique_from: usize,
    canon_depth: usize,
    pivots: bool,
    pivottab: Vec<[u8; 256]>,
    lowbits: Vec<[u8; 9]>,
    pardepth: usize,
    prefix: Vec<u8>,
    maxsol: usize,
}

struct Shared {
    nodes: Vec<AtomicU64>,
    prunes: Vec<AtomicU64>,
    nsol: AtomicUsize,
    stop: AtomicBool,
    out: Mutex<()>,
}

#[derive(Clone, Copy, Default)]
struct B256([u64; 4]);

impl B256 {
    #[inline]
    fn set(&mut self, i: usize) {
        self.0[i >> 6] |= 1 << (i & 63);
    }
    #[inline]
    fn clear(&mut self, i: usize) {
        self.0[i >> 6] &= !(1 << (i & 63));
    }
    #[inline]
    fn get(&self, i: usize) -> bool {
        self.0[i >> 6] >> (i & 63) & 1 == 1
    }
    #[inline]
    fn is_empty(&self) -> bool {
        (self.0[0] | self.0[1] | self.0[2] | self.0[3]) == 0
    }
    #[inline]
    fn count(&self) -> u32 {
        self.0.iter().map(|w| w.count_ones()).sum()
    }
    #[inline]
    fn first(&self) -> usize {
        let mut wi = 0;
        while self.0[wi] == 0 {
            wi += 1;
        }
        (wi << 6) + self.0[wi].trailing_zeros() as usize
    }
    #[inline]
    fn and(&self, o: &B256) -> B256 {
        B256([self.0[0] & o.0[0], self.0[1] & o.0[1], self.0[2] & o.0[2], self.0[3] & o.0[3]])
    }
    #[inline]
    fn and_not(&self, o: &B256) -> B256 {
        B256([self.0[0] & !o.0[0], self.0[1] & !o.0[1], self.0[2] & !o.0[2], self.0[3] & !o.0[3]])
    }
}

/// Open-addressing set of packed vectors, cleared in O(1) by a generation stamp.
struct TTable {
    keys: Vec<u64>,
    stamp: Vec<u32>,
    gen: u32,
    list: Vec<u64>,
}

impl TTable {
    fn new() -> Self {
        TTable { keys: vec![0; TSIZE], stamp: vec![0; TSIZE], gen: 0, list: Vec::with_capacity(TSIZE / 2) }
    }
    fn reset(&mut self) {
        self.gen = self.gen.wrapping_add(1);
        if self.gen == 0 {
            self.stamp.fill(0);
            self.gen = 1;
        }
        self.list.clear();
    }
    #[inline]
    fn slot(x: u64) -> usize {
        (x.wrapping_mul(0x9E37_79B9_7F4A_7C15) >> (64 - LOGT)) as usize
    }
    #[inline]
    fn has(&self, k: u64) -> bool {
        let mut s = Self::slot(k);
        while self.stamp[s] == self.gen {
            if self.keys[s] == k {
                return true;
            }
            s = (s + 1) & (TSIZE - 1);
        }
        false
    }
    #[inline]
    fn add(&mut self, k: u64) {
        let mut s = Self::slot(k);
        while self.stamp[s] == self.gen {
            if self.keys[s] == k {
                return;
            }
            s = (s + 1) & (TSIZE - 1);
        }
        self.keys[s] = k;
        self.stamp[s] = self.gen;
        self.list.push(k);
    }
}

struct Engine {
    sol: [u8; MAXN + 1],
    tt: Vec<TTable>,
    tr: Vec<Vec<i64>>,
    cand: Vec<Vec<u8>>,
    live: Vec<Vec<u8>>,
    adj: Vec<Vec<B256>>,
    nodes: [u64; MAXN + 1],
    prunes: [u64; MAXN + 1],
    unflushed: u64,
}

thread_local! {
    static ENGINE: RefCell<Option<Engine>> = const { RefCell::new(None) };
}

impl Engine {
    fn new(cfg: &Cfg) -> Self {
        let n = cfg.n;
        let mut tr = vec![Vec::new(); n + 1];
        for (d, v) in tr.iter_mut().enumerate() {
            if d > cfg.anchor {
                v.reserve(3usize.pow((d - cfg.anchor) as u32));
            }
        }
        Engine {
            sol: [0; MAXN + 1],
            tt: (0..=cfg.anchor).map(|_| TTable::new()).collect(),
            tr,
            cand: vec![Vec::with_capacity(256); n + 2],
            live: vec![Vec::with_capacity(256); n + 2],
            adj: vec![vec![B256::default(); 256]; n + 2],
            nodes: [0; MAXN + 1],
            prunes: [0; MAXN + 1],
            unflushed: 0,
        }
    }

    fn flush(&mut self, sh: &Shared) {
        for d in 0..=MAXN.min(sh.nodes.len() - 1) {
            if self.nodes[d] != 0 {
                sh.nodes[d].fetch_add(self.nodes[d], Relaxed);
                self.nodes[d] = 0;
            }
            if self.prunes[d] != 0 {
                sh.prunes[d].fetch_add(self.prunes[d], Relaxed);
                self.prunes[d] = 0;
            }
        }
        self.unflushed = 0;
    }

    /// Build the T(S) structure for depth d from depth d - 1 and column sol[d-1].
    fn t_build(&mut self, cfg: &Cfg, d: usize) {
        let c = cfg.delta[self.sol[d - 1] as usize];
        let zero = cfg.zero;
        if d <= cfg.anchor {
            let (prev, cur) = self.tt.split_at_mut(d);
            let cur = &mut cur[0];
            cur.reset();
            if d == 1 {
                cur.add(zero);
                cur.add(zero.wrapping_add(c as u64));
                cur.add(zero.wrapping_sub(c as u64));
            } else {
                assert!(3 * prev[d - 1].list.len() <= TSIZE / 2, "T table too small at depth {d}");
                for &x in &prev[d - 1].list {
                    cur.add(x);
                    cur.add(x.wrapping_add(c as u64));
                    cur.add(x.wrapping_sub(c as u64));
                }
            }
        } else {
            let (prev, cur) = self.tr.split_at_mut(d);
            let cur = &mut cur[0];
            cur.clear();
            if d - 1 == cfg.anchor {
                cur.extend_from_slice(&[0, c, -c]);
            } else {
                for &r in &prev[d - 1] {
                    cur.push(r);
                    cur.push(r + c);
                    cur.push(r - c);
                }
            }
        }
    }

    #[inline]
    fn in_t(&self, cfg: &Cfg, d: usize, v: i64) -> bool {
        if d <= cfg.anchor {
            return self.tt[d].has(cfg.zero.wrapping_add(v as u64));
        }
        let t = &self.tt[cfg.anchor];
        self.tr[d].iter().any(|&r| t.has(cfg.zero.wrapping_add((v - r) as u64)))
    }

    /// Count the node and decide whether it survives; on survival live[depth]
    /// holds its legal candidates and, if the graph is used, adj[depth] their
    /// compatibility graph. Returns (number of live candidates, graph used).
    fn prepare(&mut self, cfg: &Cfg, sh: &Shared, depth: usize, prefiltered: bool) -> Option<(usize, bool)> {
        self.nodes[depth] += 1;
        self.unflushed += 1;
        if self.unflushed >= FLUSH_EVERY {
            self.flush(sh);
        }
        let n = cfg.n;
        if depth == n {
            let k = sh.nsol.fetch_add(1, Relaxed) + 1;
            if k <= cfg.maxsol {
                let _g = sh.out.lock().unwrap();
                let types: Vec<String> = self.sol[..n].iter().map(|t| t.to_string()).collect();
                println!("SOLUTION #{}: types {}", k, types.join(" "));
                std::io::stdout().flush().ok();
            }
            if k >= cfg.maxsol {
                sh.stop.store(true, Relaxed);
            }
            return None;
        }
        let need = n - depth;
        if self.cand[depth].len() < need {
            return None;
        }
        self.t_build(cfg, depth);

        let mut l = std::mem::take(&mut self.live[depth]);
        l.clear();
        if prefiltered {
            l.extend_from_slice(&self.cand[depth]);
        } else {
            for &t in &self.cand[depth] {
                if !self.in_t(cfg, depth, cfg.delta[t as usize]) {
                    l.push(t);
                }
            }
        }
        let nlive = l.len();
        if nlive < need {
            self.live[depth] = l;
            return None;
        }

        let use_graph = depth >= cfg.clique_from && need >= 2;
        if use_graph {
            let mut a = std::mem::take(&mut self.adj[depth]);
            for row in a.iter_mut().take(nlive) {
                *row = B256::default();
            }
            for i in 0..nlive {
                let di = cfg.delta[l[i] as usize];
                for j in i + 1..nlive {
                    let dj = cfg.delta[l[j] as usize];
                    if self.in_t(cfg, depth, dj - di) || self.in_t(cfg, depth, dj + di) {
                        continue;
                    }
                    a[i].set(j);
                    a[j].set(i);
                }
            }
            let mut all = B256::default();
            for i in 0..nlive {
                all.set(i);
            }
            let ok = has_clique(&a, all, need);
            self.adj[depth] = a;
            if !ok {
                self.prunes[depth] += 1;
                self.live[depth] = l;
                return None;
            }
        }
        self.live[depth] = l;
        Some((nlive, use_graph))
    }

    /// Try child ci of the node at `depth`; on acceptance sol[depth] is set and
    /// cand[depth + 1] holds the child's candidates.
    fn child(&mut self, cfg: &Cfg, depth: usize, ci: usize, use_graph: bool) -> bool {
        let t = self.live[depth][ci];
        if depth < cfg.prefix.len() && t != cfg.prefix[depth] {
            return false;
        }
        self.sol[depth] = t;
        if depth < cfg.canon_depth && !canon_fast(cfg, &self.sol[..depth + 1]) {
            return false;
        }
        let (lo, hi) = self.cand.split_at_mut(depth + 1);
        let _ = lo;
        let next = &mut hi[0];
        next.clear();
        let live = &self.live[depth];
        if use_graph {
            let row = &self.adj[depth][ci];
            for cj in ci + 1..live.len() {
                if row.get(cj) {
                    next.push(live[cj]);
                }
            }
        } else {
            next.extend_from_slice(&live[ci + 1..]);
        }
        true
    }

    fn dfs(&mut self, cfg: &Cfg, sh: &Shared, depth: usize, prefiltered: bool) {
        if sh.stop.load(Relaxed) {
            return;
        }
        let Some((nlive, use_graph)) = self.prepare(cfg, sh, depth, prefiltered) else { return };
        let need = cfg.n - depth;
        for ci in 0..nlive {
            if nlive - ci < need {
                break;
            }
            if self.child(cfg, depth, ci, use_graph) {
                self.dfs(cfg, sh, depth + 1, use_graph);
                if sh.stop.load(Relaxed) {
                    return;
                }
            }
        }
    }

    /// Restore the per-depth T structures for a task rooted at `prefix`.
    fn load(&mut self, cfg: &Cfg, prefix: &[u8], cand: &[u8]) {
        let depth = prefix.len();
        self.sol[..depth].copy_from_slice(prefix);
        for d in 1..depth {
            self.t_build(cfg, d);
        }
        self.cand[depth].clear();
        self.cand[depth].extend_from_slice(cand);
    }
}

/// Exact test for a clique of size k inside P (Tomita-style colour bound).
fn has_clique(a: &[B256], mut p: B256, k: usize) -> bool {
    if k == 0 {
        return true;
    }
    if (p.count() as usize) < k {
        return false;
    }
    if k == 1 {
        return true;
    }
    let mut order = [0u16; 256];
    let mut colour = [0u16; 256];
    let mut m = 0;
    let mut c = 0u16;
    let mut u = p;
    while !u.is_empty() {
        c += 1;
        let mut q = u;
        while !q.is_empty() {
            let v = q.first();
            u.clear(v);
            q.clear(v);
            q = q.and_not(&a[v]);
            order[m] = v as u16;
            colour[m] = c;
            m += 1;
        }
    }
    for i in (0..m).rev() {
        if (colour[i] as usize) < k {
            return false;
        }
        let v = order[i] as usize;
        if has_clique(a, p.and(&a[v]), k - 1) {
            return true;
        }
        p.clear(v);
    }
    false
}

/// Is there a bit permutation in the coset given by cells (A_c -> B_c) whose
/// image of x, sorted, is lex-smaller than cur, given that the first i points
/// already equal cur[..i]?
#[allow(clippy::too_many_arguments)]
fn min_image_less(cfg: &Cfg, x: &[u8], cur: &[u8], i: usize, a: &[u8], b: &[u8], used: u32) -> bool {
    let k = x.len();
    if i == k {
        return false;
    }
    let mut mi = [u32::MAX; MAXN];
    let mut p = u32::MAX;
    for (j, &xj) in x.iter().enumerate() {
        if used >> j & 1 == 1 {
            continue;
        }
        let mut v = 0u32;
        for c in 0..a.len() {
            v |= cfg.lowbits[b[c] as usize][(xj & a[c]).count_ones() as usize] as u32;
        }
        mi[j] = v;
        p = p.min(v);
    }
    let target = cur[i] as u32;
    if p < target {
        return true;
    }
    if p > target {
        return false;
    }
    for (j, &xj) in x.iter().enumerate() {
        if mi[j] != p {
            continue;
        }
        let mut a2 = [0u8; 9];
        let mut b2 = [0u8; 9];
        let mut n2 = 0;
        for c in 0..a.len() {
            let ac = xj & a[c];
            let bc = cfg.lowbits[b[c] as usize][ac.count_ones() as usize];
            if ac != 0 {
                a2[n2] = ac;
                b2[n2] = bc;
                n2 += 1;
            }
            if a[c] & !ac != 0 {
                a2[n2] = a[c] & !ac;
                b2[n2] = b[c] & !bc;
                n2 += 1;
            }
        }
        if min_image_less(cfg, x, cur, i + 1, &a2[..n2], &b2[..n2], used | 1 << j) {
            return true;
        }
    }
    false
}

/// Is cur lex-least in its orbit under translations and bit permutations
/// (and the row pivots, if enabled)?
fn canon_fast(cfg: &Cfg, cur: &[u8]) -> bool {
    let k = cur.len();
    let pivots = if cfg.pivots { cfg.q } else { 1 };
    let full = ((1u32 << (cfg.q - 1)) - 1) as u8;
    let mut tf = [0u8; MAXN];
    let mut x = [0u8; MAXN];
    for piv in 0..pivots {
        for i in 0..k {
            tf[i] = cfg.pivottab[piv][cur[i] as usize];
        }
        for a in 0..k {
            let m = tf[a];
            for i in 0..k {
                x[i] = tf[i] ^ m;
            }
            if min_image_less(cfg, &x[..k], cur, 1, &[full], &[full], 1 << a) {
                return false;
            }
        }
    }
    true
}

fn explore(cfg: &Cfg, sh: &Shared, prefix: Vec<u8>, cand: Vec<u8>, prefiltered: bool) {
    if sh.stop.load(Relaxed) {
        return;
    }
    let depth = prefix.len();
    let children: Vec<(Vec<u8>, Vec<u8>, bool)> = ENGINE.with(|cell| {
        let mut slot = cell.borrow_mut();
        let e = slot.get_or_insert_with(|| Engine::new(cfg));
        e.load(cfg, &prefix, &cand);
        if depth >= cfg.pardepth {
            e.dfs(cfg, sh, depth, prefiltered);
            e.flush(sh);
            return Vec::new();
        }
        let mut out = Vec::new();
        if let Some((nlive, use_graph)) = e.prepare(cfg, sh, depth, prefiltered) {
            let need = cfg.n - depth;
            for ci in 0..nlive {
                if nlive - ci < need {
                    break;
                }
                if e.child(cfg, depth, ci, use_graph) {
                    out.push((e.sol[..depth + 1].to_vec(), e.cand[depth + 1].clone(), use_graph));
                }
            }
        }
        e.flush(sh);
        out
    });
    children.into_par_iter().for_each(|(p, c, f)| explore(cfg, sh, p, c, f));
}

fn build_cfg(args: &Args) -> Result<Cfg, String> {
    let (q, n) = (args.q, args.n);
    if !(2..=9).contains(&q) || !(2..=MAXN).contains(&n) {
        return Err("require 2<=q<=9 and 2<=n<=20".into());
    }
    let anchor = args.mitm;
    if anchor < 1 || anchor > 9 || anchor >= n {
        return Err("require 1<=mitm<=9 and mitm<n".into());
    }
    let canon_depth = args.canondepth.unwrap_or(n);
    if canon_depth > n {
        return Err("require canondepth<=n".into());
    }
    let nt = 1usize << (q - 1);
    let mut prefix = Vec::new();
    for (i, &t) in args.prefix.iter().enumerate() {
        if t >= nt || (i == 0 && t != 0) || (i > 0 && t <= args.prefix[i - 1]) || i >= n {
            return Err("prefix must start with 0, increase strictly, and use types < 2^(q-1)".into());
        }
        prefix.push(t as u8);
    }
    let fb = if q == 9 { 7 } else { 8 };
    let delta: Vec<i64> = (0..nt)
        .map(|t| {
            let mut d: i64 = 1;
            for j in 1..q {
                let s: i64 = if (t >> (j - 1)) & 1 == 1 { -1 } else { 1 };
                d += s * (1i64 << (fb * j));
            }
            d
        })
        .collect();
    let zero = (0..q).map(|j| BIAS << (fb * j)).sum();

    let k = q - 1;
    let mut pivottab = vec![[0u8; 256]; q];
    for t in 0..nt {
        pivottab[0][t] = t as u8;
    }
    for (r, row) in pivottab.iter_mut().enumerate().skip(1) {
        let r_bit = r - 1;
        for t in 0..nt {
            let b_r = (t >> r_bit) & 1;
            let mut nt_ = b_r;
            let mut out = 1;
            for other in 0..k {
                if other == r_bit {
                    continue;
                }
                if b_r ^ ((t >> other) & 1) == 1 {
                    nt_ |= 1 << out;
                }
                out += 1;
            }
            row[t] = nt_ as u8;
        }
    }
    let lowbits = (0..256usize)
        .map(|b| {
            let mut row = [0xFFu8; 9];
            for (j, slot) in row.iter_mut().enumerate() {
                let (mut out, mut got) = (0u32, 0);
                for i in 0..8 {
                    if got < j && (b >> i) & 1 == 1 {
                        out |= 1 << i;
                        got += 1;
                    }
                }
                if got == j {
                    *slot = out as u8;
                }
            }
            row
        })
        .collect();
    Ok(Cfg {
        q,
        n,
        nt,
        delta,
        zero,
        anchor,
        clique_from: args.clique,
        canon_depth,
        pivots: args.pivots,
        pivottab,
        lowbits,
        pardepth: args.pardepth,
        prefix,
        maxsol: args.maxsol,
    })
}

fn node_line(v: &[AtomicU64]) -> String {
    v.iter().map(|x| x.load(Relaxed).to_string()).collect::<Vec<_>>().join(",")
}

fn main() {
    let args = Args::parse();
    let cfg = match build_cfg(&args) {
        Ok(c) => c,
        Err(e) => {
            eprintln!("{e}");
            std::process::exit(1);
        }
    };
    if let Some(t) = args.threads {
        rayon::ThreadPoolBuilder::new().num_threads(t).build_global().expect("thread pool");
    }
    let sh = Shared {
        nodes: (0..=cfg.n).map(|_| AtomicU64::new(0)).collect(),
        prunes: (0..=cfg.n).map(|_| AtomicU64::new(0)).collect(),
        nsol: AtomicUsize::new(0),
        stop: AtomicBool::new(false),
        out: Mutex::new(()),
    };
    println!(
        "q={} n={}: {} types, mitm anchor {}, clique from {}, canon<={}{}, pardepth {}, {} threads",
        cfg.q,
        cfg.n,
        cfg.nt,
        cfg.anchor,
        cfg.clique_from,
        cfg.canon_depth,
        if cfg.pivots { ", pivots=on" } else { "" },
        cfg.pardepth,
        rayon::current_num_threads()
    );
    if !cfg.prefix.is_empty() {
        println!("forced prefix: {}", cfg.prefix.iter().map(|t| t.to_string()).collect::<Vec<_>>().join(" "));
    }
    std::io::stdout().flush().ok();

    let start = Instant::now();
    let done = AtomicBool::new(false);
    std::thread::scope(|s| {
        s.spawn(|| {
            let mut last = Instant::now();
            while !done.load(Relaxed) {
                std::thread::sleep(Duration::from_millis(200));
                if last.elapsed().as_secs_f64() >= args.report {
                    last = Instant::now();
                    let _g = sh.out.lock().unwrap();
                    println!("  t={:7.0}s nodes=[{}] sols={}", start.elapsed().as_secs_f64(), node_line(&sh.nodes), sh.nsol.load(Relaxed));
                    std::io::stdout().flush().ok();
                }
            }
        });
        let root_cand: Vec<u8> = (1..cfg.nt).map(|t| t as u8).collect();
        explore(&cfg, &sh, vec![0u8], root_cand, false);
        done.store(true, Relaxed);
    });

    let el = start.elapsed().as_secs_f64();
    let total: u64 = sh.nodes.iter().map(|x| x.load(Relaxed)).sum();
    println!(
        "\nDONE in {:.2}s  nodes/depth: [{}]  total={}  rate={:.0} nodes/s",
        el,
        node_line(&sh.nodes),
        total,
        total as f64 / el.max(1e-9)
    );
    println!("clique prunes/depth: [{}]", node_line(&sh.prunes));
    let nsol = sh.nsol.load(Relaxed);
    println!("solutions found: {}", nsol.min(cfg.maxsol));
    if nsol == 0 {
        if cfg.prefix.is_empty() {
            println!("*** NO {}x{} DETECTING MATRIX EXISTS ***", cfg.q, cfg.n);
        } else {
            println!("*** no solutions below the requested prefix ***");
        }
    }
}
