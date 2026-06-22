import { test, expect } from '@playwright/test'

test.use({ storageState: './playwright/.auth/user.json' })

test.describe('训练管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示训练管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /训练管理/i })).toBeVisible()
  })

  test('发起训练按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /发起训练/i })).toBeVisible()
  })

  test('刷新按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
  })
})
