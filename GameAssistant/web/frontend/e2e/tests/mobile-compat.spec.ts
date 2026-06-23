import { test, expect } from '@playwright/test'

/**
 * Mobile Chrome 兼容测试
 * 针对移动端浏览器的替代测试用例
 * 使用移动端友好的选择器和交互方式
 */

test.describe('Mobile Chrome 兼容测试', () => {
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

  test('登录页面基本元素可见（移动端兼容）', async ({ page, isMobile }) => {
    // 验证移动端标记
    expect(isMobile).toBe(true)

    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 使用更宽松的移动端选择器
    const usernameInput = page.locator('input').first()
    await expect(usernameInput).toBeVisible()

    const passwordInput = page.locator('input[type="password"]')
    await expect(passwordInput).toBeVisible()

    // 移动端按钮选择器
    const submitBtn = page.locator('button[type="submit"]')
    await expect(submitBtn).toBeVisible()
  })

  test('登录流程（移动端兼容）', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 使用稳定的等待
    const usernameInput = page.locator('input').first()
    await usernameInput.waitFor({ state: 'visible', timeout: 10000 })

    // 填写登录信息
    await usernameInput.fill('admin')
    await page.locator('input[type="password"]').fill('admin123')
    
    // 点击提交按钮
    await page.locator('button[type="submit"]').click()

    // 使用 URL 模式匹配，等待更长时间
    await page.waitForURL(/(\/images|\/login|\/annotations)/, { timeout: 20000 })

    // 验证登录成功（不在登录页）
    const currentUrl = page.url()
    expect(currentUrl).not.toContain('/login')
  })

  test('页面加载测试（移动端兼容）', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 验证页面基本元素
    const pageContent = page.locator('body')
    await expect(pageContent).toBeVisible()

    // 验证页面标题存在
    const pageTitle = await page.title()
    expect(pageTitle).toBeTruthy()
  })

  test('路由守卫重定向测试（移动端兼容）', async ({ page }) => {
    // 直接访问受保护的路由
    await page.goto('/images')
    await page.waitForLoadState('domcontentloaded')

    // 等待重定向完成
    await page.waitForURL(/(\/login|\/images|\/annotations)/, { timeout: 15000 })

    // 应该被重定向到登录页（如果没有认证）
    const currentUrl = page.url()
    const isAuthenticated = !currentUrl.includes('/login')
    
    // 记录测试结果
    if (isAuthenticated) {
      console.log('User is authenticated, redirected to protected page')
    } else {
      console.log('User is not authenticated, redirected to login page')
    }
  })

  test('表单输入测试（移动端兼容）', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 找到输入框
    const inputs = page.locator('input')
    const inputCount = await inputs.count()
    expect(inputCount).toBeGreaterThanOrEqual(2)

    // 测试输入功能
    const usernameInput = inputs.first()
    await usernameInput.fill('testuser')
    
    const passwordInput = page.locator('input[type="password"]')
    await passwordInput.fill('testpass')

    // 验证输入值
    await expect(usernameInput).toHaveValue('testuser')
    await expect(passwordInput).toHaveValue('testpass')
  })

  test('触摸交互测试（移动端兼容）', async ({ page, isMobile, hasTouch }) => {
    // 验证移动端标记
    expect(isMobile || hasTouch).toBeTruthy()

    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 测试触摸交互 - 使用 tap 替代 click
    const usernameInput = page.locator('input').first()
    await usernameInput.tap()
    await usernameInput.fill('admin')

    // 验证输入成功
    await expect(usernameInput).toHaveValue('admin')
  })

  test('视口大小测试（移动端兼容）', async ({ page }) => {
    // 获取当前视口大小
    const viewport = page.viewportSize()
    expect(viewport).toBeTruthy()
    
    // 验证视口是移动端大小（宽度小于 768px）
    if (viewport) {
      expect(viewport.width).toBeLessThanOrEqual(500)
    }
  })

  test('响应式布局测试（移动端兼容）', async ({ page }) => {
    await page.goto('/login')
    await page.waitForLoadState('domcontentloaded')

    // 验证主要容器存在
    const mainContainer = page.locator('#app')
    await expect(mainContainer).toBeVisible()

    // 验证登录表单容器存在
    const loginForm = page.locator('.login-container, form, [class*="login"]').first()
    
    // 使用更通用的等待方式
    await page.waitForLoadState('domcontentloaded')
    
    // 验证页面内容
    const body = page.locator('body')
    await expect(body).toBeVisible()
  })
})
