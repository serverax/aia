import fs from 'node:fs/promises'
import path from 'node:path'
import { chromium, firefox, webkit } from 'playwright'

const outDir = path.resolve('dashboard-evidence')
const appUrl = process.env.DASHBOARD_UI_URL ?? 'http://127.0.0.1:5174'
await fs.mkdir(outDir, { recursive: true })

const targets = [
  { name: 'chromium', launcher: chromium },
  { name: 'firefox', launcher: firefox },
  { name: 'webkit', launcher: webkit },
]

const results = []

for (const target of targets) {
  let browser
  try {
    browser = await target.launcher.launch({ headless: true })
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } })
    const page = await context.newPage()

    const start = performance.now()
    await page.goto(appUrl, { waitUntil: 'networkidle' })
    await page.getByRole('heading', { name: 'Glass Box Dashboard' }).waitFor({ state: 'visible', timeout: 10000 })
    const loadMs = Number((performance.now() - start).toFixed(2))

    const overviewVisible = await page.getByRole('heading', { name: 'Workflow Overview' }).isVisible()
    const activityVisible = await page.getByRole('heading', { name: 'Recent Activity' }).isVisible()
    const metricsVisible = await page.getByRole('heading', { name: 'Realtime Metrics' }).isVisible()

    await page.screenshot({
      path: path.join(outDir, `dashboard-${target.name}-desktop.png`),
      fullPage: true,
    })

    await page.setViewportSize({ width: 430, height: 900 })
    await page.waitForTimeout(200)
    const mobileOverflow = await page.evaluate(
      () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
    )
    await page.screenshot({
      path: path.join(outDir, `dashboard-${target.name}-mobile.png`),
      fullPage: true,
    })

    results.push({
      browser: target.name,
      available: true,
      load_ms: loadMs,
      overview_visible: overviewVisible,
      activity_visible: activityVisible,
      metrics_visible: metricsVisible,
      mobile_overflow: mobileOverflow,
    })

    await context.close()
  } catch (error) {
    results.push({
      browser: target.name,
      available: false,
      error: error instanceof Error ? error.message : String(error),
    })
  } finally {
    await browser?.close()
  }
}

await fs.writeFile(path.resolve('dashboard-ui-validation.json'), JSON.stringify(results, null, 2), 'utf-8')
console.log(JSON.stringify(results, null, 2))
