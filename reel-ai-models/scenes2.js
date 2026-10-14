// ======================= SCENES v2: "Сколько из них настоящих?" =======================
const SC = [];
const scene = (a, b, fn) => SC.push({ a: bt(a), b: bt(b), fn });
// one shot per model, hard cuts on the beat; [clip, from beat, to beat, source start s, focus x, focus y, zoom]
const SHOTS = [
  ['morning', 0, 6, 0.0, .55, .58, 1.10],
  ['selfie', 6, 10, 0.0, .5, .45, 1.04],
  ['laundry', 10, 13, 0.2, .5, .45, 1.04],
  ['unbox', 13, 16, 1.6, .5, .45, 1.04],
  ['dress', 16, 20, 0.3, .5, .4, 1.02],
  ['yoga', 20, 24, 0.0, .5, .5, 1.0],
  ['beach', 24, 28, 1.0, .5, .45, 1.02],
  ['makeup', 28, 32, 0.0, .5, .45, 1.02],
  ['lace', 32, 36, 4.0, .5, .45, 1.02],
  ['fire', 36, 40, 1.0, .5, .45, 1.02],
];
// a shot: full frame, one slow push-in, no shake
async function shot(s, t, o = {}) {
  const [clip, a, b, src, fx, fy, z0] = s, p = lin(t, bt(a), bt(b));
  await vid(clip, src + (t - bt(a)), 0, 0, W, H, { zoom: z0 * mix(1, 1.05, p), fx, fy, ...o });
}
function counter(n, t, tCut) {
  const p = lin(t, tCut, tCut + .3);
  { const g = ctx.createLinearGradient(0, 0, 0, 380); g.addColorStop(0, 'rgba(0,0,0,.55)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, 380); }
  rise(String(n).padStart(2, '0'), font('Unb', 120, 900), W - 70, 250, p, { align: 'right' });
  label('НАСТОЯЩАЯ?', W - 70, 300, .85, { align: 'right', size: 26, track: 6 });
  label('СКОЛЬКО ИЗ НИХ НАСТОЯЩИХ', 70, 170, .7, { size: 24, track: 5 });
}

// 0-16 build-up, 16-40 after the drop: one model per shot, counter ticks
scene(0, 40, async (t) => {
  const i = SHOTS.findIndex(s => t < bt(s[2]));
  const s = SHOTS[i < 0 ? SHOTS.length - 1 : i];
  await shot(s, t);
  if (t < bt(6)) {
    // hook: the question, big, on the first shot
    grad(H * .5, H, .8);
    { const g = ctx.createLinearGradient(0, 0, 0, 700); g.addColorStop(0, 'rgba(0,0,0,.6)'); g.addColorStop(1, 'rgba(0,0,0,0)'); ctx.fillStyle = g; ctx.fillRect(0, 0, W, 700); }
    words('Сколько из них', font('PfI', 112, 700), W / 2, 1460, .1, t);
    words('настоящих?', font('PfI', 150, 700), W / 2, 1620, .45, t);
    const u = out5(lin(t, 1.2, 1.6)); ctx.fillStyle = ACC; ctx.fillRect(W / 2 - 260 * u, 1665, 520 * u, 7);
    rise('ОТВЕТ В КОНЦЕ', font('It', 30, 700), W / 2, 1760, lin(t, 1.5, 2.0), { track: 10, color: CREAM });
    rise('01', font('Unb', 120, 900), W - 70, 250, lin(t, .2, .5), { align: 'right' });
  } else {
    counter(i + 1, t, bt(s[1]));
  }
  // single flash on the drop
  const fl = 1 - lin(t, bt(16), bt(16) + .18);
  if (t >= bt(16) && fl > 0) shade(fl * .9, '244,237,227');
});

// grid of all ten
const G = { cols: 5, rows: 2, g: 12 };
function tileRect(i) {
  const tw = (W - G.g * (G.cols + 1)) / G.cols, th = tw * 16 / 9;
  const col = i % G.cols, row = Math.floor(i / G.cols);
  const y0 = (H - (th * 2 + G.g)) / 2 + 40;
  return [G.g + col * (tw + G.g), y0 + row * (th + G.g), tw, th];
}
const small = document.createElement('canvas'); small.width = 216; small.height = 384;
async function tile(i, t, o = {}) {
  const s = SHOTS[i], [x, y, w, h] = tileRect(i);
  const pix = o.pix || 0, alpha = o.alpha ?? 1;
  if (alpha <= 0) return;
  ctx.save(); ctx.globalAlpha = alpha;
  if (pix > 1) {
    const sc = small.getContext('2d'), q = Math.max(2, Math.round(w / pix)), r = Math.round(q * h / w);
    const im = await img(s[0], s[3] + 2 + (t - bt(40)));
    sc.imageSmoothingEnabled = true; sc.clearRect(0, 0, small.width, small.height);
    const sw = W / s[6], sh = sw * h / w; sc.drawImage(im, (W - sw) * s[4], (H - sh) * s[5], sw, sh, 0, 0, q, r);
    ctx.imageSmoothingEnabled = false; ctx.drawImage(small, 0, 0, q, r, x, y, w, h); ctx.imageSmoothingEnabled = true;
  } else {
    ctx.beginPath(); ctx.roundRect(x, y, w, h, 14); ctx.clip();
    await vid(s[0], s[3] + 2 + (t - bt(40)), x, y, w, h, { zoom: 1, fx: s[4], fy: s[5] * .8 });
  }
  ctx.restore();
}
scene(40, 56, async (t) => {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 10; i++) {
    const tin = bt(40) + i * .06, pin = out3(lin(t, tin, tin + .35));
    const td = bt(48.5) + i * B / 2;                       // one tile dissolves per half beat
    const d = lin(t, td, td + .4);
    if (pin <= 0) continue;
    ctx.save(); const [x, y, w, h] = tileRect(i);
    ctx.translate(x + w / 2, y + h / 2); ctx.scale(mix(.9, 1, pin), mix(.9, 1, pin)); ctx.translate(-x - w / 2, -y - h / 2);
    await tile(i, t, { pix: d > 0 ? mix(1, 60, out3(d)) : 0, alpha: pin * (1 - in3(lin(t, td + .2, td + .45))) });
    ctx.restore();
  }
  if (t < bt(48)) {
    words('Ну что?', font('PfI', 110, 700), W / 2, 400, bt(40) + .2, t);
    words('Сколько настоящих?', font('PfI', 96, 700), W / 2, 520, bt(40) + .5, t);
    // countdown 3 2 1 on beats 45, 46, 47
    for (let k = 0; k < 3; k++) {
      const a = bt(45 + k), b = bt(46 + k);
      if (t >= a && t < b) { const p = lin(t, a, a + .2); ctx.save(); ctx.globalAlpha = 1 - lin(t, b - .12, b);
        rise(String(3 - k), font('Unb', 200, 900), W / 2, 1640, p, { color: ACC }); ctx.restore(); }
    }
  } else {
    const p = lin(t, bt(48), bt(48) + .45);
    rise('НИ ОДНОЙ.', font('Unb', 130, 900), W / 2, 500, p, { color: ACC });
    if (t > bt(52)) {
      words('Все 10 девушек', font('PfI', 80, 700), W / 2, 1520, bt(52), t);
      words('созданы нейросетью', font('PfI', 80, 700), W / 2, 1620, bt(52.5), t);
    }
  }
});

// 56-64 offer over one calm shot
scene(56, 64, async (t) => {
  const p = lin(t, bt(56), bt(64));
  await vid('lace', 6 + (t - bt(56)), 0, 0, W, H, { zoom: mix(1.04, 1.1, p), fy: .4, filter: 'brightness(.6)' });
  const fin = lin(t, bt(56), bt(56) + .35); if (fin < 1) shade(1 - fin, '10,9,9');
  grad(H * .45, H, .85);
  words('Сделаю такую модель', font('PfI', 88, 700), W / 2, 1300, bt(56) + .1, t);
  words('для вашего бренда', font('PfI', 88, 700), W / 2, 1410, bt(56) + .4, t);
  const items = ['ФОТО', 'ВИДЕО', 'РИЛС', 'UGC-РЕКЛАМА'];
  items.forEach((s, k) => rise(s, font('It', 40, 700), W / 2, 1560 + k * 62, lin(t, bt(59 + k), bt(59 + k) + .4), { track: 10, color: k % 2 ? CREAM : ACC }));
});

// 64-76 CTA
scene(64, 77.5, async (t) => {
  await vid('lace', 9 + (t - bt(64)) * .6, 0, 0, W, H, { zoom: 1.15, filter: 'blur(26px) brightness(.3)' });
  words('Хотите так же?', font('PfI', 100, 700), W / 2, 820, bt(64) + .05, t);
  const bp = spring(t - bt(65), 2, .8);
  if (bp > 0) {
    ctx.save(); ctx.translate(W / 2, 1060); ctx.scale(mix(.85, 1, bp), mix(.85, 1, bp)); ctx.globalAlpha = clamp(bp * 1.5);
    ctx.fillStyle = ACC; ctx.beginPath(); ctx.roundRect(-400, -90, 800, 180, 90); ctx.fill();
    ctx.fillStyle = INK; ctx.font = font('Unb', 64, 900); ctx.textAlign = 'center'; ctx.fillText('ПИШИ В ДИРЕКТ', 0, 24);
    ctx.restore();
  }
  rise('фото и видео под ключ', font('PfI', 54, 600), W / 2, 1260, lin(t, bt(67), bt(67) + .5));
  ctx.save(); ctx.globalAlpha = out3(lin(t, bt(68), bt(69))) * .75;
  label('все модели на видео созданы нейросетью', W / 2, 1720, 1, { align: 'center', size: 26, track: 3 }); ctx.restore();
});
