<template>
  <div class="inference-playground">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">推理测试</a-typography-title>
        <a-tag :color="statusColor">{{ statusText }}</a-tag>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="handleCheckStatus" :loading="status === 'checking'">
            <template #icon><SyncOutlined :spin="status === 'checking'" /></template>
            检测设备
          </a-button>
          <a-button @click="handleRefreshScreenshot" :loading="screenshotLoading" :disabled="!isConnected">
            <template #icon><ReloadOutlined /></template>
            截图
          </a-button>
          <a-button
            :type="autoRefresh ? 'primary' : 'default'"
            :disabled="!isConnected"
            @click="toggleAutoRefresh"
          >
            <template #icon><FieldTimeOutlined /></template>
            {{ autoRefresh ? '停止' : '自动刷新' }}
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- Device Status Alert -->
    <a-alert
      v-if="!isConnected"
      :message="statusTitle"
      :description="screenshotError || '请确保 Android 设备已通过 USB 连接并启用 USB 调试模式'"
      :type="status === 'error' ? 'error' : 'warning'"
      show-icon
      style="margin-bottom: 16px"
    />

    <!-- Device Info Card -->
    <a-card v-if="device" style="margin-bottom: 16px">
      <a-descriptions :column="4" size="small">
        <a-descriptions-item label="设备ID">{{ device.device_id }}</a-descriptions-item>
        <a-descriptions-item label="型号">{{ device.model || '未知' }}</a-descriptions-item>
        <a-descriptions-item label="分辨率">{{ device.resolution[0] }} x {{ device.resolution[1] }}</a-descriptions-item>
        <a-descriptions-item label="状态">
          <a-badge status="success" text="已连接" />
        </a-descriptions-item>
      </a-descriptions>
    </a-card>

    <!-- Main Content -->
    <a-row :gutter="16">
      <!-- Left: Screenshot + Detection Canvas -->
      <a-col :span="16">
        <a-card title="实时画面" :loading="screenshotLoading">
          <template #extra>
            <a-space v-if="detections.length > 0">
              <span class="detection-count">
                检测到 <a-badge :count="detections.length" :number-style="{ backgroundColor: '#1890ff' }" :show-zero="true" /> 个元素
              </span>
            </a-space>
          </template>

          <div class="screenshot-container">
            <div v-if="!screenshotUrl && !screenshotLoading" class="screenshot-placeholder">
              <MobileOutlined class="placeholder-icon" />
              <p>点击「截图」按钮获取设备画面</p>
            </div>
            <img
              v-if="screenshotUrl"
              :src="screenshotUrl"
              alt="设备截图"
              class="screenshot-img"
              @error="handleImgError"
            />
          </div>

          <!-- Detection Overlay Canvas -->
          <div v-if="detections.length > 0" class="detection-overlay">
            <a-divider>检测结果</a-divider>
            <div class="detection-list">
              <a-table
                :data-source="detections"
                :columns="detectionColumns"
                :pagination="{ pageSize: 5 }"
                size="small"
                row-key="cls"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'conf'">
                    <a-progress
                      :percent="Math.round(record.conf * 100)"
                      :format="() => `${(record.conf * 100).toFixed(1)}%`"
                      size="small"
                      :stroke-color="getConfColor(record.conf)"
                    />
                  </template>
                  <template v-else-if="column.key === 'source'">
                    <a-tag :color="getSourceColor(record.source)">
                      {{ getSourceLabel(record.source) }}
                    </a-tag>
                  </template>
                </template>
              </a-table>
            </div>
          </div>
        </a-card>
      </a-col>

      <!-- Right: Controls Panel -->
      <a-col :span="8">
        <!-- Inference Mode -->
        <a-card title="推理模式" style="margin-bottom: 16px">
          <a-radio-group v-model:value="inferenceMode" button-style="solid" @change="handleModeChange">
            <a-radio-button value="hybrid">混合模式</a-radio-button>
            <a-radio-button value="template">仅模板</a-radio-button>
            <a-radio-button value="yolo">仅 YOLO</a-radio-button>
          </a-radio-group>
          <div class="mode-desc">
            <p v-if="inferenceMode === 'hybrid'">
              <strong>混合模式</strong>：同时运行模板匹配和 YOLO 推理，检测全部 5 类元素。
            </p>
            <p v-else-if="inferenceMode === 'template'">
              <strong>仅模板匹配</strong>：快速检测 btn_attack / btn_skill / hp_bar / dialog_next（&lt;5ms）。
            </p>
            <p v-else>
              <strong>仅 YOLO</strong>：深度学习推理，检测 quest_marker（~40ms/帧）。
            </p>
          </div>
        </a-card>

        <!-- YOLO Confidence -->
        <a-card title="检测参数" style="margin-bottom: 16px">
          <a-form layout="vertical">
            <a-form-item label="YOLO 置信度阈值" v-if="inferenceMode !== 'template'">
              <a-slider
                v-model:value="yoloConf"
                :min="0.05"
                :max="0.95"
                :step="0.05"
                :marks="{ 0.1: '低', 0.4: '中', 0.7: '高', 0.95: '最高' }"
              />
              <div class="conf-value">当前值: {{ (yoloConf * 100).toFixed(0) }}%</div>
            </a-form-item>

            <a-form-item label="自动刷新间隔">
              <a-slider
                v-model:value="refreshInterval"
                :min="2"
                :max="30"
                :step="1"
                :marks="{ 2: '2s', 10: '10s', 30: '30s' }"
                :disabled="autoRefresh"
              />
            </a-form-item>
          </a-form>
        </a-card>

        <!-- Run Inference -->
        <a-card title="推理操作">
          <a-space direction="vertical" style="width: 100%" size="middle">
            <a-button
              type="primary"
              block
              :loading="inferenceLoading"
              :disabled="!isConnected || !screenshotUrl"
              @click="handleRunInference"
            >
              <template #icon><ThunderboltOutlined /></template>
              推理检测
            </a-button>

            <a-button
              block
              :disabled="!isConnected"
              @click="handleCaptureAndInfer"
              :loading="screenshotLoading || inferenceLoading"
            >
              <template #icon><CameraOutlined /></template>
              截图 + 推理
            </a-button>

            <a-divider />

            <a-button
              v-if="detections.length > 0"
              block
              @click="handleExportDetections"
            >
              <template #icon><DownloadOutlined /></template>
              导出检测结果
            </a-button>

            <a-button
              v-if="detections.length > 0"
              type="text"
              block
              danger
              @click="detections = []"
            >
              清除检测结果
            </a-button>
          </a-space>
        </a-card>

        <!-- Legend -->
        <a-card title="检测类别说明" style="margin-top: 16px">
          <a-descriptions :column="1" size="small">
            <a-descriptions-item label="btn_attack">攻击按钮（模板匹配）</a-descriptions-item>
            <a-descriptions-item label="btn_skill">技能按钮（模板匹配，支持多槽位）</a-descriptions-item>
            <a-descriptions-item label="hp_bar_player">玩家血条（模板匹配）</a-descriptions-item>
            <a-descriptions-item label="dialog_next">对话框继续（模板匹配）</a-descriptions-item>
            <a-descriptions-item label="quest_marker">任务标记 NPC（YOLO 推理，图标 ?/!）</a-descriptions-item>
          </a-descriptions>
        </a-card>
      </a-col>
    </a-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import {
  SyncOutlined,
  ReloadOutlined,
  FieldTimeOutlined,
  MobileOutlined,
  ThunderboltOutlined,
  CameraOutlined,
  DownloadOutlined,
} from '@ant-design/icons-vue'
import { useADBDeviceStore } from '@/stores/adb'
import type { InferenceMode } from '@/stores/adb'
import type { DetectionItem } from '@/api/adb'

