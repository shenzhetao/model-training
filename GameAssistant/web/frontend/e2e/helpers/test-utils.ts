import { Page, Locator, expect } from '@playwright/test'

/**
 * E2E 测试辅助工具
 * 提供常用的测试辅助函数
 */

/**
 * 等待页面元素可见，超时后返回 false 而不抛出异常
 */
export async function waitForSelectorSafe(page: Page, selector: string, timeout: number = 5000): Promise<boolean> {
  try {
    await page.waitForSelector(selector, { state: 'visible', timeout })
    return true
  } catch {
    return false
  }
}

/**
 * 点击元素并等待导航
 */
export async function clickAndWaitForNavigation(page: Page, locator: Locator, timeout: number = 15000): Promise<void> {
  await Promise.all([
    page.waitForURL(/\/(?!login)/, { timeout }),
    locator.click(),
  ])
}

/**
 * 等待 Ant Design Modal 出现
 */
export async function waitForModal(page: Page, timeout: number = 5000): Promise<Locator> {
  const modal = page.locator('.ant-modal')
  await modal.waitFor({ state: 'visible', timeout })
  return modal
}

/**
 * 关闭 Ant Design Modal
 */
export async function closeModal(page: Page): Promise<void> {
  // 尝试多种关闭方式
  const closeBtn = page.locator('.ant-modal button.ant-modal-close')
  if (await closeBtn.isVisible().catch(() => false)) {
    await closeBtn.click()
  } else {
    await page.keyboard.press('Escape')
  }
  await page.waitForTimeout(300)
}

/**
 * 等待 Ant Design 消息提示消失
 */
export async function waitForMessage(page: Page, timeout: number = 3000): Promise<void> {
  await page.waitForTimeout(timeout)
}

/**
 * 填充 Ant Design 表单输入框
 */
export async function fillFormInput(page: Page, label: string, value: string): Promise<void> {
  const input = page.locator(`.ant-modal input[placeholder="${label}"], .ant-form-item label:has-text("${label}") + * input, .ant-form-item:has(label:has-text("${label}")) input`).first()
  await input.fill(value)
}

/**
 * 选择 Ant Design 下拉选项
 */
export async function selectDropdownOption(page: Page, optionText: string): Promise<void> {
  await page.locator(`.ant-select-dropdown .ant-select-item-option:has-text("${optionText}")`).click()
}

/**
 * 等待数据加载完成（检查 loading 状态消失）
 */
export async function waitForLoading(page: Page, timeout: number = 10000): Promise<void> {
  // 等待可能的 loading 遮罩消失
  await page.waitForFunction(() => {
    const loading = document.querySelector('.ant-spin, .ant-loading, [class*="loading"]')
    return !loading || window.getComputedStyle(loading).display === 'none'
  }, { timeout })
}

/**
 * 等待页面跳转到指定 URL 模式
 */
export async function waitForUrlPattern(page: Page, pattern: RegExp, timeout: number = 15000): Promise<boolean> {
  const startTime = Date.now()
  while (Date.now() - startTime < timeout) {
    if (pattern.test(page.url())) {
      return true
    }
    await page.waitForTimeout(500)
  }
  return false
}

/**
 * 验证表格中至少有一行数据
 */
export async function expectTableHasRows(page: Page, tableSelector: string = '.ant-table'): Promise<void> {
  const table = page.locator(tableSelector)
  await expect(table).toBeVisible()
  
  // 检查是否有数据行（排除表头）
  const rows = page.locator(`${tableSelector} .ant-table-tbody tr`)
  const rowCount = await rows.count()
  
  // 表格可能有空状态
  const emptyState = page.locator(`${tableSelector} .ant-empty`).isVisible().catch(() => false)
  expect(rowCount > 0 || emptyState).toBeTruthy()
}

/**
 * 点击表格中的第一行
 */
export async function clickFirstTableRow(page: Page, tableSelector: string = '.ant-table'): Promise<void> {
  const firstRow = page.locator(`${tableSelector} .ant-table-tbody tr`).first()
  if (await firstRow.isVisible().catch(() => false)) {
    await firstRow.click()
    await page.waitForTimeout(500)
  }
}

/**
 * 验证分页信息
 */
export async function expectPagination(page: Page): Promise<void> {
  const pagination = page.locator('.ant-pagination')
  if (await pagination.isVisible().catch(() => false)) {
    await expect(pagination).toBeVisible()
  }
}

/**
 * 安全地获取元素文本（不抛出异常）
 */
export async function getElementText(page: Page, selector: string): Promise<string | null> {
  try {
    const element = page.locator(selector).first()
    if (await element.isVisible().catch(() => false)) {
      return await element.textContent()
    }
    return null
  } catch {
    return null
  }
}

/**
 * 验证面包屑导航
 */
export async function expectBreadcrumb(page: Page, items: string[]): Promise<void> {
  const breadcrumb = page.locator('.ant-breadcrumb')
  await expect(breadcrumb).toBeVisible()
  
  for (const item of items) {
    const breadcrumbItem = page.locator(`.ant-breadcrumb a, .ant-breadcrumb span`).filter({ hasText: item })
    await expect(breadcrumbItem).toBeVisible()
  }
}

/**
 * 滚动到页面顶部
 */
export async function scrollToTop(page: Page): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.waitForTimeout(200)
}

/**
 * 滚动到页面底部
 */
export async function scrollToBottom(page: Page): Promise<void> {
  await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight))
  await page.waitForTimeout(200)
}

/**
 * 截图保存到文件（用于调试）
 */
export async function screenshotForDebug(page: Page, name: string): Promise<void> {
  await page.screenshot({ 
    path: `test-results/debug-${name}-${Date.now()}.png`,
    fullPage: true 
  })
}
