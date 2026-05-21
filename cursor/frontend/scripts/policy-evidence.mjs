import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const outDir = path.resolve('evidence-screenshots');
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: 'Dashboard' }).click();
await page.waitForTimeout(1500);

await page.screenshot({
  path: path.join(outDir, 'policy-layer-desktop.png'),
  fullPage: true,
});

const viewButtons = page.getByRole('button', { name: 'View policy' });
if ((await viewButtons.count()) > 0) {
  await viewButtons.first().click();
}
await page.waitForTimeout(600);

await page.screenshot({
  path: path.join(outDir, 'policy-detail-desktop.png'),
  fullPage: true,
});

await page.setViewportSize({ width: 480, height: 900 });
await page.waitForTimeout(800);

await page.screenshot({
  path: path.join(outDir, 'policy-layer-mobile-480.png'),
  fullPage: true,
});

await browser.close();
console.log(JSON.stringify({
  desktopLayer: path.join(outDir, 'policy-layer-desktop.png'),
  desktopDetail: path.join(outDir, 'policy-detail-desktop.png'),
  mobileLayer: path.join(outDir, 'policy-layer-mobile-480.png'),
}, null, 2));
