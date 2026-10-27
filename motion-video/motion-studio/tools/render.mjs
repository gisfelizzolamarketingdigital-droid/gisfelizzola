// Render headless (sem throttling de aba escondida).
// uso: node tools/render.mjs projects/<nome> [full|preview] [porta]
import puppeteer from 'puppeteer';
import fs from 'fs';

// Reuse the installed Chrome instead of downloading ~170 MB of Chromium (override with PUPPETEER_EXECUTABLE_PATH).
const CHROMES = [
  process.env.PUPPETEER_EXECUTABLE_PATH,
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
  '/usr/bin/google-chrome', '/usr/bin/chromium', '/usr/bin/chromium-browser',
].filter(Boolean);
const executablePath = CHROMES.find(p => { try { return fs.existsSync(p); } catch { return false; } });

const [dir, mode = 'full', port = '8777'] = process.argv.slice(2);
const q = (mode === 'preview' ? '&step=30&scale=0.33' : mode === 'board' ? '&board' : '') + (process.env.FROM ? `&from=${process.env.FROM}&to=${process.env.TO}` : '');
const url = `http://127.0.0.1:${port}/engine/player.html?p=${encodeURIComponent(dir)}&export${q}`;

const browser = await puppeteer.launch({
  headless: true,
  ...(executablePath ? { executablePath } : {}),
  protocolTimeout: 0,   // renders longos não podem expirar
  args: ['--disable-background-timer-throttling', '--disable-renderer-backgrounding', '--disable-backgrounding-occluded-windows'],
});
const page = await browser.newPage();
page.on('console', m => { const t = m.text(); if (/^frame |EXPORT_|Error/.test(t)) console.log(t); });
page.on('pageerror', e => console.log('EXPORT_ERR ' + e.message));
await page.goto(url);
const t0 = Date.now();
await page.waitForFunction('window.EXPORT_DONE === true || !!window.EXPORT_ERR', { timeout: 0, polling: 500 });
const err = await page.evaluate('window.EXPORT_ERR');
await browser.close();
if (err) { console.error('FALHOU: ' + err); process.exit(1); }
console.log(`render ok (${mode}) em ${((Date.now() - t0) / 1000).toFixed(0)}s`);
