import { test, expect } from '@playwright/test'

test.describe('登录流程', () => {
  test.skip('登录成功 → 跳转到图片管理页', async ({ browser }) => {
    // Note: This test requires a fresh context without auth state
    // Using browser.newContext() directly may not work as expected with storageState
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'admin123')
    await page.click('button[type="submit"]')

    await page.waitForURL('**/images**', { timeout: 15000 })
    await expect(page).toHaveURL(/\/images/)

    await context.close()
  })

  test.skip('登录失败 → 显示错误提示', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('/login')
    await page.waitForLoadState('networkidle')

    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    await page.waitForTimeout(1000)
    await expect(page).toHaveURL(/\/login/)

    await context.close()
  })

  test.skip('未登录访问受保护路由 → 重定向到登录页', async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()

    await page.goto('/images')
    await expect(page).toHaveURL(/\/login/)

    await context.close()
  })
})
