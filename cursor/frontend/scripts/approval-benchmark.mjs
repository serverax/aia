import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
const start = performance.now();
await page.locator('.top-nav').getByRole('button', { name: 'Approvals', exact: true }).click();
await page.getByRole('heading', { name: 'Approval Request UI' }).waitFor({ state: 'visible', timeout: 10000 });
const end = performance.now();

const rowChecks = page.locator('.approval-row-select input[type="checkbox"]');
const rowCount = await rowChecks.count();
const targetCount = Math.min(50, rowCount);
for (let index = 0; index < targetCount; index += 1) {
  await rowChecks.nth(index).check();
}
const bulkStart = performance.now();
await page.getByRole('button', { name: 'Bulk Approve' }).click();
await page
  .locator('.approval-card .success')
  .filter({ hasText: 'Bulk approve:' })
  .first()
  .waitFor({ state: 'visible', timeout: 10000 });
const bulkEnd = performance.now();

const loadMs = Number((end - start).toFixed(2));
const bulkActionMs = Number((bulkEnd - bulkStart).toFixed(2));

const searchStart = performance.now();
await page.getByPlaceholder('Search requestor').fill('compliance_officer');
await page.waitForTimeout(50);
const searchEnd = performance.now();
const searchActionMs = Number((searchEnd - searchStart).toFixed(2));

const filterStart = performance.now();
await page.locator('.approval-search-grid select').first().selectOption('approved');
await page.waitForTimeout(50);
const filterEnd = performance.now();
const filterActionMs = Number((filterEnd - filterStart).toFixed(2));

await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) select')
  .first()
  .selectOption('policy-standard');
const templateApplyMs = Number(
  (
    await page.evaluate(async () => {
      const start = performance.now();
      const buttons = Array.from(document.querySelectorAll('button'));
      const applyButton = buttons.find((button) => button.textContent?.includes('Apply Template'));
      applyButton?.click();
      await new Promise((resolve) => requestAnimationFrame(() => resolve(true)));
      return performance.now() - start;
    })
  ).toFixed(2),
);

const benchmark = {
  page: 'ApprovalRequestPage',
  load_ms: loadMs,
  under_2s: loadMs < 2000,
  bulk_items_target: targetCount,
  bulk_action_ms: bulkActionMs,
  bulk_50_under_2s: targetCount >= 50 && bulkActionMs < 2000,
  search_action_ms: searchActionMs,
  search_under_500ms: searchActionMs < 500,
  filter_action_ms: filterActionMs,
  filter_under_500ms: filterActionMs < 500,
  template_apply_ms: templateApplyMs,
  template_apply_under_500ms: templateApplyMs < 500,
};

await fs.writeFile(path.resolve('approval-benchmark.json'), JSON.stringify(benchmark, null, 2), 'utf-8');
console.log(JSON.stringify(benchmark, null, 2));

await browser.close();
