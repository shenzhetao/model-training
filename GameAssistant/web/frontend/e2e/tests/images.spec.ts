import { test, expect } from '@playwright/test'

test.describe('图片管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示图片管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /图片管理/i })).toBeVisible()
  })

  test('上传区域可见', async ({ page }) => {
    await expect(page.locator('.upload-area')).toBeVisible()
  })

  test('工具栏按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
  })

  test('来源筛选下拉框可用', async ({ page }) => {
    const select = page.locator('.page-header input').first()
    await expect(select).toBeVisible()
  })

  test('图片网格容器可见', async ({ page }) => {
    await expect(page.locator('.image-grid-container')).toBeVisible()
  })
})
