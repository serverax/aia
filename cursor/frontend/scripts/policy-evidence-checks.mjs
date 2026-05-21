import { chromium } from 'playwright';

const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });

await page.goto('http://127.0.0.1:5173', { waitUntil: 'networkidle' });
await page.getByRole('button', { name: 'Dashboard' }).click();
await page.waitForTimeout(1500);

const matchedHeader = page.getByRole('heading', { name: 'Matched Policies' });
const rejectedHeader = page.getByRole('heading', { name: 'Rejected Policies' });
const viewPolicyButtons = page.getByRole('button', { name: 'View policy' });
const hasMatchedSection = await matchedHeader.isVisible();
const hasRejectedSection = await rejectedHeader.isVisible();
const matchedListItems = await page.locator('h3:has-text("Matched Policies") + ul li').count();
const rejectedListItems = await page.locator('h3:has-text("Rejected Policies") + ul li').count();
const viewPolicyButtonCount = await viewPolicyButtons.count();

await viewPolicyButtons.first().click();
await page.waitForTimeout(500);

const detailTitle = await page.locator('.policy-detail strong').first().textContent();
const detailSourceText = await page.locator('.policy-detail p').nth(1).textContent();
const detailOutcomeText = await page.locator('.policy-detail p').nth(2).textContent();
const detailRationaleText = await page.locator('.policy-detail p').nth(5).textContent();
const openSourceExists = (await page.locator('.policy-detail a:has-text("Open source")').count()) > 0;

await page.setViewportSize({ width: 480, height: 900 });
await page.waitForTimeout(700);
const overflow = await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth);

await browser.close();

console.log(
  JSON.stringify(
    {
      hasMatchedSection,
      hasRejectedSection,
      matchedListItems,
      rejectedListItems,
      viewPolicyButtonCount,
      detailTitle,
      detailSourceText,
      detailOutcomeText,
      detailRationaleText,
      openSourceExists,
      mobileOverflowDetected: overflow,
    },
    null,
    2,
  ),
);
