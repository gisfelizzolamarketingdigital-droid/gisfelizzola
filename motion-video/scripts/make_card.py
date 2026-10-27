#!/usr/bin/env python3
"""
Motion-graphics CARDS for our edits: renders a short, animated, premium-looking card (3D tilted panel, word-by-word
headline, counting numbers, checks, arrows) with the motion-studio engine and drops the MP4 into an editar-anuncios job
folder, ready to be used as a full-frame cutaway (`broll`) at the exact moment the voice explains it.

  python3 make_card.py --template steps    --name pasos   --job sideshift --title "Cómo empezar" \
                       --items "Descarga la app" "Crea tu cuenta" "Postula a trabajos" --accent "#39FF6A"
  python3 make_card.py --template equation --name cuenta  --job sideshift --label "Haciendo la cuenta" \
                       --items '$1.000' '× 6' '$6.000' --accent "#39FF6A"
  python3 make_card.py --template compare  --name antes   --job casa --title "Su evolución" \
                       --rows "RENTA|$350|$1.500" "NEGOCIO|$500|$100K" --accent "#39FF6A"

Templates: steps (list that checks itself off), equation (numbers that stack and resolve into a result),
compare (before -> after rows). Output 1080x1920 @30 fps by default. Brand look via --accent/--accent2/--bg dark|light.
Prints the `broll` entry for the EditPlan. Cards are SILENT in the edit (sound design comes from add_sfx.py).
Needs the motion-studio set up once: `bash <skill>/motion-studio/tools/setup.sh` (Node, FFmpeg, Python 3.10-3.12; uses
the installed Chrome, no Chromium download).
"""
import argparse, json, os, re, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
STUDIO = os.path.join(os.path.dirname(HERE), "motion-studio")
SKILLS = os.path.dirname(os.path.dirname(HERE))
EDITAR = os.path.join(SKILLS, "editar-anuncios")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "card"


def rgb(hexcolor):
    h = hexcolor.lstrip("#")
    return f"{int(h[0:2], 16)},{int(h[2:4], 16)},{int(h[4:6], 16)}"


def write_style(name, accent, accent2, bg):
    d = os.path.join(STUDIO, "styles", name)
    os.makedirs(d, exist_ok=True)
    a, b = rgb(accent), rgb(accent2)
    style = f"""window.STYLE = {{
  name: '{name}',
  colors: {{ dark: '#0A0A0A', light: '#F5F3EE', accent: '{accent}', contrast: '{accent2}', card: '#141414' }},
  fonts: {{ display: 'Anton', mono: 'Anton', files: [{{ family: 'Anton', file: 'Anton-Regular.ttf' }}], preload: ['400 80px "Anton"'] }},
  bg: {{
    dark: {{ blobs: [
      {{ x: 900, y: 1500, ax: 150, ay: 120, fx: 1, fy: 2, py: 1.5708, rx: 900, ry: 800, rgb: '{a}', a: .30 }},
      {{ x: 150, y: 250, ax: 140, ay: 100, fx: 1, fy: 2, px: 1.5708, rx: 700, ry: 600, rgb: '{a}', a: .14 }},
      {{ x: 600, y: 900, ax: 200, ay: 160, fx: 2, fy: 1, px: 1, py: 1.5708, rx: 600, ry: 500, rgb: '{b}', a: .16 }},
    ] }},
    light: {{ blobs: [
      {{ x: 900, y: 1500, ax: 150, ay: 120, fx: 1, fy: 2, px: 1.5708, rx: 900, ry: 800, rgb: '{a}', a: .22 }},
      {{ x: 200, y: 300, ax: 140, ay: 90, fx: 1, fy: 2, py: 1.5708, rx: 700, ry: 600, rgb: '{b}', a: .12 }},
    ] }},
  }},
  transition: 'circle',
  grain: .06,
  sfx: {{ transition: {{ name: 'whoosh', gain: .3, opts: {{ dur: .5, f0: 850, f1: 5500, peak: .28 }} }} }},
}};
"""
    open(os.path.join(d, "style.js"), "w").write(style)
    open(os.path.join(d, "STYLE.md"), "w").write(f"# Estilo generado por make_card.py\nAcento {accent}, secundario {accent2}, fuente Anton (local).\n")


HEAD = """// generado por make_card.py -- no editar a mano: vuelve a correr el script
const PRM = %s;
const DARK = PRM.bg !== 'light';
const TXT = DARK ? WH : K;
"""

