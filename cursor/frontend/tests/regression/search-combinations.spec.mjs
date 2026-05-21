import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.REGRESSION_APP_URL || "http://127.0.0.1:5173";
const fields = ["requestor", "date", "outcome", "policy", "comment"];

const targetFilters = {
  requestor: "analyst@synthetic.io",
  policy: "DOC_098",
  comment: "rollback",
  outcome: "rejected",
  dateFrom: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10),
  dateTo: new Date().toISOString().slice(0, 10),
};

function buildCombinations() {
  const scenarios = [];
  for (let mask = 1; mask < 1 << fields.length; mask += 1) {
    scenarios.push(fields.filter((_, index) => (mask & (1 << index)) !== 0));
  }
  return scenarios;
}

async function applyFilters(page, active) {
  await page.getByPlaceholder("Search requestor").fill(active.includes("requestor") ? targetFilters.requestor : "");
  await page
    .getByPlaceholder("Search policy ID/name")
    .fill(active.includes("policy") ? targetFilters.policy : "");
  await page
    .getByPlaceholder("Search comments/text")
    .fill(active.includes("comment") ? targetFilters.comment : "");
  await page
    .locator(".approval-search-grid select")
    .first()
    .selectOption(active.includes("outcome") ? targetFilters.outcome : "all");

  const dateInputs = page.locator('.approval-search-grid input[type="date"]');
  await dateInputs.nth(0).fill(active.includes("date") ? targetFilters.dateFrom : "");
  await dateInputs.nth(1).fill(active.includes("date") ? targetFilters.dateTo : "");
}

async function validateVisibleRows(page, active) {
  const rows = page.locator(".approval-queue-row");
  const rowCount = await rows.count();
  if (rowCount === 0) {
    return { ok: false, reason: "No visible results for active combination." };
  }

  for (let index = 0; index < Math.min(rowCount, 4); index += 1) {
    const row = rows.nth(index);
    const rowText = (await row.innerText()).toLowerCase();
    if (active.includes("requestor") && !rowText.includes(targetFilters.requestor)) {
      return { ok: false, reason: `Row ${index} failed requestor filter.` };
    }
    if (active.includes("outcome") && !rowText.includes(targetFilters.outcome)) {
      return { ok: false, reason: `Row ${index} failed outcome filter.` };
    }

    await row.getByRole("button", { name: "Open", exact: true }).click();
    await page.waitForTimeout(100);
    const detailText = (await page.locator(".approval-detail-grid").innerText()).toLowerCase();

    if (active.includes("policy") && !detailText.includes(targetFilters.policy.toLowerCase())) {
      return { ok: false, reason: `Row ${index} failed policy filter.` };
    }

    if (active.includes("comment")) {
      const threadText = (
        await page.locator(".approval-thread, .decision-explanation").first().innerText()
      ).toLowerCase();
      if (!threadText.includes(targetFilters.comment)) {
        return { ok: false, reason: `Row ${index} failed comment filter.` };
      }
    }

    if (active.includes("date") && !detailText.includes("requested at:")) {
      return { ok: false, reason: `Row ${index} missing requested date context.` };
    }
  }

  return { ok: true };
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const scenarios = buildCombinations();
  const results = [];

  await page.goto(appUrl, { waitUntil: "networkidle" });
  await page.locator(".top-nav").getByRole("button", { name: "Approvals", exact: true }).click();
  await page.getByRole("heading", { name: "Approval Request UI" }).waitFor({ state: "visible", timeout: 10000 });
  await page.locator(".approval-queue-controls select").first().selectOption("completed");
  await page.waitForTimeout(120);

  for (const active of scenarios) {
    const started = performance.now();
    await applyFilters(page, active);
    await page.waitForTimeout(120);
    const latencyMs = Number((performance.now() - started).toFixed(2));
    const validation = await validateVisibleRows(page, active);
    const underThreshold = latencyMs < 500;
    const passed = validation.ok && underThreshold;

    results.push({
      scenario: active.join("+"),
      field_count: active.length,
      latency_ms: latencyMs,
      under_500ms: underThreshold,
      passed,
      reason: validation.reason ?? null,
    });
  }

  await browser.close();

  const passedCount = results.filter((entry) => entry.passed).length;
  const report = {
    generated_at: new Date().toISOString(),
    app_url: appUrl,
    total_scenarios: results.length,
    passed_scenarios: passedCount,
    failed_scenarios: results.length - passedCount,
    all_passed: passedCount === results.length,
    scenarios: results,
  };

  const reportPath = path.resolve("tests/regression/search-combinations-report.json");
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.all_passed) {
    process.exitCode = 1;
  }
}

await main();
