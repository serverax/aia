import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium } from 'playwright';

const outDir = path.resolve('approval-evidence');
await fs.mkdir(outDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1366, height: 900 }, acceptDownloads: true });
const page = await context.newPage();

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.locator('.top-nav').getByRole('button', { name: 'Approvals', exact: true }).click();
await page.waitForTimeout(1200);

await page.screenshot({
  path: path.join(outDir, 'approval-desktop.png'),
  fullPage: true,
});

const requestFormPresent = await page.getByRole('heading', { name: 'Create Approval Request' }).isVisible();
const templatePickerPresent = await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) select')
  .first()
  .isVisible();
await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) select')
  .first()
  .selectOption('exception-fastlane');
await page.waitForTimeout(250);
const requestTypeValue = await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) .approval-form-block')
  .nth(1)
  .locator('select')
  .inputValue();
const titleValue = await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) .approval-form-block')
  .nth(2)
  .locator('input')
  .inputValue();
const reviewerTagCount = await page
  .locator('section.approval-card:has(h2:has-text("Create Approval Request")) .reviewer-tags li')
  .count();
const templateDefaultsApplied = requestTypeValue === 'exception' && titleValue.includes('Security Exception') && reviewerTagCount >= 2;
const queueFilterOptions = await page.locator('.approval-queue-controls select').first().locator('option').count();
const requestorSearchPresent = await page.getByPlaceholder('Search requestor').isVisible();
const policySearchPresent = await page.getByPlaceholder('Search policy ID/name').isVisible();
const commentSearchPresent = await page.getByPlaceholder('Search comments/text').isVisible();
const outcomeFilterPresent = (await page.locator('.approval-search-grid select').count()) > 0;
const dateRangePresent = (await page.locator('.approval-search-grid input[type="date"]').count()) === 2;
const savedPresetsPresent = (await page.locator('.preset-list li').count()) > 0;

await page.getByPlaceholder('Preset name').fill('Smoke Preset');
await page.getByRole('button', { name: 'Save Preset' }).click();
await page.waitForTimeout(250);
const savedPresetCreated = await page.getByRole('button', { name: 'Smoke Preset' }).count();
await page.reload({ waitUntil: 'networkidle' });
await page.locator('.top-nav').getByRole('button', { name: 'Approvals', exact: true }).click();
await page.waitForTimeout(400);
const presetPersistenceWorks = (await page.getByRole('button', { name: 'Smoke Preset' }).count()) > 0;

await page.getByRole('button', { name: 'Smoke Preset' }).first().click();
await page.waitForTimeout(150);
if ((await page.getByRole('button', { name: 'Delete' }).count()) > 0) {
  await page.getByRole('button', { name: 'Delete' }).first().click();
}

const bulkSelectAllPresent = await page.locator('.bulk-select-all input[type="checkbox"]').count();
const bulkActionButtonsPresent = await page.locator('.approval-bulk-actions button').count();
await page.locator('.bulk-select-all input[type="checkbox"]').check();
await page.getByRole('button', { name: 'Bulk Reject' }).click();
await page.waitForTimeout(700);
const bulkActionOperational = await page
  .locator('.approval-card .success')
  .allTextContents()
  .then((messages) => messages.some((message) => message.includes('Bulk reject applied')));

await page.locator('.approval-queue-controls select').first().selectOption('completed');
await page.waitForTimeout(400);
if ((await page.getByRole('button', { name: 'Open' }).count()) === 0) {
  await page.locator('.approval-queue-controls select').first().selectOption('waiting_others');
  await page.waitForTimeout(400);
}
await page.getByRole('button', { name: 'Open' }).first().click();
await page.waitForTimeout(600);
const detailViewOpenable = await page.getByRole('heading', { name: 'Approval Detail' }).isVisible();
const approvalButtonsPresent = await page
  .locator('.approval-actions button')
  .count();
const feedbackCommentFieldPresent = await page.locator('.approval-card textarea').count().then((count) => count > 0);
const metricsDisplayPresent = await page.getByRole('heading', { name: 'Approval Metrics' }).isVisible();
const explanationTogglePresent = await page.getByRole('button', { name: /Why this decision\?/ }).isVisible();
await page.getByRole('button', { name: /Why this decision\?/ }).click();
await page.waitForTimeout(300);
const explanationPanelVisible = await page.locator('.decision-explanation').isVisible();
const clauseRationaleVisible = await page.getByRole('heading', { name: 'Clause rationale' }).isVisible();
const decisionPathVisible = await page.getByRole('heading', { name: 'Decision path' }).isVisible();
const confidenceBadgePresent = await page.locator('.approval-detail-grid .pill[class*="confidence-"]').count();
const confidenceTooltipPresent = await page
  .locator('.approval-detail-grid .pill[class*="confidence-"]')
  .first()
  .getAttribute('title')
  .then((value) => Boolean(value && value.length > 10));

