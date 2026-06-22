<template>
  <div class="model-manager">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">模型管理</a-typography-title>
        <a-tag v-if="stats" color="blue">
          {{ stats.total_models }} 个模型 / {{ stats.active_models }} 个活跃
        </a-tag>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="loadData">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showUpload = true">
            <template #icon><UploadOutlined /></template>
            上传模型
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- Stats Row -->
    <a-row :gutter="16" style="margin-bottom: 16px" v-if="stats">
      <a-col :span="6">
        <a-statistic title="模型总数" :value="stats.total_models" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="活跃模型" :value="stats.active_models" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="总大小" :value="stats.total_size_mb" suffix="MB" :precision="1" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="架构分布" :value="Object.keys(stats.by_architecture).length" suffix="种" />
      </a-col>
    </a-row>

    <a-row :gutter="16">
      <!-- Model List -->
      <a-col :span="selectedModel ? 14 : 24">
        <a-card title="模型列表" size="small">
          <template #extra>
            <a-select
              v-model:value="filterArch"
              placeholder="按架构筛选"
              style="width: 160px"
              allowClear
              @change="loadModels"
            >
              <a-select-option v-for="(count, arch) in stats?.by_architecture" :key="arch" :value="arch">
                {{ arch }} ({{ count }})
              </a-select-option>
            </a-select>
          </template>

          <a-table
            :data-source="models"
            :columns="columns"
            :loading="loading"
            :pagination="{ pageSize: 10 }"
            row-key="id"
            size="small"
            :scroll="{ x: 700 }"
          >
            <template #bodyCell="{ column, record }">
              <template v-if="column.key === 'is_active'">
                <a-tag :color="record.is_active ? 'green' : 'default'">
                  {{ record.is_active ? '活跃' : '非活跃' }}
                </a-tag>
              </template>
              <template v-else-if="column.key === 'metrics'">
                <a-space direction="vertical" size="small">
                  <span v-if="record.map50_95">
                    mAP: <strong>{{ (record.map50_95 * 100).toFixed(1) }}%</strong>
                  </span>
                  <span v-if="record.map50">
                    mAP50: <strong>{{ (record.map50 * 100).toFixed(1) }}%</strong>
                  </span>
                </a-space>
              </template>
              <template v-else-if="column.key === 'size'">
                {{ formatSize(record.file_size) }}
              </template>
              <template v-else-if="column.key === 'action'">
                <a-space>
                  <a-button type="link" size="small" @click="selectModel(record)">详情</a-button>
                  <a-button
                    v-if="!record.is_active"
                    type="link"
                    size="small"
                    :loading="activating === record.id"
                    @click="handleActivate(record)"
                  >设为默认</a-button>
                  <a-button type="link" danger size="small" @click="handleDelete(record)">删除</a-button>
                </a-space>
              </template>
            </template>
          </a-table>
        </a-card>
      </a-col>

      <!-- Model Detail -->
      <a-col :span="10" v-if="selectedModel">
        <a-card title="模型详情" size="small">
          <template #extra>
            <a-button type="link" size="small" @click="selectedModel = null">关闭</a-button>
          </template>

          <a-descriptions :column="1" size="small" bordered>
            <a-descriptions-item label="名称">{{ selectedModel.name }}</a-descriptions-item>
            <a-descriptions-item label="架构">{{ selectedModel.architecture }}</a-descriptions-item>
            <a-descriptions-item label="格式">{{ selectedModel.format.toUpperCase() }}</a-descriptions-item>
            <a-descriptions-item label="文件大小">{{ formatSize(selectedModel.file_size) }}</a-descriptions-item>
            <a-descriptions-item label="训练参数">
              {{ selectedModel.epochs || '-' }} epochs / {{ selectedModel.batch_size || '-' }} batch / {{ selectedModel.img_size || '-' }}px
            </a-descriptions-item>
            <a-descriptions-item label="性能指标" v-if="selectedModel.map50_95">
              mAP50-95: {{ (selectedModel.map50_95 * 100).toFixed(2) }}%
            </a-descriptions-item>
            <a-descriptions-item label="类别">
              <a-tag v-for="(n, i) in selectedModel.yolo_class_names" :key="i" style="margin: 2px">
                {{ n }}
              </a-tag>
              <span v-if="!selectedModel.yolo_class_names?.length">-</span>
            </a-descriptions-item>
            <a-descriptions-item label="描述">{{ selectedModel.description || '-' }}</a-descriptions-item>
            <a-descriptions-item label="上传时间">
              {{ new Date(selectedModel.created_at).toLocaleString('zh-CN') }}
            </a-descriptions-item>
          </a-descriptions>

          <!-- Training Metrics Chart Placeholder -->
          <a-divider>训练曲线</a-divider>
          <a-alert
            v-if="selectedModel.training_job_id"
            type="info"
            message="查看完整训练曲线，请在训练管理页面查看该任务详情。"
            show-icon
          />
          <a-empty v-else description="暂无训练记录" :image="Empty.PRESENTED_IMAGE_SIMPLE" />

          <!-- Tags -->
          <a-divider>标签</a-divider>
          <a-tag
            v-for="tag in (selectedModel.tags || [])"
            :key="tag"
            closable
            @close="removeTag(selectedModel, tag)"
          >
            {{ tag }}
          </a-tag>
          <a-input
            v-if="addingTag"
            ref="tagInputRef"
            size="small"
            style="width: 80px"
            v-model:value="newTag"
            @keyup.enter="addTag(selectedModel)"
            @blur="addingTag = false"
            placeholder="添加标签"
          />
          <a-button v-else size="small" type="dashed" @click="startAddTag">
            <template #icon><PlusOutlined /></template>
            标签
          </a-button>
        </a-card>
      </a-col>
    </a-row>

    <!-- Upload Modal -->
    <a-modal v-model:open="showUpload" title="上传模型" :width="500" @ok="handleUpload" :confirm-loading="uploading">
      <a-form :model="uploadForm" layout="vertical">
        <a-form-item label="模型文件 (.pt / .onnx)" required>
          <a-upload
            :before-upload="handleFileChange"
            :show-upload-list="false"
            accept=".pt,.pth,.onnx,.tflite"
          >
            <a-button><UploadOutlined />选择模型文件</a-button>
          </a-upload>
          <div v-if="uploadForm.file" class="file-preview">
            {{ uploadForm.file.name }} ({{ formatSize(uploadForm.file.size) }})
          </div>
        </a-form-item>
        <a-form-item label="模型名称" required>
          <a-input v-model:value="uploadForm.name" placeholder="如: game_ui_v1_best" />
        </a-form-item>
        <a-form-item label="架构">
          <a-select v-model:value="uploadForm.architecture">
            <a-select-option value="yolov8n">YOLOv8 Nano</a-select-option>
            <a-select-option value="yolov8s">YOLOv8 Small</a-select-option>
            <a-select-option value="yolov8m">YOLOv8 Medium</a-select-option>
            <a-select-option value="yolov8l">YOLOv8 Large</a-select-option>
            <a-select-option value="yolov8x">YOLOv8 XLarge</a-select-option>
            <a-select-option value="yolov5n">YOLOv5 Nano</a-select-option>
            <a-select-option value="yolov5s">YOLOv5 Small</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="uploadForm.description" :rows="2" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive, nextTick } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import { ReloadOutlined, UploadOutlined, PlusOutlined } from '@ant-design/icons-vue'
