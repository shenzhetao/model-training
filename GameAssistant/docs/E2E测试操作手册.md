# GameAssistant Web E2E 测试操作手册

> 生成日期：2026-06-24
> 当前循环：35（Loop 机制已停止）

---

## 一、项目结构

```
c:\project\modelTraining\GameAssistant
├── docs/
│   └── loop/                 # 循环开发文档
│       ├── loop.md            # 循环机制说明
│       ├── loop-031/          # 第31轮文档
│       ├── loop-032/
│       ├── loop-033/
│       ├── loop-034/
│       └── loop-035/
└── web/
    └── frontend/
        └── e2e/               # E2E 测试根目录
            ├── playwright.config.ts
            ├── global-setup.ts         # 登录认证
            ├── global-teardown.ts      # 测试后清理
            ├── fixtures/
            │   └── test-data.ts        # 测试数据管理
            ├── helpers/
            │   └── test-utils.ts       # 辅助工具函数
            └── tests/
                ├── login.spec.ts        # 登录测试
                ├── annotations.spec.ts  # 标注管理测试
                ├── datasets.spec.ts     # 数据集测试
                ├── images.spec.ts       # 图片管理测试
                ├── models.spec.ts       # 模型管理测试
                ├── templates.spec.ts    # 模板管理测试
                ├── training.spec.ts     # 训练管理测试
                ├── training-basic.spec.ts
                ├── inference.spec.ts    # 推理测试
                ├── user-flow.spec.ts    # 完整用户流程
                ├── webkit-compat.spec.ts # WebKit 兼容性
                ├── mobile-compat.spec.ts # 移动端兼容性
                └── page-load.spec.ts     # 页面加载测试
```

---

## 二、运行测试

### 2.1 前置条件

1. **启动前端开发服务器**（在另一个终端）：

```bash
cd c:\project\modelTraining\GameAssistant\web\frontend
npm run dev
```

2. **安装/更新依赖**：

```bash
cd c:\project\modelTraining\GameAssistant\web\frontend\e2e
npm install
```

### 2.2 基础命令

#### 切换到测试目录

```bash
cd c:\project\modelTraining\GameAssistant\web\frontend\e2e
```

**作用**：所有后续的 Playwright 命令都需要在 `e2e` 目录下执行，因为该目录包含了 `playwright.config.ts` 配置文件、`package.json`、以及 `tests/` 测试文件。Playwright 会自动读取该目录下的配置和测试文件。

---

#### 命令 1：运行完整测试套件

```bash
npx playwright test --config=playwright.config.ts
```

| 参数 | 含义 |
|------|------|
| `npx playwright test` | 调用 Playwright 的测试运行器 |
| `--config=playwright.config.ts` | 指定配置文件路径（必须） |

**作用**：执行 `tests/` 目录下所有 `.spec.ts` 文件中的测试用例，按照 `playwright.config.ts` 中定义的所有 `projects`（浏览器配置）依次运行。

**实际效果**：
- 依次运行 chromium、firefox、webkit、Mobile Chrome 四个浏览器项目
- 所有测试用例全部执行
- 生成 HTML 测试报告
- 汇总每个浏览器的通过/失败/跳过数量

**输出示例**：
```
chromium ......... 95 passed (42s)
firefox .......... 90 passed, 5 skipped (38s)
webkit ........... 25 passed, 70 skipped (21s)
Mobile Chrome ... 8 passed, 87 skipped (15s)
```

---

#### 命令 2：运行指定浏览器

```bash
npx playwright test --config=playwright.config.ts --project=chromium
npx playwright test --config=playwright.config.ts --project=firefox
npx playwright test --config=playwright.config.ts --project=webkit
```

| 参数 | 含义 |
|------|------|
| `--project=chromium` | 只运行名称为 `chromium` 的项目配置 |

**作用**：只执行指定浏览器项目中的测试，跳过其他浏览器项目。这是最常用的命令，用于：

