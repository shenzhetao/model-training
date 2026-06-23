import { test, expect } from '@playwright/test'

test.describe('页面加载验证', () => {
  test('登录页面能正常加载且无控制台错误', async ({ page }) => {
    // 监听控制台错误
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // 访问登录页
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // 验证页面标题
    await expect(page).toHaveTitle(/GameAssistant/)

    // 验证登录表单元素存在
    const usernameInput = page.locator('input[placeholder="用户名"]')
    const passwordInput = page.locator('input[placeholder="密码"]')
    const submitButton = page.locator('button[type="submit"]')

    await expect(usernameInput).toBeVisible()
    await expect(passwordInput).toBeVisible()
    await expect(submitButton).toBeVisible()

    // 验证无控制台错误（忽略一些常见的非关键错误）
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes('Failed to load resource') &&
        !err.includes('net::ERR') &&
        !err.includes('favicon')
    )

    expect(criticalErrors).toHaveLength(0)
  })

  test('登录后能正常跳转到图片管理页', async ({ page }) => {
    // 监听控制台错误
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text())
      }
    })

    // 访问登录页
    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    // 填写登录表单
    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'admin123')

    // 提交登录
    await page.click('button[type="submit"]')

    // 等待跳转到图片管理页
    await page.waitForURL(/\/images/, { timeout: 15000 })

    // 验证当前 URL
    await expect(page).toHaveURL(/\/images/)

    // 验证页面内容加载
    await page.waitForLoadState('networkidle')

    // 验证无控制台错误
    const criticalErrors = consoleErrors.filter(
      (err) =>
        !err.includes('Failed to load resource') &&
        !err.includes('net::ERR') &&
        !err.includes('favicon')
    )

    expect(criticalErrors).toHaveLength(0)
  })
})