import { useModelsStore } from '@/stores/models'
import modelsApi from '@/api/models'
import type { TrainedModel } from '@/api/models'

const store = useModelsStore()
const models = computed(() => store.models)
const stats = computed(() => store.stats)
const loading = computed(() => store.loading)
const uploading = computed(() => store.uploading)

const selectedModel = ref<TrainedModel | null>(null)
const filterArch = ref<string | null>(null)
const activating = ref<string | null>(null)
const showUpload = ref(false)
const addingTag = ref(false)
const newTag = ref('')
const tagInputRef = ref<HTMLInputElement | null>(null)

const columns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '架构', dataIndex: 'architecture', key: 'architecture', width: 120 },
  { title: '状态', key: 'is_active', width: 80 },
  { title: '性能', key: 'metrics', width: 160 },
  { title: '大小', key: 'size', width: 100 },
  { title: '上传时间', dataIndex: 'created_at', key: 'created_at', width: 170,
    customRender: ({ text }: { text: string }) => new Date(text).toLocaleDateString('zh-CN') },
  { title: '操作', key: 'action', width: 180, fixed: 'right' },
]

const uploadForm = reactive({
  file: null as File | null,
  name: '',
  architecture: 'yolov8n',
  description: '',
})

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function selectModel(m: TrainedModel) { selectedModel.value = m }

async function loadModels() {
  await store.fetchModels({ architecture: filterArch.value || undefined })
}

async function loadData() {
  await Promise.all([loadModels(), store.fetchStats()])
}

async function handleActivate(m: TrainedModel) {
  activating.value = m.id
  try {
    await store.activateModel(m.id)
    message.success(`「${m.name}」已设为默认模型`)
    selectedModel.value = m
  } finally {
    activating.value = null
  }
}

async function handleDelete(m: TrainedModel) {
  Modal.confirm({
    title: '确认删除',
    content: `删除模型「${m.name}」？`,
    okText: '删除', okType: 'danger',
    async onOk() {
      await store.deleteModel(m.id)
      message.success('已删除')
      if (selectedModel.value?.id === m.id) selectedModel.value = null
    },
  })
}

function handleFileChange(file: File) {
  uploadForm.file = file
  if (!uploadForm.name) {
    uploadForm.name = file.name.replace(/\.[^.]+$/, '')
  }
  return false
}

async function handleUpload() {
  if (!uploadForm.file || !uploadForm.name) { message.error('请选择文件并填写名称'); return }
  const fd = new FormData()
  fd.append('file', uploadForm.file)
  fd.append('name', uploadForm.name)
  fd.append('architecture', uploadForm.architecture)
  fd.append('description', uploadForm.description)
  try {
    await store.uploadModel(fd)
    message.success('模型上传成功')
    showUpload.value = false
    uploadForm.file = null
    uploadForm.name = ''
    uploadForm.description = ''
    await loadData()
  } catch { message.error('上传失败') }
}

function startAddTag() {
  addingTag.value = true
  nextTick(() => tagInputRef.value?.focus())
}

async function addTag(m: TrainedModel) {
  if (!newTag.value.trim()) return
  const tags = [...(m.tags || []), newTag.value.trim()]
  await store.modelsApi.update(m.id, { tags })
  m.tags = tags
  newTag.value = ''
  addingTag.value = false
}

async function removeTag(m: TrainedModel, tag: string) {
  const tags = (m.tags || []).filter(t => t !== tag)
  await store.modelsApi.update(m.id, { tags })
  m.tags = tags
}

onMounted(() => { loadData() })
</script>

<style scoped>
.model-manager { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }
.file-preview { margin-top: 8px; font-size: 13px; color: #52c41a; }
</style>