- **chromium**：开发调试首选，速度最快，兼容性最好，推荐日常使用
- **firefox**：验证 Firefox 兼容性
- **webkit**：验证 Safari/WebKit 兼容性（测试用例较少，部分敏感用例被跳过）

**为什么常用 chromium**：
- Chromium 是 Chrome 的开源版本，测试最稳定
- 执行速度最快（约 40-50 秒）
- 覆盖的测试用例最全面（95 个）

---

#### 命令 3：运行指定测试文件

```bash
npx playwright test --config=playwright.config.ts tests/annotations.spec.ts
npx playwright test --config=playwright.config.ts tests/login.spec.ts
```

**作用**：只执行指定的测试文件，在所有匹配的浏览器项目中运行该文件中的测试用例。

**参数说明**：
- `tests/annotations.spec.ts` — 相对路径，从 `e2e` 目录指向 `tests/` 下的具体测试文件
- 可以省略 `.ts` 后缀，写成 `tests/annotations`

**实际效果**：
- 例如 `tests/annotations.spec.ts` 包含 16 个测试用例
- 在 chromium 和 firefox 两个浏览器中分别运行
- 总计执行 32 个测试（16 × 2）

**使用场景**：
- 调试某个模块时，只运行该模块的测试，避免等待完整套件
- 开发新功能时，频繁运行单个文件加快迭代速度

---

#### 命令 4：运行带 UI 的测试（调试用）

```bash
npx playwright test --config=playwright.config.ts --project=chromium --headed
```

| 参数 | 含义 |
|------|------|
| `--headed` | 以"有头"模式运行，即显示浏览器窗口 |

**作用**：默认 Playwright 以"无头"（headless）模式运行，即在后台无界面运行。加上 `--headed` 后会打开真实的浏览器窗口，可以：

- 实时观察测试执行过程
- 看到页面上的实际操作（点击、输入、跳转等）
- 在测试暂停时检查页面 DOM 状态
- 排查选择器问题（肉眼可见地看到点了哪里）

**注意**：
- 会显著减慢测试速度
- 不适合 CI/CD 环境
- 通常配合 `--timeout=60000` 增加超时时间

---

#### 命令 5：查看 HTML 测试报告

```bash
npx playwright show-report
```

**作用**：打开上一次测试运行生成的 HTML 报告，在浏览器中以可视化方式展示测试结果。

**报告内容包括**：
- 每个测试用例的通过/失败状态
- 失败用例的错误信息和截图
- 测试执行耗时统计
- 每个浏览器的通过率对比

**文件位置**：`e2e/playwright-report/` 目录下

**注意**：`show-report` 使用的是上一次运行生成的报告，需要先执行过 `playwright test` 后才有报告可查看。

### 2.3 常用调试命令

```bash
# 单个测试，headed 模式
npx playwright test --config=playwright.config.ts tests/login.spec.ts --headed --project=chromium --timeout=60000

# 显示所有打印语句
npx playwright test --config=playwright.config.ts --reporter=list

# 在第一行错误处停止
npx playwright test --config=playwright.config.ts --project=chromium --debug
```

### 2.4 CI 命令

```bash
cd c:\project\modelTraining\GameAssistant\web\frontend\e2e

# 生成新的认证状态（chromium）
npx playwright test --config=playwright.config.ts --project=chromium-fresh

# 运行 CI 模式（1次重试）
npx playwright test --config=playwright.config.ts --project=chromium --retries=2
```

---

## 三、认证配置

### 3.1 认证文件位置

认证状态文件存储在 `e2e/.auth/` 目录：

| 文件 | 用途 |
|------|------|
| `.auth/chromium.json` | Desktop Chromium |
| `.auth/firefox.json` | Desktop Firefox |
| `.auth/webkit.json` | Desktop WebKit |
| `.auth/mobile-chrome.json` | Mobile Chrome |

### 3.2 重新生成认证

如果登录失败，需要重新生成认证状态：

