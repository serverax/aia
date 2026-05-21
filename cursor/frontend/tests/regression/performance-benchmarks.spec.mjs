import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.REGRESSION_APP_URL || "http://127.0.0.1:5173";
const thresholdMs = 500;
const runsPerMetric = 20;

function percentile(values, p) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(p * sorted.length));
  return Number(sorted[index].toFixed(2));
}

function summarize(values) {
  return {
    samples: values.length,
    p50: percentile(values, 0.5),
    p95: percentile(values, 0.95),
    p99: percentile(values, 0.99),
    max: Number(Math.max(...values).toFixed(2)),
  };
}

function underThreshold(summary) {
  return summary.p50 < thresholdMs && summary.p95 < thresholdMs && summary.p99 < thresholdMs;
}

async function openApprovals(page) {
  await page.goto(appUrl, { waitUntil: "networkidle" });
  await page.locator(".top-nav").getByRole("button", { name: "Approvals", exact: true }).click();
  await page.getByRole("heading", { name: "Approval Request UI" }).waitFor({ state: "visible", timeout: 10000 });
}

async function measureSearchAction(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await openApprovals(page);
  await page.locator(".approval-queue-controls select").first().selectOption("completed");
  await page.waitForTimeout(80);
  const start = performance.now();
  await page.getByPlaceholder("Search requestor").fill("analyst@synthetic.io");
  await page.waitForTimeout(60);
  const elapsed = Number((performance.now() - start).toFixed(2));
  await page.close();
  return elapsed;
}

async function measurePresetApplyAction(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await openApprovals(page);
  const start = performance.now();
  await page.getByRole("button", { name: "My Pending Approvals", exact: true }).click();
  await page.waitForTimeout(60);
  const elapsed = Number((performance.now() - start).toFixed(2));
  await page.close();
  return elapsed;
}

async function measureBulkAction(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await openApprovals(page);
  await page.locator(".approval-queue-controls select").first().selectOption("waiting_others");
  await page.waitForTimeout(80);
  await page.locator(".approval-search-grid select").first().selectOption("pending");
  await page.waitForTimeout(80);
  await page.locator(".bulk-select-all input[type='checkbox']").check();
  const start = performance.now();
  await page.getByRole("button", { name: "Bulk Approve", exact: true }).click();
  await page.locator(".approval-card .success").filter({ hasText: "Bulk approve applied" }).first().waitFor({
    state: "visible",
    timeout: 5000,
  });
  const elapsed = Number((performance.now() - start).toFixed(2));
  await page.close();
  return elapsed;
}

async function measureDetailOpenAction(browser) {
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  await openApprovals(page);
  await page.locator(".approval-queue-controls select").first().selectOption("completed");
  await page.waitForTimeout(80);
  await page.getByPlaceholder("Search policy ID/name").fill("DOC_098");
  await page.waitForTimeout(60);
  const start = performance.now();
  await page.getByRole("button", { name: "Open", exact: true }).first().click();
  await page.getByRole("heading", { name: "Approval Detail" }).waitFor({ state: "visible", timeout: 5000 });
  await page.waitForTimeout(60);
  const elapsed = Number((performance.now() - start).toFixed(2));
  await page.close();
  return elapsed;
}

async function gatherMetrics(browser, label, fn) {
  const values = [];
  for (let i = 0; i < runsPerMetric; i += 1) {
    values.push(await fn(browser));
  }
  const summary = summarize(values);
  return {
    label,
    threshold_ms: thresholdMs,
    ...summary,
    pass: underThreshold(summary),
  };
}

async function main() {
  const browser = await chromium.launch({ headless: true });

  const metrics = [
    await gatherMetrics(browser, "workstream1_search", measureSearchAction),
    await gatherMetrics(browser, "workstream2_preset_apply", measurePresetApplyAction),
    await gatherMetrics(browser, "workstream3_bulk_action", measureBulkAction),
    await gatherMetrics(browser, "workstream4_detail_open", measureDetailOpenAction),
  ];

  await browser.close();

  const report = {
    generated_at: new Date().toISOString(),
    app_url: appUrl,
    runs_per_metric: runsPerMetric,
    threshold_ms: thresholdMs,
    all_metrics_pass: metrics.every((metric) => metric.pass),
    metrics,
  };

  const reportPath = path.resolve("tests/regression/performance-benchmarks-report.json");
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.all_metrics_pass) {
    process.exitCode = 1;
  }
}

await main();
