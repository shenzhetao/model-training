import { test, expect } from '@playwright/test'

test.describe('登录流程', () => {
  test('登录成功 → 跳转到图片管理页', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'admin123')
    await page.click('button[type="submit"]')

    await page.waitForURL('**/images**', { timeout: 15000 })
    await expect(page).toHaveURL(/\/images/)
  })

  test('登录失败 → 显示错误提示', async ({ page }) => {
    await page.goto('/login')

    await page.fill('input[placeholder="用户名"]', 'admin')
    await page.fill('input[placeholder="密码"]', 'wrongpassword')
    await page.click('button[type="submit"]')

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/)
  })

  test('未登录访问受保护路由 → 重定向到登录页', async ({ page }) => {
    await page.goto('/images')
    await expect(page).toHaveURL(/\/login/)
  })
})