```bash
cd c:\project\modelTraining\GameAssistant\web\frontend\e2e

# 编辑 .env 文件设置测试账号
echo "E2E_TEST_USERNAME=your_username" > .env
echo "E2E_TEST_PASSWORD=your_password" >> .env

# 重新生成认证
npx playwright test --config=playwright.config.ts --project=chromium-fresh

# 手动删除后重新生成
rm .auth/chromium.json
npx playwright test --config=playwright.config.ts --project=chromium-fresh tests/login.spec.ts
```

### 3.3 认证环境变量

在 `e2e/.env` 文件中配置：

```
E2E_BASE_URL=http://localhost:3000
E2E_TEST_USERNAME=admin
E2E_TEST_PASSWORD=admin123
```

---

## 四、测试文件说明

### 4.1 各测试模块职责

| 测试文件 | 测试内容 | 浏览器支持 |
|----------|----------|------------|
| `login.spec.ts` | 登录成功/失败、路由守卫 | Chromium, Firefox, WebKit |
| `annotations.spec.ts` | 标注管理：Tab切换、弹窗、分类、审核 | Chromium, Firefox |
| `datasets.spec.ts` | 数据集：CRUD、版本管理 | Chromium |
| `images.spec.ts` | 图片管理：上传、筛选、视频抽帧 | Chromium |
| `models.spec.ts` | 模型管理：上传详情、筛选 | Chromium |
| `templates.spec.ts` | 模板管理：搜索、筛选、上传 | Chromium |
| `training.spec.ts` | 训练管理：ECharts图表、Tab切换 | Chromium |
| `training-basic.spec.ts` | 训练管理：基础UI验证 | Chromium |
| `inference.spec.ts` | 推理测试：视频/图片模式、历史 | Chromium |
| `user-flow.spec.ts` | 完整用户流程：登录→训练→推理 | Chromium |
| `webkit-compat.spec.ts` | WebKit兼容性测试 | WebKit |
| `mobile-compat.spec.ts` | 移动端兼容性测试 | Mobile Chrome |
| `page-load.spec.ts` | 页面加载验证、控制台错误 | Chromium, Firefox, WebKit |

### 4.2 辅助工具

**test-data.ts** - 测试数据管理：

```typescript
import { generateTestName, cleanupTestData } from '../fixtures/test-data';

// 生成唯一测试数据名称
const testDatasetName = generateTestName('Dataset');

// 记录创建的资源
recordResource({ type: 'dataset', name: testDatasetName });

// 测试后清理
await cleanupTestData();
```

**test-utils.ts** - 通用辅助函数：

```typescript
import { waitForModal, closeModal, fillForm, selectDropdown } from '../helpers/test-utils';

// 等待 Modal 出现
await waitForModal(page, '创建数据集');

// 关闭 Modal
await closeModal(page);

// 填充表单
await fillForm(page, { name: 'Test', description: 'Test Desc' });

// 选择下拉框
await selectDropdown(page, '选择类型', '类型A');
```

---

## 五、配置说明

### 5.1 playwright.config.ts 关键配置

```typescript
// 测试超时
timeout: 30000,
expect: { timeout: 10000 },

// 全局重试
retries: process.env.CI ? 2 : 1,

// 并行执行（CI 中禁用）
workers: process.env.CI ? 1 : undefined,

// 浏览器视口
chromium: { viewport: { width: 1920, height: 1080 } },
firefox: { viewport: { width: 1920, height: 1080 } },
webkit: { viewport: { width: 1920, height: 1080 } },
"Mobile Chrome": { viewport: { width: 412, height: 915 }, deviceScaleFactor: 2.625 },
```

### 5.2 添加新的测试浏览器

在 `playwright.config.ts` 中的 `projects` 数组添加：

```typescript
{
  name: 'safari',
  use: {
    browserName: 'webkit',
    channel: 'safari',
    ...devices['Safari'],
  },
  testMatch: [/.*\.spec\.ts/],
  dependencies: ['chromium-fresh'],
},
```

