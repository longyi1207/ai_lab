import itertools, math, cmath, random
# Moser spindle
s3=math.sqrt(3)
def rot(p,a): c,s=math.cos(a),math.sin(a); return (c*p[0]-s*p[1], s*p[0]+c*p[1])
O=(0,0); B=(0.5,s3/2); C=(1,0); T=(1.5,s3/2)  # rhombus O,B,C,T ; OT = sqrt3
# rotate so that two tips are distance 1: angle between tips theta with 2*sqrt3*sin(theta/2)=1
th=2*math.asin(1/(2*s3))
print("rotation angle deg",math.degrees(th))
P1=[O,B,C,T]; P2=[rot(p,th) for p in P1]
pts={'O':O,'B1':B,'C1':C,'T1':T,'B2':P2[1],'C2':P2[2],'T2':P2[3]}
for k,v in pts.items(): print(k, tuple(round(x,4) for x in v))
names=list(pts); edges=[]
for a,b in itertools.combinations(names,2):
    d=math.dist(pts[a],pts[b])
    if abs(d-1)<1e-9: edges.append((a,b))
print("unit edges",len(edges),edges)
print("OT dist",math.dist(O,T), "T1T2",math.dist(T,P2[3]))
def colorings(k,names,edges):
    idx={n:i for i,n in enumerate(names)}
    return [c for c in itertools.product(range(k),repeat=len(names)) if all(c[idx[a]]!=c[idx[b]] for a,b in edges)]
for k in (3,4): print("k",k,"proper colorings of Moser spindle:",len(colorings(k,names,edges)))
# rhombus alone 3 colorings: tip same as O?
rn=['O','B1','C1','T1']; re_=[e for e in edges if e[0] in rn and e[1] in rn]
cs=colorings(3,rn,re_); print("rhombus 3-colorings",len(cs),"all O==T:",all(c[0]==c[3] for c in cs))
# triangle
print("triangle 2-colorings:",len(colorings(2,['a','b','c'],[('a','b'),('b','c'),('a','c')])))
# Hexagon 7-coloring
r=0.4
print("2r",2*r,"sqrt21 r",math.sqrt(21)*r,"(sqrt21-2)r",(math.sqrt(21)-2)*r)
w=cmath.exp(2j*math.pi/3); print("|2-w|^2",abs(2-w)**2)
# coloring: lattice spanned by a=sqrt3 r, b=sqrt3 r*w ; color by (m+ 3n?) mod 7 -- use coset of sublattice (2-w)Z[w]
a=s3*r
def center(z):
    # nearest lattice point in a*(Z+Zw); brute force neighbors
    u=z/a; # solve u = m + n w
    n=u.imag/w.imag; m=u.real-n*w.real
    best=None
    for dm in (-1,0,1,2):
        for dn in (-1,0,1,2):
            M=math.floor(m)+dm; N=math.floor(n)+dn
            c=a*(M+N*w); d=abs(z-c)
            if best is None or d<best[0]: best=(d,M,N)
    return best
def color(z):
    d,M,N=center(z)
    # coset of (2-w)Z[w] in Z[w]: map m+nw -> (m + 2n?) mod 7 ; find homomorphism killing 2-w and (2-w)w = 2w - w^2 = 2w +1+w = 1+3w
    return (M+ 2*N)%7   # check: 2-w -> (2,-1): 2-2=0 ; 1+3w -> 1+6=7=0 ok
random.seed(0); bad=0; N=200000; maxd=0
for _ in range(N):
    z=complex(random.uniform(-20,20),random.uniform(-20,20)); t=random.uniform(0,2*math.pi)
    z2=z+cmath.exp(1j*t)
    if color(z)==color(z2): bad+=1
    maxd=max(maxd,center(z)[0])
print("hex 7-coloring random unit pairs",N,"monochromatic",bad,"max dist to center",round(maxd,4))
# 6 colors via same trick fails? try mod 6 coloring with other homomorphism - skip
# search-space sizes
for n,k in [(7,3),(1581,4),(553,4),(509,4)]:
    print(n,k,"log10 k^n =",round(n*math.log10(k),1))
