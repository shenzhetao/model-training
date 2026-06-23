import { test, expect } from '@playwright/test'

test.describe('页面加载验证', () => {
  test('登录页面能正常加载且无控制台错误', async ({ page, browser }) => {
    // 创建一个干净的 context，确保没有 auth state
    const context = await browser.newContext({
      storageState: undefined
    })
    const cleanPage = await context.newPage()

    // 监听控制台错误
    const consoleErrors: string[] = []
    cleanPage.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // 忽略 API 相关的错误（测试环境 CORS 问题）
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          consoleErrors.push(text)
        }
      }
    })

    // 访问登录页
    await cleanPage.goto('/login')
    await cleanPage.waitForLoadState('networkidle')
    await cleanPage.waitForTimeout(2000)

    // 验证页面标题
    await expect(cleanPage).toHaveTitle(/GameAssistant/)

    // 验证登录表单存在（在没有 auth state 的情况下）
    const hasLoginForm = await cleanPage.locator('input[placeholder="用户名"]').isVisible().catch(() => false)
    expect(hasLoginForm).toBeTruthy()

    // 验证表单元素
    await expect(cleanPage.locator('input[placeholder="用户名"]')).toBeVisible()
    await expect(cleanPage.locator('input[placeholder="密码"]')).toBeVisible()
    await expect(cleanPage.locator('button[type="submit"]')).toBeVisible()

    // 验证无关键控制台错误
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes('Failed to load resource') &&
        !err.includes('net::ERR') &&
        !err.includes('favicon')
    )

    expect(criticalErrors).toHaveLength(0)

    await context.close()
  })

  test('已登录状态访问关键页面正常', async ({ page }) => {
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

    // 访问图片管理页
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 验证图片管理页面加载（使用更具体的定位器）
    await expect(page.locator('.main-menu')).toBeVisible()
    await expect(page.locator('.ant-layout-content')).toBeVisible()

    // 访问训练管理页
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    // 验证训练管理页面加载
    await expect(page.locator('.ant-layout-content')).toBeVisible()

    // 访问推理测试页
    await page.goto('/inference')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(1000)

    // 验证推理测试页面加载
    await expect(page.locator('.ant-layout-content')).toBeVisible()

    // 验证无关键控制台错误
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes('Failed to load resource') &&
        !err.includes('net::ERR') &&
        !err.includes('favicon')
    )

    expect(criticalErrors).toHaveLength(0)
  })

  test('生产构建预览正常', async ({ page }) => {
    // 访问生产构建预览（端口 4173）
    await page.goto('http://localhost:4173/')
    await page.waitForLoadState('networkidle')
    await page.waitForTimeout(2000)

    // 验证页面正常加载（应该重定向到 /login 或 /images）
    const currentUrl = page.url()
    expect(currentUrl).toMatch(/\/(login|images)/)

    // 如果在 /login，验证登录表单
    if (currentUrl.includes('login')) {
      const hasLoginForm = await page.locator('input[placeholder="用户名"]').isVisible().catch(() => false)
      expect(hasLoginForm).toBeTruthy()
    }
  })
})
