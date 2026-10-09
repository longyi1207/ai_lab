import numpy as np, math, random
random.seed(1)
def rand_reg(n,d):
    # union of d/2 random permutations -> 2*(d/2) regular multigraph
    A=np.zeros((n,n))
    for _ in range(d//2):
        p=list(range(n)); random.shuffle(p)
        for i in range(n): A[i,p[i]]+=1; A[p[i],i]+=1
    return A
def cyc(n):
    A=np.zeros((n,n))
    for i in range(n): A[i,(i+1)%n]+=1; A[(i+1)%n,i]+=1
    return A
def lam2(A,d):
    ev=sorted(abs(np.linalg.eigvalsh(A/d)),reverse=True); return ev[1]
for n in [16,64,256,1024]:
    lc=lam2(cyc(n),2); lr=lam2(rand_reg(n,4),4)
    # steps to mix to 1/n^2 : ~ log(n^2)/ (1-lam)
    print(n, f"cycle lam2={lc:.4f} mix~{2*math.log(n)/(1-lc):.0f}", f"rand4 lam2={lr:.4f} mix~{2*math.log(n)/(1-lr):.0f}")
print("Ramanujan 2sqrt(3)/4=",2*math.sqrt(3)/4)
