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

  projects: [
    {
      name: 'chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: path.join(__dirname, '.auth', 'chromium.json'),
      },
    },
    {
      name: 'firefox',
      use: {
        ...devices['Desktop Firefox'],
        storageState: path.join(__dirname, '.auth', 'firefox.json'),
      },
    },
    {
      name: 'webkit',
      use: {
        ...devices['Desktop Safari'],
        storageState: path.join(__dirname, '.auth', 'webkit.json'),
      },
    },
    {
      name: 'Mobile Chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: path.join(__dirname, '.auth', 'mobile-chrome.json'),
      },
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
