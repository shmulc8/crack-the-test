/* Random differential test of the lex-min canonicity tests in enum_fast.c:
 * canon_fast (minimal-image search) against canon_ok (brute force) and an
 * independent brute-force lex-min computed here. Sets are drawn from small
 * sub-cubes as well as the full cube, so ties and large stabilisers are common.
 * Usage: canon_random_check Q ITERATIONS SEED  (exit status 1 on any mismatch) */
#define main enum_main
#include "enum_fast.c"
#undef main
static unsigned long long rs = 88172645463325252ULL;
static unsigned rnd(void){ rs ^= rs<<13; rs ^= rs>>7; rs ^= rs<<17; return (unsigned)rs; }
static int cmpi(const void*a,const void*b){return *(int*)a-*(int*)b;}
/* brute-force lex-min image of a set (any set; translations by all m) */
static void lexmin(const int *s, int k, int *out){
  int best[MAXN]; int have=0; int img[MAXN];
  for(int a=0;a<k;a++){ int m=s[a];
    for(int p=0;p<NPERM;p++){ const unsigned char*P=permtab+(size_t)p*NT;
      for(int i=0;i<k;i++) img[i]=P[s[i]^m];
      qsort(img,k,sizeof(int),cmpi);
      int less=!have; if(have) for(int i=0;i<k;i++){ if(img[i]<best[i]){less=1;break;} if(img[i]>best[i])break; }
      if(less){ memcpy(best,img,sizeof(int)*k); have=1; }
    }}
  memcpy(out,best,sizeof(int)*k);
}
int main(int argc,char**argv){
  q=atoi(argv[1]); int iters=atoi(argv[2]); rs ^= (unsigned long long)atoi(argv[3])*0x9E3779B97F4A7C15ULL;
  NT=1<<(q-1); build_perms(); build_lowbits(); use_pivots=0;
  long long tested=0, canon1=0, mism=0;
  int s[MAXN], c[MAXN];
  for(int it=0;it<iters;it++){
    int k=2+rnd()%15; /* 2..16 */
    int mode=rnd()%4; int poolbits = (mode==0)? q-1 : 3+rnd()%(q-3);
    int poolmask=(1<<poolbits)-1; if (poolmask>NT-1) poolmask=NT-1;
    int pool=poolmask+1; if(k>pool) k=pool;
    /* pick k distinct from pool, scatter bits randomly by a random perm? keep as-is */
    int used[256]={0}; int cnt=0;
    while(cnt<k){ int t=rnd()&poolmask; if(mode==3) t = t & (rnd()&poolmask); if(!used[t]){used[t]=1;s[cnt++]=t;} }
    qsort(s,k,sizeof(int),cmpi);
    lexmin(s,k,c); /* c is canonical, contains 0 */
    /* test c itself and variants */
    int vars[4][MAXN]; int nv=0;
    memcpy(vars[nv++],c,sizeof(int)*k);
    /* random set containing 0 */
    { int t[MAXN]; memcpy(t,s,sizeof(int)*k); int m=t[rnd()%k]; for(int i=0;i<k;i++) t[i]^=m; qsort(t,k,sizeof(int),cmpi); memcpy(vars[nv++],t,sizeof(int)*k); }
    /* perturb last element of canonical */
    if(k>=2){ int t[MAXN]; memcpy(t,c,sizeof(int)*k); int ok=0; for(int tries=0;tries<20&&!ok;tries++){ int v=rnd()%NT; int dup=0; for(int i=0;i<k-1;i++) if(t[i]==v) dup=1; if(!dup && v>t[k-2]){ t[k-1]=v; ok=1; } } if(ok){memcpy(vars[nv++],t,sizeof(int)*k);} }
    /* perturb a middle element */
    if(k>=3){ int t[MAXN]; memcpy(t,c,sizeof(int)*k); int j=1+rnd()%(k-1); int v=rnd()%NT; int dup=0; for(int i=0;i<k;i++) if(t[i]==v) dup=1; if(!dup&&v!=0){ t[j]=v; qsort(t,k,sizeof(int),cmpi); if(t[0]==0) memcpy(vars[nv++],t,sizeof(int)*k);} }
    for(int v=0;v<nv;v++){
      int a=canon_ok(vars[v],k), b=canon_fast(vars[v],k); tested++; canon1+=a;
      /* independent oracle: lexmin equals itself */
      int lm[MAXN]; lexmin(vars[v],k,lm); int ind = memcmp(lm,vars[v],sizeof(int)*k)==0;
      if(a!=b || a!=ind){ mism++; fprintf(stderr,"MISMATCH brute=%d fast=%d indep=%d k=%d:",a,b,ind,k); for(int i=0;i<k;i++) fprintf(stderr," %d",vars[v][i]); fprintf(stderr,"\n"); }
    }
  }
  printf("q=%d tested=%lld canonical=%lld mismatches=%lld\n",q,tested,canon1,mism);
  return mism?1:0;
}
