// ======================= SCENES v2: "Сколько из них настоящих?" =======================
const SC = [];
const scene = (a, b, fn) => SC.push({ a: bt(a), b: bt(b), fn });
// one shot per model, hard cuts on the beat; [clip, from beat, to beat, source start s, focus x, focus y, zoom]
const SHOTS = [
  ['morning', 0, 6, 0.0, .55, .58, 1.10, 0],
  ['selfie', 6, 10, 0.0, .5, .45, 1.04, 4],
  ['makeup', 10, 13, 0.0, .5, .45, 1.02, 3],
  ['beach', 13, 16, 1.0, .5, .45, 1.02, 2],
  ['dress', 16, 20, 0.3, .5, .4, 1.02, 1],
  ['laundry', 20, 24, 0.2, .5, .45, 1.04, 0],
  ['lace', 24, 28, 4.0, .5, .45, 1.02, 3],
  ['yoga', 28, 32, 0.0, .5, .5, 1.0, 1],
  ['fire', 32, 36, 1.0, .5, .45, 1.02, 2],
  ['unbox', 36, 40, 1.6, .5, .45, 1.04, 0],
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
  label('КАДР ИЗ 10', W - 70, 300, .85, { align: 'right', size: 26, track: 6 });
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
// rows by model after the second twist
const ROWS = [0, 1, 2, 3, 4].map(m => SHOTS.map((s, i) => [s, i]).filter(([s]) => s[7] === m).map(([, i]) => i));
function groupRect(i) {
  const th = 262, tw = th * 9 / 16, g = 14, x0 = 470, y0 = 330;
  const m = SHOTS[i][7], k = ROWS[m].indexOf(i);
  return [x0 + k * (tw + g), y0 + m * (th + g), tw, th];
}
const small = document.createElement('canvas'); small.width = 216; small.height = 384;
async function tile(i, t, o = {}) {
  const s = SHOTS[i], [x, y, w, h] = o.rect || tileRect(i);
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
scene(40, 64, async (t) => {
  ctx.fillStyle = INK; ctx.fillRect(0, 0, W, H);
  for (let i = 0; i < 10; i++) {
    const tin = bt(40) + i * .06, pin = out3(lin(t, tin, tin + .35));
    if (pin <= 0) continue;
    // "fake" glitch on the answer: every tile pixelates for a moment, staggered
    const tg = bt(48) + i * .05, gl = Math.max(0, 1 - Math.abs((t - tg - .18) / .18));
    // second twist: tiles fly into one row per model
    const mv = spring(t - (bt(53) + SHOTS[i][7] * .08 + i * .02), 1.6, .82);
    const A = tileRect(i), Bq = groupRect(i), r = A.map((v, k) => mix(v, Bq[k], mv));
    ctx.save(); const [x, y, w, h] = r;
    ctx.translate(x + w / 2, y + h / 2); ctx.scale(mix(.9, 1, pin), mix(.9, 1, pin)); ctx.translate(-x - w / 2, -y - h / 2);
    await tile(i, t, { rect: r, pix: gl > .05 ? mix(1, 24, gl) : 0, alpha: pin });
    ctx.restore();
  }
  if (t < bt(48)) {
    words('Ну что?', font('PfI', 110, 700), W / 2, 400, bt(40) + .2, t);
    words('Сколько настоящих?', font('PfI', 96, 700), W / 2, 520, bt(40) + .5, t);
    for (let k = 0; k < 3; k++) {
      const a = bt(45 + k), b = bt(46 + k);
      if (t >= a && t < b) { const p = lin(t, a, a + .2); ctx.save(); ctx.globalAlpha = 1 - lin(t, b - .12, b);
        rise(String(3 - k), font('Unb', 200, 900), W / 2, 1640, p, { color: ACC }); ctx.restore(); }
    }
  } else if (t < bt(53)) {
    rise('НИ ОДНОЙ.', font('Unb', 130, 900), W / 2, 500, lin(t, bt(48), bt(48) + .45), { color: ACC });
    words('И их даже не десять.', font('PfI', 80, 700), W / 2, 1560, bt(50), t);
  } else {
    rise('ИХ ПЯТЬ.', font('Unb', 110, 900), W / 2, 230, lin(t, bt(54), bt(54) + .45), { color: ACC });
    for (let m = 0; m < 5; m++) {
      const p = lin(t, bt(54.5) + m * .08, bt(54.5) + m * .08 + .4);
      rise(`МОДЕЛЬ ${m + 1}`, font('It', 30, 700), 170, 330 + m * 276 + 140, p, { align: 'left', track: 6 });
      rise(`${ROWS[m].length} ${ROWS[m].length === 1 ? 'образ' : 'образа'}`, font('PfI', 40, 600), 170, 330 + m * 276 + 190, p, { align: 'left', color: 'rgba(244,237,227,.7)' });
    }
    words('Одна модель. Любой образ.', font('PfI', 76, 700), W / 2, 1780, bt(58), t);
  }
});

// 64-76 CTA
scene(64, 77.5, async (t) => {
  await vid('lace', 9 + (t - bt(64)) * .6, 0, 0, W, H, { zoom: 1.15, filter: 'blur(26px) brightness(.3)' });
  const fin = lin(t, bt(64), bt(64) + .3); if (fin < 1) shade(1 - fin, '10,9,9');
  words('Сделаю такую модель', font('PfI', 88, 700), W / 2, 700, bt(64) + .05, t);
  words('для вашего бренда', font('PfI', 88, 700), W / 2, 810, bt(64) + .35, t);
  const bp = spring(t - bt(66), 2, .8);
  if (bp > 0) {
    ctx.save(); ctx.translate(W / 2, 1060); ctx.scale(mix(.85, 1, bp), mix(.85, 1, bp)); ctx.globalAlpha = clamp(bp * 1.5);
    ctx.fillStyle = ACC; ctx.beginPath(); ctx.roundRect(-400, -90, 800, 180, 90); ctx.fill();
    ctx.fillStyle = INK; ctx.font = font('Unb', 64, 900); ctx.textAlign = 'center'; ctx.fillText('ПИШИ В ДИРЕКТ', 0, 24);
    ctx.restore();
  }
  rise('ФОТО · ВИДЕО · РИЛС · UGC', font('It', 36, 700), W / 2, 1260, lin(t, bt(67.5), bt(67.5) + .5), { track: 8 });
  ctx.save(); ctx.globalAlpha = out3(lin(t, bt(68), bt(69))) * .75;
  label('все модели на видео созданы нейросетью', W / 2, 1720, 1, { align: 'center', size: 26, track: 3 }); ctx.restore();
});
