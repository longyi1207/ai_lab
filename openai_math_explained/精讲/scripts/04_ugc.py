import math, itertools, random
import numpy as np
from scipy.optimize import minimize_scalar
print("== GW constant ==")
f=lambda t: 2*t/(math.pi*(1-math.cos(t)))
r=minimize_scalar(f,bounds=(0.1,math.pi),method='bounded',options={'xatol':1e-12})
print("alpha_GW=%.6f theta*=%.4f rad=%.2f deg rho=%.4f"%(r.fun,r.x,math.degrees(r.x),math.cos(r.x)))
for deg in [60,90,120,133.56,150,180]:
    t=math.radians(deg); print(deg, "sdp=%.4f cutprob=%.4f ratio=%.4f"%((1-math.cos(t))/2,t/math.pi,f(t)))
print("16/17=%.6f"%(16/17), "sqrt2=%.4f"%math.sqrt(2))
# Monte Carlo hyperplane
rng=np.random.default_rng(0)
for deg in [90,120,150]:
    t=math.radians(deg); u=np.array([1,0,0.]); v=np.array([math.cos(t),math.sin(t),0])
    g=rng.standard_normal((1_000_000,3)); p=np.mean(np.sign(g@u)!=np.sign(g@v))
    print("MC deg",deg,"P(cut)=%.4f vs theta/pi=%.4f"%(p,t/math.pi))
def maxcut(n,E):
    best=0
    for s in itertools.product([0,1],repeat=n):
        best=max(best,sum(s[a]!=s[b] for a,b in E))
    return best
tri=[(0,1),(1,2),(0,2)]; C5=[(i,(i+1)%5) for i in range(5)]
pet=[(i,(i+1)%5) for i in range(5)]+[(5+i,5+(i+2)%5) for i in range(5)]+[(i,i+5) for i in range(5)]
for name,n,E in [("triangle",3,tri),("C5",5,C5),("Petersen",10,pet)]:
    m=maxcut(n,E); print(name,"edges",len(E),"maxcut",m,"random",len(E)/2,"ratio %.4f"%(len(E)/2/m))
# C5 SDP: angle 4pi/5
t=4*math.pi/5; sdp=5*(1-math.cos(t))/2; gw=5*t/math.pi
print("C5 SDP=%.4f GW expected=%.4f OPT=4 OPT/SDP=%.4f"%(sdp,gw,4/sdp))
print("== Unique games toys ==")
def ug_opt(n,k,cons):
    best=0;arg=None
    for lab in itertools.product(range(k),repeat=n):
        s=sum((lab[i]-lab[j])%k==c for i,j,c in cons)
        if s>best: best,arg=s,lab
    return best,arg
# x_i - x_j = c mod k
print(ug_opt(3,3,[(1,0,1),(2,1,1),(0,2,1)]))
print(ug_opt(3,3,[(1,0,1),(2,1,1),(0,2,2)]))
cons=[(1,0,2),(2,1,3),(3,2,1),(0,3,4),(2,0,0)]
print("4var mod5",ug_opt(4,5,cons))
cons2=[(1,0,2),(2,1,3),(3,2,1),(0,3,4),(2,0,1)]
print("4var mod5 v2",ug_opt(4,5,cons2))
# propagation demo on noisy expander-ish random graph
def demo(n=2000,d=6,k=7,noise=0.05,seed=1,trials=20):
    rnd=random.Random(seed)
    planted=[rnd.randrange(k) for _ in range(n)]
    E=set()
    while len(E)<n*d//2:
        a,b=rnd.randrange(n),rnd.randrange(n)
        if a!=b and (a,b) not in E and (b,a) not in E: E.add((a,b))
    E=list(E); cons=[]
    for a,b in E:
        c=(planted[a]-planted[b])%k
        if rnd.random()<noise: c=(c+rnd.randrange(1,k))%k
        cons.append((a,b,c))
    adj=[[] for _ in range(n)]
    for a,b,c in cons: adj[b].append((a,c)); adj[a].append((b,(-c)%k))
    val=lambda lab: sum((lab[a]-lab[b])%k==c for a,b,c in cons)/len(cons)
    res=[]
    for t in range(trials):
        root=rnd.randrange(n); lab=[None]*n; lab[root]=0; q=[root]
        for u in q:
            for v,c in adj[u]:
                if lab[v] is None: lab[v]=(lab[u]+c)%k; q.append(v)
        lab=[x if x is not None else 0 for x in lab]
        res.append(val(lab))
    return val(planted),sum(res)/len(res),max(res)
for nz in [0.0,0.01,0.05,0.10]:
    p,a,m=demo(noise=nz); print("noise",nz,"planted %.3f bfs-avg %.3f bfs-max %.3f"%(p,a,m))
print("== growth ==")
for n in [100,1000,10**6]:
    print(n,"3^n=10^%.1f"%(n*math.log10(3)),"2^(n^0.1)=%.3g"%(2**(n**0.1)),"2^(n^(1/3))=10^%.1f"%(n**(1/3)*math.log10(2)),"n^3=%.3g"%n**3)
