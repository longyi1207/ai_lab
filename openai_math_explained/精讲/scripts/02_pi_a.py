import math
from fractions import Fraction
from mpmath import mp, mpf, pi, e, sqrt, log, floor, sin, fabs
mp.dps = 3000
def cf(x, n):
    a=[]; 
    for _ in range(n):
        ai=int(floor(x)); a.append(ai); x=x-ai
        if x==0: break
        x=1/x
    return a
def convergents(a):
    p0,q0,p1,q1=1,0,a[0],1
    out=[(p1,q1)]
    for ai in a[1:]:
        p0,q0,p1,q1=p1,q1,ai*p1+p0,ai*q1+q0
        out.append((p1,q1))
    return out
PI=+pi
print("pi cf first 20:", cf(PI,20))
print("e cf first 20:", cf(+e,20))
print("sqrt2 cf:", cf(sqrt(2),10))
print("phi cf:", cf((1+sqrt(5))/2,10))
a=cf(PI,1200); C=convergents(a)
print("\n# pi convergents")
for i,(p,q) in enumerate(C[:8]):
    err=fabs(PI-mpf(p)/q)
    print(i,f"{p}/{q}", "err=%.3e"%float(err), "1/q^2=%.3e"%float(mpf(1)/q**2), "q^2*err=%.4f"%float(q*q*err), "nu=%.4f"%(float(-log(err)/log(q)) if q>1 else float('nan')), "next a=",a[i+1])
# max effective exponent over convergents with q>=10^k
nus=[]
for i,(p,q) in enumerate(C[:1000]):
    if q<10: continue
    err=fabs(PI-mpf(p)/q); nus.append((float(-log(err)/log(q)),i,len(str(q))))
nus.sort(reverse=True); print("\ntop effective exponents among first 1000 convergents (nu, index, digits of q):", nus[:5])
print("largest partial quotient among first 1000:", max(a[1:1001]), "at index", a[1:1001].index(max(a[1:1001]))+1)
print("digits of q_999:", len(str(C[999][1])))
# 'other' fractions 3, 22/7, 333/106, 355/113 already; compare 314/100
for p,q in [(314,100),(3,1),(22,7),(333,106),(355,113),(103993,33102)]:
    err=fabs(PI-mpf(p)/q); print(f"{p}/{q}: err={float(err):.3e}")
# Dirichlet pigeonhole demo: for each q<=1000 count with |pi-p/q|<1/q^2 using best p
print("\n# count q<=N where best p gives |pi-p/q|< 1/q^nu")
for nu in [2,2.2,2.5,3]:
    cnt=[q for q in range(1,100001) if fabs(PI-mpf(round(float(PI)*q))/q) < mpf(q)**(-nu)] if False else None
import mpmath
mp.dps=50; PI=+pi
for nu in [2,2.2,2.5,3]:
    qs=[q for q in range(2,100001) if fabs(PI-mpf(int(mpmath.nint(PI*q)))/q) < mpf(q)**(-nu)]
    print(nu, len(qs), qs[:12])
# e convergents nu
mp.dps=500
ae=cf(+e,60); Ce=convergents(ae)
print("\n# e effective exponent at convergents 10,20,40,59:",[ (Ce[i][1], round(float(-log(fabs(e-mpf(Ce[i][0])/Ce[i][1]))/log(Ce[i][1])),4)) for i in [10,20,40,59]])
# sqrt2 convergents q^2 err
a2=cf(sqrt(2),30); C2=convergents(a2)
print("sqrt2 q^2*err:",[ (p,q,round(float(q*q*fabs(sqrt(2)-mpf(p)/q)),4)) for p,q in C2[1:7]])
# Liouville
mp.dps=1000
L=sum(mpf(10)**(-math.factorial(k)) for k in range(1,7))
for n in [2,3,4]:
    q=10**math.factorial(n); p=int(floor(L*q)); 
    print("Liouville k<=%d: q=10^%d err=10^%.2f nu=%.2f"%(n,math.factorial(n),float(log(fabs(L-mpf(p)/q),10)), float(-log(fabs(L-mpf(p)/q))/log(q))))
# Flint Hills partial sums
mp.dps=40
s=mpf(0); marks={1,3,21,22,354,355,1000,52162,52163,103992,103993,200000}
out={}
for n in range(1,200001):
    pass
for n in []:
    t=1/(mpf(n)**3*sin(n)**2) if n in marks or n%1==0 else 0
    s+=t
    if n in marks: out[n]=(float(s),float(t))
for n in sorted(out): print("FH n=%d partial=%.4f term=%.4g"%(n,*out[n]))
