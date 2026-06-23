import { test, expect } from '@playwright/test'

test.use({ storageState: './playwright/.auth/user.json' })

test.describe('数据集管理', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/datasets')
    await page.waitForLoadState('networkidle')
  })

  test('页面加载正常，显示数据集管理标题', async ({ page }) => {
    await expect(page.getByRole('heading', { name: /数据集管理/i })).toBeVisible()
  })

  test('新建数据集按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /新建数据集/i })).toBeVisible()
  })

  test('刷新按钮可见', async ({ page }) => {
    await expect(page.getByRole('button', { name: /刷新/i })).toBeVisible()
  })

  test('点击新建数据集 → 弹出表单', async ({ page }) => {
    await page.getByRole('button', { name: /新建数据集/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    await expect(page.locator('.ant-modal input').first()).toBeVisible()
  })

  test('创建数据集成功', async ({ page }) => {
    await page.getByRole('button', { name: /新建数据集/i }).click()
    await expect(page.locator('.ant-modal')).toBeVisible()
    const nameInput = page.locator('.ant-modal input').first()
    await nameInput.waitFor({ state: 'visible' })
    await nameInput.fill(`e2e-test-dataset-${Date.now()}`)
    await page.locator('.ant-modal .ant-btn-primary').click()
    await page.waitForTimeout(2000)
  })
})
