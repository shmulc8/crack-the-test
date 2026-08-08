/* Direct test of the proved implication E(q)>=D(q-1)+1: every McKay dissociated 12-set S in {0,1}^7,
   with 0 adjoined, must be a valid 8x13 detecting matrix -- i.e. all 2^13
   subset sums distinct once the all-ones row supplies the subset size. */
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#define FLD 5                     /* 5 bits/coord: sums <= 13 < 32 ; 5*8=40 bits */
static uint64_t sums[1<<13];
static int cmp64(const void*a,const void*b){uint64_t x=*(const uint64_t*)a,y=*(const uint64_t*)b;return x<y?-1:(x>y);}
static uint64_t delta_of(int t){                /* type t -> packed +1 in coord 0 (count) + bits */
    uint64_t d = 1;                              /* coord 0 counts subset size */
    for (int j = 0; j < 7; j++) if ((t>>j)&1) d += (uint64_t)1 << (FLD*(j+1));
    return d;
}
static int detecting(const int *T, int k){
    long long cnt = 1; sums[0] = 0;
    for (int i = 0; i < k; i++){
        uint64_t d = delta_of(T[i]);
        for (long long j = 0; j < cnt; j++) sums[cnt+j] = sums[j] + d;
        cnt *= 2;
    }
    qsort(sums, cnt, sizeof(uint64_t), cmp64);
    for (long long i = 1; i < cnt; i++) if (sums[i] == sums[i-1]) return 0;
    return 1;
}
int main(int argc,char**argv){
    if (argc != 2) { fprintf(stderr, "usage: %s <mckay7.txt>\n", argv[0]); return 2; }
    FILE *f = fopen(argv[1], "r");
    if (!f) { perror(argv[1]); return 2; }
    long n = 0, ok = 0, bad = 0; int v, S[13], rc;
    while ((rc = fscanf(f, "%d", &v)) == 1){
        if (v < 0 || v >= 128) { fprintf(stderr, "invalid type %d in record %ld\n", v, n + 1); fclose(f); return 2; }
        S[1] = v;
        for (int i = 2; i <= 12; i++) {
            if (fscanf(f, "%d", &v) != 1 || v < 0 || v >= 128) {
                fprintf(stderr, "malformed record %ld\n", n + 1); fclose(f); return 2;
            }
            S[i] = v;
        }
        S[0] = 0;                                 /* adjoin the zero vector */
        n++;
        if (detecting(S,13)) ok++; else bad++;
    }
    if (rc != EOF) { fprintf(stderr, "invalid token after record %ld\n", n); fclose(f); return 2; }
    fclose(f);
    printf("McKay 12-sets tested : %ld\n", n);
    printf("  S u {0} is a valid 8x13 detecting matrix : %ld\n", ok);
    printf("  FAILED                                   : %ld\n", bad);
    if (n != 118485) {
        fprintf(stderr, "expected 118485 McKay records, got %ld\n", n);
        return 2;
    }
    printf(bad==0 ? "\nPASS: every McKay dissociated 12-set yields an 8x13 detecting matrix after adjoining 0\n"
                  : "\nFAIL: the proved implication was violated\n");
    return bad != 0;
}
