import { test, expect } from '@playwright/test'

test.describe('推理测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/inference')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示推理测试标题', async ({ page }) => {
    await expect(page.locator('h2').filter({ hasText: /推理测试/i })).toBeVisible()
  })

  test('工具栏按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /检测设备/i })).toBeVisible()
  })

  test('截图按钮可见', async ({ page }) => {
    await expect(page.locator('.page-header >> button', { hasText: '截图' })).toBeVisible()
  })

  test('推理模式 Tab 切换可见', async ({ page }) => {
    const videoTab = page.locator('.ant-tabs-tab').filter({ hasText: '视频推理' })
    const imageTab = page.locator('.ant-tabs-tab').filter({ hasText: '图片推理' })
    const historyTab = page.locator('.ant-tabs-tab').filter({ hasText: '推理历史' })

    await expect(videoTab).toBeVisible()
    await expect(imageTab).toBeVisible()
    await expect(historyTab).toBeVisible()
  })

  test('点击图片推理 Tab → 切换到图片模式', async ({ page }) => {
    await page.locator('.ant-tabs-tab').filter({ hasText: '图片推理' }).click()
    await expect(page.getByText(/选择图片/i)).toBeVisible()
  })

  test('点击历史记录 Tab → 切换到历史模式', async ({ page }) => {
    await page.locator('.ant-tabs-tab').filter({ hasText: '推理历史' }).click()
    await expect(page.locator('.ant-tabs-content')).toBeVisible()
  })
})
