import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.REGRESSION_APP_URL || "http://127.0.0.1:5173";

async function openApprovals(page) {
  await page.goto(appUrl, { waitUntil: "networkidle" });
  await page.locator(".top-nav").getByRole("button", { name: "Approvals", exact: true }).click();
  await page.getByRole("heading", { name: "Approval Request UI" }).waitFor({ state: "visible", timeout: 10000 });
}

async function setOutcomeFilter(page, outcome) {
  await page.locator(".approval-search-grid select").first().selectOption(outcome);
  await page.waitForTimeout(120);
}

async function clearSearchFilters(page) {
  await page.getByPlaceholder("Search requestor").fill("");
  await page.getByPlaceholder("Search policy ID/name").fill("");
  await page.getByPlaceholder("Search comments/text").fill("");
  const dates = page.locator('.approval-search-grid input[type="date"]');
  await dates.nth(0).fill("");
  await dates.nth(1).fill("");
}

async function getVisibleQueueRows(page) {
  const rows = page.locator(".approval-queue-row");
  const count = await rows.count();
  const entries = [];
  for (let i = 0; i < count; i += 1) {
    const row = rows.nth(i);
    const title = (await row.locator("strong").first().innerText()).trim();
    entries.push({ index: i, title });
  }
  return entries;
}

async function runBulkScenario(action) {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  await openApprovals(page);
  await clearSearchFilters(page);
  await setOutcomeFilter(page, "pending");

  const beforeRows = await getVisibleQueueRows(page);
  const beforeCount = beforeRows.length;
  const auditCountBefore = await page.locator(".audit-timeline li").count();

  const selectedByCheckbox = await page.locator(".bulk-select-all input[type='checkbox']").isVisible();
  if (selectedByCheckbox) {
    await page.locator(".bulk-select-all input[type='checkbox']").check();
  }

  const selectedText = await page.locator(".approval-bulk-bar span").innerText();
  const selectedCount = Number((selectedText.match(/\d+/) || ["0"])[0]);

  const actionButtonName =
    action === "approve" ? "Bulk Approve" : action === "reject" ? "Bulk Reject" : "Bulk Escalate";

  const started = performance.now();
  await page.getByRole("button", { name: actionButtonName, exact: true }).click();
  await page.waitForTimeout(180);
  const latencyMs = Number((performance.now() - started).toFixed(2));

  const statusMessage = await page.locator(".approval-card .success").first().innerText();
  const actionedCountFromMessage = Number((statusMessage.match(/\d+/) || ["0"])[0]);
  const afterPendingRows = await getVisibleQueueRows(page);
  const auditCountAfter = await page.locator(".audit-timeline li").count();
  const selectedAfterText = await page.locator(".approval-bulk-bar span").innerText();
  const selectedAfterCount = Number((selectedAfterText.match(/\d+/) || ["0"])[0]);

  // Verify only filtered subset changed by checking acted titles appear in expected result state.
  const actedTitles = beforeRows.map((row) => row.title);
  let targetedStateVerified = false;
  if (action === "approve") {
    await setOutcomeFilter(page, "approved");
    const approvedTitles = (await getVisibleQueueRows(page)).map((row) => row.title);
    targetedStateVerified = actedTitles.every((title) => approvedTitles.includes(title));
  } else if (action === "reject") {
    await setOutcomeFilter(page, "rejected");
    const rejectedTitles = (await getVisibleQueueRows(page)).map((row) => row.title);
    targetedStateVerified = actedTitles.every((title) => rejectedTitles.includes(title));
  } else {
    await setOutcomeFilter(page, "escalated");
    const escalatedTitles = (await getVisibleQueueRows(page)).map((row) => row.title);
    targetedStateVerified = actedTitles.every((title) => escalatedTitles.includes(title));
  }

  await browser.close();

  return {
    action,
    beforeCount,
    selectedCount,
    latencyMs,
    under500ms: latencyMs < 500,
    statusMessage,
    actionedCountFromMessage,
    pendingReduced: afterPendingRows.length <= Math.max(0, beforeCount - selectedCount),
    auditUpdated: auditCountAfter >= auditCountBefore + selectedCount,
    selectionReset: selectedAfterCount === 0,
    targetedStateVerified,
  };
}

