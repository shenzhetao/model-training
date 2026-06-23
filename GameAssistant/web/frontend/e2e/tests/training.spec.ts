import { test, expect } from '@playwright/test'

test.describe('训练管理 - 图表验证', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/training')
    await page.waitForLoadState('networkidle')
  })

  test('ECharts 图表渲染无控制台错误', async ({ page }) => {
    // 监听控制台错误
    const consoleErrors: string[] = []
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        const text = msg.text()
        // 忽略 API 相关的错误（测试环境 CORS 问题）
        if (!text.includes('CORS') && !text.includes('localhost/api') && !text.includes('AxiosError')) {
          consoleErrors.push(text)
        }
      }
    })

    // 点击查看一个任务
    const viewButton = page.locator('button:has-text("查看")').first()

    if (await viewButton.isVisible().catch(() => false)) {
      await viewButton.click()
      await page.waitForTimeout(2000)

      // 验证图表区域可见
      const chartWrapper = page.locator('.chart-wrapper').first()
      await expect(chartWrapper).toBeVisible()

      // 验证 ECharts canvas 元素存在
      const echartsCanvas = chartWrapper.locator('canvas')
      const canvasExists = await echartsCanvas.count() > 0

      // 如果有 canvas，检查是否渲染成功（不是空白）
      if (canvasExists) {
        const canvasHandle = await echartsCanvas.first().elementHandle()
        if (canvasHandle) {
          const box = await canvasHandle.boundingBox()
          // 验证 canvas 有实际尺寸
          expect(box).not.toBeNull()
          if (box) {
            expect(box.width).toBeGreaterThan(0)
            expect(box.height).toBeGreaterThan(0)
          }
        }
      }

      // 检查 ECharts 相关的控制台错误
      const echartsErrors = consoleErrors.filter(err =>
        err.includes('echarts') ||
        err.includes('ECharts') ||
        err.includes('v-chart') ||
        err.includes('canvas')
      )

      expect(echartsErrors).toHaveLength(0)
    } else {
      // 没有任务时，验证空状态显示正常
      await expect(page.locator('.ant-empty')).toBeVisible()
    }
  })

  test('Loss 图表标签页切换正常', async ({ page }) => {
    const viewButton = page.locator('button:has-text("查看")').first()

    if (await viewButton.isVisible().catch(() => false)) {
      await viewButton.click()
      await page.waitForTimeout(1000)

      // 切换到 Loss 标签
      const lossTab = page.locator('.ant-tabs-tab:has-text("Loss")')
      if (await lossTab.isVisible().catch(() => false)) {
        await lossTab.click()
        await page.waitForTimeout(500)

        // 验证图表容器或空状态可见
        const chartWrapper = page.locator('.chart-wrapper').first()
        await expect(chartWrapper).toBeVisible()
      }
    }
  })

  test('mAP 图表标签页切换正常', async ({ page }) => {
    const viewButton = page.locator('button:has-text("查看")').first()

    if (await viewButton.isVisible().catch(() => false)) {
      await viewButton.click()
      await page.waitForTimeout(1000)

      // 切换到 mAP 标签
      const mapTab = page.locator('.ant-tabs-tab:has-text("mAP")')
      if (await mapTab.isVisible().catch(() => false)) {
        await mapTab.click()
        await page.waitForTimeout(500)

        const chartWrapper = page.locator('.chart-wrapper').nth(1)
        await expect(chartWrapper).toBeVisible()
      }
    }
  })

  test('Precision/Recall 图表标签页切换正常', async ({ page }) => {
    const viewButton = page.locator('button:has-text("查看")').first()

    if (await viewButton.isVisible().catch(() => false)) {
      await viewButton.click()
      await page.waitForTimeout(1000)

      // 切换到 Precision/Recall 标签
      const prTab = page.locator('.ant-tabs-tab:has-text("Precision")')
      if (await prTab.isVisible().catch(() => false)) {
        await prTab.click()
        await page.waitForTimeout(500)

        const chartWrapper = page.locator('.chart-wrapper').nth(2)
        await expect(chartWrapper).toBeVisible()
      }
    }
  })

  test('原始日志标签页显示正常', async ({ page }) => {
    const viewButton = page.locator('button:has-text("查看")').first()

    if (await viewButton.isVisible().catch(() => false)) {
      await viewButton.click()
      await page.waitForTimeout(1000)

      // 切换到原始日志标签
      const logTab = page.locator('.ant-tabs-tab:has-text("原始日志")')
      if (await logTab.isVisible().catch(() => false)) {
        await logTab.click()
        await page.waitForTimeout(500)

        // 验证日志容器存在
        const logContainer = page.locator('.log-container')
        await expect(logContainer).toBeVisible()
      }
    }
  })
})