STEPS = HEAD + """
const n = PRM.items.length, CW = 940, CH = 150 + n * 150;
const card = mk(CW, CH);
function drawCard(f) {
  const c = card.getContext('2d'); c.clearRect(0, 0, CW, CH);
  rr(c, 1, 1, CW - 2, CH - 2, 44); c.fillStyle = DARK ? CARD : '#fff'; c.fill();
  c.strokeStyle = DARK ? 'rgba(255,255,255,.12)' : 'rgba(10,10,10,.08)'; c.lineWidth = 2; c.stroke();
  c.textBaseline = 'middle';
  PRM.items.forEach((s, i) => {
    const st = 36 + i * 26, a = prog(f, st, st + 14, E.out5), y = 110 + i * 150;
    c.globalAlpha = .22 + .78 * a;
    rr(c, 40, y - 54, CW - 80, 108, 28); c.fillStyle = DARK ? '#1B1B1B' : '#F1EEE7'; c.fill();
    if (a > .98) { c.strokeStyle = O; c.lineWidth = 4; c.stroke(); }
    c.font = font(400, 34, MONO); c.fillStyle = O; c.textAlign = 'left'; c.fillText(String(i + 1).padStart(2, '0'), 78, y + 2);
    c.font = font(400, 54, DISPLAY); c.fillStyle = TXT; c.fillText(s.toUpperCase(), 170, y + 4);
    const k = prog(f, st + 12, st + 26, E.out5);
    if (k > 0) {  // drawn check
      c.strokeStyle = O; c.lineWidth = 9; c.lineCap = 'round'; c.lineJoin = 'round'; c.beginPath();
      c.moveTo(CW - 150, y + 2); const a1 = Math.min(1, k * 2), a2 = Math.max(0, k * 2 - 1);
      c.lineTo(CW - 150 + 22 * a1, y + 2 + 22 * a1); if (a2 > 0) c.lineTo(CW - 128 + 44 * a2, y + 24 - 50 * a2); c.stroke();
    }
    c.globalAlpha = 1;
  });
}
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.06);
  const out = prog(f, N - 14, N, E.inC);
  ctx.globalAlpha = 1 - out;
  words(ctx, f, [[PRM.title.toUpperCase(), TXT]], { x: 540, y: 330, start: 4, size: 96, weight: 400, drift: prog(f, 10, N, E.lin) * 8, color: TXT });
  const r = spring(f, 14, { k: 80, c: 14 });
  drawCard(f); ctx.globalAlpha = clamp(r * 1.6) * (1 - out);
  persp(ctx, card, 540, lerp(1500, 1030, r) - prog(f, 40, N, E.lin) * 20, { ry: .15 - prog(f, 30, N, E.lin) * .07 + Math.sin(f / 45) * .025, light: !DARK });
  ctx.restore();
}
const SFX = [['pop', 6, .45], ...PRM.items.map((_, i) => ['click', 36 + i * 26 + 12, .5, 0, { freq: 2300 + i * 160, dur: .03 }]), ['chime', 36 + (n - 1) * 26 + 20, .4]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

EQUATION = HEAD + """
const T = PRM.items;                       // e.g. ['$1.000', '× 6', '$6.000']
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.08);
  const out = prog(f, N - 12, N, E.inC);
  ctx.globalAlpha = 1 - out;
  if (PRM.label) words(ctx, f, [[PRM.label.toUpperCase(), TXT]], { x: 540, y: 380, start: 2, size: 56, weight: 400, color: DARK ? '#A8A8A8' : '#555' });
  const last = T.length - 1, base = 720;
  T.forEach((t, i) => {
    const st = 10 + i * 24, isRes = i === last, s = spring(f, st, isRes ? { k: 120, c: 11 } : { k: 160, c: 14 });
    const y = base + i * 230 + (isRes ? 70 : 0);
    ctx.save(); ctx.translate(540, y); const sc = lerp(.4, 1, s); ctx.scale(sc, sc); ctx.globalAlpha *= clamp(s * 1.5);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = font(400, isRes ? 250 : 170, DISPLAY);
    if (isRes) { ctx.shadowColor = O; ctx.shadowBlur = 50 + 20 * Math.sin(f / 8); ctx.fillStyle = O; }
    else ctx.fillStyle = TXT;
    let txt = t;
    if (isRes) { const m = t.match(/^(\\D*)([\\d.,]+)(\\D*)$/); if (m) { const num = parseFloat(m[2].replace(/\\./g, '').replace(',', '.')); const v = Math.round(num * prog(f, st, st + 34, E.out5)); txt = m[1] + v.toLocaleString('es-CO') + m[3]; } }
    ctx.fillText(txt, 0, 0); ctx.restore();
    if (i === last - 1) {   // rule above the result
      const w = prog(f, st + 8, st + 20, E.out5) * 560;
      ctx.fillStyle = DARK ? 'rgba(255,255,255,.35)' : 'rgba(10,10,10,.35)'; ctx.fillRect(540 - w / 2, y + 130, w, 8);
    }
  });
  ctx.restore();
}
const SFX = [...T.map((_, i) => i === T.length - 1 ? ['boom', 10 + i * 24, .55, 0, { dur: .9 }] : ['pop', 10 + i * 24, .5]), ['chime', 10 + (T.length - 1) * 24 + 26, .4]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

COMPARE = HEAD + """
const R = PRM.rows;                        // [{label, from, to}]
const CW = 940, CH = 200 + R.length * 330;
const card = mk(CW, CH);
function drawCard(f) {
  const c = card.getContext('2d'); c.clearRect(0, 0, CW, CH);
  rr(c, 1, 1, CW - 2, CH - 2, 44); c.fillStyle = DARK ? CARD : '#fff'; c.fill();
  c.strokeStyle = DARK ? 'rgba(255,255,255,.12)' : 'rgba(10,10,10,.08)'; c.lineWidth = 2; c.stroke();
  c.textBaseline = 'middle';
  R.forEach((r, i) => {
    const st = 30 + i * 52, a = prog(f, st, st + 14, E.out5), y = 150 + i * 330;
    c.globalAlpha = .2 + .8 * a;
    c.font = font(400, 40, MONO); c.fillStyle = DARK ? '#9a9a9a' : '#777'; c.textAlign = 'left'; c.fillText(r.label.toUpperCase(), 70, y);
    c.font = font(400, 112, DISPLAY); c.fillStyle = DARK ? '#7d7d7d' : '#999'; c.fillText(r.from, 70, y + 120);
    const ar = prog(f, st + 14, st + 30, E.out5);
    c.strokeStyle = O; c.lineWidth = 12; c.lineCap = 'round'; c.lineJoin = 'round';
    const x0 = 440, x1 = x0 + 90 * ar; c.beginPath(); c.moveTo(x0, y + 120); c.lineTo(x1, y + 120);
    if (ar > .6) { c.moveTo(x1 - 22, y + 98); c.lineTo(x1, y + 120); c.lineTo(x1 - 22, y + 142); } c.stroke();
    const s = spring(f, st + 28, { k: 130, c: 11 });
    c.save(); c.translate(580, y + 120); c.scale(lerp(.6, 1, s), lerp(.6, 1, s)); c.globalAlpha *= clamp(s * 1.5);
    c.font = font(400, 150, DISPLAY); c.fillStyle = O; c.shadowColor = O; c.shadowBlur = 24; c.fillText(r.to, 0, 0); c.restore();
    c.globalAlpha = 1;
  });
}
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.06);
  const out = prog(f, N - 14, N, E.inC);
  ctx.globalAlpha = 1 - out;
  words(ctx, f, [[PRM.title.toUpperCase(), TXT]], { x: 540, y: 330, start: 4, size: 96, weight: 400, drift: prog(f, 10, N, E.lin) * 8, color: TXT });
  const r = spring(f, 14, { k: 80, c: 14 });
  drawCard(f); ctx.globalAlpha = clamp(r * 1.6) * (1 - out);
  persp(ctx, card, 540, lerp(1500, 1060, r) - prog(f, 40, N, E.lin) * 20, { ry: .14 - prog(f, 30, N, E.lin) * .06 + Math.sin(f / 45) * .025, light: !DARK });
  ctx.restore();
}
const SFX = [['pop', 6, .45], ...R.flatMap((_, i) => [['click', 30 + i * 52 + 14, .5], ['boom', 30 + i * 52 + 30, .35, 0, { dur: .6 }]])];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""


HOOK = HEAD + """
// PRM.title: lines separated by '|', *word* = highlighted in the accent colour. PRM.label = small kicker above.
const LINES = PRM.title.split('|').map(l => l.trim());
const maxc = Math.max(...LINES.map(l => l.replace(/\\*/g, '').length));
const SZ = Math.max(80, Math.min(190, Math.floor(1000 / (maxc * .50))));
const LH = SZ * 1.12, Y0 = 960 - (LINES.length - 1) * LH / 2;
function parts(l) { return l.split(/(\\*[^*]+\\*)/).filter(Boolean).map(t => t.startsWith('*') ? [t.slice(1, -1).toUpperCase(), O] : [t.toUpperCase(), TXT]); }
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.07);
  const out = prog(f, N - 10, N, E.inC);
  ctx.globalAlpha = 1 - out;
  if (PRM.label) words(ctx, f, [[PRM.label.toUpperCase(), DARK ? '#A8A8A8' : '#555']], { x: 540, y: Y0 - LH * .95, start: 2, size: 52, weight: 400, ls: 4 });
  LINES.forEach((l, i) => words(ctx, f, parts(l), { x: 540, y: Y0 + i * LH, start: 8 + i * 14, stagger: 4, size: SZ, weight: 400, ls: 0, drift: prog(f, 10, N, E.lin) * 6 }));
  const w = prog(f, 14 + LINES.length * 14, 28 + LINES.length * 14, E.out5) * 620;
  ctx.fillStyle = O; ctx.fillRect(540 - w / 2, Y0 + (LINES.length - 1) * LH + SZ * .62, w, 10);
  ctx.restore();
}
const SFX = [...LINES.map((_, i) => ['pop', 8 + i * 14, .5]), ['boom', 14 + LINES.length * 14, .35, 0, { dur: .6 }]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

CTA = HEAD + """
// PRM.title = what to do ('ENTRA AHORA'), PRM.label = button text, PRM.items[0] = small line under the button.
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.06);
  const out = prog(f, N - 10, N, E.inC);
  ctx.globalAlpha = 1 - out;
  words(ctx, f, [[PRM.title.toUpperCase(), TXT]], { x: 540, y: 640, start: 2, size: 130, weight: 400, ls: 0 });
  const s = spring(f, 22, { k: 120, c: 12 }), pulse = 1 + .035 * Math.sin(f / 5) * clamp((f - 40) / 10);
  const BW = 860, BH = 190, by = 1010;
  ctx.save(); ctx.translate(540, by); ctx.scale(lerp(.5, 1, s) * pulse, lerp(.5, 1, s) * pulse); ctx.globalAlpha *= clamp(s * 1.6);
  ctx.shadowColor = O; ctx.shadowBlur = 40 + 25 * Math.sin(f / 6);
  rr(ctx, -BW / 2, -BH / 2, BW, BH, 95); ctx.fillStyle = O; ctx.fill(); ctx.shadowBlur = 0;
  ctx.font = font(400, 88, DISPLAY); ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#0A0A0A';
  ctx.fillText((PRM.label || 'QUIERO ENTRAR').toUpperCase(), 0, 6); ctx.restore();
  // finger-tap arrow bouncing under the button
  const a = prog(f, 40, 54, E.out5), bounce = Math.abs(Math.sin(f / 7)) * 34;
  if (a > 0) {
    ctx.save(); ctx.globalAlpha *= a; ctx.strokeStyle = TXT; ctx.lineWidth = 16; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
    const ay = by + 190 + bounce; ctx.beginPath(); ctx.moveTo(540, ay + 130); ctx.lineTo(540, ay); ctx.moveTo(480, ay + 60); ctx.lineTo(540, ay); ctx.lineTo(600, ay + 60); ctx.stroke(); ctx.restore();
  }
  if (PRM.items[0]) words(ctx, f, [[PRM.items[0].toUpperCase(), DARK ? '#A8A8A8' : '#555']], { x: 540, y: 1560, start: 30, size: 48, weight: 400, ls: 3 });
  ctx.restore();
}
const SFX = [['pop', 4, .5], ['boom', 24, .5, 0, { dur: .7 }], ['chime', 44, .45]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

PHONE = HEAD + """
// PRM.images = the user's screenshots (copied into assets as shot0..): the phone enters and cuts between them.
const IM = PRM.images, HOLD = 52;
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.05);
  const out = prog(f, N - 12, N, E.inC);
  ctx.globalAlpha = 1 - out;
  if (PRM.title) words(ctx, f, [[PRM.title.toUpperCase(), TXT]], { x: 540, y: 250, start: 4, size: 96, weight: 400, ls: 0 });
  const k = Math.min(IM.length - 1, Math.max(0, Math.floor((f - 26) / HOLD)));
  phone(ctx, f, { x: 540, y: 1100, w: 640, start: 6, from: 'bottom', dist: 1200, light: !DARK,
    screen: (g, w, h) => { const im = IMG('shot' + k + '.png'); if (im) cover(g, im, 0, 0, w, h, { s: 1, ox: .5, oy: 0 }); } });
  ctx.restore();
}
const SFX = [['pop', 8, .5], ...IM.slice(1).map((_, i) => ['click', 26 + (i + 1) * HOLD, .5])];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""