const adbStore = useADBDeviceStore()

const refreshInterval = ref(5)

const status = computed(() => adbStore.status)
const device = computed(() => adbStore.device)
const screenshotUrl = computed(() => adbStore.screenshotUrl)
const screenshotLoading = computed(() => adbStore.screenshotLoading)
const screenshotError = computed(() => adbStore.screenshotError)
const inferenceLoading = computed(() => adbStore.inferenceLoading)
const detections = computed(() => adbStore.detections)
const inferenceMode = computed({
  get: () => adbStore.inferenceMode,
  set: (v: InferenceMode) => adbStore.setMode(v),
})
const yoloConf = computed({
  get: () => adbStore.yoloConf,
  set: (v: number) => adbStore.setYoloConf(v),
})
const autoRefresh = computed(() => adbStore.autoRefresh)

const isConnected = computed(() => status.value === 'connected')

const statusText = computed(() => {
  const map: Record<string, string> = {
    idle: '未检测',
    checking: '检测中',
    connected: '已连接',
    disconnected: '未连接',
    error: 'ADB 错误',
  }
  return map[status.value] || '未知'
})

const statusColor = computed(() => {
  const map: Record<string, string> = {
    idle: 'default',
    checking: 'processing',
    connected: 'success',
    disconnected: 'warning',
    error: 'error',
  }
  return map[status.value] || 'default'
})

