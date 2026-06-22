<template>
  <div class="training-manager">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">训练管理</a-typography-title>
        <a-space>
          <a-tag v-for="(count, status) in statusCounts" :key="status" :color="statusColor(status)">
            {{ statusLabel(status) }}: {{ count }}
          </a-tag>
        </a-space>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="loadJobs">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showCreateJob = true">
            <template #icon><PlusOutlined /></template>
            新建训练
          </a-button>
        </a-space>
      </div>
    </div>

    <a-row :gutter="16">
      <!-- Left: Job List -->
      <a-col :span="currentJob ? 10 : 24">
        <a-card title="训练任务" size="small">
          <template #extra>
            <a-select
              v-model:value="filterStatus"
              placeholder="筛选状态"
              style="width: 140px"
              allowClear
              @change="loadJobs"
            >
              <a-select-option value="pending">等待中</a-select-option>
              <a-select-option value="running">进行中</a-select-option>
              <a-select-option value="completed">已完成</a-select-option>
              <a-select-option value="failed">失败</a-select-option>
            </a-select>
          </template>

          <a-table
            :data-source="jobs"
            :columns="columns"
            :loading="loading"
            :pagination="{ pageSize: 15 }"
            row-key="id"
            size="small"
            :scroll="{ x: 600 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'status'">
                <a-tag :color="statusColor(record.status)">
                  {{ statusLabel(record.status) }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'progress'">
                <a-progress
                  v-if="record.status === 'running' || record.status === 'completed'"
                  :percent="Math.round((record.current_epoch || 0) / record.epochs * 100)"
                  size="small"
                  :status="record.status === 'completed' ? 'success' : 'active'"
                />
                <span v-else class="no-progress">-</span>
              </template>
              <template v-else-if="column.key === 'metrics'">
                <a-space direction="vertical" size="small" style="font-size: 12px">
                  <span v-if="record.status === 'completed'">
                    <StarOutlined /> mAP50: <strong>{{ record.log_summary?.map50 ? (record.log_summary.map50 * 100).toFixed(1) + '%' : '-' }}</strong>
                  </span>
                  <span v-else>-</span>
                </a-space>
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="selectJob(record)">查看</a-button>
                  <a-button
                    v-if="record.status === 'running'"
                    type="link"
                    size="small"
                    danger
                    @click="handleStop(record)"
                  >停止</a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <!-- Right: Job Detail + Metrics -->
      <a-col :span="14" v-if="currentJob">
        <a-card size="small" style="margin-bottom: 16px">
          <template #title>
            <div class="job-detail-header">
              <span>{{ currentJob.name }}</span>
              <a-tag :color="statusColor(currentJob.status)">
                {{ statusLabel(currentJob.status) }}
              </a-tag>
            </div>
          </template>
          <template #extra>
            <a-button type="link" size="small" @click="currentJob = null">关闭</a-button>
          </template>

          <a-descriptions :column="3" size="small" bordered>
            <a-descriptions-item label="架构">{{ currentJob.base_model_architecture }}</a-descriptions-item>
            <a-descriptions-item label="Epochs">{{ currentJob.epochs }}</a-descriptions-item>
            <a-descriptions-item label="Batch">{{ currentJob.batch_size }}</a-descriptions-item>
            <a-descriptions-item label="图片尺寸">{{ currentJob.img_size }}px</a-descriptions-item>
            <a-descriptions-item label="学习率">{{ currentJob.lr0 }}</a-descriptions-item>
            <a-descriptions-item label="当前Epoch">
              {{ currentJob.current_epoch || 0 }} / {{ currentJob.epochs }}
            </a-descriptions-item>
            <a-descriptions-item label="GPU">{{ currentJob.gpu_device || '-' }}</a-descriptions-item>
            <a-descriptions-item label="开始时间">
              {{ currentJob.started_at ? new Date(currentJob.started_at).toLocaleString('zh-CN') : '-' }}
            </a-descriptions-item>
            <a-descriptions-item label="用时">
              {{ formatDuration(currentJob) }}
            </a-descriptions-item>
          </a-descriptions>

          <!-- Error message -->
          <a-alert
            v-if="currentJob.error_message"
            type="error"
            :message="currentJob.error_message"
            style="margin-top: 12px"
            show-icon
          />

          <!-- Live progress -->
          <a-progress
            v-if="currentJob.status === 'running'"
            :percent="Math.round((currentJob.current_epoch || 0) / currentJob.epochs * 100)"
            :status="'active'"
            style="margin-top: 16px"
          />
        </a-card>

        <!-- Metrics Chart -->
        <a-card title="训练指标" size="small">
          <a-tabs>
            <a-tab-pane key="loss" tab="Loss">
              <div ref="lossChartRef" class="chart-container"></div>
            </a-tab-pane>
            <a-tab-pane key="map" tab="mAP">
              <div ref="mapChartRef" class="chart-container"></div>
            </a-tab-pane>
            <a-tab-pane key="log" tab="原始日志">
              <div class="log-container">
                <pre class="log-pre">{{ jobLogPreview }}</pre>
              </div>
            </a-tab-pane>
          </a-tabs>
        </a-card>
      </a-col>
    </a-row>

    <!-- Create Job Modal -->
    <a-modal
      v-model:open="showCreateJob"
      title="发起训练"
      :width="700"
      @ok="handleCreateJob"
      :confirm-loading="starting"
    >
      <a-form :model="jobForm" layout="vertical">
        <a-form-item label="任务名称" required>
          <a-input v-model:value="jobForm.name" placeholder="如: game_ui_yolov8n_v1" />
        </a-form-item>

        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="数据集版本" required>
              <a-select
                v-model:value="jobForm.dataset_version_id"
                placeholder="选择数据集版本"
                show-search
                style="width: 100%"
              >
                <a-select-option v-for="v in availableVersions" :key="v.id" :value="v.id">
                  {{ v.dataset_name }} / {{ v.version_name }} ({{ v.image_count }} 图)
                </a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="模型架构">
              <a-select v-model:value="jobForm.base_model_architecture" style="width: 100%">
                <a-select-option value="yolov8n">YOLOv8 Nano (最轻量)</a-select-option>
                <a-select-option value="yolov8s">YOLOv8 Small</a-select-option>
                <a-select-option value="yolov8m">YOLOv8 Medium</a-select-option>
                <a-select-option value="yolov8l">YOLOv8 Large</a-select-option>
                <a-select-option value="yolov8x">YOLOv8 XLarge (最重)</a-select-option>
              </a-select>
            </a-form-item>
          </a-col>
        </a-row>

        <a-divider>训练参数</a-divider>

        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="Epochs">
              <a-input-number v-model:value="jobForm.epochs" :min="1" :max="1000" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Batch Size">
              <a-input-number v-model:value="jobForm.batch_size" :min="1" :max="256" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="图片尺寸">
              <a-input-number v-model:value="jobForm.img_size" :min="320" :max="1280" :step="32" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="初始学习率">
              <a-input-number v-model:value="jobForm.lr0" :min="0" :max="1" :step="0.001" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="最终学习率">
              <a-input-number v-model:value="jobForm.lrf" :min="0" :max="1" :step="0.001" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="Early Stop">
              <a-input-number v-model:value="jobForm.patience" :min="5" :max="200" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>

        <a-row :gutter="12">
          <a-col :span="8">
            <a-form-item label="Mosaic">
              <a-slider v-model:value="jobForm.mosaic" :min="0" :max="1" :step="0.1" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="MixUp">
              <a-slider v-model:value="jobForm.mixup" :min="0" :max="1" :step="0.1" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="水平翻转">
              <a-slider v-model:value="jobForm.flip_lr" :min="0" :max="1" :step="0.1" />
            </a-form-item>
          </a-col>
        </a-row>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, onUnmounted, watch } from 'vue'
