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

await page.locator('.approval-search-grid select').first().selectOption('all');
await page.waitForTimeout(50);

await page.locator('.approval-queue-controls select').first().selectOption('waiting_others');
await page.getByPlaceholder('Search requestor').fill('');
await page.getByPlaceholder('Search policy ID/name').fill('');
await page.getByPlaceholder('Search comments/text').fill('');
await page.getByPlaceholder('Search request ID/content').fill('');
await page.getByPlaceholder('Filter assignee').fill('');
await page.locator('.approval-search-grid select').nth(0).selectOption('all');
await page.locator('.approval-search-grid select').nth(1).selectOption('all');
await page.locator('.approval-search-grid select').nth(2).selectOption('all');
await page.locator('.approval-search-grid select').nth(3).selectOption('all');
await page.waitForTimeout(120);

const baselineFilterRows = await page.locator('.approval-queue-row').count();
const filter50Start = performance.now();
await page.getByPlaceholder('Search request ID/content').fill('APR-05');
await page.waitForFunction(
  (baseline) => {
    const rows = document.querySelectorAll('.approval-queue-row');
    return rows.length > 0 && rows.length < baseline && rows.length <= 50;
  },
  baselineFilterRows,
  { timeout: 5000 },
);
const filter50End = performance.now();
const filter50Ms = Number((filter50End - filter50Start).toFixed(2));
const filteredRowCount = await page.locator('.approval-queue-row').count();

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

await page.locator('.audit-filters select').nth(3).selectOption('bulk_action');
await page.waitForTimeout(120);
const latestAuditText = (await page.locator('.audit-timeline li').first().innerText()).trim();
const writeLatencyMatch = latestAuditText.match(/Write latency:\s*(\d+)ms/i);
const auditWriteLatencyMs = writeLatencyMatch ? Number(writeLatencyMatch[1]) : null;

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
  filter_baseline_rows: baselineFilterRows,
  filter_result_rows: filteredRowCount,
  filter_50_query_ms: filter50Ms,
  filter_50_under_500ms: filter50Ms < 500 && baselineFilterRows >= 50,
  template_apply_ms: templateApplyMs,
  template_apply_under_500ms: templateApplyMs < 500,
  audit_write_latency_ms: auditWriteLatencyMs,
  audit_write_under_100ms: typeof auditWriteLatencyMs === 'number' ? auditWriteLatencyMs < 100 : false,
};

await fs.writeFile(path.resolve('approval-benchmark.json'), JSON.stringify(benchmark, null, 2), 'utf-8');
console.log(JSON.stringify(benchmark, null, 2));

await browser.close();
