import numpy as np
sr=22050; x=np.fromfile('src/music.f32',dtype=np.float32)
hop=512; n=len(x)//hop
fr=x[:n*hop].reshape(n,hop)
rms=np.sqrt((fr**2).mean(1))
# low band energy via simple spectral
spec=np.abs(np.fft.rfft(fr*np.hanning(hop),axis=1))
low=spec[:,1:6].sum(1)  # <~200Hz
flux=np.maximum(0,np.diff(spec,axis=0)).sum(1); flux=np.r_[0,flux]
# BPM via autocorr of flux
f=flux-flux.mean(); ac=np.correlate(f[:20000],f[:20000],'full')[19999:]
fps=sr/hop
lags=np.arange(len(ac))/fps
m=(lags>60/180)&(lags<60/70)
best=lags[m][np.argmax(ac[m])]; print('BPM',60/best)
# per 2s energy
sec=int(2*fps)
for i in range(0,n//sec):
    s=slice(i*sec,(i+1)*sec)
    print(f"{i*2:4d}s rms {rms[s].mean():.3f} low {low[s].mean():7.1f}", '#'*int(rms[s].mean()*200))
