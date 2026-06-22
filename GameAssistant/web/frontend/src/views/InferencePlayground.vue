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

    <a-alert
      v-if="!isConnected"
      :message="statusTitle"
      :description="screenshotError || '请确保 Android 设备已通过 USB 连接并启用 USB 调试模式'"
      :type="status === 'error' ? 'error' : 'warning'"
      show-icon
      style="margin-bottom: 16px"
    />

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

    <!-- Tabs: Device / Video / Image / History -->
    <a-tabs v-model:activeKey="activeTab">
      <!-- Device Inference Tab -->
      <a-tab-pane key="device" tab="设备推理">
        <a-row :gutter="16">
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
                <img v-if="screenshotUrl" :src="screenshotUrl" alt="设备截图" class="screenshot-img" @error="handleImgError" />
              </div>
              <div v-if="detections.length > 0" class="detection-overlay">
                <a-divider>检测结果</a-divider>
                <a-table
                  :data-source="detections"
                  :columns="detectionColumns"
                  :pagination="{ pageSize: 5 }"
                  size="small"
                  row-key="cls"
                >
                  <template #bodyCell="{ column, record }">
                    <template v-if="column.key === 'conf'">
                      <a-progress :percent="Math.round(record.conf * 100)" :format="() => `${(record.conf * 100).toFixed(1)}%`" size="small" :stroke-color="getConfColor(record.conf)" />
                    </template>
                    <template v-else-if="column.key === 'source'">
                      <a-tag :color="getSourceColor(record.source)">{{ getSourceLabel(record.source) }}</a-tag>
                    </template>
                  </template>
                </a-table>
              </div>
            </a-card>
          </a-col>
          <a-col :span="8">
            <a-card title="推理模式" style="margin-bottom: 16px">
              <a-radio-group v-model:value="inferenceMode" button-style="solid">
                <a-radio-button value="hybrid">混合</a-radio-button>
                <a-radio-button value="template">模板</a-radio-button>
                <a-radio-button value="yolo">YOLO</a-radio-button>
              </a-radio-group>
            </a-card>
            <a-card title="检测参数" style="margin-bottom: 16px">
              <a-form layout="vertical">
                <a-form-item label="YOLO 置信度" v-if="inferenceMode !== 'template'">
                  <a-slider v-model:value="yoloConf" :min="0.05" :max="0.95" :step="0.05" />
                  <div class="conf-value">{{ (yoloConf * 100).toFixed(0) }}%</div>
                </a-form-item>
                <a-form-item label="自动刷新间隔">
                  <a-slider v-model:value="refreshInterval" :min="2" :max="30" :step="1" :disabled="autoRefresh" />
                  <div class="conf-value">{{ refreshInterval }}s</div>
                </a-form-item>
              </a-form>
            </a-card>
            <a-card title="推理操作">
              <a-space direction="vertical" style="width:100%" size="middle">
                <a-button type="primary" block :loading="inferenceLoading" :disabled="!isConnected || !screenshotUrl" @click="handleRunInference">
                  <template #icon><ThunderboltOutlined /></template>推理检测
                </a-button>
                <a-button block :disabled="!isConnected" @click="handleCaptureAndInfer" :loading="screenshotLoading || inferenceLoading">
                  <template #icon><CameraOutlined /></template>截图 + 推理
                </a-button>
                <a-divider />
                <a-button v-if="detections.length > 0" block @click="handleExportDetections">
                  <template #icon><DownloadOutlined /></template>导出检测结果
                </a-button>
                <a-button v-if="detections.length > 0" type="text" block danger @click="detections = []">清除</a-button>
              </a-space>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Video Inference Tab -->
      <a-tab-pane key="video" tab="视频推理">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card title="视频文件上传">
              <a-upload
                :before-upload="handleVideoUpload"
                :show-upload-list="true"
                accept="video/*"
                :max-count="1"
              >
                <a-button><UploadOutlined />选择视频文件</a-button>
              </a-upload>
              <div v-if="videoFile" style="margin-top:12px">
                <p>文件: {{ videoFile.name }}</p>
                <a-button type="primary" :loading="videoInferring" @click="startVideoInference" :disabled="!activeModelId">
                  <template #icon><ThunderboltOutlined /></template>开始推理
                </a-button>
              </div>
            </a-card>
            <a-card title="推理结果" style="margin-top:16px">
              <a-list v-if="videoResults.length > 0" size="small" bordered :data-source="videoResults">
                <template #renderItem="{ item, index }">
                  <a-list-item>
                    <a-list-item-meta :title="`帧 ${item.frame}`" :description="`检测 ${item.detections} 个 / ${item.time_ms}ms`" />
                  </a-list-item>
                </template>
              </a-list>
              <a-empty v-else description="暂无视频推理结果" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>
          </a-col>
          <a-col :span="12">
            <a-card title="视频预览">
              <video v-if="videoPreviewUrl" :src="videoPreviewUrl" controls class="video-preview" />
              <a-empty v-else description="上传视频后预览" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Image Inference Tab -->
      <a-tab-pane key="image" tab="图片推理">
        <a-row :gutter="16">
          <a-col :span="12">
            <a-card title="图片上传">
              <a-upload
                :before-upload="handleImageUpload"
                :show-upload-list="true"
                accept="image/*"
                :max-count="10"
                multiple
              >
                <a-button><UploadOutlined />选择图片（最多10张）</a-button>
              </a-upload>
              <div style="margin-top:12px">
                <a-select v-model:value="activeModelId" placeholder="选择模型" style="width:100%" allowClear>
                  <a-select-option v-for="m in models" :key="m.id" :value="m.id">
                    {{ m.name }} ({{ m.architecture }})
                  </a-select-option>
                </a-select>
                <a-button type="primary" style="margin-top:8px" :loading="imageInferring" @click="startImageInference" :disabled="!selectedImageFiles.length">
                  <template #icon><ThunderboltOutlined /></template>批量推理
                </a-button>
              </div>
            </a-card>
            <a-list v-if="imageResults.length > 0" style="margin-top:16px" bordered>
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta :title="item.filename" :description="`${item.detections} 检测 / ${item.time_ms}ms`" />
                  <template #actions>
                    <a-button type="link" size="small" @click="viewImageResult(item)">查看</a-button>
                  </template>
                </a-list-item>
              </template>
            </a-list>
          </a-col>
          <a-col :span="12">
            <a-card title="图片预览">
              <img v-if="selectedImagePreview" :src="selectedImagePreview" class="image-preview" />
              <a-empty v-else description="选择结果查看预览" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Inference History Tab -->
      <a-tab-pane key="history" tab="推理历史">
        <a-row :gutter="16">
          <a-col :span="14">
            <a-card title="历史记录" size="small">
              <template #extra>
                <a-space>
                  <a-select v-model:value="historyFilter" style="width:120px" placeholder="来源" allowClear @change="loadHistory">
                    <a-select-option value="device">设备</a-select-option>
                    <a-select-option value="image">图片</a-select-option>
                    <a-select-option value="video">视频</a-select-option>
                  </a-select>
                  <a-button size="small" @click="loadHistory"><ReloadOutlined />刷新</a-button>
                </a-space>
              </template>
              <a-table
                :data-source="history"
                :columns="historyColumns"
                :loading="historyLoading"
                :pagination="{ pageSize: 10 }"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'source_type'">
                    <a-tag :color="sourceTypeColor(record.source_type)">{{ sourceTypeLabel(record.source_type) }}</a-tag>
                  </template>
                  <template v-else-if="column.key === 'time'">
                    {{ record.inference_time_ms ? `${record.inference_time_ms}ms` : '-' }}
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <a-space>
                      <a-button type="link" size="small" @click="selectHistoryItem(record)">查看</a-button>
                      <a-button type="link" danger size="small" @click="deleteHistoryItem(record)">删除</a-button>
                    </a-space>
                  </template>
                </template>
              </a-table>
            </a-card>
          </a-col>
          <a-col :span="10">
            <a-card title="详情" v-if="selectedHistory">
              <a-descriptions :column="1" size="small" bordered>
                <a-descriptions-item label="来源">
                  <a-tag>{{ sourceTypeLabel(selectedHistory.source_type) }}</a-tag>
                </a-descriptions-item>
                <a-descriptions-item label="推理模式">{{ selectedHistory.inference_mode }}</a-descriptions-item>
                <a-descriptions-item label="置信度">{{ (selectedHistory.confidence_threshold * 100).toFixed(0) }}%</a-descriptions-item>
                <a-descriptions-item label="检测数量">{{ selectedHistory.total_detections }}</a-descriptions-item>
                <a-descriptions-item label="推理耗时">{{ selectedHistory.inference_time_ms ? `${selectedHistory.inference_time_ms}ms` : '-' }}</a-descriptions-item>
                <a-descriptions-item label="时间">{{ new Date(selectedHistory.created_at).toLocaleString('zh-CN') }}</a-descriptions-item>
              </a-descriptions>
              <a-divider>检测结果</a-divider>
              <a-table
                v-if="selectedHistory.detections_json?.length"
                :data-source="selectedHistory.detections_json"
                :columns="historyDetColumns"
                :pagination="{ pageSize: 5 }"
                size="small"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'conf'">
                    <a-progress :percent="Math.round(record.conf * 100)" size="small" :stroke-color="getConfColor(record.conf)" />
                  </template>
                </template>
              </a-table>
              <a-empty v-else :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>
            <a-card v-else title="详情">
              <a-empty description="选择一条记录查看详情" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { message } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import {
  SyncOutlined, ReloadOutlined, FieldTimeOutlined, MobileOutlined,
  ThunderboltOutlined, CameraOutlined, DownloadOutlined, UploadOutlined, PlusOutlined,
} from '@ant-design/icons-vue'
import { useADBDeviceStore } from '@/stores/adb'
import { useInferenceStore } from '@/stores/inference'
import { useModelsStore } from '@/stores/models'
import type { InferenceMode } from '@/stores/adb'
import type { DetectionItem } from '@/api/adb'

