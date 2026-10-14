// ======================= SCENES v4: lookbook / offer for lingerie & clothing stores =======================
const PAPER = '#f2ede6', BURG = '#7a1f2b', INK2 = '#151312', MUTE = '#8b847b';
const SC = [];
const scene = (a, b, fn) => SC.push({ a: bt(a), b: bt(b), fn });
function paper() { ctx.fillStyle = PAPER; ctx.fillRect(0, 0, W, H); }
function txt(str, f, x, y, o = {}) { ctx.save(); ctx.font = f; ctx.fillStyle = o.color || INK2; ctx.textAlign = o.align || 'center'; if (o.track) ctx.letterSpacing = o.track + 'px'; ctx.globalAlpha = o.alpha ?? 1; ctx.fillText(str, x, y); ctx.restore(); }
function smallcaps(str, x, y, a = 1, o = {}) { label(str, x, y, a, { color: o.color || INK2, size: o.size || 24, track: o.track ?? 6, align: o.align }); }
function hairline(x, y, w, p, col = INK2) { ctx.fillStyle = col; ctx.fillRect(x, y, w * out5(p), 2); }
// magazine chrome on every paper scene
function chrome(t, page) {
  smallcaps('LOOKBOOK', 70, 120, .9);
  smallcaps(page, W - 70, 120, .9, { align: 'right' });
  hairline(70, 140, W - 140, lin(t, 0, .6));
}
// a framed clip; the frame opens vertically from a line
async function frame(clip, src, x, y, w, h, open = 1, o = {}) {
  if (open <= 0) return;
  const hh = h * out5(open), yy = y + (h - hh) / 2;
  ctx.save(); ctx.beginPath(); ctx.rect(x, yy, w, hh); ctx.clip();
  await vid(clip, src, x, y, w, h, { zoom: o.zoom || 1.02, fx: o.fx ?? .5, fy: o.fy ?? .4 });
  ctx.restore();
}

// 0-16: hook and build-up, one frame, cuts inside it every 2 beats after beat 8
const HOOK = [['lace', 4.0], ['fire', 1.0], ['beach', 1.0], ['dress', 0.6]];
scene(0, 16, async (t) => {
  paper(); chrome(t, 'AI-МОДЕЛИ ДЛЯ МАГАЗИНОВ');
  const fw = 560, fh = 860, fx = (W - fw) / 2, fy = 620;
  let clip = HOOK[0], k = 0;
  if (t >= bt(8)) { k = Math.min(3, Math.floor((t - bt(8)) / (2 * B))); clip = HOOK[k]; }
  await frame(clip[0], clip[1] + (t - (t >= bt(8) ? bt(8 + 2 * k) : 0)) * .9, fx, fy, fw, fh, lin(t, .5, 1.3));
  // headline
  rise('Новая коллекция.', font('Pf', 92, 700), W / 2, 360, lin(t, .15, .7), { color: INK2 });
  rise('Ноль съёмок.', font('PfI', 92, 700), W / 2, 470, lin(t, .5, 1.05), { color: BURG });
  // captions under the frame
  if (t < bt(8)) {
    rise('фото и видео для вашего магазина', font('PfI', 46, 600), W / 2, 1580, lin(t, 1.3, 1.8), { color: INK2 });
  } else {
    const W3 = ['МОДЕЛЬ', 'ЛОКАЦИЯ', 'СВЕТ', 'ОБРАЗ'];
    for (let i = 0; i <= k; i++) {
      const p = lin(t, bt(8 + 2 * i), bt(8 + 2 * i) + .35);
      rise(W3[i], font('It', 34, 700), 180 + i * 240, 1580, p, { color: i === k ? BURG : INK2, track: 6 });
    }
    rise('на ваш выбор', font('PfI', 46, 600), W / 2, 1670, lin(t, bt(14), bt(14) + .4), { color: INK2 });
  }
  smallcaps('ПРИМЕР', fx, fy + fh + 40, .55 * out3(lin(t, 1, 1.5)), { size: 20 });
  smallcaps(['01', '02', '03', '04'][k], fx + fw, fy + fh + 40, .55 * out3(lin(t, 1, 1.5)), { size: 20, align: 'right' });
});

