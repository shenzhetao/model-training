import { defineConfig, devices } from '@playwright/test'
import * as path from 'path'

export default defineConfig({
  testDir: './tests',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 1,  // CI 环境重试 2 次，本地重试 1 次
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [['github'], ['html']] : [['html']],
  timeout: 30000,  // 单个测试超时 30 秒
  expect: {
    timeout: 10000,  // expect 断言超时 10 秒
  },

  use: {
    baseURL: process.env.BASE_URL || 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  globalSetup: './global-setup.ts',
  globalTeardown: './global-teardown.ts',

  // 测试匹配规则 - 用于在特定浏览器上跳过或仅运行特定测试
  testMatch: [
    '**/*.spec.ts',
  ],

  projects: [
    // Chromium 项目 - 主要测试平台
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'chromium.json'),
      },
    },
    // Firefox 项目
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: path.join(__dirname, '.auth', 'firefox.json'),
      },
    },
    // WebKit 项目 - 使用 WebKit 兼容测试
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: path.join(__dirname, '.auth', 'webkit.json'),
      },
      // WebKit 使用兼容测试替代
      testMatch: [
        '**/login.spec.ts',
        '**/page-load.spec.ts',
        '**/webkit-compat.spec.ts',  // WebKit 兼容测试
      ],
      testIgnore: [
        '**/annotations.spec.ts',
        '**/datasets.spec.ts',
        '**/images.spec.ts',
        '**/models.spec.ts',
        '**/templates.spec.ts',
        '**/training*.spec.ts',
        '**/inference.spec.ts',
        '**/user-flow.spec.ts',
      ],
    },
    // Mobile Chrome 项目 - 移动端测试配置
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        // 优化移动端上下文配置
        viewport: { width: 412, height: 915 },
        deviceScaleFactor: 2.625,
        isMobile: true,
        hasTouch: true,
        // 移动端使用独立的 storageState 文件
        storageState: path.join(__dirname, '.auth', 'mobile-chrome.json'),
      },
      // 移动端只运行移动端兼容测试
      testMatch: [
        '**/mobile-compat.spec.ts',
      ],
      testIgnore: [],
    },
    // Login tests project - fresh context without auth
    {
      name: 'chromium-fresh',
      testMatch: ['**/login.spec.ts'],
      testIgnore: ['**/page-load.spec.ts', '**/training*.spec.ts', '**/images.spec.ts', '**/datasets.spec.ts', '**/models.spec.ts', '**/templates.spec.ts', '**/inference.spec.ts'],
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],

  webServer: process.env.CI
    ? undefined
    : {
        command: 'cd .. && npm run dev',
        url: 'http://localhost:3000',
        reuseExistingServer: !process.env.CI,
        timeout: 120 * 1000,
      },
})
