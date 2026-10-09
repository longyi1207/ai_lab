import math
# 1. toy phase space: 12 particles on a line
pts=[(0.2,1.0),(0.5,1.0),(0.7,-1.0),(1.1,0.5),(1.3,1.0),(1.6,-0.5),(2.2,0.5),(2.4,-1.0),(2.5,1.0),(2.8,0.5),(3.3,-0.5),(3.6,1.0)]
def hist(ps):
    H={}
    for x,v in ps:
        H[(math.floor(x),v)]=H.get((math.floor(x),v),0)+1
    return H
print("t=0",sorted(hist(pts).items()))
pts1=[(x+v*1.0,v) for x,v in pts]
print("t=1",sorted(hist(pts1).items()))
print("pos-only t0",[sum(1 for x,v in pts if math.floor(x)==b) for b in range(-1,6)])
print("pos-only t1",[sum(1 for x,v in pts1 if math.floor(x)==b) for b in range(-1,6)])
# 2. relativistic velocity
for p in [0.01,0.1,0.5,1,2,3,10,100,1000]:
    print("p",p,"v",p/math.sqrt(1+p*p),"gamma",math.sqrt(1+p*p),"1-v",1-p/math.sqrt(1+p*p))
# 3. electron kinetic energies
mc2=511.0  # keV
for K in [0.001,1,10,100,1000,10000]:
    g=1+K/mc2; p=math.sqrt(g*g-1); print("K keV",K,"gamma",g,"p(mc)",p,"v/c",p/g)
print("10keV in K",10e3*11604.5)
print("solar wind 400km/s v/c",400/299792.458)
# 4. doubling times
H=lambda n: sum(1/k for k in range(1,n+1))
for n in [10,60,100,1000,10**6]: print("H",n,H(n))
# blowup ODE dp/dt=p^2 from p=1: doubling from 2^k to 2^{k+1} takes 1/2^k - 1/2^{k+1} = 1/2^{k+1}
s=0
for k in range(0,60): s+=1/2**(k+1)
print("p'=p^2 total doubling time 60 doublings",s)
# paper-shaped doubling time c/log(2+1024*2^n) with c=1
for N in [10,100,1000,10**4,10**5]:
    print("sum 1/log(2+1024*2^n) n=1..",N, sum(1/math.log(2+1024*2**min(n,1000)) if n<=1000 else 1/(n*math.log(2)+math.log(1024)) for n in range(1,N+1)))
# toy blowup by p' = p^2 vs p' = p log p? p'=p: doubling time ln2 constant
# 5 Coulomb energy outside R: ∫_R^∞ (1/(4π r^2))^2 4π r^2 dr = 1/(4π R)
for R in [1,10]: print("coulomb energy outside R",R,1/(4*math.pi*R))
