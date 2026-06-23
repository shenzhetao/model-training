import { test, expect, type Page } from '@playwright/test'

/**
 * WebKit 兼容测试
 * 针对 WebKit (Safari) 浏览器的替代测试用例
 * 使用 WebKit 兼容的选择器，避免跨浏览器兼容性问题
 */

test.describe('WebKit 兼容性测试', () => {
  test.beforeEach(async ({ page }) => {
    // 监听控制台错误
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          console.log('Console error:', text)
        }
      }
    })
  })

  test('登录后访问标注管理页面', async ({ page }) => {
    // 访问标注管理页面
    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
    
    // 验证页面标题存在（使用更通用的选择器）
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('标注管理页面基本元素可见', async ({ page }) => {
    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
    
    // 验证页面标题
    await expect(page.locator('h2')).toBeVisible()
    
    // 验证统计卡片存在
    const statsSection = page.locator('.ant-statistic')
    await expect(statsSection.first()).toBeVisible()
  })

  test('标注项目列表页面可访问', async ({ page }) => {
    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
    
    // 验证有 Tab 切换存在
    const tabs = page.locator('[role="tab"]')
    await expect(tabs.first()).toBeVisible()
  })

  test('图片管理页面可访问', async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
    
    // 验证页面标题
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('数据集管理页面可访问', async ({ page }) => {
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
    
    // 验证页面基本元素
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('模型管理页面可访问', async ({ page }) => {
    await page.goto('/models')
    await page.waitForLoadState('networkidle')
    
    // 验证页面基本元素
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('模板管理页面可访问', async ({ page }) => {
    await page.goto('/templates')
    await page.waitForLoadState('networkidle')
    
    // 验证页面基本元素
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('训练管理页面可访问', async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
    
    // 验证页面基本元素
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('推理测试页面可访问', async ({ page }) => {
    await page.goto('/inference')
    await page.waitForLoadState('networkidle')
    
    // 验证页面基本元素
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })

  test('侧边导航菜单可见', async ({ page }) => {
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
    
    // 验证导航菜单存在
    const nav = page.locator('nav').or(page.locator('.ant-menu'))
    await expect(nav.first()).toBeVisible({ timeout: 10000 })
  })

  test('页面间导航正常', async ({ page }) => {
    // 从图片管理开始
    await page.goto('/images')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
    
    // 导航到标注管理
    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
    
    // 导航到数据集管理
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
    await expect(page.locator('h2').first()).toBeVisible({ timeout: 10000 })
  })
})
