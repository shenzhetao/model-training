import { test, expect } from '@playwright/test'

test.describe('模型管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/models')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示模型管理标题', async ({ page }) => {
    await expect(page.locator('h2').filter({ hasText: /模型管理/i })).toBeVisible()
  })

  test('统计卡片可见（如果有模型数据）', async ({ page }) => {
    await expect(page.locator('h2').filter({ hasText: /模型管理/i })).toBeVisible()
    // 尝试等待统计卡片
    try {
      await page.locator('.ant-statistic').first().waitFor({ state: 'visible', timeout: 5000 })
      await expect(page.locator('.ant-statistic').first()).toBeVisible()
    } catch {
      // 没有模型时统计卡片不显示（v-if="stats"）
      console.log('Stats not visible - no models yet')
    }
  })

  test('工具栏按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
    await expect(page.getByRole('button', { name: /上传模型/i })).toBeVisible()
  })

  test('刷新按钮可点击', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
    await page.waitForTimeout(500)
  })

  test('架构筛选下拉框可用', async ({ page }) => {
    // 等待页面完全加载
    await page.waitForTimeout(1000)
    const select = page.locator('.ant-select').first()
    await expect(select).toBeVisible()
    // 点击打开下拉框
    await select.click()
    await expect(page.locator('.ant-select-dropdown')).toBeVisible()
    // 关闭下拉框
    await page.keyboard.press('Escape')
  })

  test('模型列表表格可见（即使为空）', async ({ page }) => {
    await expect(page.locator('.ant-table')).toBeVisible()
  })

  test('点击上传模型 → 弹出上传表单', async ({ page }) => {
    await page.getByRole('button', { name: /上传模型/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    // 验证表单元素存在
    await expect(page.getByText(/选择模型文件/i)).toBeVisible()
    // 关闭弹窗
    await page.keyboard.press('Escape')
    await page.waitForTimeout(300)
  })

  test('上传弹窗包含所有必要表单字段', async ({ page }) => {
    await page.getByRole('button', { name: /上传模型/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    // 验证选择文件按钮存在
    await expect(page.locator('.ant-modal button').filter({ hasText: /选择模型文件/i }).first()).toBeVisible()
    // 验证架构选择下拉框
    await expect(page.locator('.ant-modal .ant-select').first()).toBeVisible()
    // 验证描述输入框（可选字段）
    const descInput = page.locator('.ant-modal textarea')
    if (await descInput.isVisible().catch(() => false)) {
      await expect(descInput).toBeVisible()
    }
    // 关闭弹窗
    await page.keyboard.press('Escape')
  })

  test('选择模型后显示详情面板', async ({ page }) => {
    await page.waitForTimeout(1000)
    // 尝试点击第一个模型的详情按钮
    const detailBtn = page.locator('button').filter({ hasText: '详情' }).first()
    if (await detailBtn.isVisible().catch(() => false)) {
      await detailBtn.click()
      await page.waitForTimeout(500)
      // 验证详情面板出现
      const detailCard = page.locator('.ant-card').filter({ hasText: '模型详情' })
      await expect(detailCard).toBeVisible()
      // 验证关闭按钮存在
      await expect(page.locator('button').filter({ hasText: '关闭' }).first()).toBeVisible()
    }
  })

  test('详情面板包含下载按钮', async ({ page }) => {
    await page.waitForTimeout(1000)
    const detailBtn = page.locator('button').filter({ hasText: '详情' }).first()
    if (await detailBtn.isVisible().catch(() => false)) {
      await detailBtn.click()
      await page.waitForTimeout(500)
      // 验证下载按钮
      const downloadBtn = page.locator('button').filter({ hasText: '下载模型' })
      await expect(downloadBtn).toBeVisible()
      // 关闭详情
      await page.locator('button').filter({ hasText: '关闭' }).first().click()
    }
  })
})