### 5.3 调整测试匹配规则

如果某个浏览器跳过某些测试，在配置中添加 `testIgnore`：

```typescript
{
  name: 'webkit',
  use: { ...devices['WebKit'] },
  testMatch: [/.*\.spec\.ts/],
  testIgnore: [
    /annotations\.spec\.ts/,
    /datasets\.spec\.ts/,
  ],
},
```

---

## 六、循环开发机制

### 6.1 循环结构

每个循环（Loop）包含两个阶段：

1. **开发循环**（奇数轮）：执行开发任务，创建/修改代码
2. **评估循环**（偶数轮）：评估上一轮成果，生成下一轮建议

### 6.2 循环文档位置

```
docs/loop/
├── loop.md                    # 机制说明文档
├── loop-031/
│   ├── 修改与测试报告.md       # 本轮做了什么
│   └── 任务建议.md             # 下轮要做什么
├── loop-032/
├── loop-033/
├── loop-034/
└── loop-035/
```

### 6.3 新增一个循环的步骤

1. 创建文件夹：`docs/loop/loop-0XX/`
2. 开发 Agent 执行任务
3. Agent 创建 `修改与测试报告.md`
4. Agent 创建 `任务建议.md`
5. Git 提交

---

## 七、常见问题排查

### 7.1 测试全部失败 - 登录问题

```bash
# 检查认证文件是否存在
ls c:\project\modelTraining\GameAssistant\web\frontend\e2e\.auth\

# 删除旧认证重新生成
rm c:\project\modelTraining\GameAssistant\web\frontend\e2e\.auth\chromium.json
npx playwright test --config=playwright.config.ts --project=chromium-fresh tests/login.spec.ts

# 检查后端服务是否运行
curl http://localhost:3000/api/auth/login
```

### 7.2 选择器找不到元素

```typescript
// 使用更稳定的选择器（按优先级）
await page.click('[data-testid="submit-btn"]');    // 最稳定
await page.click('button[type="submit"]');        // 次稳定
await page.click('.ant-btn-primary');              // 不稳定
await page.click('text=提交');                     // 文本匹配
```

### 7.3 等待超时

```typescript
// 增加等待时间
test.setTimeout(60000);

// 使用条件等待
await page.waitForResponse(
  response => response.url().includes('/api/') && response.status() === 200,
  { timeout: 30000 }
);

// 等待元素可见
await page.waitForSelector('.ant-table-row', { state: 'visible', timeout: 30000 });
```

### 7.4 跨浏览器测试不一致

```typescript
test('跨浏览器测试', async ({ browserName }) => {
  test.skip(browserName === 'webkit', 'WebKit 不支持此功能');
  // ...
});
```

---

## 八、Git 工作流

### 8.1 提交规范

```bash
# 循环提交格式
git add .
git commit -m "Loop XXX: <本次修改的简要描述>"

# 示例
git commit -m "Loop 035: Fix annotations tab switching and add webkit tests"
```

### 8.2 查看历史

```bash
# 查看最近的循环提交
git log --oneline -20

# 查看某个循环的修改
git show <commit-hash>

# 查看当前未提交的修改
git status
```

---

## 九、性能基准

| 指标 | 当前值 | 目标值 |
|------|--------|--------|
| 完整测试执行时间 | ~54秒 | <60秒 |
| Chromium 通过率 | 100% | 保持 |
| Firefox 通过率 | 100% | 保持 |
| WebKit 通过率 | 100% | 保持 |
| Mobile 通过率 | 100% | 保持 |

---

## 十、联系人与资源

- **项目文档**: `c:\project\modelTraining\GameAssistant\docs\`
- **Playwright 官网**: https://playwright.dev/
- **Loop 机制说明**: `docs/loop/loop.md`
- **最新循环文档**: `docs/loop/loop-035/`