await page.locator('.approval-queue-controls select').first().selectOption('completed');
await page.waitForTimeout(400);
await page.getByRole('button', { name: 'Open' }).first().click();
await page.waitForTimeout(450);
const guardrailCheckboxPresent = await page.locator('.guardrail-check input[type="checkbox"]').count();
const approveDisabledBeforeAck = await page.getByRole('button', { name: 'Approve', exact: true }).isDisabled();
await page.locator('.guardrail-check input[type="checkbox"]').check();
await page.waitForTimeout(250);
const approveEnabledAfterAck = !(await page.getByRole('button', { name: 'Approve', exact: true }).isDisabled());
const auditTimelinePresent = await page.getByRole('heading', { name: 'Audit Trail Timeline' }).isVisible();
const auditFilterCount = await page.locator('.audit-filters select').count();
const dateRangeInputsPresent = await page.locator('.audit-date-range input[type="date"]').count();
const exportButtonsPresent = await page.locator('.audit-export-row button').count();
const retentionPolicyPresent = await page.getByRole('heading', { name: 'Retention Policy' }).isVisible();
const initialAuditRows = await page.locator('.audit-timeline li').count();

await page
  .locator('section.approval-card:has(h2:has-text("Approval Detail")) textarea')
  .fill('Escalating for executive override evidence');
await page.getByRole('button', { name: 'Escalate', exact: true }).click();
await page.waitForTimeout(700);

const updatedAuditRows = await page.locator('.audit-timeline li').count();
const auditUpdatedAfterAction = updatedAuditRows > initialAuditRows;
await page.locator('.audit-filters select').nth(2).selectOption('overrode');
await page.waitForTimeout(250);
const filteredOverrideRows = await page.locator('.audit-timeline li').count();
const auditFilterOperational = filteredOverrideRows >= 1;

await page.locator('.audit-date-range input[type="date"]').first().fill('2099-01-01');
await page.waitForTimeout(450);
const dateRangeQueryOperational = (await page.locator('.audit-timeline li').count()) === 0;
await page.locator('.audit-date-range input[type="date"]').first().fill('');
await page.waitForTimeout(450);

const [csvDownload] = await Promise.all([
  page.waitForEvent('download'),
  page.getByRole('button', { name: 'Export CSV' }).click(),
]);
const [jsonDownload] = await Promise.all([
  page.waitForEvent('download'),
  page.getByRole('button', { name: 'Export JSON' }).click(),
]);
const exportDownloadsWorking = Boolean(csvDownload.suggestedFilename() && jsonDownload.suggestedFilename());

await page.screenshot({
  path: path.join(outDir, 'approval-detail-desktop.png'),
  fullPage: true,
});

await page.setViewportSize({ width: 480, height: 900 });
await page.waitForTimeout(800);
const mobileOverflowDetected = await page.evaluate(
  () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
);

await page.screenshot({
  path: path.join(outDir, 'approval-mobile-480.png'),
  fullPage: true,
});

const validation = {
  requestFormPresent,
  requestorSearchPresent,
  dateRangePresent,
  outcomeFilterPresent,
  policySearchPresent,
  commentSearchPresent,
  savedPresetsPresent,
  presetPersistenceWorks,
  savedPresetCreated,
  templatePickerPresent,
  templateDefaultsApplied,
  queueFiltersPresent: queueFilterOptions,
  bulkSelectAllPresent,
  bulkActionButtonsPresent,
  bulkActionOperational,
  detailViewOpenable,
  approvalButtonsPresent,
  feedbackCommentFieldPresent,
  metricsDisplayPresent,
  explanationTogglePresent,
  explanationPanelVisible,
  clauseRationaleVisible,
  decisionPathVisible,
  confidenceBadgePresent,
  confidenceTooltipPresent,
  guardrailCheckboxPresent,
  approveDisabledBeforeAck,
  approveEnabledAfterAck,
  auditTimelinePresent,
  auditFilterCount,
  dateRangeInputsPresent,
  exportButtonsPresent,
  retentionPolicyPresent,
  auditUpdatedAfterAction,
  auditFilterOperational,
  dateRangeQueryOperational,
  exportDownloadsWorking,
  mobileOverflowDetected,
};

await fs.writeFile(path.resolve('approval-validation.json'), JSON.stringify(validation, null, 2), 'utf-8');
console.log(JSON.stringify(validation, null, 2));

await context.close();
await browser.close();
