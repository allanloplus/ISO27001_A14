// 將動畫簡報逐格渲染成 MP4（含旁白）
// 用法：NODE_PATH=/opt/node-tools/node_modules node tools/render_video.mjs [fps] [workers] [width]
import { createRequire } from 'module';
import { spawn, execFileSync } from 'child_process';
import path from 'path';
import fs from 'fs';
import { routeFonts } from './fontproxy.mjs';
const { chromium } = createRequire(import.meta.url)('playwright');

const FPS = +(process.argv[2] || 20), WORKERS = +(process.argv[3] || 3), W = +(process.argv[4] || 1920), H = Math.round(W * 9 / 16);
const html = 'file://' + path.resolve('index.html') + '?capture';
const tmp = path.resolve('build/video'); fs.mkdirSync(tmp, { recursive: true });
const browser = await chromium.launch();

async function openPage() {
  const page = await browser.newPage({ viewport: { width: W, height: H } });
  await routeFonts(page);
  await page.goto(html, { waitUntil: 'networkidle' });
  await page.evaluate(async () => { await document.fonts.load('400 40px Huninn', '資訊安全保證'); await document.fonts.load('700 40px "Noto Sans TC"', '資訊安全'); await document.fonts.ready; });
  return page;
}
const probe = await openPage();
const duration = await probe.evaluate(() => window.__duration);
await probe.close();
const total = Math.ceil(duration * FPS);
console.log(`duration ${duration}s → ${total} frames @${FPS}fps, ${W}x${H}, ${WORKERS} workers`);

async function worker(k) {
  const from = Math.floor(total * k / WORKERS), to = Math.floor(total * (k + 1) / WORKERS);
  const page = await openPage();
  const out = path.join(tmp, `seg${k}.mp4`);
  const ff = spawn('ffmpeg', ['-v', 'error', '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-c:v', 'libx264', '-preset', 'medium', '-crf', '21', '-pix_fmt', 'yuv420p', '-r', String(FPS), out], { stdio: ['pipe', 'inherit', 'inherit'] });
  for (let f = from; f < to; f++) {
    await page.evaluate(t => window.__render(t), f / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 90 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    if ((f - from) % 500 === 0) console.log(`worker ${k}: ${f - from}/${to - from}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on('close', r));
  await page.close();
  return out;
}
const segs = await Promise.all([...Array(WORKERS).keys()].map(worker));
await browser.close();
fs.writeFileSync(path.join(tmp, 'list.txt'), segs.map(s => `file '${s}'`).join('\n'));
const outFile = path.resolve('output/資訊安全保證_動畫簡報.mp4');
execFileSync('ffmpeg', ['-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', path.join(tmp, 'list.txt'), '-i', path.resolve('build/narration.mp3'),
  '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', '-movflags', '+faststart', outFile], { stdio: 'inherit' });
console.log('Wrote', outFile, (fs.statSync(outFile).size / 1e6).toFixed(1), 'MB');
