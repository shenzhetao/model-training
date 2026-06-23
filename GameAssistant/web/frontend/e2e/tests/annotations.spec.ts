import { test, expect, type Page } from '@playwright/test'

/**
 * 标注管理 E2E 测试
 * 测试标注管理模块的基本交互和列表页面
 */

// Tab 切换辅助函数 - 使用 aria 属性选择器，更可靠
async function switchToTab(page: Page, tabText: string) {
  // 优先使用 role="tab" 选择器，更符合 ARIA 规范
  const tab = page.locator('[role="tab"]', { hasText: new RegExp(tabText, 'i') })
  await tab.waitFor({ state: 'visible', timeout: 10000 })
  await tab.click()
  
  // 等待 Tab 内容区域更新 - 检查 aria-selected 属性
  await page.waitForFunction(
    (text) => {
      const tabs = document.querySelectorAll('[role="tab"]')
      for (const tab of tabs) {
        if (tab.textContent?.includes(text)) {
          return tab.getAttribute('aria-selected') === 'true'
        }
      }
      return false
    },
    tabText,
    { timeout: 10000 }
  )
  
  // 额外等待确保 Vue 渲染完成
  await page.waitForLoadState('domcontentloaded')
}

// 等待 Modal 出现
async function waitForModal(page: Page, timeout: number = 5000) {
  await page.waitForSelector('.ant-modal-content', { state: 'visible', timeout })
}

test.describe('标注管理', () => {
  test.beforeEach(async ({ page }) => {
    // 监听控制台错误
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // 忽略 API 相关的错误（测试环境）
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          console.log('Console error:', text)
        }
      }
    })

    await page.goto('/annotations')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示标注管理标题', async ({ page }) => {
    await expect(page.locator('h2').filter({ hasText: /标注管理/i })).toBeVisible()
  })

  test('统计信息卡片可见', async ({ page }) => {
    // 查找总标注数统计
    const statsSection = page.locator('.ant-statistic')
    await expect(statsSection.first()).toBeVisible()
  })

  test('标注项目 Tab 显示正常', async ({ page }) => {
    // 验证默认显示"标注项目" Tab（使用 aria 属性）
    const projectsTab = page.locator('[role="tab"]', { hasText: /标注项目/i })
    await expect(projectsTab).toBeVisible()
    
    // 验证默认 Tab 已激活
    await expect(projectsTab).toHaveAttribute('aria-selected', 'true')

    // 验证 Tab 内容区域可见
    const tabContent = page.locator('[role="tabpanel"]').first()
    await expect(tabContent).toBeVisible()
  })

  test('新建项目按钮可见且可点击', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /新建项目/i })
    await expect(createBtn).toBeVisible()

    // 点击打开弹窗
    await createBtn.click()
    await waitForModal(page)

    // 验证弹窗出现
    const modal = page.locator('.ant-modal')
    await expect(modal).toBeVisible()

    // 验证弹窗标题包含"项目"
    const modalTitle = page.locator('.ant-modal-title')
    await expect(modalTitle).toContainText('项目')
  })

  test('新建项目弹窗包含所有必要表单字段', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /新建项目/i })
    await createBtn.click()
    await waitForModal(page)

    // 验证表单字段存在
    await expect(page.locator('.ant-modal input').first()).toBeVisible()
    await expect(page.locator('.ant-modal textarea').first()).toBeVisible()
    await expect(page.locator('.ant-modal .ant-select').first()).toBeVisible()
  })

  test('Tab 切换：标注项目 → 图片标注', async ({ page }) => {
    // 使用辅助函数切换 Tab
    await switchToTab(page, '图片标注')

    // 验证图片列表卡片可见
    const imageListCard = page.locator('.ant-card').filter({ hasText: /图片列表/i })
    await expect(imageListCard).toBeVisible({ timeout: 10000 })
  })

  test('Tab 切换：图片标注 → 类别管理', async ({ page }) => {
    // 先切换到图片标注 Tab
    await switchToTab(page, '图片标注')
    
    // 再切换到类别管理 Tab
    await switchToTab(page, '类别管理')

    // 验证类别管理内容：新建类别按钮存在
    const createClassBtn = page.getByRole('button', { name: /新建类别/i })
    await expect(createClassBtn).toBeVisible({ timeout: 10000 })
  })

  test('Tab 切换：类别管理 → 审核管理', async ({ page }) => {
    // 直接切换到审核管理 Tab
    await switchToTab(page, '审核管理')

    // 验证审核管理内容：审核队列卡片存在
    const queueCard = page.locator('.ant-card').filter({ hasText: /审核队列/i })
    await expect(queueCard).toBeVisible({ timeout: 10000 })
  })

  test('刷新按钮可见且可点击', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
    await page.waitForTimeout(1000)
  })

  test('状态筛选下拉框可用', async ({ page }) => {
    const filterSelect = page.locator('.ant-select').filter({ hasText: /筛选状态/i }).or(
      page.locator('.ant-select').first()
    )
    await expect(filterSelect).toBeVisible()
  })

  test('类别管理页面类别列表可见', async ({ page }) => {
    // 使用辅助函数切换到类别管理 Tab
    await switchToTab(page, '类别管理')

    // 验证新建类别按钮存在（说明类别管理 Tab 已正确切换）
    const createClassBtn = page.getByRole('button', { name: /新建类别/i })
    await expect(createClassBtn).toBeVisible({ timeout: 10000 })
  })

  test('新建类别按钮可打开弹窗', async ({ page }) => {
    // 切换到类别管理 Tab
    await switchToTab(page, '类别管理')

    // 点击新建类别按钮
    const createBtn = page.getByRole('button', { name: /新建类别/i })
    await createBtn.click()
    await waitForModal(page)

    // 验证弹窗
    const modal = page.locator('.ant-modal')
    await expect(modal).toBeVisible()

    // 验证表单字段存在
    await expect(page.locator('.ant-modal input').first()).toBeVisible()
  })

  test('图片标注 Tab：图片列表容器可见', async ({ page }) => {
    // 使用辅助函数切换到图片标注 Tab
    await switchToTab(page, '图片标注')

    // 验证图片列表卡片
    const imageListCard = page.locator('.ant-card').filter({ hasText: /图片列表/i })
    await expect(imageListCard).toBeVisible()
  })

  test('图片标注 Tab：标注画布容器可见', async ({ page }) => {
    // 使用辅助函数切换到图片标注 Tab
    await switchToTab(page, '图片标注')

    // 验证标注画布卡片
    const canvasCard = page.locator('.ant-card').filter({ hasText: /标注画布/i })
    await expect(canvasCard).toBeVisible()

    // 验证画布占位符
    const placeholder = page.locator('.canvas-placeholder')
    await expect(placeholder).toBeVisible()
  })

  test('审核管理 Tab：审核统计可见', async ({ page }) => {
    // 使用辅助函数切换到审核管理 Tab
    await switchToTab(page, '审核管理')

    // 验证统计卡片
    const statCards = page.locator('.ant-statistic')
    expect(await statCards.count()).toBeGreaterThan(0)
  })

  test('审核管理 Tab：审核队列表格可见', async ({ page }) => {
    // 使用辅助函数切换到审核管理 Tab
    await switchToTab(page, '审核管理')

    // 验证审核队列卡片
    const queueCard = page.locator('.ant-card').filter({ hasText: /审核队列/i })
    await expect(queueCard).toBeVisible()
  })
})