import { message } from 'ant-design-vue'
import { ReloadOutlined, PlusOutlined, StarOutlined } from '@ant-design/icons-vue'
import { useTrainingStore } from '@/stores/training'
import trainingApi from '@/api/training'
import type { TrainingJob } from '@/api/training'

const store = useTrainingStore()
const jobs = computed(() => store.jobs)
const loading = computed(() => store.loading)
const starting = computed(() => store.starting)
const currentJob = computed(() => store.currentJob)
const metrics = computed(() => store.metrics)

const filterStatus = ref<string | null>(null)
const showCreateJob = ref(false)
const availableVersions = ref<any[]>([])
const jobLogPreview = ref('')
const lossChartRef = ref<HTMLDivElement | null>(null)
const mapChartRef = ref<HTMLDivElement | null>(null)

const columns = [
  { title: '任务名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '架构', dataIndex: 'base_model_architecture', key: 'base_model_architecture', width: 120 },
  { title: 'Epochs', dataIndex: 'epochs', key: 'epochs', width: 70,
    customRender: ({ record }: { record: TrainingJob }) => `${record.current_epoch || 0}/${record.epochs}` },
  { title: '状态', key: 'status', width: 90 },
  { title: '进度', key: 'progress', width: 150 },
  { title: 'mAP', key: 'metrics', width: 100 },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 150,
    customRender: ({ text }: { text: string }) => new Date(text).toLocaleDateString('zh-CN') },
  { title: '操作', key: 'action', width: 100 },
]

const statusCounts = computed(() => {
  const c: Record<string, number> = {}
  for (const j of jobs.value) {
    c[j.status] = (c[j.status] || 0) + 1
  }
  return c
})

function statusColor(status: string): string {
  return { pending: 'default', running: 'processing', completed: 'success', failed: 'error', cancelled: 'warning' }[status] || 'default'
}

function statusLabel(status: string): string {
  return { pending: '等待', running: '进行', completed: '完成', failed: '失败', cancelled: '已停止' }[status] || status
}

