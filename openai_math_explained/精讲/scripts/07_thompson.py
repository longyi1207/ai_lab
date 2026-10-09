from fractions import Fraction as Fr
from itertools import product
import math

print("=== 1. square symmetries: r=rotate 90 ccw, s=reflect across vertical axis; act on corners")
# corners labelled 0..3 ccw starting top-right; as coordinates
pts={(1,1):'A',(-1,1):'B',(-1,-1):'C',(1,-1):'D'}
r=lambda p:(-p[1],p[0]); s=lambda p:(-p[0],p[1])
def comp(f,g): return lambda p:f(g(p))
def show(f): return ''.join(pts[f(p)] for p in [(1,1),(-1,1),(-1,-1),(1,-1)])
print("r∘s:",show(comp(r,s)),"s∘r:",show(comp(s,r)))
# generate group
elems={}
frontier=[lambda p:p]
seen={show(frontier[0]):frontier[0]}
while frontier:
    nf=[]
    for f in frontier:
        for g in (r,s):
            h=comp(g,f); k=show(h)
            if k not in seen: seen[k]=h; nf.append(h)
    frontier=nf
print("group size",len(seen))

print("=== 2. free group F2 word counts")
gens=['a','A','b','B']; inv={'a':'A','A':'a','b':'B','B':'b'}
def reduce(w):
    st=[]
    for c in w:
        if st and st[-1]==inv[c]: st.pop()
        else: st.append(c)
    return ''.join(st)
spheres=[{''}]
for n in range(1,11):
    spheres.append({w+c for w in spheres[-1] for c in gens if not (w and w[-1]==inv[c])})
for n in range(0,11):
    ball=sum(len(spheres[k]) for k in range(n+1))
    print(n,len(spheres[n]),ball, "sphere/ball=%.4f"%(len(spheres[n])/ball))
# Z^2 ball (L1) for comparison
for n in [1,2,5,10]:
    print("Z2 L1 ball",n, 2*n*n+2*n+1, "sphere",4*n if n else 1)

print("=== 3. Folner ratios")
for n in [1,2,5,10,100,1000]:
    print("Z  n=%d |A|=%d ratio=%.5f"%(n,2*n+1,2/(2*n+1)))
for n in [1,2,5,10,100]:
    A={(i,j) for i in range(-n,n+1) for j in range(-n,n+1)}
    hA={(i+1,j) for i,j in A}
    print("Z2 box n=%d |A|=%d ratio=%.5f"%(n,len(A),len(hA^A)/len(A)))
for n in [1,2,4,6,8,10]:
    B=set().union(*spheres[:n+1])
    for h in ['a','b']:
        hB={reduce(h+w) for w in B}
        print("F2 ball n=%d |B|=%d h=%s ratio=%.4f"%(n,len(B),h,len(hB^B)/len(B)))

print("=== 4. paradoxical decomposition check on F2 ball radius 8")
N=8
B=set().union(*spheres[:N+1])
Wa={w for w in B if w.startswith('a')}; WA={w for w in B if w.startswith('A')}
Wb={w for w in B if w.startswith('b')}; WB={w for w in B if w.startswith('B')}
print("sizes e,Wa,WA,Wb,WB:",1,len(Wa),len(WA),len(Wb),len(WB))
# check every w in ball radius N-1 is in Wa ∪ a·WA
B7=set().union(*spheres[:N])
ok=all(w.startswith('a') or reduce('A'+w).startswith('A') for w in B7)
print("every word (len<=7) in Wa ∪ a·W(a^-1):",ok)
okb=all(w.startswith('b') or reduce('B'+w).startswith('B') for w in B7)
print("every word in Wb ∪ b·W(b^-1):",okb)

print("=== 5. Thompson F as PL maps (exact fractions)")
# represent map by list of breakpoints [(x,y)] including (0,0),(1,1)
x0=[(Fr(0),Fr(0)),(Fr(1,2),Fr(1,4)),(Fr(3,4),Fr(1,2)),(Fr(1),Fr(1))]
x1=[(Fr(0),Fr(0)),(Fr(1,2),Fr(1,2)),(Fr(3,4),Fr(5,8)),(Fr(7,8),Fr(3,4)),(Fr(1),Fr(1))]
def ev(f,x):
    for (a,b),(c,d) in zip(f,f[1:]):
        if a<=x<=c: return b+(d-b)/(c-a)*(x-a)
