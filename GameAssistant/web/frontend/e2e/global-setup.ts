import { chromium, firefox, webkit, FullConfig } from '@playwright/test'
import * as fs from 'fs'
import * as path from 'path'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'
const ADMIN_USER = process.env.E2E_USER || 'admin'
const ADMIN_PASS = process.env.E2E_PASS || 'admin123'

interface BrowserConfig {
  browser: typeof chromium | typeof firefox | typeof webkit
  name: string
}

const BROWSERS: Record<string, BrowserConfig> = {
  chromium: { browser: chromium, name: 'chromium' },
  firefox: { browser: firefox, name: 'firefox' },
  webkit: { browser: webkit, name: 'webkit' },
  'mobile-chrome': { browser: chromium, name: 'mobile-chrome' },
}

async function login(page: any, browserName: string): Promise<void> {
  console.log(`Navigating to login page for ${browserName}...`)
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle' })

  // Additional wait for page to be fully loaded
  await page.waitForLoadState('domcontentloaded')

  // Fill login form
  console.log(`Filling login form for ${browserName}...`)
  await page.fill('input[placeholder="用户名"]', ADMIN_USER)
  await page.fill('input[placeholder="密码"]', ADMIN_PASS)

  // Click submit and wait for navigation
  console.log(`Submitting login for ${browserName}...`)
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle', timeout: 20000 }),
    page.click('button[type="submit"]')
  ])

  // Wait for localStorage to be updated (critical for Firefox/WebKit)
  await page.waitForFunction(() => {
    const token = localStorage.getItem('gameassistant_token')
    return token !== null && token !== ''
  }, { timeout: 15000 })

  // Additional wait for Vue/Pinia to process the token
  await page.waitForTimeout(1000)

  // Verify we're not on the login page anymore
  const currentUrl = page.url()
  if (currentUrl.includes('/login')) {
    throw new Error(`Login failed: still on login page (${currentUrl})`)
  }

  console.log(`Login successful for ${browserName}, redirected to: ${currentUrl}`)
}

async function getLocalStorageData(page: any): Promise<Record<string, string>> {
  return await page.evaluate(() => {
    const data: Record<string, string> = {}
    for (let i = 0; i < localStorage.length; i++) {
      const key = localStorage.key(i)
      if (key) {
        data[key] = localStorage.getItem(key) || ''
      }
    }
    return data
  })
}

async function setLocalStorageData(page: any, data: Record<string, string>): Promise<void> {
  await page.evaluate((items) => {
    for (const [key, value] of Object.entries(items)) {
      localStorage.setItem(key, value)
    }
  }, data)
}

async function globalSetup(_config: FullConfig) {
  const authDir = path.join(__dirname, '.auth')

  // Ensure auth directory exists
  if (!fs.existsSync(authDir)) {
    fs.mkdirSync(authDir, { recursive: true })
  }

  // Create auth state for each browser
  for (const [browserName, { browser }] of Object.entries(BROWSERS)) {
    const authFile = path.join(authDir, `${browserName}.json`)

    // Skip if already authenticated (for faster local dev)
    if (fs.existsSync(authFile) && !process.env.CI) {
      console.log(`Auth state for ${browserName} already exists, skipping...`)
      continue
    }

    let browserInstance = null
    try {
      browserInstance = await browser.launch()
    } catch (error: any) {
      // Browser not installed, skip but log warning
      if (error.message?.includes("Executable doesn't exist")) {
        console.warn(`⚠ Browser ${browserName} not installed, skipping auth generation. Run 'npx playwright install ${browserName}' to enable.`)
        continue
      }
      throw error
    }

    const context = await browserInstance.newContext()
    const page = await context.newPage()

    try {
      await login(page, browserName)

      // Get localStorage data after login (contains JWT token)
      const localStorageData = await getLocalStorageData(page)

      // Save cookies from context
      const cookies = await context.cookies()

      // Create storage state with both cookies and localStorage
      const storageState = {
        cookies: cookies.map(cookie => ({
          name: cookie.name,
          value: cookie.value,
          domain: cookie.domain,
          path: cookie.path,
          expires: cookie.expires,
          httpOnly: cookie.httpOnly,
          secure: cookie.secure,
          sameSite: cookie.sameSite,
        })),
        origins: [
          {
            origin: new URL(BASE_URL).origin,
            localStorage: Object.entries(localStorageData).map(([name, value]) => ({
              name,
              value,
            })),
          },
        ],
      }

      fs.writeFileSync(authFile, JSON.stringify(storageState, null, 2))
      console.log(`Auth state saved for ${browserName}: ${authFile}`)
    } catch (error) {
      console.error(`Login failed for ${browserName}:`, error)
      // Continue with other browsers even if one fails
    } finally {
      await browserInstance.close()
    }
  }
}

export default globalSetup
