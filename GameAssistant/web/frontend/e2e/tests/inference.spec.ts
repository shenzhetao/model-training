import { test, expect } from '@playwright/test'

test.use({ storageState: './playwright/.auth/user.json' })

test.describe('推理测试', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/inference')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示推理测试标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /推理测试/i })).toBeVisible()
  })

  test('工具栏按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /检测设备/i })).toBeVisible()
  })

  test('截图按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /截图/i })).toBeVisible()
  })

  test('推理模式 Tab 切换可见', async ({ page }) => {
    const videoTab = page.getByRole('tab', { name: /视频/i })
    const imageTab = page.getByRole('tab', { name: /图片/i })
    const historyTab = page.getByRole('tab', { name: /历史记录/i })

    await expect(videoTab).toBeVisible()
    await expect(imageTab).toBeVisible()
    await expect(historyTab).toBeVisible()
  })

  test('点击图片推理 Tab → 切换到图片模式', async ({ page }) => {
    await page.getByRole('tab', { name: /图片/i }).click()
    await expect(page.getByText(/选择图片/i)).toBeVisible()
  })

  test('点击历史记录 Tab → 切换到历史模式', async ({ page }) => {
    await page.getByRole('tab', { name: /历史记录/i }).click()
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
  })
})
