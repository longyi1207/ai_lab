import math, sympy as sp, itertools, random
print("== 1. exponents from fixed-size decompositions")
for k,r,lab in [(2,8,'naive'),(2,7,'Strassen'),(3,27,'naive3'),(3,23,'Laderman'),(4,49,'Strassen^2'),(4,48,'AlphaEvolve C'),(4,47,'AlphaTensor GF2')]:
    print(k,r,lab, round(math.log(r,k),4))
print("u^2.25 for u=2..10:",[(u,round(u**2.25,2)) for u in range(2,11)])
print("needed rank < u^2.25 vs naive u^3:",[(u,math.floor(u**2.25 - 1e-9), u**3) for u in [2,4,8,16,32,64]])
print("== 2. Strassen symbolic check")
a,b,c,d,e,f,g,h=sp.symbols('a b c d e f g h')
M1=(a+d)*(e+h);M2=(c+d)*e;M3=a*(f-h);M4=d*(g-e);M5=(a+b)*h;M6=(c-a)*(e+f);M7=(b-d)*(g+h)
C=[M1+M4-M5+M7, M3+M5, M2+M4, M1-M2+M3+M6]
T=[a*e+b*g, a*f+b*h, c*e+d*g, c*f+d*h]
print([sp.expand(x-y)==0 for x,y in zip(C,T)])
print("== 3. counts")
def S_mult(n): return 1 if n==1 else 7*S_mult(n//2)
def S_tot(n,cut=1):
    if n<=cut: return 2*n**3-n**2
    return 7*S_tot(n//2,cut)+18*(n//2)**2
for k in range(1,13):
    n=2**k; naive_m=n**3; naive_t=2*n**3-n**2
    print(n, naive_m, S_mult(n), round(S_mult(n)/naive_m,3), naive_t, S_tot(n), round(S_tot(n)/naive_t,3), S_tot(n,cut=64) if n>64 else '')
print("== 4. Karatsuba-like C(2,2)")
x0,x1,y0,y1=sp.symbols('x0 x1 y0 y1')
P0=x0*y0; P1=(x0+x1)*(y0+y1); P2=x1*y1
print(sp.expand(P1-P0-P2))
print("== 5. border rank W tensor")
X0,X1,Y0,Y1,Z0,Z1,eps=sp.symbols('X0 X1 Y0 Y1 Z0 Z1 epsilon')
expr=sp.expand(((X0+eps*X1)*(Y0+eps*Y1)*(Z0+eps*Z1)-X0*Y0*Z0)/eps)
print(sp.collect(expr,eps))
print("== 6. history diffs")
hist=[(1969,2.807355),(1978,2.796),(1979,2.780),(1981,2.522),(1986,2.479),(1990,2.375477),(2014,2.3728639),(2021,2.3728596),(2023,2.371866),(2024,2.371552),(2024.5,2.371339),(2026.6,2.371177),(2026.7,2.371054886),(2026.75,2.258),(2026.76,2.25)]
for (y1,w1),(y2,w2) in zip(hist,hist[1:]): print(y2,w2,round(w1-w2,7))
print("1990->2024.5 drop",2.375477-2.371339,"2014->Aug2026",2.3728639-2.371177,"Aug2026->9/4",2.371177-2.25)
print("== 7. t=0.8 failure point")
for t in [0.8,0.76,0.751]:
    s=1/t
    # find smallest a with a^{4/3} > (2a-1)^{s}
    lo=1
    a=2
    while a**(4/3) <= (2*a-1)**s: a=int(a*1.5)+1
    hi=a; lo=a//2
    while lo<hi:
        m=(lo+hi)//2
        if m**(4/3)>(2*m-1)**s: hi=m
        else: lo=m+1
    print(t, lo)
print("flattening t=2/3: 3t =",3*2/3)
print("== 8. Lemma 5.1 product")
for A in [2,5,10,100,1000]:
    p=1
    for m in range(1,A): p*=1+1/(3*m)
    print(A, round(p,4), round(A**(1/3),4), round((3*A-1)/2*p,3), round(A**(4/3),3))
print("== 9. ratios")
for n in [1024,4096,16384,10**6]:
    print(n, f"n^3/n^2.807={n**(3-math.log2(7)):.2f}", f"n^3/n^2.371={n**(3-2.371339):.2f}", f"n^3/n^2.25={n**0.75:.1f}")
for Cc in [1e3,1e6,1e9]:
    nstar=(Cc/2)**(4/3)
    print("hyp const",Cc,"crossover n ~ %.3g"%nstar, "fp16 bytes per matrix %.3g"%(2*nstar**2))
print("== 10. C(2,4) tripling partition check (a=2,h=1)")
a_,h_=2,1;B=3*h_+a_-1
Yl=range(0,h_);Ym=range(h_,2*h_+a_-1);Yr=range(2*h_+a_-1,3*h_+a_-1)
Zm=range(h_+a_-1,2*h_+a_-1)
for x in range(a_):
    for y in range(B):
        z=x+y; w=(1 if y in Ym else 0)+(-1 if z in Zm else 0)
        print((x,y,z),w,end='; ')
print()
