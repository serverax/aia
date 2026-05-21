import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.REGRESSION_APP_URL || "http://127.0.0.1:5173";

function percentile(values, p) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(p * sorted.length));
  return Number(sorted[index].toFixed(2));
}

async function openApprovals(page) {
  await page.goto(appUrl, { waitUntil: "networkidle" });
  await page.locator(".top-nav").getByRole("button", { name: "Approvals", exact: true }).click();
  await page.getByRole("heading", { name: "Approval Request UI" }).waitFor({ state: "visible", timeout: 10000 });
}

async function clearFilters(page) {
  await page.getByPlaceholder("Search requestor").fill("");
  await page.getByPlaceholder("Search policy ID/name").fill("");
  await page.getByPlaceholder("Search comments/text").fill("");
  await page.locator(".approval-search-grid select").first().selectOption("all");
  const dates = page.locator('.approval-search-grid input[type="date"]');
  await dates.nth(0).fill("");
  await dates.nth(1).fill("");
  await page.waitForTimeout(120);
}

async function openFirstVisibleDetail(page) {
  if ((await page.getByRole("button", { name: "Open", exact: true }).count()) === 0) {
    throw new Error("No visible Open button for current filtered view.");
  }
  const start = performance.now();
  await page.getByRole("button", { name: "Open", exact: true }).first().click();
  await page.getByRole("heading", { name: "Approval Detail" }).waitFor({ state: "visible", timeout: 3000 });
  await page.waitForTimeout(80);
  const elapsed = Number((performance.now() - start).toFixed(2));
  return elapsed;
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
  const scenarios = [];
  const openLatencies = [];

  await openApprovals(page);
  await clearFilters(page);
  await page.locator(".approval-queue-controls select").first().selectOption("completed");
  await page.waitForTimeout(120);

  // Scenario 1: Filtered policy -> explanation contract visible
  await page.getByPlaceholder("Search policy ID/name").fill("DOC_098");
  await page.waitForTimeout(120);
  const latencyOne = await openFirstVisibleDetail(page);
  openLatencies.push(latencyOne);
  await page.getByRole("button", { name: /Why this decision\?/, exact: false }).click();
  await page.waitForTimeout(80);
  const summaryText = await page.locator(".decision-explanation p").first().innerText();
  const clausesCount = await page.locator(".decision-explanation .approval-list li").count();
  const pathCount = await page.locator(".decision-path li").count();
  scenarios.push({
    scenario: "filtered item loads explanation payload structure",
    passed: summaryText.length > 10 && clausesCount >= 1 && pathCount >= 1 && latencyOne < 500,
    latency_ms: latencyOne,
    details: `summary=${summaryText.length}, clauses=${clausesCount}, path=${pathCount}`,
  });

  // Scenario 2: Confidence badge/band/score valid
  const confidenceText = await page.locator(".approval-detail-grid .pill[class*='confidence-']").first().innerText();
  const confidenceTitle = await page.locator(".approval-detail-grid .pill[class*='confidence-']").first().getAttribute("title");
  const scoreMatch = confidenceText.match(/\((\d+(\.\d+)?)\)/);
  const score = scoreMatch ? Number(scoreMatch[1]) : -1;
  const bandOk = /low|medium|high/.test(confidenceText.toLowerCase());
  scenarios.push({
    scenario: "confidence badge and factor tooltip render correctly",
    passed: bandOk && score >= 0 && score <= 1 && Boolean(confidenceTitle && confidenceTitle.length > 8),
    details: `badge=${confidenceText}`,
  });

  // Scenario 3: Guardrail checkbox appears for low confidence
  const guardrailVisible = (await page.locator(".guardrail-check input[type='checkbox']").count()) > 0;
  scenarios.push({
    scenario: "low confidence guardrail appears in filtered detail view",
    passed: guardrailVisible,
    details: `guardrailVisible=${guardrailVisible}`,
  });

  // Scenario 4: Guardrail blocks then allows approve
  const approveBefore = await page.getByRole("button", { name: "Approve", exact: true }).isDisabled();
  if (guardrailVisible) {
    await page.locator(".guardrail-check input[type='checkbox']").check();
    await page.waitForTimeout(80);
  }
  const approveAfter = await page.getByRole("button", { name: "Approve", exact: true }).isDisabled();
  scenarios.push({
    scenario: "guardrail requires explicit acknowledgement before approve",
    passed: approveBefore && !approveAfter,
    details: `before=${approveBefore}, after=${approveAfter}`,
  });

  // Scenario 5: Clause rationale and decision path headings present
  const rationaleVisible = await page.getByRole("heading", { name: "Clause rationale" }).isVisible();
  const decisionPathVisible = await page.getByRole("heading", { name: "Decision path" }).isVisible();
  scenarios.push({
    scenario: "explanation panel shows clause rationale and decision path",
    passed: rationaleVisible && decisionPathVisible,
    details: `rationale=${rationaleVisible}, path=${decisionPathVisible}`,
  });

  // Scenario 6: switching filtered items updates detail pane
  await clearFilters(page);
  await page.locator(".approval-queue-controls select").first().selectOption("waiting_others");
  await page.waitForTimeout(100);
  await page.locator(".approval-search-grid select").first().selectOption("pending");
  await page.waitForTimeout(120);
  const rows = page.locator(".approval-queue-row");
  const rowCount = await rows.count();
  let switched = false;
  let latencyTwo = 0;
  if (rowCount >= 2) {
    const firstTitle = await rows.nth(0).locator("strong").innerText();
    await rows.nth(0).getByRole("button", { name: "Open", exact: true }).click();
    await page.waitForTimeout(80);
    const detailFirst = await page.locator(".approval-detail-grid strong").first().innerText();

    const start = performance.now();
    await rows.nth(1).getByRole("button", { name: "Open", exact: true }).click();
    await page.waitForTimeout(90);
    latencyTwo = Number((performance.now() - start).toFixed(2));
    openLatencies.push(latencyTwo);
    const secondTitle = await rows.nth(1).locator("strong").innerText();
    const detailSecond = await page.locator(".approval-detail-grid strong").first().innerText();
    switched = firstTitle !== secondTitle && detailFirst !== detailSecond;
  }
  scenarios.push({
    scenario: "switching between filtered items updates detail pane",
    passed: switched && (latencyTwo === 0 || latencyTwo < 500),
    latency_ms: latencyTwo,
    details: `rowCount=${rowCount}, switched=${switched}`,
  });

  await browser.close();

  const passed = scenarios.filter((item) => item.passed).length;
  const report = {
    generated_at: new Date().toISOString(),
    app_url: appUrl,
    total_scenarios: scenarios.length,
    passed_scenarios: passed,
    failed_scenarios: scenarios.length - passed,
    all_passed: passed === scenarios.length,
    detail_open_latency_ms: {
      samples: openLatencies,
      p95: percentile(openLatencies, 0.95),
      threshold: 500,
      under_threshold: openLatencies.every((value) => value < 500),
    },
    scenarios,
  };

  const reportPath = path.resolve("tests/regression/explanation-in-filters-report.json");
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.all_passed || !report.detail_open_latency_ms.under_threshold) {
    process.exitCode = 1;
  }
}

await main();