// 16-32: product-card carousel; swipes on beats 20, 24, 28
const CARDS = [
  ['lace', 4.0, 'БЕЛЬЁ', 'Комплект кружевной', 'пудровый', ['#e9cfc3', '#151312', '#f5f1ea']],
  ['fire', 1.0, 'БЕЛЬЁ', 'Комплект «Ночь»', 'чёрный', ['#151312', '#7a1f2b', '#e9cfc3']],
  ['beach', 1.0, 'КУПАЛЬНИКИ', 'Купальник на завязках', 'песочный', ['#d9c2a3', '#151312', '#f5f1ea']],
  ['dress', 0.4, 'ПЛАТЬЯ', 'Платье миди', 'шампань', ['#e8d8c0', '#151312', '#7a1f2b']],
];
async function card(c, src, cx, alpha = 1) {
  const w = 760, h = 1360, x = cx - w / 2, y = 330;
  ctx.save(); ctx.globalAlpha = alpha;
  ctx.shadowColor = 'rgba(40,30,20,.18)'; ctx.shadowBlur = 50; ctx.shadowOffsetY = 20;
  ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.roundRect(x, y, w, h, 28); ctx.fill(); ctx.shadowColor = 'transparent';
  const ih = w * 4 / 3;
  ctx.save(); ctx.beginPath(); ctx.roundRect(x, y, w, ih, [28, 28, 0, 0]); ctx.clip();
  await vid(c[0], src, x, y, w, ih, { zoom: 1.0, fy: .42 });
  ctx.restore();
  // badge
  ctx.fillStyle = 'rgba(255,255,255,.92)'; ctx.beginPath(); ctx.roundRect(x + 24, y + 24, 210, 52, 26); ctx.fill();
  txt(c[2], font('It', 22, 700), x + 129, y + 58, { track: 3 });
  const ty = y + ih + 70;
  txt(c[3], font('Pf', 44, 700), x + 36, ty, { align: 'left' });
  txt(c[4], font('PfI', 34, 600), x + 36, ty + 48, { align: 'left', color: MUTE });
  // colour dots and sizes
  c[5].forEach((col, i) => { ctx.fillStyle = col; ctx.beginPath(); ctx.arc(x + w - 150 + i * 46, ty - 14, 15, 0, 7); ctx.fill();
    ctx.strokeStyle = 'rgba(0,0,0,.15)'; ctx.lineWidth = 2; ctx.stroke(); });
  ['XS', 'S', 'M', 'L'].forEach((s, i) => { ctx.strokeStyle = i === 2 ? INK2 : '#d8d2ca'; ctx.lineWidth = 2;
    ctx.beginPath(); ctx.roundRect(x + 36 + i * 92, ty + 82, 76, 52, 10); ctx.stroke();
    txt(s, font('It', 24, 700), x + 74 + i * 92, ty + 117, { color: i === 2 ? INK2 : MUTE }); });
  ctx.fillStyle = INK2; ctx.beginPath(); ctx.roundRect(x + w - 300, ty + 82, 264, 52, 26); ctx.fill();
  txt('В КОРЗИНУ', font('It', 22, 700), x + w - 168, ty + 116, { color: '#fff', track: 3 });
  ctx.restore();
}
scene(16, 32, async (t) => {
  paper(); chrome(t - bt(16), 'КАРТОЧКИ ТОВАРА');
  const k = Math.min(3, Math.floor((t - bt(16)) / (4 * B)));
  // swipe: the card slides out left while the next comes in from the right, eased, 0.5 s
  const ts = bt(16 + 4 * k), sw = k < 3 ? io(lin(t, ts + 4 * B - .5, ts + 4 * B)) : 0;
  const enter = k === 0 ? out5(lin(t, bt(16), bt(16) + .5)) : 1;
  await card(CARDS[k], CARDS[k][1] + (t - ts), W / 2 - sw * 900 + (1 - enter) * 900);
  if (sw > 0) await card(CARDS[k + 1], CARDS[k + 1][1], W / 2 + 900 - sw * 900);
  rise('Фото и видео для карточек', font('PfI', 50, 600), W / 2, 260, lin(t, bt(16) + .2, bt(16) + .7), { color: INK2 });
  // pager dots
  for (let i = 0; i < 4; i++) { ctx.fillStyle = i === k ? INK2 : '#cfc8bf'; ctx.beginPath(); ctx.arc(W / 2 - 45 + i * 30, 1760, i === k ? 7 : 5, 0, 7); ctx.fill(); }
  smallcaps('ПРИМЕР КАРТОЧКИ', W / 2, 1830, .5, { align: 'center', size: 20 });
});

