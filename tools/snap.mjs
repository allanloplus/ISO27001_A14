// 擷取各段落畫面做檢查：node tools/snap.mjs <outdir> [mode]
// mode = end（預設，段落結尾）或 mid（段落中某句講話中）
import { createRequire } from 'module';
const { chromium } = createRequire(import.meta.url)('playwright');
import path from 'path';
const [out, mode = 'end'] = process.argv.slice(2);
const file = 'file://' + path.resolve('index.html') + '?capture';
import { routeFonts } from './fontproxy.mjs';
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
await routeFonts(page);
page.on('pageerror', e => console.log('pageerror:', e.message));
await page.goto(file, { waitUntil: 'networkidle' });
await page.evaluate(async () => { await document.fonts.load('400 40px Huninn', '資訊安全保證'); await document.fonts.load('700 40px "Noto Sans TC"', '資訊安全'); await document.fonts.ready; });
console.log('fonts:', await page.evaluate(() => [...new Set([...document.fonts].filter(f => f.status === 'loaded').map(f => f.family))].join(',')));
const sc = await page.evaluate(() => window.__scenes);
for (const [i, s] of sc.entries()) {
  const l = s.lines[s.lines.length - 1];
  const t = mode === 'end' ? l[1] - 0.2 : (s.lines[1] ? (s.lines[1][0] + s.lines[1][1]) / 2 : l[0] + 1);
  await page.evaluate(t => window.__render(t), t);
  await page.screenshot({ path: `${out}/${String(i).padStart(2, '0')}-${s.id}-${mode}.jpg`, quality: 80, type: 'jpeg' });
}
await browser.close();
