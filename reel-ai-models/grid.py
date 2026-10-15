import numpy as np
sr=22050; x=np.fromfile('src/music.f32',dtype=np.float32)
hop=128; a=132.0; b=150.0
seg=x[int(a*sr):int(b*sr)]; n=len(seg)//hop
fr=seg[:n*hop].reshape(n,hop); sp=np.abs(np.fft.rfft(fr*np.hanning(hop),axis=1))
fl=np.r_[0,np.maximum(0,np.diff(sp,axis=0)).sum(1)]
fps=sr/hop
best=None
for bpm in np.arange(150,154,0.01):
  bl=60/bpm
  for ph in np.arange(0,bl,0.002):
    t=np.arange(ph,b-a-0.1,bl); s=fl[(t*fps).astype(int)].sum()
    if best is None or s>best[0]: best=(s,bpm,ph)
s,bpm,ph=best; bl=60/bpm
print('bpm',round(bpm,2),'beat',round(bl,4))
# beat nearest to drop 131.0
k=round((131.0-(a+ph))/bl); print('drop beat ~', round(a+ph+k*bl,3))
