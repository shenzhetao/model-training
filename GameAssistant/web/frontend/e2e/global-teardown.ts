// global-teardown.ts — cleanup after all tests
import * as fs from 'fs'
import * as path from 'path'

async function globalTeardown() {
  // 清理测试期间生成的认证文件（保留用于下次测试）
  // 注意：在 CI 环境中清理，本地开发环境保留以便快速重试
  
  if (process.env.CI) {
    const authDir = path.join(__dirname, '.auth')
    if (fs.existsSync(authDir)) {
      const authFiles = fs.readdirSync(authDir).filter(f => f.endsWith('.json'))
      for (const file of authFiles) {
        try {
          fs.unlinkSync(path.join(authDir, file))
          console.log(`Cleaned up auth file: ${file}`)
        } catch (e) {
          console.log(`Failed to clean up auth file: ${file}`)
        }
      }
    }
  }

  // 清理测试结果中的临时文件
  const testResultsDir = path.join(__dirname, 'test-results')
  if (fs.existsSync(testResultsDir)) {
    // 保留最后一次运行的报告
    const files = fs.readdirSync(testResultsDir)
    const now = Date.now()
    const maxAge = 7 * 24 * 60 * 60 * 1000 // 7 天

    for (const file of files) {
      const filePath = path.join(testResultsDir, file)
      const stats = fs.statSync(filePath)
      if (now - stats.mtimeMs > maxAge) {
        try {
          fs.unlinkSync(filePath)
          console.log(`Cleaned up old test result: ${file}`)
        } catch (e) {
          console.log(`Failed to clean up test result: ${file}`)
        }
      }
    }
  }

  console.log('Global teardown completed')
}

export default globalTeardown
