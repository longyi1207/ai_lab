import numpy as np, math
print("== 1. heat eq u_t = k u_xx, box initial |x|<0.5 -> 1, k=1, explicit FD")
L=10; N=1001; x=np.linspace(-L/2,L/2,N); dx=x[1]-x[0]; k=1.0
u=np.where(np.abs(x)<0.5,1.0,0.0); dt=0.4*dx*dx/k; t=0
for T in [0,0.01,0.05,0.1,0.5,1.0]:
    while t<T-1e-12:
        h=min(dt,T-t); u[1:-1]=u[1:-1]+k*h/dx**2*(u[2:]-2*u[1:-1]+u[:-2]); t+=h
    exact=0.5*(math.erf((0.5)/math.sqrt(4*k*T))*2) if T>0 else 1.0
    print(f"t={T}: max={u.max():.4f} exact_center={exact:.4f} total={u.sum()*dx:.4f} maxslope={np.abs(np.diff(u)/dx).max():.3f}")
print("== hand toy: 5 cells [0,0,1,0,0], r=k dt/dx^2=0.25 one step")
v=np.array([0,0,1.0,0,0]); w=v.copy(); w[1:-1]=v[1:-1]+0.25*(v[2:]-2*v[1:-1]+v[:-2]); print(w, w.sum())
print("== 2. ODEs")
for t in [0,0.5,0.9,0.99,0.999]: print(f"y'=y^2,y0=1: t={t} y={1/(1-t):.1f}  e^t={math.e**t:.3f}")
def rk4(f,y,T,n=200000):
    h=T/n
    for i in range(n):
        k1=f(y);k2=f(y+h/2*k1);k3=f(y+h/2*k2);k4=f(y+h*k3);y=y+h/6*(k1+2*k2+2*k3+k4)
        if abs(y)>1e8: return float('inf'),i*h
    return y,T
for t in [0.5,0.9,0.99]: print("RK4 y^2 at",t, rk4(lambda y:y*y,1.0,t)[0])
for y0 in [0.5,0.9,1.0,1.1,2.0]:
    # exact: y=1/x... x=1/y: x' = -y'/y^2 = -(1 - 1/y)= x-1 -> x=1+(x0-1)e^t ; blowup when x=0 -> t=ln(1/(1-x0)) if x0<1
    x0=1/y0
    tb = math.log(1/(1-x0)) if x0<1 else None
    print(f"y'=y^2-y y0={y0}: blowup t*={tb}", "y(3)=" , (1/(1+(x0-1)*math.e**3) if tb is None else 'inf'))
print("== 3. scaling u_l = l u(l x, l^2 t)")
for lam in [1,10,100,1000]:
    print(f"lam={lam}: length 1/{lam}, time 1/{lam**2}, speed x{lam}, energy3D x{1/lam}, energy2D x1")
print("== energy-limited Reynolds: E=1, nu=1; 3D U<=sqrt(E/L^3), Re=UL/nu = L^-1/2; 2D U<=sqrt(E)/L, Re=1")
for Lc in [1,1e-2,1e-4,1e-6,1e-8]:
    print(f"L={Lc:g}: Re3D_max={math.sqrt(1/Lc**3)*Lc:.4g}  Re2D_max={math.sqrt(1/Lc**2)*Lc:.4g}")
print("== 4. OpenAI core scalings, h=0.005")
h=0.005
for tau in [1e-2,1e-4,1e-6,1e-8,1e-12]:
    lr=tau**0.5; lz=tau**(0.5-h); U=tau**(-0.5-h); E=tau**(0.5-3*h); Re=tau**(-h)
    print(f"tau={tau:g}: lr={lr:.3g} lz={lz:.3g} lz/lr={lz/lr:.4g} U={U:.4g} Ecore={E:.4g} Re_theta={Re:.4g} vol={tau**(1.5-h):.3g}")
print("== 5. real fluids Re=UL/nu")
for name,nu,U,Lc in [("water pipe",1.0e-6,1,0.1),("air car",1.5e-5,30,4),("blood capillary",3e-6,1e-3,1e-5)]:
    print(name, f"Re={U*Lc/nu:.3g}")
print("== 6. viscous Burgers u_t+u u_x = nu u_xx, u0=-sin x, periodic; max |u_x| over time")
def burgers(nu,N,T=3.0):
    x=np.linspace(0,2*np.pi,N,endpoint=False); kk=np.fft.fftfreq(N,1/N); u=-np.sin(x)
    dt=min(0.2*(2*np.pi/N), 0.2*(2*np.pi/N)**2/nu); t=0; best=(0,0); out={}
    def rhs(u):
        uh=np.fft.fft(u); ux=np.real(np.fft.ifft(1j*kk*uh)); uxx=np.real(np.fft.ifft(-(kk**2)*uh))
        return -u*ux+nu*uxx, ux
    marks=[0.5,0.9,1.0,1.5,3.0]; mi=0
    while t<T-1e-12:
        k1,ux=rhs(u); m=np.abs(ux).max()
        if m>best[0]: best=(m,t)
        k2,_=rhs(u+dt/2*k1);k3,_=rhs(u+dt/2*k2);k4,_=rhs(u+dt*k3); u=u+dt/6*(k1+2*k2+2*k3+k4); t+=dt
        if mi<len(marks) and t>=marks[mi]-1e-9:
            out[marks[mi]]=np.abs(rhs(u)[1]).max(); mi+=1
    return best,out
for nu,N in [(0.1,256),(0.03,512),(0.01,1024),(0.003,2048)]:
    best,out=burgers(nu,N)
    print(f"nu={nu}: max|u_x|={best[0]:.2f} at t={best[1]:.2f}; samples", {k:round(v,2) for k,v in out.items()}, " 1/(2nu)=",round(1/(2*nu),1))
print("inviscid: slope at x=pi... u0'=-cos x min=-1 at x=0 -> u_x(0,t)= -1/(1-t)")
for t in [0.5,0.9,0.99]: print(t, -1/(1-t))
