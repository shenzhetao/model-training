import { test, expect } from '@playwright/test'

test.use({ storageState: './playwright/.auth/user.json' })

test.describe('模板管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/templates')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示模板管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /模板管理/i })).toBeVisible()
  })

  test('工具栏按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /上传模板/i })).toBeVisible()
  })

  test('搜索框可用', async ({ page }) => {
    const searchInput = page.locator('input[placeholder="搜索模板..."]')
    await expect(searchInput).toBeVisible()
    await searchInput.fill('test')
    await searchInput.clear()
  })

  test('类别筛选下拉框可用', async ({ page }) => {
    const select = page.locator('.ant-select').first()
    await expect(select).toBeVisible()
  })

  test('点击上传模板 → 弹出上传表单', async ({ page }) => {
    await page.getByRole('button', { name: /上传模板/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    await page.keyboard.press('Escape')
  })
})
