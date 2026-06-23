import { test, expect } from '@playwright/test'

/**
 * 标注管理 E2E 测试
 * 测试标注管理模块的基本交互和列表页面
 */

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
    // 验证默认显示"标注项目" Tab
    const projectsTab = page.locator('.ant-tabs-tab').filter({ hasText: /标注项目/i })
    await expect(projectsTab).toBeVisible()

    // 验证 Tab 内容区域可见
    const tabContent = page.locator('.ant-tabs-tabpane-active')
    await expect(tabContent).toBeVisible()
  })

  test('新建项目按钮可见且可点击', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /新建项目/i })
    await expect(createBtn).toBeVisible()

    // 点击打开弹窗
    await createBtn.click()
    await page.waitForTimeout(500)

    // 验证弹窗出现
    const modal = page.locator('.ant-modal')
    await expect(modal).toBeVisible()

    // 验证弹窗标题
    const modalTitle = page.locator('.ant-modal-title')
    await expect(modalTitle).toContainText('项目')
  })

  test('新建项目弹窗包含所有必要表单字段', async ({ page }) => {
    const createBtn = page.getByRole('button', { name: /新建项目/i })
    await createBtn.click()
    await page.waitForTimeout(500)

    // 验证表单字段
    await expect(page.locator('.ant-modal').getByLabel('项目名称')).toBeVisible()
    await expect(page.locator('.ant-modal').getByLabel('描述')).toBeVisible()
    await expect(page.locator('.ant-modal').getByText('包含类别')).toBeVisible()
  })

  test('Tab 切换：标注项目 → 图片标注', async ({ page }) => {
    // 点击"图片标注" Tab
    const annotateTab = page.locator('.ant-tabs-tab').filter({ hasText: /图片标注/i })
    await annotateTab.click()
    await page.waitForTimeout(500)

    // 验证 Tab 内容切换
    const annotateContent = page.locator('.ant-tab-pane').filter({ hasText: /图片列表/i })
    await expect(annotateContent).toBeVisible()
  })

  test('Tab 切换：图片标注 → 类别管理', async ({ page }) => {
    // 先切换到图片标注 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /图片标注/i }).click()
    await page.waitForTimeout(300)

    // 点击"类别管理" Tab
    const classesTab = page.locator('.ant-tabs-tab').filter({ hasText: /类别管理/i })
    await classesTab.click()
    await page.waitForTimeout(500)

    // 验证类别管理内容
    const classesContent = page.locator('.ant-tab-pane').filter({ hasText: /类别管理/i })
    await expect(classesContent).toBeVisible()

    // 验证新建类别按钮
    await expect(page.getByRole('button', { name: /新建类别/i })).toBeVisible()
  })

  test('Tab 切换：类别管理 → 审核管理', async ({ page }) => {
    // 切换到审核管理 Tab
    const reviewTab = page.locator('.ant-tabs-tab').filter({ hasText: /审核管理/i })
    await reviewTab.click()
    await page.waitForTimeout(500)

    // 验证审核管理内容
    const reviewContent = page.locator('.ant-tab-pane').filter({ hasText: /审核队列/i })
    await expect(reviewContent).toBeVisible()
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
    // 切换到类别管理 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /类别管理/i }).click()
    await page.waitForTimeout(500)

    // 验证表格可见
    const table = page.locator('.ant-table')
    await expect(table).toBeVisible()
  })

  test('新建类别按钮可打开弹窗', async ({ page }) => {
    // 切换到类别管理 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /类别管理/i }).click()
    await page.waitForTimeout(500)

    // 点击新建类别按钮
    const createBtn = page.getByRole('button', { name: /新建类别/i })
    await createBtn.click()
    await page.waitForTimeout(500)

    // 验证弹窗
    const modal = page.locator('.ant-modal')
    await expect(modal).toBeVisible()

    // 验证表单字段
    await expect(page.locator('.ant-modal').getByLabel('类别名称')).toBeVisible()
    await expect(page.locator('.ant-modal').getByLabel('显示名称')).toBeVisible()
  })

  test('图片标注 Tab：图片列表容器可见', async ({ page }) => {
    // 切换到图片标注 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /图片标注/i }).click()
    await page.waitForTimeout(500)

    // 验证图片列表卡片
    const imageListCard = page.locator('.ant-card').filter({ hasText: /图片列表/i })
    await expect(imageListCard).toBeVisible()
  })

  test('图片标注 Tab：标注画布容器可见', async ({ page }) => {
    // 切换到图片标注 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /图片标注/i }).click()
    await page.waitForTimeout(500)

    // 验证标注画布卡片
    const canvasCard = page.locator('.ant-card').filter({ hasText: /标注画布/i })
    await expect(canvasCard).toBeVisible()

    // 验证画布占位符
    const placeholder = page.locator('.canvas-placeholder')
    await expect(placeholder).toBeVisible()
  })

  test('审核管理 Tab：审核统计可见', async ({ page }) => {
    // 切换到审核管理 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /审核管理/i }).click()
    await page.waitForTimeout(500)

    // 验证统计卡片
    const statCards = page.locator('.ant-statistic')
    expect(await statCards.count()).toBeGreaterThan(0)
  })

  test('审核管理 Tab：审核队列表格可见', async ({ page }) => {
    // 切换到审核管理 Tab
    await page.locator('.ant-tabs-tab').filter({ hasText: /审核管理/i }).click()
    await page.waitForTimeout(500)

    // 验证审核队列卡片
    const queueCard = page.locator('.ant-card').filter({ hasText: /审核队列/i })
    await expect(queueCard).toBeVisible()
  })
})
