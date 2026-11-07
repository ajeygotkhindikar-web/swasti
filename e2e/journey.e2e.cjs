/**
 * End-to-end user journeys through the real UI (Playwright).
 * Requires the API on :8000 and `vite preview` (or dev) on BASE_URL. Run: node e2e/journey.e2e.cjs
 */
const { chromium, devices } = require('playwright')
const assert = require('assert')
const BASE = process.env.BASE_URL || 'http://localhost:4173'

async function individualJourney(browser) {
  const ctx = await browser.newContext({ ...devices['Pixel 7'] }) // mobile viewport
  const p = await ctx.newPage()
  const errors = []; p.on('pageerror', (e) => errors.push(e.message))
  const email = `e2e${Date.now()}@example.com`
  await p.goto(BASE + '/register')
  await p.fill('#n', 'E2E Tester'); await p.fill('#e', email); await p.fill('#p', 'Passw0rd!')
  await p.check('input[required][type=checkbox]')
  await p.click('button:has-text("Create account")')
  await p.waitForURL(BASE + '/assessment')
  await p.click('button:has-text("Begin")')
  for (let step = 0; step < 14; step++) {
    const blocks = p.locator('fieldset.card')
    const n = await blocks.count()
    for (let i = 0; i < n; i++) await blocks.nth(i).locator('button[aria-pressed]').nth(step % 2 ? 3 : 2).click()
    if (step < 13) await p.click('button:has-text("Next")')
  }
  await p.click('button:has-text("Submit assessment (56/56)")')
  await p.waitForSelector('text=assessment saved')
  await p.click('a:has-text("View my 360° dashboard")')
  await p.waitForSelector('text=Your fourteen dimensions')
  assert.equal(await p.locator('article.card').count(), 14, '14 dimension cards')
  await p.waitForSelector('text=Top improvement priorities')
  // agents finish in background -> detail page shows agent analysis with evidence
  await p.goto(BASE + '/dashboard/PHY')
  await p.waitForSelector('text=Recommended actions (evidence-linked)', { timeout: 15000 })
  await p.click('button:has-text("Add to plan & habits")')
  await p.goto(BASE + '/habits')
  await p.waitForSelector('[aria-label^="Mark "]')
  await p.locator('[aria-label^="Mark "]').first().click()
  await p.waitForSelector('[aria-label^="Undo "]')
  const overflow = await p.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  assert.ok(overflow <= 0, 'no horizontal scroll on mobile')
  assert.deepEqual(errors, [])
  await ctx.close()
  console.log('✓ individual journey (register → 56-question assessment → dashboard → agent detail → plan → habit)')
}

async function privacyJourney(browser) {
  const ctx = await browser.newContext()
  const p = await ctx.newPage()
  await p.goto(BASE + '/login'); await p.fill('#email', 'admin@swasti.demo'); await p.fill('#pw', 'Demo@1234')
  await p.click('button:has-text("Sign in")'); await p.waitForURL(BASE + '/')
  await p.goto(BASE + '/dashboard') // admin is redirected away from individual dashboards
  await p.waitForURL(BASE + '/')
  const res = await p.evaluate(async () => (await fetch('/api/dashboard', { headers: { Authorization: 'Bearer ' + sessionStorage.getItem('swasti.token') } })).status)
  assert.equal(res, 403)
  await ctx.close()
  console.log('✓ admin cannot view individual wellness data')
}

;(async () => {
  const browser = await chromium.launch()
  try { await individualJourney(browser); await privacyJourney(browser) } finally { await browser.close() }
})().catch((e) => { console.error(e); process.exit(1) })
