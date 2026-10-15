import numpy as np, sys
sr=22050; x=np.fromfile('src/music.f32',dtype=np.float32)
a,b=float(sys.argv[1]),float(sys.argv[2]); w=int(0.025*sr)
seg=x[int(a*sr):int(b*sr)]
n=len(seg)//w; fr=seg[:n*w].reshape(n,w)
sp=np.abs(np.fft.rfft(fr,axis=1)); low=sp[:,1:8].sum(1); tot=np.sqrt((fr**2).mean(1))
# smoothed low energy over 0.5s; find biggest ratio jump
k=20; L=np.convolve(low,np.ones(k)/k,'same')
r=[(L[i+k]/(L[i-k]+1e-6),i) for i in range(k,n-k)]
r.sort(reverse=True)
for v,i in r[:5]: print(f"{a+i*0.025:.3f}s ratio {v:.1f}")
# kick onsets (low-band peaks) in region
on=np.where((low[1:-1]>low[:-2])&(low[1:-1]>=low[2:])&(low[1:-1]>np.percentile(low,90)))[0]+1
print('kicks',[round(a+i*0.025,3) for i in on][:40])
