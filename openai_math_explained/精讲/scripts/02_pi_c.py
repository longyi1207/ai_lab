from mpmath import mp, mpf, pi, floor, log, fabs
mp.dps=3000
x=+pi; a=[]
for _ in range(1001):
    ai=int(floor(x)); a.append(ai); x=1/(x-ai)
p0,q0,p1,q1=1,0,a[0],1; qs=[1]
for ai in a[1:]:
    p0,q0,p1,q1=p1,q1,ai*p1+p0,ai*q1+q0; qs.append(q1)
for i in [1,3,431]:
    print(i, "a_next=",a[i+1],"q digits",len(str(qs[i])),"2+log a/log q=%.4f"%(2+float(log(a[i+1])/log(qs[i])) if qs[i]>1 else 0))
print(a[430:434], len(str(qs[430])))
i=430; print("idx430 2+log a/log q=%.4f"%(2+float(log(a[i+1])/log(qs[i]))), "actual nu=%.4f"%float(-log(fabs(pi-mpf(p1)/q1))/log(q1)) if False else "")
# actual exponent of convergent 430
def conv(n):
    p0,q0,p1,q1=1,0,a[0],1
    for ai in a[1:n+1]: p0,q0,p1,q1=p1,q1,ai*p1+p0,ai*q1+q0
    return p1,q1
p,q=conv(430); print("conv430 nu=%.4f"%float(-log(fabs(pi-mpf(p)/q))/log(q)))
p,q=conv(3); print("conv3 nu=%.4f"%float(-log(fabs(pi-mpf(p)/q))/log(q)))
