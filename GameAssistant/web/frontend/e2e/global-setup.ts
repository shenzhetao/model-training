import { chromium, FullConfig } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'
const ADMIN_USER = process.env.E2E_USER || 'admin'
const ADMIN_PASS = process.env.E2E_PASS || 'admin123'

async function globalSetup(_config: FullConfig) {
  const browser = await chromium.launch()
  const context = await browser.newContext()
  const page = await context.newPage()

  await page.goto(`${BASE_URL}/login`)

  // Fill login form
  await page.fill('input[placeholder="用户名"]', ADMIN_USER)
  await page.fill('input[placeholder="密码"]', ADMIN_PASS)
  await page.click('button[type="submit"]')

  // Wait for redirect after login
  await page.waitForURL(url => !url.pathname.includes('/login'), { timeout: 15000 })

  // Save auth state
  await context.storageState({ path: './playwright/.auth/user.json' })

  await browser.close()
  console.log('Global setup complete — auth state saved.')
}

export default globalSetup