def inverse(f): return [(y,x) for x,y in f]
def simplify(f):
    out=[f[0]]
    for i in range(1,len(f)-1):
        (a,b),(c,d),(e,g)=out[-1],f[i],f[i+1]
        if (d-b)*(e-c)!=(g-d)*(c-a): out.append(f[i])
    out.append(f[-1]); return out
def compose(h,g): # (h∘g)(x)=h(g(x))
    xs=set(x for x,_ in g)|set(ev(inverse(g),x) for x,_ in h)
    return simplify([(x,ev(h,ev(g,x))) for x in sorted(xs)])
def slopes(f): return [(d-b)/(c-a) for (a,b),(c,d) in zip(f,f[1:])]
def fmt(f): return ' '.join(f"({x},{y})" for x,y in f)
I=[(Fr(0),Fr(0)),(Fr(1),Fr(1))]
print("x0:",fmt(x0),"slopes",[str(s) for s in slopes(x0)])
print("x1:",fmt(x1),"slopes",[str(s) for s in slopes(x1)])
for name,f in [("x0∘x1",compose(x0,x1)),("x1∘x0",compose(x1,x0)),("x0^-1",inverse(x0)),("x0∘x0",compose(x0,x0))]:
    print(name,":",fmt(f),"slopes",[str(s) for s in slopes(f)])
print("x0(3/8)=",ev(x0,Fr(3,8)),"x1(x0(7/8))=",ev(x1,ev(x0,Fr(7/8) if False else Fr(7,8))),"x0(x1(7/8))=",ev(x0,ev(x1,Fr(7,8))))
X0i=inverse(x0); X1i=inverse(x1)
def word(*fs):
    r=I
    for f in fs: r=compose(r,f)   # word read left-to-right = composition h∘g∘...
    return r
def comm(a,b): return word(inverse(a),inverse(b),a,b)
u=word(x0,X1i)
v1=word(X0i,x1,x0); v2=word(X0i,X0i,x1,x0,x0)
print("u=x0 x1^-1:",fmt(u))
print("v1=x0^-1 x1 x0:",fmt(v1))
print("[u,v1]==id:",comm(u,v1)==I, " [u,v2]==id:",comm(u,v2)==I)
# supports
print("support u (non-fixed region) ~ ; v1 breakpoints",fmt(v1))
# x2 = x0^-1 x1 x0 in CFP; check x1 commutes with x0^-1 x1 x0? 
print("x1 commutes with x0^-1x1x0 ?", word(x1,v1)==word(v1,x1))
print("x0 x1 == x1 x0 ?", compose(x0,x1)==compose(x1,x0))

print("=== 6. growth of F balls (generators x0,x1 and inverses)")
gensF=[x0,x1,X0i,X1i]
key=lambda f:tuple(f)
seen={key(I)}; front=[I]; sizes=[1]
for n in range(1,9):
    nf=[]
    for f in front:
        for g in gensF:
            h=compose(g,f); k=key(h)
            if k not in seen: seen.add(k); nf.append(h)
    front=nf; sizes.append(len(seen))
    print(n,"sphere",len(nf),"ball",len(seen),"F2 ball",2*3**n-1)
# Folner ratio of F balls
ballF=None

print("=== 7. Kakutani fixed-point-free map on l2 ball: displacement at x=(t,..,t) N coords")
for N in [1,4,100,10**4,10**6]:
    t=1/(1+math.sqrt(N)); print("N=%d t=%.5f |x|=%.5f displacement=%.5f"%(N,t,t*math.sqrt(N),t))
print("=== 8. paper constants: delta=1/2 -> need D > 4L^2/delta^2 = 16 L^2")
for L in [1,2,10]:
    D=16*L*L+1
    print("L=%d D=%d bound=%.6f"%(L,D,((0.25)/L**2-4/D)/(4*(1-1/D))))
