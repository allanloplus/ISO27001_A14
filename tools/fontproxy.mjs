// 讓無頭瀏覽器透過 curl 取得 Google Fonts（沙箱環境的 Chromium 不信任代理憑證時使用）
import { execFileSync } from 'child_process';
const cache = new Map();
export async function routeFonts(page) {
  await page.route(/https:\/\/fonts\.(googleapis|gstatic)\.com\/.*/, async route => {
    const url = route.request().url();
    try {
      if (!cache.has(url)) {
        const body = execFileSync('curl', ['-sSfL', '-A', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36', url], { maxBuffer: 64 << 20 });
        cache.set(url, body);
      }
      const ct = url.includes('googleapis') ? 'text/css; charset=utf-8' : 'font/woff2';
      await route.fulfill({ status: 200, body: cache.get(url), headers: { 'content-type': ct, 'access-control-allow-origin': '*' } });
    } catch (e) { await route.abort(); }
  });
}