STRIKE = HEAD + """
// PRM.items = pains that get crossed out one by one; PRM.label = big closing word (e.g. 'DE CERO')
const T = PRM.items, RED = '#FF3B3B', STEP = PRM.step || 20;
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.05);
  const out = prog(f, N - 10, N, E.inC); ctx.globalAlpha = 1 - out;
  T.forEach((t, i) => {
    const st = 6 + i * STEP, a = prog(f, st, st + 10, E.out5), y = 500 + i * 190 + (1 - a) * 40;
    const s = prog(f, st + 12, st + 22, E.out5);
    ctx.save(); ctx.globalAlpha *= a; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    ctx.font = font(400, 112, DISPLAY); ctx.fillStyle = s > .5 ? (DARK ? '#6f6f6f' : '#999') : TXT;
    ctx.fillText(t.toUpperCase(), 540, y); const w = ctx.measureText(t.toUpperCase()).width;
    if (s > 0) { ctx.strokeStyle = RED; ctx.lineWidth = 16; ctx.lineCap = 'round'; ctx.beginPath(); ctx.moveTo(540 - w / 2 - 20, y + 4); ctx.lineTo(540 - w / 2 - 20 + (w + 40) * s, y + 4); ctx.stroke(); }
    ctx.restore();
  });
  if (PRM.label) {
    const st = 6 + T.length * STEP + 14, r = spring(f, st, { k: 120, c: 11 });
    ctx.save(); ctx.translate(540, 1500); const sc = lerp(.5, 1, r); ctx.scale(sc, sc); ctx.globalAlpha *= clamp(r * 1.5);
    ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.font = font(400, 190, DISPLAY); ctx.fillStyle = O; ctx.shadowColor = O; ctx.shadowBlur = 40;
    ctx.fillText(PRM.label.toUpperCase(), 0, 0); ctx.restore();
  }
  ctx.restore();
}
const SFX = [...T.flatMap((_, i) => [['pop', 6 + i * STEP, .45], ['click', 6 + i * STEP + 14, .5]]), ['boom', 6 + T.length * STEP + 14, .5, 0, { dur: .8 }]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

RANKING = HEAD + """
// PRM.images = thumbnails (avatars), PRM.items = platform chips, PRM.title on top. Rows start shuffled and sort themselves.
const IM = PRM.images, NR = Math.min(IM.length, 5), LEN = [1, .84, .68, .52, .38];
const START = [3, 0, 4, 1, 2].slice(0, NR).map(x => Math.min(x, NR - 1));
function rowY(i) { return 520 + i * 220; }
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.05);
  const out = prog(f, N - 10, N, E.inC); ctx.globalAlpha = 1 - out;
  words(ctx, f, [[PRM.title.toUpperCase(), TXT]], { x: 540, y: 300, start: 2, size: 84, weight: 400, ls: 0 });
  const mv = E.out5(prog(f, 52, 78, E.lin));
  for (let i = NR - 1; i >= 0; i--) {
    const a = prog(f, 8 + i * 5, 20 + i * 5, E.out5), y0 = rowY(START[i] %% NR), y = lerp(y0, rowY(i), mv) + (1 - a) * 50;
    const grow = prog(f, 14 + i * 5, 50 + i * 5, E.out5), top = i === 0 && mv > .98;
    ctx.save(); ctx.globalAlpha *= a;
    ctx.fillStyle = DARK ? '#1B1B1B' : '#EEE'; rr(ctx, 90, y - 92, 900, 184, 40); ctx.fill();
    if (top) { ctx.strokeStyle = O; ctx.lineWidth = 5; ctx.shadowColor = O; ctx.shadowBlur = 24; ctx.stroke(); ctx.shadowBlur = 0; }
    ctx.save(); rr(ctx, 110, y - 76, 152, 152, 34); ctx.clip(); const im = IMG('shot' + i + '.png'); if (im) cover(ctx, im, 110, y - 76, 152, 152, { s: 1.5, ox: .5, oy: .3 }); ctx.restore();
    const BW = 640 * LEN[i] * grow;
    rr(ctx, 290, y - 30, Math.max(8, BW), 60, 30); ctx.fillStyle = top ? O : (DARK ? '#3a3a3a' : '#bbb'); ctx.fill();
    ctx.textBaseline = 'middle'; ctx.textAlign = 'left'; ctx.font = font(400, 34, MONO); ctx.fillStyle = top ? '#0A0A0A' : TXT;
    if (PRM.items[i] && BW > 200) ctx.fillText(PRM.items[i].toUpperCase(), 316, y + 2);
    ctx.font = font(400, 54, DISPLAY); ctx.fillStyle = top ? O : (DARK ? '#777' : '#999'); ctx.textAlign = 'right'; ctx.fillText('#' + (i + 1), 968, y - 52 + 14);
    ctx.restore();
  }
  ctx.restore();
}
const SFX = [['pop', 4, .45], ['whoosh', 52, .4], ['chime', 80, .45]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

ANATOMY = HEAD + """
// PRM.items = structure labels (GANCHO, PROBLEMA, ...). Phase 1: the ad is taken apart. Phase 2: every block turns into the user's own offer.
const L = PRM.items, PAL = ['#FF5C5C', '#FFB020', '#39FF6A', '#4DA3FF', '#C77DFF', '#FF7AC8'];
const SW = PRM.step || 78;
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.05);
  const out = prog(f, N - 10, N, E.inC); ctx.globalAlpha = 1 - out;
  const sw = prog(f, SW, SW + 14, E.out5);
  words(ctx, f, [[(sw > .5 ? PRM.label : PRM.title).toUpperCase(), sw > .5 ? O : TXT]], { x: 540, y: 330, start: sw > .5 ? SW : 2, size: 84, weight: 400, ls: 0 });
  L.forEach((t, i) => {
    const st = 8 + i * 8, a = prog(f, st, st + 12, E.out5), y = 500 + i * 220, gap = E.out5(prog(f, 34, 60, E.lin)) * 26 * (i - (L.length - 1) / 2);
    const rec = prog(f, SW + 6 + i * 5, SW + 22 + i * 5, E.out5);
    ctx.save(); ctx.globalAlpha *= a; ctx.translate((1 - a) * -120, gap);
    ctx.fillStyle = DARK ? '#1B1B1B' : '#EEE'; rr(ctx, 70, y - 92, 940, 184, 36); ctx.fill();
    ctx.fillStyle = PAL[i %% PAL.length]; rr(ctx, 92, y - 70, 250, 140, 28); ctx.fill();
    ctx.textBaseline = 'middle'; ctx.textAlign = 'center'; ctx.font = font(400, 44, DISPLAY); ctx.fillStyle = '#0A0A0A'; ctx.fillText(t.toUpperCase(), 217, y + 2);
    const w1 = 520 - (i %% 3) * 60, w2 = 360 + (i %% 2) * 90;
    [[y - 28, w1], [y + 26, w2]].forEach(([yy, w]) => {
      ctx.fillStyle = DARK ? '#3a3a3a' : '#bbb'; rr(ctx, 372, yy - 14, w, 28, 14); ctx.fill();
      if (rec > 0) { ctx.fillStyle = O; rr(ctx, 372, yy - 14, w * rec, 28, 14); ctx.fill(); }
    });
    if (rec > .98) { ctx.strokeStyle = O; ctx.lineWidth = 8; ctx.lineCap = 'round'; ctx.lineJoin = 'round'; ctx.beginPath(); ctx.moveTo(930, y); ctx.lineTo(950, y + 22); ctx.lineTo(985, y - 24); ctx.stroke(); }
    ctx.restore();
  });
  ctx.restore();
}
const SFX = [['pop', 6, .4], ...L.map((_, i) => ['click', 8 + i * 8, .4]), ['whoosh', 34, .4], ['chime', SW + 6, .5], ...L.map((_, i) => ['click', SW + 14 + i * 5, .35])];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

WALL = HEAD + """
// PRM.images = avatar stills (up to 6), shown as a 2x3 wall of faces with a voice waveform underneath. PRM.label = caption under the wall.
const IM = PRM.images, NW = Math.min(6, IM.length), TW = 470, TH = 520;
function scene(ctx, f) {
  ctx.save(); bg(ctx, f, DARK); cam(ctx, f, 0, N, 1, 1.05);
  const out = prog(f, N - 10, N, E.inC); ctx.globalAlpha = 1 - out;
  for (let i = 0; i < NW; i++) {
    const col = i %% 2, row = Math.floor(i / 2), x = 70 + col * (TW + 20), y = 150 + row * (TH + 20);
    const r = spring(f, 4 + i * 6, { k: 150, c: 13 }), sc = lerp(.6, 1, r);
    ctx.save(); ctx.translate(x + TW / 2, y + TH / 2); ctx.scale(sc, sc); ctx.globalAlpha *= clamp(r * 1.6);
    ctx.save(); rr(ctx, -TW / 2, -TH / 2, TW, TH, 36); ctx.clip(); const im = IMG('shot' + i + '.png'); if (im) cover(ctx, im, -TW / 2, -TH / 2, TW, TH, { s: 1.35 + prog(f, 0, N, E.lin) * .06, ox: .5, oy: .32 }); ctx.restore();
    ctx.strokeStyle = 'rgba(255,255,255,.18)'; ctx.lineWidth = 3; rr(ctx, -TW / 2, -TH / 2, TW, TH, 36); ctx.stroke();
    ctx.fillStyle = 'rgba(10,10,10,.72)'; rr(ctx, -TW / 2 + 18, TH / 2 - 62, 150, 44, 22); ctx.fill();
    ctx.fillStyle = O; ctx.beginPath(); ctx.arc(-TW / 2 + 42, TH / 2 - 40, 7, 0, 7); ctx.fill();
    ctx.font = font(400, 26, MONO); ctx.textAlign = 'left'; ctx.textBaseline = 'middle'; ctx.fillStyle = '#fff'; ctx.fillText('AVATAR IA', -TW / 2 + 58, TH / 2 - 39);
    ctx.restore();
  }
  const wv = prog(f, 30, 44, E.out5);
  ctx.save(); ctx.globalAlpha *= wv;
  for (let k = 0; k < 41; k++) { const h = 14 + Math.abs(Math.sin(f / 5 + k * .9) * Math.cos(f / 11 + k * .35)) * 120 * (.5 + .5 * Math.sin(k / 6)); ctx.fillStyle = O; rr(ctx, 90 + k * 22, 1760 - h / 2, 12, h, 6); ctx.fill(); }
  if (PRM.label) words(ctx, f, [[PRM.label.toUpperCase(), TXT]], { x: 540, y: 1650, start: 34, size: 60, weight: 400, ls: 2 });
  ctx.restore();
  ctx.restore();
}
const SFX = [...Array.from({ length: NW }, (_, i) => ['pop', 4 + i * 6, .4]), ['chime', 36, .45]];
const SC = [{ a: 0, fn: scene }]; const TR = [];
"""

TEMPLATES = {"steps": STEPS, "equation": EQUATION, "compare": COMPARE, "hook": HOOK, "cta": CTA, "phone": PHONE, "strike": STRIKE, "ranking": RANKING, "anatomy": ANATOMY, "wall": WALL}


def duration_for(a):
    if a.duration:
        return a.duration
    if a.template == "steps":
        return round(2.2 + 0.9 * len(a.items) + 0.8, 1)
    if a.template == "equation":
        return round(1.2 + 0.8 * len(a.items) + 1.4, 1)
    if a.template == "hook":
        return round(1.4 + 0.5 * len(a.title.split("|")) + 1.2, 1)
    if a.template == "cta":
        return 3.2
    if a.template == "phone":
        return round(1.6 + 1.75 * max(1, len(a.images)) + 0.6, 1)
    if a.template == "strike":
        return round(0.6 + (a.step or 20) / 30 * len(a.items) + 1.8, 1)
    if a.template == "ranking":
        return 4.2
    if a.template == "anatomy":
        return 5.4
    if a.template == "wall":
        return 4.0
    return round(1.8 + 1.8 * len(a.rows) + 0.9, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--template", required=True, choices=list(TEMPLATES))
    ap.add_argument("--name", required=True)
    ap.add_argument("--job", required=True, help="editar-anuncios job slug: the MP4 goes to remotion/public/jobs/<job>/")
    ap.add_argument("--title", default="")
    ap.add_argument("--label", default="")
    ap.add_argument("--items", nargs="*", default=[])
    ap.add_argument("--images", nargs="*", default=[], help="phone template: screenshots to show on the phone, in order")
    ap.add_argument("--step", type=int, default=0, help="strike template: frames between items (default 20)")
    ap.add_argument("--rows", nargs="*", default=[], help='"LABEL|from|to"')
    ap.add_argument("--accent", default="#39FF6A")
    ap.add_argument("--accent2", default="#2340C8")
    ap.add_argument("--bg", default="dark", choices=["dark", "light"])
    ap.add_argument("--duration", type=float)
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--speed", type=float, default=1.0, help="play the finished card faster (e.g. 1.7) when the voice says things quickly")
    a = ap.parse_args()
    if not os.path.isdir(os.path.join(STUDIO, "node_modules")):
        sys.exit(f"motion-studio is not set up. Run once: bash {STUDIO}/tools/setup.sh")
    name = slug(a.name)
    dur = duration_for(a)
    frames = int(round(dur * a.fps))
    style = f"gen-{slug(a.accent)}-{slug(a.accent2)}"
    write_style(style, a.accent, a.accent2, a.bg)
    proj = os.path.join(STUDIO, "projects", name)
    os.makedirs(proj, exist_ok=True)
    rows = [dict(zip(("label", "from", "to"), r.split("|"))) for r in a.rows]
    params = {"title": a.title, "label": a.label, "items": a.items, "rows": rows, "accent": a.accent, "bg": a.bg, "images": a.images, "step": a.step}
    assets = []
    if a.template in ("phone", "ranking", "wall"):
        if not a.images:
            sys.exit(f"{a.template} template needs --images <image> [...]")
        adir = os.path.join(proj, "assets"); os.makedirs(adir, exist_ok=True)
        for i, im in enumerate(a.images):
            fn = f"shot{i}.png"
            if not os.path.isfile(os.path.expanduser(im)):
                sys.exit(f"image not found: {im}")
            dst = os.path.join(adir, fn)
            # the engine loads assets by file name: normalise any screenshot (png/jpg/heic/webp) to PNG
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.expanduser(im), "-frames:v", "1", dst], check=True, stdin=subprocess.DEVNULL)
            assets.append(fn)
    open(os.path.join(proj, "project.js"), "w").write(
        f"window.PROJECT = {{ name: '{name}', style: '{style}', brand: '', w: 1080, h: 1920, fps: {a.fps}, frames: {frames}, assets: {json.dumps(assets)} }};\n")
    scenes = TEMPLATES[a.template] % json.dumps(params, ensure_ascii=False)   # N (frames) is a global of the engine
    open(os.path.join(proj, "scenes.js"), "w").write(scenes)
    # a render server left over from another copy of the studio would write frames into the wrong folder
    subprocess.run(["pkill", "-f", "tools/server.py"], capture_output=True)
    env = dict(os.environ, PATH="/opt/homebrew/bin:" + os.environ.get("PATH", ""))
    r = subprocess.run(["bash", "tools/render.sh", name], cwd=STUDIO, env=env, capture_output=True, text=True)
    out = os.path.join(proj, "out", "video.mp4")
    if r.returncode != 0 or not os.path.isfile(out):
        sys.exit("render failed:\n" + (r.stdout + r.stderr)[-1200:])
    dst_dir = os.path.join(EDITAR, "remotion", "public", "jobs", a.job)
    os.makedirs(dst_dir, exist_ok=True)
    # re-encode: constant frame rate H.264 with short keyframes (same reason as prepare_source.py)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", out, "-an", "-vf", f"setpts=PTS/{a.speed},fps={a.fps}", "-c:v", "libx264", "-crf", "16", "-g", "12", "-pix_fmt", "yuv420p",
                    os.path.join(dst_dir, f"{name}.mp4")], check=True, stdin=subprocess.DEVNULL)
    dead = [l.strip() for l in r.stdout.splitlines() if "DEAD HOLD" in l]
    print(f"ok: {dur / a.speed:.1f}s card -> {dst_dir}/{name}.mp4" + (f"   (dead holds: {len(dead)})" if dead else "   (no dead holds)"))
    print(json.dumps({"src": f"jobs/{a.job}/{name}.mp4", "atMs": 0, "durationMs": int(dur / a.speed * 1000), "scrim": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
