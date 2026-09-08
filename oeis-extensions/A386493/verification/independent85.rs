// Contributed by Shmulik Cohen, Sep 08 2026; developed with AI assistance.
// Fixed exhaustive exclusion: 15 points, squared diameter at most 85.
use std::time::{Instant,Duration};
struct Search { adj:Vec<u128>, bad:Vec<Vec<u128>>, sel:Vec<usize>, nodes:u64, start:Instant, timeout:bool, witness:Option<Vec<usize>> }
impl Search {
 fn dfs(&mut self, mut cand:u128) {
  self.nodes+=1;
  if self.nodes%4096==0 && self.start.elapsed()>Duration::from_secs(85) {self.timeout=true;return}
  if self.sel.len()==15 {self.witness=Some(self.sel.clone());return}
  while cand.count_ones() as usize + self.sel.len() >=15 {
   let v=cand.trailing_zeros() as usize; cand &= cand-1;
   let mut next=cand & self.adj[v];
   for &u in &self.sel {next &= !self.bad[v][u]}
   self.sel.push(v);self.dfs(next);self.sel.pop();
   if self.timeout || self.witness.is_some(){return}
  }
 }
}
fn main(){
 let m=100usize; let mut ds=vec![vec![0i32;m];m];
 for i in 0..m {for j in 0..m {let dx=(i%10) as i32-(j%10) as i32;let dy=(i/10) as i32-(j/10) as i32;ds[i][j]=dx*dx+dy*dy;}}
 let mut adj=vec![0u128;m];let mut bad=vec![vec![0u128;m];m];
 for i in 0..m {for j in 0..m {if i!=j && ds[i][j]<=85 {adj[i]|=1<<j;}
  if i==j {continue}
  for k in 0..m {if k==i || k==j {continue}
   let t=[i,j,k];let mut invalid=false;
   for a in 0..3 {let apex=t[a];if ds[apex][t[(a+1)%3]]==ds[apex][t[(a+2)%3]] {invalid=true}}
   if invalid {bad[i][j]|=1<<k}
  }
 }}
 let mut s=Search{adj,bad,sel:vec![],nodes:0,start:Instant::now(),timeout:false,witness:None};s.dfs((1u128<<100)-1);
 let status=if s.timeout {"timeout"}else if s.witness.is_some(){"sat"}else{"unsat"};
 println!("{{\"status\":\"{}\",\"exhaustive\":{},\"nodes\":{},\"seconds\":{},\"D\":85,\"n\":15,\"domain_points\":100,\"pruning\":\"candidate count only\",\"witness_indices\":{:?}}}",status,status=="unsat",s.nodes,s.start.elapsed().as_secs_f64(),s.witness.unwrap_or_default());
}