const statusTitle = computed(() => {
  if (status.value === 'error') return 'ADB 不可用'
  if (status.value === 'checking') return '正在检测设备...'
  return '未检测到设备'
})

const detectionColumns = [
  { title: '类别', dataIndex: 'cls', key: 'cls', width: 140 },
  { title: '坐标', key: 'position', width: 120,
    customRender: ({ record }: { record: DetectionItem }) =>
      `${record.x}, ${record.y} (${record.w}x${record.h})`
  },
  { title: '置信度', key: 'conf', width: 140 },
  { title: '来源', key: 'source', width: 90 },
]

function getConfColor(conf: number): string {
  if (conf >= 0.8) return '#52c41a'
  if (conf >= 0.6) return '#1890ff'
  if (conf >= 0.4) return '#faad14'
  return '#f5222d'
}

function getSourceColor(source: string): string {
  if (source === 'yolo') return 'orange'
  if (source.startsWith('template')) return 'cyan'
  return 'default'
}

function getSourceLabel(source: string): string {
  if (source === 'yolo') return 'YOLO'
  if (source.startsWith('template:')) return `模板:${source.split(':')[1]}`
  return source
}

async function handleCheckStatus() {
  await adbStore.checkStatus()
  if (isConnected.value) {
    await adbStore.captureScreenshot()
  }
}

async function handleRefreshScreenshot() {
  await adbStore.captureScreenshot()
}

function toggleAutoRefresh() {
  if (autoRefresh.value) {
    adbStore.stopAutoRefresh()
  } else {
    adbStore.startAutoRefresh(refreshInterval.value * 1000)
  }
}

async function handleModeChange() {
  adbStore.setMode(inferenceMode.value)
}

async function handleRunInference() {
  await adbStore.runInference()
}

async function handleCaptureAndInfer() {
  await adbStore.captureScreenshot()
  await adbStore.runInference()
}

function handleImgError() {
  message.error('截图加载失败，请重试')
}

function handleExportDetections() {
  const data = JSON.stringify(detections.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `detections_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  message.success('检测结果已导出')
}

onMounted(async () => {
  await adbStore.checkStatus()
  if (isConnected.value) {
    await adbStore.captureScreenshot()
  }
})

onUnmounted(() => {
  adbStore.reset()
})
</script>

<style scoped>
.inference-playground {
  padding: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.screenshot-container {
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f5f5;
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.screenshot-placeholder {
  text-align: center;
  color: #999;
}

.placeholder-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.screenshot-img {
  max-width: 100%;
  display: block;
  border-radius: 8px;
}

.detection-overlay {
  margin-top: 16px;
}

.detection-count {
  font-size: 14px;
  color: #666;
}

.mode-desc {
  margin-top: 12px;
  padding: 12px;
  background: #fafafa;
  border-radius: 6px;
  font-size: 13px;
  color: #666;
}

.mode-desc p {
  margin: 0;
  line-height: 1.6;
}

.conf-value {
  text-align: center;
  color: #1890ff;
  font-weight: 500;
  margin-top: 4px;
}
</style>
