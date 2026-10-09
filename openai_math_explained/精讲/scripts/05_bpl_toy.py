import random, math, itertools
import numpy as np
random.seed(0); np.random.seed(0)
print("== 1. log sizes ==")
for n in [10**3,10**6,10**9,10**12]:
    l=math.log2(n); print(n, f"log={l:.1f} log^1.5={l**1.5:.0f} log^2={l**2:.0f}  n_bytes={n}")
print("== 2. PIT toy ==")
S=range(100); cnt=sum(1 for x in S for y in S if (x+y)**2 == x*x+y*y)
print("wrong identity agree count",cnt,"of",100*100, cnt/1e4)
# 3. random walks
def walk_hit(adj,s,t,trials=20000):
    tot=0; mx=0
    for _ in range(trials):
        v=s; k=0
        while v!=t:
            v=random.choice(adj[v]); k+=1
        tot+=k; mx=max(mx,k)
    return tot/trials, mx
def cover(adj,s,trials=5000):
    n=len(adj); tot=0
    for _ in range(trials):
        seen={s}; v=s; k=0
        while len(seen)<n:
            v=random.choice(adj[v]); seen.add(v); k+=1
        tot+=k
    return tot/trials
print("== 3. toy graph 6 nodes ==")
# toy graph: 0-1,0-2,1-2,2-3,3-4,4-5
E=[(0,1),(0,2),(1,2),(2,3),(3,4),(4,5)]
adj=[[] for _ in range(6)]
for a,b in E: adj[a].append(b); adj[b].append(a)
print("hit 0->5", walk_hit(adj,0,5), "cover from 0", cover(adj,0), "bound 2|E|(n-1)=",2*len(E)*5)
# one sample trace
random.seed(1); v=0; tr=[0]
while v!=5: v=random.choice(adj[v]); tr.append(v)
print("trace",tr,len(tr)-1)
print("== path graph hitting 0->n-1 (exact (n-1)^2) ==")
for n in [5,10,20,40]:
    adj=[[j for j in (i-1,i+1) if 0<=j<n] for i in range(n)]
    print(n, walk_hit(adj,0,n-1,5000)[0], (n-1)**2)
print("== lollipop worst case: clique of n/2 + path n/2, start in clique, target path end; exact via linear solve ==")
def hit_exact(adj,t):
    n=len(adj); A=np.eye(n); b=np.ones(n)
    for v in range(n):
        if v==t: A[v]=0; A[v,v]=1; b[v]=0; continue
        for u in adj[v]: A[v,u]-=1/len(adj[v])
    return np.linalg.solve(A,b)
for n in [10,20,40,80]:
    k=n//2; adj=[[] for _ in range(n)]
    for i in range(k):
        for j in range(k):
            if i!=j: adj[i].append(j)
    for i in range(k-1,n-1): adj[i].append(i+1); adj[i+1].append(i)
    h=hit_exact(adj,n-1); m=sum(len(a) for a in adj)//2
    print(n, f"H(0->end)={h[0]:.0f}", "n^3=",n**3, f"ratio={h[0]/n**3:.3f}", "2m(n-1)=",2*m*(n-1))
print("== directed: forward edge i->i+1 or reset to 0, prob 1/2 each ==")
for n in [5,10,15,20,30]:
    # E[time to reach n] from 0
    adj=[[i+1,0] for i in range(n)]+[[n]]
    h=hit_exact(adj,n)
    print(n, f"{h[0]:.0f}", 2**(n+1)-2)
print("== amplification BPL: majority of k runs at p=2/3 ==")
from math import comb
for k in [1,11,51,101,201]:
    err=sum(comb(k,i)*(2/3)**i*(1/3)**(k-i) for i in range(0,k//2+1))
    print(k, f"{err:.2e}", "counter bits", math.ceil(math.log2(k+1)))
print("== layered toy: acceptance prob via matrix powers ==")
# width 3 layered program, 4 steps; states 0,1,2; each step coin: 0->(0|1),1->(2|0),2->(2|2)
T=np.array([[.5,.5,0],[.5,0,.5],[0,0,1]])
v=np.array([1.,0,0])
for t in range(1,5):
    v=v@T; print(t, v)
print("accept=state2 prob", v[2])
# brute force over 16 coin strings
nxt={0:(0,1),1:(2,0),2:(2,2)}; acc=0
for bits in itertools.product([0,1],repeat=4):
    s=0
    for b in bits: s=nxt[s][b]
    acc+= s==2
print("brute",acc,"/16")
print("== spectral gap cycle vs random 4-regular ==")
import networkx as nx
for n in [16,64,256]:
    C=nx.cycle_graph(n); R=nx.random_regular_graph(4,n,seed=1)
    def lam2(G,d):
        M=nx.to_numpy_array(G)/d; ev=sorted(abs(np.linalg.eigvalsh(M)),reverse=True); return ev[1]
    print(n, f"cycle lam2={lam2(C,2):.4f}", f"rand4reg lam2={lam2(R,4):.4f}", f"bound 2sqrt3/4={2*math.sqrt(3)/4:.4f}")
print("== seeds ==")
for n in [10**3,10**6]:
    l=math.log2(n); print(n, f"truly random bits n^1 ~ {n}", f"Nisan seed ~log^2={l*l:.0f} -> enumerate 2^{l*l:.0f}", f"ideal seed ~log n={l:.0f} -> enumerate {n}")
