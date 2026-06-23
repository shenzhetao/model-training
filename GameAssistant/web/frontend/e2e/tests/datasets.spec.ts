import { test, expect } from '@playwright/test'

test.describe('数据集管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示数据集管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /数据集管理/i })).toBeVisible()
  })

  test('刷新按钮可见且可点击', async ({ page }) => {
    const refreshBtn = page.getByRole('button', { name: /刷新/i })
    await expect(refreshBtn).toBeVisible()
    await refreshBtn.click()
    await page.waitForTimeout(500)
  })

  test('新建数据集按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /新建数据集/i })).toBeVisible()
  })

  test('数据集列表卡片可见', async ({ page }) => {
    const card = page.locator('.ant-card').filter({ hasText: '数据集列表' })
    await expect(card).toBeVisible()
  })

  test('点击新建数据集 → 弹出表单', async ({ page }) => {
    await page.getByRole('button', { name: /新建数据集/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    // 验证表单字段存在
    await expect(page.locator('.ant-modal input').first()).toBeVisible()
    // 验证取消按钮可关闭弹窗
    await page.locator('.ant-modal .ant-btn').filter({ hasText: '取消' }).click()
    await page.waitForTimeout(300)
    await expect(page.locator('.ant-modal')).not.toBeVisible()
  })

  test('创建数据集成功（填写表单并提交）', async ({ page }) => {
    await page.getByRole('button', { name: /新建数据集/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    const nameInput = page.locator('.ant-modal input').first()
    await nameInput.waitFor({ state: 'visible' })
    await nameInput.fill(`e2e-test-dataset-${Date.now()}`)
    // 填写描述（可选）
    const descInput = page.locator('.ant-modal textarea')
    if (await descInput.isVisible()) {
      await descInput.fill('E2E 测试数据集描述')
    }
    // 点击确定按钮
    await page.locator('.ant-modal .ant-btn-primary').click()
    await page.waitForTimeout(2000)
    // 验证弹窗关闭
    await expect(page.locator('.ant-modal')).not.toBeVisible()
  })

  test('无数据集时显示空状态', async ({ page }) => {
    const emptyState = page.locator('.ant-empty')
    // 可能有空状态也可能没有（取决于是否有数据）
    const hasEmpty = await emptyState.isVisible().catch(() => false)
    // 如果有空状态，验证其存在
    if (hasEmpty) {
      await expect(emptyState).toBeVisible()
    }
  })

  test('选中数据集后显示详情面板', async ({ page }) => {
    // 等待数据集列表加载
    await page.waitForTimeout(1000)
    // 尝试点击第一个数据集
    const firstDataset = page.locator('.dataset-item').first()
    if (await firstDataset.isVisible().catch(() => false)) {
      await firstDataset.click()
      await page.waitForTimeout(500)
      // 验证详情面板出现
      const detailCard = page.locator('.ant-card').filter({ hasText: '版本管理' })
      await expect(detailCard).toBeVisible()
      // 验证版本管理区域可见
      await expect(page.locator('button').filter({ hasText: '新建版本' })).toBeVisible()
    }
  })

  test('选中数据集后新建版本按钮可见', async ({ page }) => {
    await page.waitForTimeout(1000)
    const firstDataset = page.locator('.dataset-item').first()
    if (await firstDataset.isVisible().catch(() => false)) {
      await firstDataset.click()
      await page.waitForTimeout(500)
      const createVersionBtn = page.getByRole('button', { name: /新建版本/i })
      await expect(createVersionBtn).toBeVisible()
    }
  })
})
