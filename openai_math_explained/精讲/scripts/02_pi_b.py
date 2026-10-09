import math
from mpmath import mp, mpf, pi, nint, fabs
mp.dps=50; PI=+pi
for N in [1000,100000]:
  for nu in [2,2.2,2.5,3]:
    qs=[]
    for q in range(2,N+1):
        p=int(nint(PI*q))
        if math.gcd(p,q)!=1: continue
        if fabs(PI-mpf(p)/q) < mpf(q)**(-nu): qs.append(q)
    print(N,nu,len(qs),qs[:15])
# Flint Hills partial sums (float64)
s=0.0; marks=[1,2,3,21,22,354,355,1000,10000,33101,33102,52162,52163,103992,103993,104347,104348,200000,1000000]
big=[]
for n in range(1,1000001):
    t=1.0/(n**3*math.sin(n)**2); s+=t
    if t>0.01: big.append((n,round(t,4)))
    if n in marks: print("FH n=%d partial=%.4f term=%.4g"%(n,s,t))
print("terms > 0.01:",big)
# Dirichlet pigeonhole demo Q=10 for pi: fractional parts of q*pi, q=0..10
fr=[(q,(q*math.pi)%1) for q in range(0,11)]
print(sorted(fr,key=lambda x:x[1]))
