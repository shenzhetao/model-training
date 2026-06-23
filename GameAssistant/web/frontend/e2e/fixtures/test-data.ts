import { test as base, Page, BrowserContext } from '@playwright/test'

/**
 * 测试数据准备与清理 Fixture
 * 用于在测试前准备测试数据，测试后清理
 */

// 测试数据命名空间前缀
export const TEST_DATA_PREFIX = 'e2e-test-'

// 存储测试期间创建的资源 ID
const createdResources: {
  datasets: string[]
  images: string[]
  annotations: string[]
  models: string[]
  templates: string[]
  trainingJobs: string[]
} = {
  datasets: [],
  images: [],
  annotations: [],
  models: [],
  templates: [],
  trainingJobs: [],
}

/**
 * 清理所有测试数据
 * 通过调用后端 API 删除测试期间创建的资源
 */
async function cleanupTestData(page: Page): Promise<void> {
  const apiBase = 'http://localhost:8000/api/v1'

  for (const datasetId of createdResources.datasets) {
    try {
      await page.request.delete(`${apiBase}/datasets/${datasetId}`)
    } catch (e) {
      console.log(`Failed to cleanup dataset ${datasetId}:`, e)
    }
  }

  for (const imageId of createdResources.images) {
    try {
      await page.request.delete(`${apiBase}/images/${imageId}`)
    } catch (e) {
      console.log(`Failed to cleanup image ${imageId}:`, e)
    }
  }

  for (const annotationId of createdResources.annotations) {
    try {
      await page.request.delete(`${apiBase}/annotations/${annotationId}`)
    } catch (e) {
      console.log(`Failed to cleanup annotation ${annotationId}:`, e)
    }
  }

  for (const modelId of createdResources.models) {
    try {
      await page.request.delete(`${apiBase}/models/${modelId}`)
    } catch (e) {
      console.log(`Failed to cleanup model ${modelId}:`, e)
    }
  }

  for (const templateId of createdResources.templates) {
    try {
      await page.request.delete(`${apiBase}/templates/${templateId}`)
    } catch (e) {
      console.log(`Failed to cleanup template ${templateId}:`, e)
    }
  }

  for (const jobId of createdResources.trainingJobs) {
    try {
      await page.request.delete(`${apiBase}/training/${jobId}`)
    } catch (e) {
      console.log(`Failed to cleanup training job ${jobId}:`, e)
    }
  }

  // 清空记录
  createdResources.datasets = []
  createdResources.images = []
  createdResources.annotations = []
  createdResources.models = []
  createdResources.templates = []
  createdResources.trainingJobs = []
}

/**
 * 生成唯一的测试数据名称
 */
export function generateTestName(prefix: string): string {
  return `${TEST_DATA_PREFIX}${prefix}-${Date.now()}-${Math.random().toString(36).substring(7)}`
}

/**
 * 重置测试资源记录
 */
export function resetTestResources(): void {
  createdResources.datasets = []
  createdResources.images = []
  createdResources.annotations = []
  createdResources.models = []
  createdResources.templates = []
  createdResources.trainingJobs = []
}

/**
 * 记录创建的资源 ID
 */
export function recordResource(type: keyof typeof createdResources, id: string): void {
  createdResources[type].push(id)
}

// 扩展 Playwright Test 类型
interface TestFixtures {
  testData: {
    cleanup: () => Promise<void>
    generateName: (prefix: string) => string
    reset: () => void
    record: (type: keyof typeof createdResources, id: string) => void
  }
  authenticatedPage: Page
}

// 创建带有测试数据 fixture 的基础测试
export const test = base.extend<TestFixtures>({
  // 测试数据管理 fixture
  testData: async ({ page }, use) => {
    const testDataManager = {
      cleanup: async () => {
        await cleanupTestData(page)
      },
      generateName: generateTestName,
      reset: resetTestResources,
      record: recordResource,
    }

    await use(testDataManager)
  },

  // 已认证页面的便捷 fixture
  authenticatedPage: async ({ page }, use) => {
    // 确保页面已认证
    await page.goto('/')
    await page.waitForLoadState('networkidle')
    
    // 如果被重定向到登录页，进行登录
    if (page.url().includes('/login')) {
      await page.fill('input[placeholder="用户名"]', process.env.E2E_USER || 'admin')
      await page.fill('input[placeholder="密码"]', process.env.E2E_PASS || 'admin123')
      await page.click('button[type="submit"]')
      await page.waitForURL('**/images**', { timeout: 15000 })
    }

    await use(page)

    // 测试后清理
    await cleanupTestData(page)
  },
})

// 导出 expect 用于测试
export { expect } from '@playwright/test'
