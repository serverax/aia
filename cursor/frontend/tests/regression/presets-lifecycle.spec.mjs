import fs from "node:fs/promises";
import path from "node:path";
import { chromium } from "playwright";

const appUrl = process.env.REGRESSION_APP_URL || "http://127.0.0.1:5173";

function median(values) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  if (sorted.length % 2 === 0) return Number(((sorted[mid - 1] + sorted[mid]) / 2).toFixed(2));
  return Number(sorted[mid].toFixed(2));
}

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

async function applyPresetAndMeasure(page, presetName) {
  const start = performance.now();
  await page.getByRole("button", { name: presetName, exact: true }).click();
  await page.waitForTimeout(150);
  const end = performance.now();
  return Number((end - start).toFixed(2));
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
  const page = await context.newPage();
  const results = [];
  const latencies = [];

  await openApprovals(page);

  // Built-in preset scenarios (4)
  {
    const latency = await applyPresetAndMeasure(page, "My Pending Approvals");
    latencies.push(latency);
    const outcomeValue = await page.locator(".approval-search-grid select").first().inputValue();
    results.push({
      scenario: "built-in my pending approvals",
      passed: outcomeValue === "pending" && latency < 500,
      latency_ms: latency,
      details: `outcome=${outcomeValue}`,
    });
  }
  {
    const latency = await applyPresetAndMeasure(page, "Escalated Items");
    latencies.push(latency);
    const outcomeValue = await page.locator(".approval-search-grid select").first().inputValue();
    const commentValue = await page.getByPlaceholder("Search comments/text").inputValue();
    results.push({
      scenario: "built-in escalated items",
      passed: outcomeValue === "escalated" && commentValue.toLowerCase().includes("escalated") && latency < 500,
      latency_ms: latency,
      details: `outcome=${outcomeValue}, comment=${commentValue}`,
    });
  }
  {
    const latency = await applyPresetAndMeasure(page, "Last 24 Hours");
    latencies.push(latency);
    const dates = page.locator('.approval-search-grid input[type="date"]');
    const fromValue = await dates.nth(0).inputValue();
    const toValue = await dates.nth(1).inputValue();
    results.push({
      scenario: "built-in last 24 hours",
      passed: Boolean(fromValue) && Boolean(toValue) && latency < 500,
      latency_ms: latency,
      details: `from=${fromValue}, to=${toValue}`,
    });
  }
  {
    const latency = await applyPresetAndMeasure(page, "High Confidence");
    latencies.push(latency);
    const commentValue = await page.getByPlaceholder("Search comments/text").inputValue();
    results.push({
      scenario: "built-in high confidence",
      passed: commentValue.toLowerCase().includes("positive") && latency < 500,
      latency_ms: latency,
      details: `comment=${commentValue}`,
    });
  }

  const customPresetName = `WS2-Custom-${Date.now()}`;
  const modifiedPresetName = `${customPresetName}-Updated`;

  // Save custom preset
  {
    await page.getByPlaceholder("Search requestor").fill("editor@synthetic.io");
    await page.getByPlaceholder("Search policy ID/name").fill("DOC_777");
    await page.getByPlaceholder("Search comments/text").fill("classification");
    await page.locator(".approval-search-grid select").first().selectOption("approved");
    await page.getByPlaceholder("Preset name").fill(customPresetName);
    const start = performance.now();
    await page.getByRole("button", { name: "Save Preset", exact: true }).click();
    await page.waitForTimeout(150);
    const latency = Number((performance.now() - start).toFixed(2));
    latencies.push(latency);
    const exists = (await page.getByRole("button", { name: customPresetName, exact: true }).count()) > 0;
    results.push({
      scenario: "custom save preset",
      passed: exists && latency < 500,
      latency_ms: latency,
      details: `created=${exists}`,
    });
  }

  // Apply custom preset
  {
    const latency = await applyPresetAndMeasure(page, customPresetName);
    latencies.push(latency);
    const requestorValue = await page.getByPlaceholder("Search requestor").inputValue();
    const outcomeValue = await page.locator(".approval-search-grid select").first().inputValue();
    results.push({
      scenario: "custom apply preset",
      passed: requestorValue === "editor@synthetic.io" && outcomeValue === "approved" && latency < 500,
      latency_ms: latency,
      details: `requestor=${requestorValue}, outcome=${outcomeValue}`,
    });
  }

  // Modify preset by deleting and recreating with updated filter
  {
    const presetRow = page.locator(".preset-list li").filter({ hasText: customPresetName }).first();
    await presetRow.getByRole("button", { name: "Delete", exact: true }).click();
    await page.waitForTimeout(100);
    await page.getByPlaceholder("Search requestor").fill("analyst@synthetic.io");
    await page.getByPlaceholder("Preset name").fill(modifiedPresetName);
    const start = performance.now();
    await page.getByRole("button", { name: "Save Preset", exact: true }).click();
    await page.waitForTimeout(150);
    const latency = Number((performance.now() - start).toFixed(2));
    latencies.push(latency);
    const exists = (await page.getByRole("button", { name: modifiedPresetName, exact: true }).count()) > 0;
    results.push({
      scenario: "custom modify preset",
      passed: exists && latency < 500,
      latency_ms: latency,
      details: `updated=${exists}`,
    });
  }

  // Delete custom preset
  {
    const start = performance.now();
    const presetRow = page.locator(".preset-list li").filter({ hasText: modifiedPresetName }).first();
    await presetRow.getByRole("button", { name: "Delete", exact: true }).click();
    await page.waitForTimeout(120);
    const latency = Number((performance.now() - start).toFixed(2));
    latencies.push(latency);
    const stillExists = (await page.getByRole("button", { name: modifiedPresetName, exact: true }).count()) > 0;
    results.push({
      scenario: "custom delete preset",
      passed: !stillExists && latency < 500,
      latency_ms: latency,
      details: `exists_after_delete=${stillExists}`,
    });
  }

  // Persistence test (save new custom preset, reload, verify present + applies)
  {
    const persistentName = `WS2-Persist-${Date.now()}`;
    await page.getByPlaceholder("Search requestor").fill("compliance_officer@synthetic.io");
    await page.getByPlaceholder("Preset name").fill(persistentName);
    await page.getByRole("button", { name: "Save Preset", exact: true }).click();
    await page.waitForTimeout(120);
    await page.reload({ waitUntil: "networkidle" });
    await page.locator(".top-nav").getByRole("button", { name: "Approvals", exact: true }).click();
    await page.waitForTimeout(300);
    const existsAfterReload = (await page.getByRole("button", { name: persistentName, exact: true }).count()) > 0;
    const latency = await applyPresetAndMeasure(page, persistentName);
    latencies.push(latency);
    const requestorValue = await page.getByPlaceholder("Search requestor").inputValue();
    results.push({
      scenario: "preset persistence across reload",
      passed: existsAfterReload && requestorValue === "compliance_officer@synthetic.io" && latency < 500,
      latency_ms: latency,
      details: `exists=${existsAfterReload}, requestor=${requestorValue}`,
    });
  }

  await context.close();
  await browser.close();

  const passed = results.filter((item) => item.passed).length;
  const report = {
    generated_at: new Date().toISOString(),
    app_url: appUrl,
    total_scenarios: results.length,
    passed_scenarios: passed,
    failed_scenarios: results.length - passed,
    all_passed: passed === results.length,
    latency_summary_ms: {
      p50: median(latencies),
      p95: percentile(latencies, 0.95),
      max: Number(Math.max(...latencies).toFixed(2)),
      threshold: 500,
      all_under_threshold: latencies.every((value) => value < 500),
    },
    scenarios: results,
  };

  const outPath = path.resolve("tests/regression/presets-lifecycle-report.json");
  await fs.writeFile(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.all_passed || !report.latency_summary_ms.all_under_threshold) {
    process.exitCode = 1;
  }
}

await main();
