// Render the README media from the viewer: results/demo.gif, results/demo.mp4,
// and results/demo_still.png.
//
// Requirements: Node 18+, Playwright with Chromium (npm i playwright &&
// npx playwright install chromium), and ffmpeg on PATH.
//
//   python export_run.py                 # writes viewer/data.js
//   node tools/render_media.mjs          # writes the three media files
//
// Options (environment variables):
//   THREE_DIR   path to a local `three` package (node_modules/three) to use
//               instead of the unpkg CDN, for offline rendering
//   SPEED       playback speed relative to simulation time (default 2.5)
//   FPS         output frame rate (default 12)
//   GIF_WIDTH   GIF width in pixels (default 800); the MP4 stays at 1280x720

import { createRequire } from 'node:module';
import { createServer } from 'node:http';
import { readFile, mkdir, rm, stat } from 'node:fs/promises';
import { execFileSync } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const { chromium } = createRequire(import.meta.url)('playwright');
const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const VIEWER = path.join(ROOT, 'viewer');
const RESULTS = path.join(ROOT, 'results');
const FRAMES = path.join(RESULTS, 'frames');
const SPEED = Number(process.env.SPEED || 2.5);
const FPS = Number(process.env.FPS || 12);
const GIF_WIDTH = Number(process.env.GIF_WIDTH || 800);
const THREE_DIR = process.env.THREE_DIR;
const MIME = { '.html': 'text/html', '.js': 'text/javascript' };

const server = createServer(async (req, res) => {
  try {
    const file = path.join(VIEWER, decodeURIComponent(new URL(req.url, 'http://x').pathname));
    if (!file.startsWith(VIEWER)) throw new Error('outside viewer');
    res.writeHead(200, { 'Content-Type': MIME[path.extname(file)] || 'application/octet-stream' });
    res.end(await readFile(file));
  } catch { res.writeHead(404); res.end(); }
}).listen(0);
const url = dpr => `http://127.0.0.1:${server.address().port}/index.html?capture&dpr=${dpr}`;

const browser = await chromium.launch({ args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });

async function openPage(width, height, dpr = 1) {
  const page = await browser.newPage({ viewport: { width, height }, deviceScaleFactor: dpr });
  if (THREE_DIR) {
    await page.route('https://unpkg.com/three@0.160.0/**', async route => {
      const rel = new URL(route.request().url()).pathname.replace('/three@0.160.0/', '');
      route.fulfill({ contentType: 'text/javascript', body: await readFile(path.join(THREE_DIR, rel)) });
    });
  }
  page.on('pageerror', e => console.error('page error:', e.message));
  await page.goto(url(dpr));
  await page.waitForFunction(() => window.__ready === true, null, { timeout: 60000 });
  await page.evaluate(() => document.fonts.ready);
  return page;
}

// ---- animation frames (camera smoothing is stateful, so frames run in order from t = 0)
await rm(FRAMES, { recursive: true, force: true });
await mkdir(FRAMES, { recursive: true });
const page = await openPage(1280, 720);
const tEnd = await page.evaluate(() => window.__T_END);
const dt = SPEED / FPS;
const n = Math.ceil(tEnd / dt - 1e-9) + 1;   // last frame lands exactly on tEnd
for (let k = 0; k < n; k++) {
  const t = Math.min(tEnd, k * dt);
  await page.evaluate(([t, dt]) => window.__render(t, dt), [t, dt]);
  await page.screenshot({ path: path.join(FRAMES, `f_${String(k).padStart(4, '0')}.png`) });
  if (k % 25 === 0) console.log(`frame ${k + 1}/${n}`);
}
await page.close();

// ---- still image at a busy moment (several intercepts, network visible)
const STILL_T = 22.4;
const still = await openPage(1280, 720, 2);
for (let t = 0; t <= STILL_T + 1e-6; t += 0.4) await still.evaluate(([t]) => window.__render(t, 0.4), [t]);
await still.screenshot({ path: path.join(RESULTS, 'demo_still.png'), timeout: 180000 });
await still.close();

await browser.close();
server.close();

// ---- encode
const input = ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(FRAMES, 'f_%04d.png')];
const hold = 'tpad=start_mode=clone:start_duration=0.6:stop_mode=clone:stop_duration=2.5';
execFileSync('ffmpeg', [...input, '-vf',
  `${hold},scale=${GIF_WIDTH}:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=64:stats_mode=diff[p];` +
  '[b][p]paletteuse=dither=none:diff_mode=rectangle',
  path.join(RESULTS, 'demo.gif')]);
execFileSync('ffmpeg', [...input, '-vf', `${hold},format=yuv420p`, '-c:v', 'libx264',
  '-preset', 'veryfast', '-crf', '20', '-movflags', '+faststart', path.join(RESULTS, 'demo.mp4')]);
if (!process.env.KEEP_FRAMES) await rm(FRAMES, { recursive: true, force: true });

for (const f of ['demo.gif', 'demo.mp4', 'demo_still.png']) {
  const s = await stat(path.join(RESULTS, f));
  console.log(`wrote results/${f} (${(s.size / 1e6).toFixed(2)} MB)`);
}
