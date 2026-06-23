import { test, expect } from '@playwright/test'

test.describe('训练管理 - 基础功能', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示训练管理标题', async ({ page }) => {
    await expect(page.locator('h2').filter({ hasText: /训练管理/i })).toBeVisible()
  })

  test('发起训练按钮可见', async ({ page }) => {
    await expect(page.locator('.page-header >> button', { hasText: /训练/ })).toBeVisible()
  })

  test('刷新按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
  })

  test('训练任务表格可见', async ({ page }) => {
    // 验证表格容器存在
    await expect(page.locator('.ant-table')).toBeVisible()
  })

  test('状态筛选下拉框可用', async ({ page }) => {
    const filterSelect = page.locator('.ant-select').first()
    await expect(filterSelect).toBeVisible()
    await filterSelect.click()
    await page.waitForTimeout(500)
    // 验证有状态选项
    await expect(page.locator('.ant-select-dropdown')).toBeVisible()
    // 点击空白关闭下拉框
    await page.keyboard.press('Escape')
  })

  test('新建训练弹窗可打开', async ({ page }) => {
    // 点击新建训练按钮
    const newButton = page.locator('button:has-text("新建训练")')
    await newButton.click()

    // 验证弹窗出现
    await expect(page.locator('.ant-modal')).toBeVisible({ timeout: 5000 })
    // 验证弹窗标题存在
    await expect(page.locator('.ant-modal .ant-modal-title').or(page.locator('.ant-modal .ant-modal-header')).first()).toBeVisible()

    // 验证表单元素存在
    await expect(page.locator('.ant-modal input').first()).toBeVisible()

    // 关闭弹窗 - 点击 modal 外部区域
    const modal = page.locator('.ant-modal')
    await modal.press('Escape')
    await page.waitForTimeout(500)
  })
})
