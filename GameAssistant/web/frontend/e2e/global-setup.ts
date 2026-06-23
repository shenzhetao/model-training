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

/**
 * 等待特定元素出现
 */
async function waitForElement(page: any, selector: string, timeout: number = 10000): Promise<boolean> {
  try {
    await page.waitForSelector(selector, { state: 'visible', timeout })
    return true
  } catch {
    return false
  }
}

/**
 * 等待页面 URL 变化
 */
async function waitForUrlChange(page: any, expectedPattern: RegExp, timeout: number = 20000): Promise<boolean> {
  const startTime = Date.now()
  while (Date.now() - startTime < timeout) {
    const url = page.url()
    if (expectedPattern.test(url)) {
      return true
    }
    await page.waitForTimeout(500)
  }
  return false
}

async function login(page: any, browserName: string): Promise<void> {
  console.log(`Navigating to login page for ${browserName}...`)
  
  // 导航到登录页
  await page.goto(`${BASE_URL}/login`, { waitUntil: 'networkidle', timeout: 30000 })
  
  // 等待 DOM 加载完成
  await page.waitForLoadState('domcontentloaded')
  
  // 等待登录表单出现（更健壮的等待机制）
  const formSelector = 'input[placeholder="用户名"]'
  const formVisible = await waitForElement(page, formSelector, 15000)
  if (!formVisible) {
    throw new Error(`Login form not found for ${browserName}`)
  }

  // 填充登录表单
  console.log(`Filling login form for ${browserName}...`)
  await page.fill('input[placeholder="用户名"]', ADMIN_USER)
  await page.fill('input[placeholder="密码"]', ADMIN_PASS)

  // 点击提交按钮
  console.log(`Submitting login for ${browserName}...`)
  
  // 使用更可靠的点击和导航等待方式
  await Promise.all([
    page.waitForNavigation({ waitUntil: 'networkidle', timeout: 20000 }).catch(() => {
      // 如果导航失败，尝试其他方式检测登录成功
      console.log(`Navigation wait failed for ${browserName}, checking URL...`)
    }),
    page.click('button[type="submit"]')
  ])

  // 等待一小段时间让 Vue/Pinia 处理
  await page.waitForTimeout(1000)

  // 等待 localStorage 中的 token 出现（适用于所有浏览器）
  console.log(`Waiting for auth token for ${browserName}...`)
  const tokenSet = await page.waitForFunction(
    () => {
      const token = localStorage.getItem('gameassistant_token')
      return token !== null && token !== ''
    },
    { timeout: 15000 }
  ).then(() => true).catch(() => false)

  if (!tokenSet) {
    // 如果 token 没有设置，尝试检测 URL 是否已改变
    const currentUrl = page.url()
    console.log(`Token not found, current URL: ${currentUrl}`)
    if (currentUrl.includes('/login')) {
      throw new Error(`Login failed: still on login page (${currentUrl})`)
    }
  }

  // 额外等待确保 Vue 状态更新完成
  await page.waitForTimeout(1500)

  // 验证最终 URL
  const finalUrl = page.url()
  console.log(`Login result for ${browserName}: ${finalUrl}`)
  
  // 检查是否成功跳转到受保护的页面
  if (finalUrl.includes('/login')) {
    throw new Error(`Login failed: still on login page`)
  }
  
  console.log(`Login successful for ${browserName}, redirected to: ${finalUrl}`)
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

    const context = await browserInstance.newContext({
      // 添加浏览器特定选项
      ...(browserName === 'webkit' ? { viewport: { width: 1280, height: 720 } } : {}),
      ...(browserName === 'mobile-chrome' ? { viewport: { width: 393, height: 851 }, hasTouch: true } : {}),
    })
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