// 32-40: not only lingerie, three portrait cards, full figure visible
const SPREAD = [['yoga', 0.0, 'СПОРТ'], ['morning', 0.0, 'ДОМАШНЯЯ'], ['unbox', 1.6, 'БАЗОВЫЙ']];
scene(32, 40, async (t) => {
  paper(); chrome(t - bt(32), 'НЕ ТОЛЬКО БЕЛЬЁ');
  rise('Любая категория', font('Pf', 84, 700), W / 2, 380, lin(t, bt(32), bt(32) + .5), { color: INK2 });
  rise('вашего магазина', font('PfI', 84, 700), W / 2, 480, lin(t, bt(32) + .25, bt(32) + .75), { color: BURG });
  const w = 310, h = w * 16 / 9, g = 24, x0 = (W - 3 * w - 2 * g) / 2, y = 640;
  for (let i = 0; i < 3; i++) {
    const p = spring(t - bt(32.5) - i * B, 2, .82);
    if (p <= 0) continue;
    const x = x0 + i * (w + g);
    ctx.save(); ctx.globalAlpha = clamp(p * 1.4); ctx.translate(0, (1 - p) * 60);
    ctx.beginPath(); ctx.rect(x, y, w, h); ctx.clip();
    const s = SPREAD[i]; await vid(s[0], s[1] + (t - bt(32)) * (s[0] === 'morning' ? .8 : 1), x, y, w, h, { zoom: 1, fy: .45 });
    ctx.restore();
    ctx.save(); ctx.globalAlpha = clamp(p * 1.4);
    hairline(x, y + h + 30, w, p); smallcaps(s[2], x, y + h + 70, 1, { size: 24 }); ctx.restore();
  }
  rise('одежда · бельё · купальники · спорт', font('PfI', 44, 600), W / 2, 1700, lin(t, bt(36), bt(36) + .5), { color: INK2 });
});

// 40-48: formats, UGC phone with the unboxing clip
scene(40, 48, async (t) => {
  paper(); chrome(t - bt(40), 'ФОРМАТЫ');
  const pw = 470, ph = 940, px = 90, py = 470;
  const p = spring(t - bt(40), 1.8, .82);
  ctx.save(); ctx.translate(0, (1 - p) * 120); ctx.globalAlpha = clamp(p * 1.3);
  ctx.fillStyle = INK2; ctx.beginPath(); ctx.roundRect(px - 16, py - 16, pw + 32, ph + 32, 64); ctx.fill();
  ctx.beginPath(); ctx.roundRect(px, py, pw, ph, 50); ctx.clip();
  await vid('unbox', 2.5 + (t - bt(40)), px, py, pw, ph, { zoom: 1, fy: .45 });
  ctx.restore();
  rise('Что получаете', font('Pf', 76, 700), W / 2, 330, lin(t, bt(40), bt(40) + .5), { color: INK2 });
  const F = ['Фото для карточек', 'Видео-обложки', 'Рилс и сторис', 'UGC-распаковки', 'Лукбуки коллекций'];
  F.forEach((s, i) => {
    const q = lin(t, bt(41 + i), bt(41 + i) + .4);
    const y = 560 + i * 170;
    ctx.save(); ctx.globalAlpha = out3(q); hairline(620, y + 40, 390, q, '#cfc8bf'); ctx.restore();
    rise(String(i + 1).padStart(2, '0'), font('It', 26, 700), 620, y - 44, q, { align: 'left', color: BURG, track: 4 });
    rise(s, font('PfI', 46, 600), 620, y + 22, q, { align: 'left', color: INK2 });
  });
});

// 48-60: CTA
scene(48, 61.5, async (t) => {
  paper(); chrome(t - bt(48), 'СВЯЗАТЬСЯ');
  const fw = 380, fh = 560, fx = (W - fw) / 2, fy = 300;
  await frame('lace', 6 + (t - bt(48)) * .8, fx, fy, fw, fh, lin(t, bt(48), bt(48) + .7), { fy: .35 });
  words('Контент для вашего', font('Pf', 76, 700), W / 2, 1040, bt(48.5), t, { color: INK2 });
  words('магазина', font('PfI', 76, 700), W / 2, 1130, bt(49), t, { color: BURG });
  rise('без студии, фотографа и моделей', font('PfI', 44, 600), W / 2, 1230, lin(t, bt(50), bt(50) + .5), { color: MUTE });
  const bp = spring(t - bt(52), 2, .82);
  if (bp > 0) {
    ctx.save(); ctx.translate(W / 2, 1420); ctx.scale(mix(.9, 1, bp), mix(.9, 1, bp)); ctx.globalAlpha = clamp(bp * 1.5);
    ctx.fillStyle = INK2; ctx.beginPath(); ctx.roundRect(-380, -70, 760, 140, 70); ctx.fill();
    txt('НАПИСАТЬ В ДИРЕКТ', font('It', 40, 800), 0, 14, { color: PAPER, track: 5 });
    ctx.restore();
  }
  smallcaps('модели на видео созданы нейросетью', W / 2, 1800, .55 * out3(lin(t, bt(54), bt(55))), { align: 'center', size: 20, track: 3 });
});