async function main() {
  const scenarios = [];

  // Scenario 1 + 2 baseline checks on pending filter and select-all match.
  {
    const browser = await chromium.launch({ headless: true });
    const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
    await openApprovals(page);
    await clearSearchFilters(page);
    await setOutcomeFilter(page, "pending");
    const visible = await getVisibleQueueRows(page);
    await page.locator(".bulk-select-all input[type='checkbox']").check();
    const selectedText = await page.locator(".approval-bulk-bar span").innerText();
    const selectedCount = Number((selectedText.match(/\d+/) || ["0"])[0]);
    scenarios.push({
      scenario: "filtered pending view returns rows",
      passed: visible.length > 0,
      details: `visible=${visible.length}`,
    });
    scenarios.push({
      scenario: "select all visible matches filtered count",
      passed: selectedCount === visible.length,
      details: `selected=${selectedCount}, visible=${visible.length}`,
    });
    await browser.close();
  }

  const approveRun = await runBulkScenario("approve");
  scenarios.push({
    scenario: "bulk approve applies only filtered subset",
    passed:
      approveRun.pendingReduced &&
      approveRun.actionedCountFromMessage === approveRun.selectedCount &&
      approveRun.under500ms,
    latency_ms: approveRun.latencyMs,
    details: `reduced=${approveRun.pendingReduced}, actioned=${approveRun.actionedCountFromMessage}/${approveRun.selectedCount}`,
  });
  scenarios.push({
    scenario: "bulk approve audit updated per selected item",
    passed: approveRun.auditUpdated,
    latency_ms: approveRun.latencyMs,
    details: `auditUpdated=${approveRun.auditUpdated}, selected=${approveRun.selectedCount}`,
  });
  scenarios.push({
    scenario: "bulk approve queue refresh resets selection",
    passed: approveRun.selectionReset && approveRun.under500ms,
    latency_ms: approveRun.latencyMs,
    details: `selectionReset=${approveRun.selectionReset}, under500=${approveRun.under500ms}`,
  });

  const rejectRun = await runBulkScenario("reject");
  scenarios.push({
    scenario: "bulk reject applies only filtered subset",
    passed:
      rejectRun.pendingReduced &&
      rejectRun.actionedCountFromMessage === rejectRun.selectedCount &&
      rejectRun.under500ms,
    latency_ms: rejectRun.latencyMs,
    details: `reduced=${rejectRun.pendingReduced}, actioned=${rejectRun.actionedCountFromMessage}/${rejectRun.selectedCount}`,
  });

  const escalateRun = await runBulkScenario("escalate");
  scenarios.push({
    scenario: "bulk escalate applies only filtered subset",
    passed:
      escalateRun.targetedStateVerified &&
      escalateRun.actionedCountFromMessage === escalateRun.selectedCount &&
      escalateRun.under500ms,
    latency_ms: escalateRun.latencyMs,
    details: `targeted=${escalateRun.targetedStateVerified}, actioned=${escalateRun.actionedCountFromMessage}/${escalateRun.selectedCount}`,
  });

  const passed = scenarios.filter((item) => item.passed).length;
  const report = {
    generated_at: new Date().toISOString(),
    app_url: appUrl,
    total_scenarios: scenarios.length,
    passed_scenarios: passed,
    failed_scenarios: scenarios.length - passed,
    all_passed: passed === scenarios.length,
    scenarios,
  };

  const reportPath = path.resolve("tests/regression/bulk-with-filters-report.json");
  await fs.writeFile(reportPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.all_passed) {
    process.exitCode = 1;
  }
}

await main();
