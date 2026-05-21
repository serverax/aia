import fs from "node:fs/promises";
import path from "node:path";

const baseUrl =
  process.env.LIVE_BACKEND_BASE_URL ||
  process.env.VITE_ORCHESTRATOR_BASE_URL ||
  "http://127.0.0.1:8080";
const evaluatePath = process.env.LIVE_EVALUATE_PATH || "/evaluate";
const approvalsPath = process.env.LIVE_APPROVALS_PATH || "/api/v1/approval-requests";

async function fetchWithTimeout(url, options = {}, timeoutMs = 10000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    return response;
  } finally {
    clearTimeout(timer);
  }
}

async function main() {
  const allowGracefulFallback = process.env.ALLOW_GRACEFUL_FALLBACK === "true";
  const report = {
    started_at: new Date().toISOString(),
    base_url: baseUrl,
    endpoints: {
      evaluate: `${baseUrl}${evaluatePath}`,
      approvals: `${baseUrl}${approvalsPath}`,
    },
    checks: {
      evaluate_status_ok: false,
      evaluate_response_shape_ok: false,
      evaluate_under_2s: false,
      approvals_status_ok: false,
      approvals_shape_ok: false,
      explanation_present: false,
      confidence_present: false,
    },
    latencies_ms: {},
    notes: [],
    graceful_fallback_mode: allowGracefulFallback,
  };

  try {
    const evaluatePayload = {
      request_type: "policy_change",
      title: "Live Integration Smoke Check",
      description: "Validate explanation and confidence payloads from live backend.",
      requestor: "integration-smoke@synthetic.io",
      deadline: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      approval_strategy: "all_must_approve",
      metadata: { risk_score: 6.2 },
    };

    const evalStart = performance.now();
    const evalResponse = await fetchWithTimeout(
      `${baseUrl}${evaluatePath}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(evaluatePayload),
      },
      10000,
    );
    const evalEnd = performance.now();
    const evaluateLatency = Number((evalEnd - evalStart).toFixed(2));
    report.latencies_ms.evaluate = evaluateLatency;
    report.checks.evaluate_under_2s = evaluateLatency < 2000;
    report.checks.evaluate_status_ok = evalResponse.ok;

    const evalBody = await evalResponse.json().catch(() => null);
    if (evalBody && typeof evalBody === "object") {
      const hasObjectLikeContent = Object.keys(evalBody).length > 0;
      report.checks.evaluate_response_shape_ok = hasObjectLikeContent;
      if (!hasObjectLikeContent) {
        report.notes.push("Evaluate endpoint returned empty object.");
      }
    } else {
      report.notes.push("Evaluate endpoint did not return JSON object.");
    }

    const approvalsStart = performance.now();
    const approvalsResponse = await fetchWithTimeout(`${baseUrl}${approvalsPath}`, {}, 10000);
    const approvalsEnd = performance.now();
    const approvalsLatency = Number((approvalsEnd - approvalsStart).toFixed(2));
    report.latencies_ms.approvals = approvalsLatency;
    report.checks.approvals_status_ok = approvalsResponse.ok;

    const approvalsBody = await approvalsResponse.json().catch(() => null);
    const approvalsArray = Array.isArray(approvalsBody) ? approvalsBody : [];
    report.checks.approvals_shape_ok = Array.isArray(approvalsBody);

    const withExplanation = approvalsArray.find(
      (item) => item && typeof item === "object" && item.decision_explanation,
    );
    const withConfidence = approvalsArray.find(
      (item) => item && typeof item === "object" && item.recommendation_confidence,
    );
    report.checks.explanation_present = Boolean(withExplanation);
    report.checks.confidence_present = Boolean(withConfidence);

    if (!report.checks.explanation_present) {
      report.notes.push("No approval request included decision_explanation.");
    }
    if (!report.checks.confidence_present) {
      report.notes.push("No approval request included recommendation_confidence.");
    }
  } catch (error) {
    report.notes.push(`Smoke test error: ${error instanceof Error ? error.message : String(error)}`);
  }

  report.finished_at = new Date().toISOString();
  report.passed = Object.values(report.checks).every(Boolean);
  report.graceful_fallback_ready = !report.passed && allowGracefulFallback;

  const outPath = path.resolve("integration-live-backend-report.json");
  await fs.writeFile(outPath, JSON.stringify(report, null, 2), "utf-8");
  console.log(JSON.stringify(report, null, 2));

  if (!report.passed && !allowGracefulFallback) {
    process.exitCode = 1;
  }
}

await main();
