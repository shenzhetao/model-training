import { test, expect } from '@playwright/test'

test.describe('图片管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示图片管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /图片管理/i })).toBeVisible()
  })

  test('图片计数显示正常', async ({ page }) => {
    const countText = page.locator('.total-count')
    await expect(countText).toBeVisible()
  })

  test('来源筛选下拉框可用', async ({ page }) => {
    const select = page.locator('.page-header .ant-select').first()
    await expect(select).toBeVisible()
    // 点击打开下拉框
    await select.click()
    await expect(page.locator('.ant-select-dropdown')).toBeVisible()
    // 选择一个选项
    await page.locator('.ant-select-item').filter({ hasText: '手动上传' }).click()
    // 等待筛选结果
    await page.waitForTimeout(1000)
  })

  test('刷新按钮可见且可点击', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
    await page.waitForTimeout(500)
  })

  test('上传区域可见', async ({ page }) => {
    await expect(page.locator('.upload-area')).toBeVisible()
  })

  test('上传单张图片按钮可见', async ({ page }) => {
    const uploadBtn = page.locator('.upload-area button').filter({ hasText: '上传单张图片' })
    await expect(uploadBtn).toBeVisible()
  })

  test('上传 ZIP 包按钮可见', async ({ page }) => {
    const zipBtn = page.locator('.upload-area button').filter({ hasText: '上传 ZIP 包' })
    await expect(zipBtn).toBeVisible()
  })

  test('视频抽帧折叠面板可见', async ({ page }) => {
    const videoPanel = page.locator('.video-panel')
    await expect(videoPanel).toBeVisible()
    // 展开折叠面板
    const panelHeader = page.locator('.ant-collapse-header').filter({ hasText: '视频抽帧' })
    await panelHeader.click()
    await page.waitForTimeout(500)
    // 验证面板内容
    await expect(panelHeader).toBeVisible()
  })

  test('图片网格容器可见（空状态或已有图片）', async ({ page }) => {
    await expect(page.locator('.image-grid-container')).toBeVisible()
    // 可能是空状态或有图片
    const hasImages = await page.locator('.image-card').count() > 0
    const hasEmpty = await page.locator('.empty-container').isVisible().catch(() => false)
    expect(hasImages || hasEmpty).toBeTruthy()
  })

  test('点击刷新按钮后页面正常刷新', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await refreshBtn.click()
    // 等待加载完成
    await page.waitForTimeout(1000)
    // 页面应该仍然正常显示
    await expect(page.locator('.image-grid-container')).toBeVisible()
  })
})
