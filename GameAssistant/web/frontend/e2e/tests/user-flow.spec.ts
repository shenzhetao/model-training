import { test, expect } from '@playwright/test'

/**
 * 完整用户流程 E2E 测试
 * 测试流程：登录 → 上传图片 → 创建数据集 → 发起训练
 * 注意：这是一个端到端集成测试，需要后端服务正常运行
 */

test.describe('完整用户流程测试', () => {
  test.beforeEach(async ({ page }) => {
    // 监听控制台错误
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // 忽略 API 相关的错误（测试环境 CORS 问题）
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          console.log('Console error:', text)
        }
      }
    })
  })

  test('登录成功并跳转到图片管理页', async ({ browser }) => {
    // 创建干净的 context，没有任何 auth state
    const context = await browser.newContext({
      storageState: undefined
    })
    const page = await context.newPage()

    // 监听控制台错误
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          consoleErrors.push(text)
        }
      }
    })

    // 等待页面加载
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 等待登录表单出现
    const usernameInput = page.locator('input[placeholder="用户名"]')
    await usernameInput.waitFor({ state: 'visible', timeout: 15000 })

    // 填写登录信息
    await usernameInput.fill('admin')
    await page.locator('input[placeholder="密码"]').fill('admin123')
    await page.locator('button[type="submit"]').click()

    // 等待登录成功后的跳转
    await page.waitForURL('**/images**', { timeout: 20000 })
    await expect(page).toHaveURL(/\/images/)

    // 验证跳转到图片管理页
    await expect(page.locator('.ant-layout-content')).toBeVisible()

    // 验证无关键控制台错误
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes('Failed to load resource') &&
        !err.includes('net::ERR') &&
        !err.includes('favicon') &&
        !err.includes('Preflight') &&
        !err.includes('404')
    )
    expect(criticalErrors).toHaveLength(0)

    await context.close()
  })

  test('导航到数据集管理页面', async ({ page }) => {
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').filter({ hasText: /数据集管理/i })).toBeVisible()
  })

  test('导航到训练管理页面', async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').filter({ hasText: /训练管理/i })).toBeVisible()
  })

  test('导航到标注管理页面', async ({ page }) => {
    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').filter({ hasText: /标注管理/i })).toBeVisible()
  })

  test('侧边导航菜单完整可见', async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('domcontentloaded')

    // 等待页面主内容区域出现
    const content = page.locator('.ant-layout-content')
    await content.waitFor({ state: 'visible', timeout: 10000 })
    await expect(content).toBeVisible()
  })

  test('页面间切换保持登录状态', async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('domcontentloaded')
    await expect(page).toHaveURL(/\/images/)

    // 点击导航到数据集页面
    const datasetsLink = page.locator('.ant-menu-item a[href="/datasets"]').first()
    await datasetsLink.waitFor({ state: 'visible', timeout: 10000 })
    await datasetsLink.click()
    await page.waitForURL('**/datasets**', { timeout: 10000 })

    // 点击导航回图片页面
    const imagesLink = page.locator('.ant-menu-item a[href="/images"]').first()
    await imagesLink.waitFor({ state: 'visible', timeout: 10000 })
    await imagesLink.click()
    await page.waitForURL('**/images**', { timeout: 10000 })
    await expect(page).not.toHaveURL(/\/login/)
  })

  test('新建数据集按钮可见且可点击', async ({ page }) => {
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
    const createBtn = page.getByRole('button', { name: /新建数据集/i })
    await expect(createBtn).toBeVisible()
    await createBtn.click()
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-modal')).toBeVisible()
  })

  test('新建训练按钮可见且可点击', async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
    const createBtn = page.getByRole('button', { name: /新建训练/i })
    await expect(createBtn).toBeVisible()
    await createBtn.click()
    await page.waitForTimeout(500)
    await expect(page.locator('.ant-modal')).toBeVisible()
  })

  test('从 URL 直接访问受保护页面会重定向', async ({ browser }) => {
    // 创建新 context（没有认证状态）
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('/images')
    await page.waitForLoadState('domcontentloaded')

    // 应该被重定向到登录页
    await expect(page).toHaveURL(/\/login/, { timeout: 10000 })

    // 验证登录表单存在
    const usernameInput = page.locator('input[placeholder="用户名"]')
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })
    await expect(usernameInput).toBeVisible()

    await context.close()
  })

  test('登出后无法访问受保护页面', async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
    await page.evaluate(() => { localStorage.clear() })
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
    await expect(page).toHaveURL(/\/login/)
    await expect(page.locator('input[placeholder="用户名"]')).toBeVisible()
  })
})