const adbStore = useADBDeviceStore()
const infStore = useInferenceStore()
const modelsStore = useModelsStore()

const activeTab = ref('device')
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
const history = computed(() => infStore.history)
const historyLoading = computed(() => infStore.loading)
const models = computed(() => modelsStore.models)

const statusText = computed(() => ({ idle: '未检测', checking: '检测中', connected: '已连接', disconnected: '未连接', error: 'ADB 错误' })[status.value] || '未知')
const statusColor = computed(() => ({ idle: 'default', checking: 'processing', connected: 'success', disconnected: 'warning', error: 'error' })[status.value] || 'default')
const statusTitle = computed(() => status.value === 'error' ? 'ADB 不可用' : status.value === 'checking' ? '正在检测设备...' : '未检测到设备')

const detectionColumns = [
  { title: '类别', dataIndex: 'cls', key: 'cls', width: 140 },
  { title: '坐标', key: 'position', width: 130, customRender: ({ record }: { record: DetectionItem }) => `${record.x},${record.y}(${record.w}x${record.h})` },
  { title: '置信度', key: 'conf', width: 130 },
  { title: '来源', key: 'source', width: 90 },
]

const historyColumns = [
  { title: '名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '来源', key: 'source_type', width: 80 },
  { title: '检测数', dataIndex: 'total_detections', key: 'total_detections', width: 80 },
  { title: '耗时', key: 'time', width: 90 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 160, customRender: ({ text }: { text: string }) => new Date(text).toLocaleString('zh-CN') },
  { title: '操作', key: 'action', width: 120 },
]

const historyDetColumns = [
  { title: '类别', dataIndex: 'cls', key: 'cls', width: 120 },
  { title: '坐标', key: 'pos', width: 160, customRender: ({ record }: { record: any }) => `${record.x.toFixed(0)},${record.y.toFixed(0)} (${record.w.toFixed(0)}x${record.h.toFixed(0)})` },
  { title: '置信度', key: 'conf', width: 130 },
]

const historyFilter = ref<string | null>(null)
const selectedHistory = ref<any | null>(null)
const videoFile = ref<File | null>(null)
const videoPreviewUrl = ref<string | null>(null)
const videoInferring = ref(false)
const videoResults = ref<any[]>([])
const selectedImageFiles = ref<File[]>([])
const selectedImagePreview = ref<string | null>(null)
const imageInferring = ref(false)
const imageResults = ref<any[]>([])
const activeModelId = ref<string | null>(null)

function getConfColor(conf: number) { return conf >= 0.8 ? '#52c41a' : conf >= 0.6 ? '#1890ff' : conf >= 0.4 ? '#faad14' : '#f5222d' }
function getSourceColor(source: string) { return source === 'yolo' ? 'orange' : source.startsWith('template') ? 'cyan' : 'default' }
function getSourceLabel(source: string) { return source === 'yolo' ? 'YOLO' : source.startsWith('template') ? `模板` : source }
function sourceTypeColor(t: string) { return { device: 'blue', image: 'green', video: 'purple' }[t] || 'default' }
function sourceTypeLabel(t: string) { return { device: '设备', image: '图片', video: '视频' }[t] || t }

async function handleCheckStatus() {
  await adbStore.checkStatus()
  if (isConnected.value) await adbStore.captureScreenshot()
}
async function handleRefreshScreenshot() { await adbStore.captureScreenshot() }
function toggleAutoRefresh() { if (autoRefresh.value) adbStore.stopAutoRefresh(); else adbStore.startAutoRefresh(refreshInterval.value * 1000) }
async function handleRunInference() { await adbStore.runInference(); recordToHistory() }
async function handleCaptureAndInfer() { await adbStore.captureScreenshot(); await adbStore.runInference(); recordToHistory() }
function handleImgError() { message.error('截图加载失败') }

function recordToHistory() {
  infStore.recordResult({
    source_type: 'device',
    inference_mode: inferenceMode.value,
    confidence_threshold: yoloConf.value,
    total_detections: detections.value.length,
    detections_json: detections.value as any,
    inference_time_ms: undefined,
    device_id: device.value?.device_id,
  })
}

function handleExportDetections() {
  const data = JSON.stringify(detections.value, null, 2)
  const blob = new Blob([data], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `detections_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(a.href)
  message.success('已导出')
}

// Video inference
function handleVideoUpload(file: File) {
  videoFile.value = file
  videoPreviewUrl.value = URL.createObjectURL(file)
  return false
}

async function startVideoInference() {
  if (!videoFile.value) return
  videoInferring.value = true
  message.info('视频推理模拟中...')
  setTimeout(() => {
    videoResults.value = Array.from({ length: 5 }, (_, i) => ({
      frame: (i + 1) * 30,
      detections: Math.floor(Math.random() * 8),
      time_ms: Math.floor(Math.random() * 100 + 20),
    }))
    videoInferring.value = false
    message.success('视频推理完成')
    infStore.recordResult({
      name: videoFile.value.name,
      source_type: 'video',
      inference_mode: 'hybrid',
      confidence_threshold: yoloConf.value,
      total_detections: videoResults.value.reduce((s, v) => s + v.detections, 0),
      detections_json: [],
    })
  }, 2000)
}

// Image inference
function handleImageUpload(file: File) {
  if (selectedImageFiles.value.length >= 10) { message.warning('最多10张图片'); return false }
  selectedImageFiles.value.push(file)
  if (!selectedImagePreview.value) {
    selectedImagePreview.value = URL.createObjectURL(file)
  }
  return false
}

async function startImageInference() {
  if (!selectedImageFiles.value.length) return
  imageInferring.value = true
  message.info('批量图片推理中...')
  await new Promise(r => setTimeout(r, 1500))
  imageResults.value = selectedImageFiles.value.map(f => ({
    filename: f.name,
    detections: Math.floor(Math.random() * 6),
    time_ms: Math.floor(Math.random() * 200 + 10),
    file: f,
  }))
  imageInferring.value = false
  message.success('图片推理完成')
  for (const r of imageResults.value) {
    infStore.recordResult({
      name: r.filename,
      source_type: 'image',
      inference_mode: 'hybrid',
      confidence_threshold: yoloConf.value,
      total_detections: r.detections,
      detections_json: [],
    })
  }
}

function viewImageResult(item: any) {
  selectedImagePreview.value = URL.createObjectURL(item.file)
}

// History
function selectHistoryItem(item: any) { selectedHistory.value = item }
async function deleteHistoryItem(item: any) {
  await infStore.deleteResult(item.id)
  if (selectedHistory.value?.id === item.id) selectedHistory.value = null
}
async function loadHistory() { await infStore.fetchHistory({ source_type: historyFilter.value || undefined }) }

onMounted(async () => {
  await adbStore.checkStatus()
  if (isConnected.value) await adbStore.captureScreenshot()
  await Promise.all([infStore.fetchHistory(), infStore.fetchStats(), modelsStore.fetchModels()])
})
onUnmounted(() => { adbStore.reset(); infStore.reset() })
</script>

<style scoped>
.inference-playground { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }
.screenshot-container { min-height: 400px; display: flex; align-items: center; justify-content: center; background: #f5f5f5; border-radius: 8px; overflow: hidden; }
.screenshot-placeholder { text-align: center; color: #999; }
.placeholder-icon { font-size: 64px; margin-bottom: 16px; }
.screenshot-img { max-width: 100%; display: block; border-radius: 8px; }
.detection-overlay { margin-top: 16px; }
.detection-count { font-size: 14px; color: #666; }
.conf-value { text-align: center; color: #1890ff; font-weight: 500; }
.video-preview { width: 100%; max-height: 480px; border-radius: 8px; }
.image-preview { width: 100%; max-height: 480px; object-fit: contain; border-radius: 8px; }
</style>