function formatDuration(job: TrainingJob): string {
  if (!job.started_at) return '-'
  const end = job.completed_at ? new Date(job.completed_at) : new Date()
  const start = new Date(job.started_at)
  const ms = end.getTime() - start.getTime()
  if (ms < 0) return '-'
  const h = Math.floor(ms / 3600000)
  const m = Math.floor((ms % 3600000) / 60000)
  const s = Math.floor((ms % 60000) / 1000)
  if (h > 0) return `${h}h ${m}m`
  if (m > 0) return `${m}m ${s}s`
  return `${s}s`
}

async function loadJobs() {
  await store.fetchJobs({ status: filterStatus.value || undefined })
}

async function selectJob(job: TrainingJob) {
  store.currentJob = job
  await store.fetchMetrics(job.id)
  if (job.log_output) {
    jobLogPreview.value = job.log_output.split('\n').slice(-200).join('\n')
  }
  if (job.status === 'running') {
    store.subscribeToLogs(job.id, (log) => {
      jobLogPreview.value = (jobLogPreview.value + '\n' + `Epoch ${log.epoch}: box=${log.train_box_loss?.toFixed(4)} cls=${log.train_cls_loss?.toFixed(4)} mAP50=${log.map50?.toFixed(4)}`).slice(-5000)
    })
  }
  renderCharts()
}

function renderCharts() {
  // Simple text-based chart fallback (could upgrade to Chart.js)
  const m = metrics.value
  if (!m.length) return

  // Loss chart as ASCII text
  if (lossChartRef.value) {
    const latest = m.slice(-50)
    const maxLoss = Math.max(...latest.map(l => l.train_box_loss || 0.01))
    const lines: string[] = []
    for (let row = 0; row < 8; row++) {
      const threshold = maxLoss * (8 - row) / 8
      const bar = latest.map(l => (l.train_box_loss || 0) >= threshold ? '█' : ' ').join('')
      lines.push(`${(threshold).toFixed(3).padStart(7)} │${bar}`)
    }
    lines.push('         └' + '─'.repeat(Math.min(latest.length, 50)))
    if (lossChartRef.value) lossChartRef.value.innerText = lines.join('\n')
  }

  if (mapChartRef.value) {
    const latest = m.slice(-50)
    const maxMap = Math.min(1, Math.max(...latest.map(l => l.map50 || 0.01)))
    const lines: string[] = []
    for (let row = 0; row < 8; row++) {
      const threshold = maxMap * (8 - row) / 8
      const bar = latest.map(l => (l.map50 || 0) >= threshold ? '█' : ' ').join('')
      lines.push(`${(threshold).toFixed(3).padStart(7)} │${bar}`)
    }
    lines.push('         └' + '─'.repeat(Math.min(latest.length, 50)))
    if (mapChartRef.value) mapChartRef.value.innerText = lines.join('\n')
  }
}

watch(metrics, () => { renderCharts() }, { deep: true })

// Create job
const jobForm = reactive({
  name: '',
  dataset_version_id: '',
  base_model_architecture: 'yolov8n',
  epochs: 50,
  batch_size: 8,
  img_size: 640,
  lr0: 0.01,
  lrf: 0.01,
  patience: 15,
  mosaic: 1.0,
  mixup: 0.0,
  flip_lr: 0.5,
})

async function loadAvailableVersions() {
  try {
    const datasets = await import('@/api/datasets').then(m => m.default.getList())
    const allVersions: any[] = []
    for (const ds of datasets) {
      const versions = await import('@/api/datasets').then(m => m.default.getVersions(ds.id))
      for (const v of versions) {
        allVersions.push({ ...v, dataset_name: ds.name })
      }
    }
    availableVersions.value = allVersions.filter(v => v.status === 'ready')
  } catch (e) { console.error(e) }
}

async function handleCreateJob() {
  if (!jobForm.name.trim()) { message.error('请填写任务名称'); return }
  if (!jobForm.dataset_version_id) { message.error('请选择数据集版本'); return }
  try {
    const job = await store.createJob(jobForm)
    message.success('训练任务已创建，稍后自动开始')
    showCreateJob.value = false
    jobForm.name = ''
    await loadJobs()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '创建失败')
  }
}

async function handleStop(job: TrainingJob) {
  await store.stopJob(job.id)
  message.success('训练已停止')
  await loadJobs()
}

onMounted(async () => {
  await loadJobs()
  await loadAvailableVersions()
})

onUnmounted(() => {
  store.closeEventSource()
})
</script>

<style scoped>
.training-manager { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }
.job-detail-header { display: flex; align-items: center; gap: 8px; }
.no-progress { color: #999; }
.log-container { max-height: 400px; overflow-y: auto; background: #1e1e1e; border-radius: 8px; padding: 12px; }
.log-pre { color: #d4d4d4; font-size: 11px; font-family: monospace; white-space: pre-wrap; margin: 0; }
.chart-container {
  background: #1e1e1e;
  border-radius: 8px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  color: #d4d4d4;
  white-space: pre;
  overflow-x: auto;
  min-height: 180px;
}
</style>
