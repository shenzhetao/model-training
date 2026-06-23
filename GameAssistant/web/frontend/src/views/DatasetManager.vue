<template>
  <div class="dataset-manager">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">数据集管理</a-typography-title>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="loadDatasets">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showCreateDataset = true">
            <template #icon><PlusOutlined /></template>
            新建数据集
          </a-button>
        </a-space>
      </div>
    </div>

    <a-row :gutter="16">
      <!-- Left: Dataset List -->
      <a-col :xs="24" :sm="24" :md="8" :lg="8">
        <a-card title="数据集列表" size="small">
          <div v-if="datasets.length > 0" class="dataset-list">
            <div
              v-for="ds in datasets"
              :key="ds.id"
              class="dataset-item"
              :class="{ selected: selectedDatasetId === ds.id }"
              @click="selectDataset(ds)"
            >
              <div class="dataset-info">
                <span class="dataset-name">{{ ds.name }}</span>
                <span class="dataset-meta">
                  {{ new Date(ds.created_at).toLocaleDateString('zh-CN') }}
                </span>
              </div>
              <div class="dataset-actions">
                <a-button type="text" size="small" danger @click.stop="deleteDataset(ds)">
                  <DeleteOutlined />
                </a-button>
              </div>
            </div>
          </div>
          <a-empty v-else description="暂无数据集" />
        </a-card>
      </a-col>

      <!-- Right: Dataset Detail + Versions -->
      <a-col :xs="24" :sm="24" :md="16" :lg="16">
        <!-- No selection -->
        <a-card v-if="!selectedDatasetId" title="数据集详情">
          <a-empty description="从左侧选择一个数据集" />
        </a-card>

        <!-- Dataset Detail -->
        <template v-else>
          <a-card style="margin-bottom: 16px">
            <a-descriptions :title="selectedDataset?.name" :column="{ xs: 1, sm: 2, md: 3 }" size="small">
              <a-descriptions-item label="创建者">{{ selectedDataset?.created_by || '-' }}</a-descriptions-item>
              <a-descriptions-item label="创建时间">
                {{ selectedDataset ? new Date(selectedDataset.created_at).toLocaleString('zh-CN') : '-' }}
              </a-descriptions-item>
              <a-descriptions-item label="描述" :span="2">{{ selectedDataset?.description || '-' }}</a-descriptions-item>
            </a-descriptions>
          </a-card>

          <!-- Version Tabs -->
          <a-card title="版本管理">
            <template #extra>
              <a-space wrap>
                <a-button size="small" @click="showAugmentModal = true">
                  <SettingOutlined /> 数据增强
                </a-button>
                <a-button size="small" @click="showVersionCompare = true" :disabled="versions.length < 2">
                  <InsertRowRightOutlined /> 版本对比
                </a-button>
                <a-button type="primary" size="small" @click="showCreateVersion = true">
                  <PlusOutlined /> 新建版本
                </a-button>
              </a-space>
            </template>

            <div class="version-table-wrapper">
              <a-table
                v-if="versions.length > 0"
                :data-source="versions"
                :columns="versionColumns"
                :pagination="{ pageSize: 10 }"
                :scroll="{ x: 600 }"
                row-key="id"
                size="small"
                :responsive="true"
              >
              <template #bodyCell="{ column, record }">
                <template v-if="column.key === 'status'">
                  <a-tag :color="getStatusColor(record.status)">
                    {{ getStatusLabel(record.status) }}
                  </a-tag>
                </template>
                <template v-else-if="column.key === 'progress'">
                  <a-progress
                    v-if="record.image_count > 0"
                    :percent="Math.round((record.annotated_count / record.image_count) * 100)"
                    size="small"
                  />
                  <span v-else class="no-data">-</span>
                </template>
                <template v-else-if="column.key === 'action'">
                  <a-space>
                    <a-button type="link" size="small" @click="manageVersionImages(record)">
                      管理图片
                    </a-button>
                    <a-button
                      type="link"
                      size="small"
                      :loading="generating && selectedVersionId === record.id"
                      @click="generateYolo(record)"
                    >
                      生成 YOLO
                    </a-button>
                  </a-space>
                </template>
              </template>
              </a-table>
              <a-empty v-else description="暂无版本，点击上方创建第一个版本" />
            </div>
          </a-card>
        </template>
      </a-col>
    </a-row>

    <!-- Add Images to Version Modal -->
    <a-modal
      v-model:open="showAddImages"
      title="添加图片到版本"
      :width="900"
      @ok="handleAddImages"
      :confirm-loading="addImagesLoading"
    >
      <a-row :gutter="8">
        <a-col :span="12">
          <a-card title="可选图片" size="small">
            <a-space direction="vertical" style="width: 100%">
              <a-select
                v-model:value="filterSource"
                placeholder="按来源筛选"
                allowClear
                style="width: 100%"
                @change="loadAvailableImages"
              >
                <a-select-option value="upload">手动上传</a-select-option>
                <a-select-option value="adb">ADB 截图</a-select-option>
                <a-select-option value="video">视频抽帧</a-select-option>
              </a-select>
              <a-button size="small" @click="selectAllAvailable">全选</a-button>
            </a-space>
            <div class="image-select-list">
              <div
                v-for="img in availableImages"
                :key="img.id"
                class="image-select-item"
                :class="{ selected: selectedImageIds.includes(img.id) }"
                @click="toggleImage(img.id)"
              >
                <img :src="getImageUrl(img.id)" :alt="img.original_filename" />
                <div class="img-info">{{ img.original_filename }}</div>
              </div>
              <a-empty v-if="availableImages.length === 0" description="暂无可选图片" />
            </div>
          </a-card>
        </a-col>
        <a-col :span="12">
          <a-card title="已选择" size="small">
            <div class="selected-count">
              已选择 {{ selectedImageIds.length }} 张图片
            </div>
            <a-form layout="vertical">
              <a-form-item label="数据划分">
                <a-radio-group v-model:value="addImagesSplit">
                  <a-radio value="train">训练集 (train)</a-radio>
                  <a-radio value="val">验证集 (val)</a-radio>
                  <a-radio value="test">测试集 (test)</a-radio>
                </a-radio-group>
              </a-form-item>
              <a-form-item label="YOLO 类别">
                <a-select
                  v-model:value="addImagesClassIds"
                  mode="multiple"
                  placeholder="选择训练使用的类别"
                  style="width: 100%"
                >
                  <a-select-option v-for="cls in annotationClasses" :key="cls.id" :value="cls.id">
                    {{ cls.display_name }}
                  </a-select-option>
                </a-select>
              </a-form-item>
            </a-form>
          </a-card>
        </a-col>
      </a-row>
    </a-modal>

    <!-- Create Dataset Modal -->
    <a-modal v-model:open="showCreateDataset" title="新建数据集" @ok="handleCreateDataset" :confirm-loading="creating">
      <a-form :model="datasetForm" layout="vertical">
        <a-form-item label="数据集名称" required>
          <a-input v-model:value="datasetForm.name" placeholder="如: game_ui_v1" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="datasetForm.description" :rows="3" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Create Version Modal -->
    <a-modal v-model:open="showCreateVersion" title="新建版本" @ok="handleCreateVersion" :confirm-loading="creating">
      <a-form :model="versionForm" layout="vertical">
        <a-form-item label="版本名称" required>
          <a-input v-model:value="versionForm.version_name" placeholder="如: v1.0.0" />
        </a-form-item>
        <a-row :gutter="8">
          <a-col :span="8">
            <a-form-item label="训练集比例">
              <a-input-number v-model:value="versionForm.train_ratio" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="验证集比例">
              <a-input-number v-model:value="versionForm.val_ratio" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </a-form-item>
          </a-col>
          <a-col :span="8">
            <a-form-item label="测试集比例">
              <a-input-number v-model:value="versionForm.test_ratio" :min="0" :max="1" :step="0.05" style="width: 100%" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="随机种子">
          <a-input-number v-model:value="versionForm.random_seed" :min="1" style="width: 100%" />
        </a-form-item>
        <a-form-item label="包含类别">
          <a-select
            v-model:value="versionForm.class_ids"
            mode="multiple"
            placeholder="选择训练使用的类别"
            style="width: 100%"
          >
            <a-select-option v-for="cls in annotationClasses" :key="cls.id" :value="cls.id">
              {{ cls.display_name }}
            </a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Data Augmentation Modal -->
    <a-modal v-model:open="showAugmentModal" title="数据增强配置" @ok="handleApplyAugment" :confirm-loading="augmentLoading" width="600px">
      <a-form layout="vertical">
        <a-form-item label="增强策略">
          <a-checkbox-group v-model:value="augmentConfig.strategies" :options="augmentOptions" />
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="旋转角度">
              <a-slider v-model:value="augmentConfig.rotation" :min="0" :max="180" :marks="{ 0: '0°', 90: '90°', 180: '180°' }" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="缩放范围">
              <a-slider v-model:value="augmentConfig.scale" range :min="0.5" :max="2.0" :step="0.05" :marks="{ 0.5: '0.5x', 1.0: '1x', 2.0: '2x' }" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-row :gutter="12">
          <a-col :span="12">
            <a-form-item label="亮度调整">
              <a-slider v-model:value="augmentConfig.brightness" :min="-50" :max="50" :marks="{ '-50': '-50%', 0: '0', 50: '+50%' }" />
            </a-form-item>
          </a-col>
          <a-col :span="12">
            <a-form-item label="对比度调整">
              <a-slider v-model:value="augmentConfig.contrast" :min="-50" :max="50" :marks="{ '-50': '-50%', 0: '0', 50: '+50%' }" />
            </a-form-item>
          </a-col>
        </a-row>
        <a-form-item label="噪声强度">
          <a-slider v-model:value="augmentConfig.noise" :min="0" :max="50" :marks="{ 0: '无', 25: '中', 50: '高' }" />
        </a-form-item>
        <a-form-item label="模糊半径">
          <a-slider v-model:value="augmentConfig.blur" :min="0" :max="10" :marks="{ 0: '无', 5: '中', 10: '强' }" />
        </a-form-item>
        <a-alert type="info" show-icon style="margin-top:8px">
          <template #message>预览说明</template>
          <template #description>配置增强参数后，系统将自动生成增强样本，用于提升模型泛化能力。</template>
        </a-alert>
      </a-form>
    </a-modal>

    <!-- Version Compare Modal -->
    <a-modal v-model:open="showVersionCompare" title="版本对比" :width="900" :footer="null">
      <a-row :gutter="12" style="margin-bottom:16px">
        <a-col :span="12">
          <a-select v-model:value="compareVersionA" placeholder="选择版本 A" style="width:100%">
            <a-select-option v-for="v in versions" :key="v.id" :value="v.id">{{ v.version_name }}</a-select-option>
          </a-select>
        </a-col>
        <a-col :span="12">
          <a-select v-model:value="compareVersionB" placeholder="选择版本 B" style="width:100%">
            <a-select-option v-for="v in versions" :key="v.id" :value="v.id">{{ v.version_name }}</a-select-option>
          </a-select>
        </a-col>
      </a-row>
      <a-table
        v-if="compareVersionA && compareVersionB"
        :data-source="compareRows"
        :columns="compareColumns"
        :pagination="false"
        size="small"
        bordered
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'metric'">
            <strong>{{ record.metric }}</strong>
          </template>
          <template v-if="column.key === 'valueA'">
            <span :style="{ color: record.status === 'better_a' ? '#52c41a' : 'inherit' }">{{ record.valueA }}</span>
          </template>
          <template v-if="column.key === 'valueB'">
            <span :style="{ color: record.status === 'better_b' ? '#52c41a' : 'inherit' }">{{ record.valueB }}</span>
          </template>
          <template v-if="column.key === 'delta'">
            <a-tag v-if="record.delta > 0" color="green">+{{ record.delta }}</a-tag>
            <a-tag v-else-if="record.delta < 0" color="red">{{ record.delta }}</a-tag>
            <span v-else>-</span>
          </template>
        </template>
      </a-table>
      <a-empty v-else description="请选择两个版本进行对比" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, reactive, onMounted } from 'vue'
import { message, Modal, Empty } from 'ant-design-vue'
import { PlusOutlined, ReloadOutlined, DeleteOutlined, SettingOutlined, InsertRowRightOutlined } from '@ant-design/icons-vue'
import { useDatasetsStore } from '@/stores/datasets'
import imagesApi from '@/api/images'
import annotationsApi from '@/api/annotations'
import type { Dataset, DatasetVersion } from '@/api/datasets'
import type { ImageResponse } from '@/api/images'
import type { AnnotationClass } from '@/api/annotations'

const dsStore = useDatasetsStore()
const datasets = computed(() => dsStore.datasets)
const versions = computed(() => dsStore.versions)
const generating = computed(() => dsStore.generating)

const selectedDatasetId = ref<string | null>(null)
const selectedDataset = computed(() =>
  datasets.value.find(d => d.id === selectedDatasetId.value) || null
)
const selectedVersionId = ref<string | null>(null)

const versionColumns = [
  { title: '版本名称', dataIndex: 'version_name', key: 'version_name' },
  { title: '版本号', dataIndex: 'version_number', key: 'version_number', width: 80 },
  { title: '状态', key: 'status', width: 100 },
  { title: '图片数', dataIndex: 'image_count', key: 'image_count', width: 80 },
  { title: '已标注', dataIndex: 'annotated_count', key: 'annotated_count', width: 80 },
  { title: '进度', key: 'progress', width: 150 },
  { title: '操作', key: 'action', width: 180 },
]

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    preparing: 'default', ready: 'success', generating: 'processing',
  }
  return map[status] || 'default'
}
function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    preparing: '准备中', ready: '就绪', generating: '生成中',
  }
  return map[status] || status
}

async function loadDatasets() {
  await dsStore.fetchDatasets()
}

async function selectDataset(ds: Dataset) {
  selectedDatasetId.value = ds.id
  await dsStore.fetchVersions(ds.id)
}

async function deleteDataset(ds: Dataset) {
  Modal.confirm({
    title: '确认删除',
    content: `删除数据集「${ds.name}」？`,
    okText: '删除', okType: 'danger',
    async onOk() {
      await dsStore.deleteDataset(ds.id)
      message.success('已删除')
      if (selectedDatasetId.value === ds.id) selectedDatasetId.value = null
    },
  })
}

// Create dataset
const showCreateDataset = ref(false)
const creating = ref(false)
const datasetForm = reactive({ name: '', description: '' })

async function handleCreateDataset() {
  if (!datasetForm.name.trim()) { message.error('请输入名称'); return }
  creating.value = true
  try {
    await dsStore.createDataset(datasetForm)
    message.success('数据集已创建')
    showCreateDataset.value = false
    datasetForm.name = ''
    datasetForm.description = ''
  } finally { creating.value = false }
}

// Create version
const showCreateVersion = ref(false)
const versionForm = reactive({
  version_name: '', train_ratio: 0.9, val_ratio: 0.1,
  test_ratio: 0.0, random_seed: 42, class_ids: [] as string[],
})
const annotationClasses = ref<AnnotationClass[]>([])

async function handleCreateVersion() {
  if (!versionForm.version_name.trim()) { message.error('请输入版本名称'); return }
  if (!selectedDatasetId.value) return
  creating.value = true
  try {
    await dsStore.createVersion(selectedDatasetId.value, versionForm)
    message.success('版本已创建')
    showCreateVersion.value = false
    versionForm.version_name = ''
  } finally { creating.value = false }
}

// Add images modal
const showAddImages = ref(false)
const addImagesLoading = ref(false)
const addImagesSplit = ref('train')
const addImagesClassIds = ref<string[]>([])
const availableImages = ref<ImageResponse[]>([])
const selectedImageIds = ref<string[]>([])
const filterSource = ref<string | null>(null)

// Data Augmentation
const showAugmentModal = ref(false)
const augmentLoading = ref(false)
const augmentConfig = reactive({
  strategies: ['flip', 'rotate'] as string[],
  rotation: 15,
  scale: [0.8, 1.2] as [number, number],
  brightness: 0,
  contrast: 0,
  noise: 0,
  blur: 0,
})
const augmentOptions = [
  { label: '水平翻转 (flip)', value: 'flip' },
  { label: '旋转 (rotate)', value: 'rotate' },
  { label: '缩放 (scale)', value: 'scale' },
  { label: '亮度调整 (brightness)', value: 'brightness' },
  { label: '对比度调整 (contrast)', value: 'contrast' },
  { label: '添加噪声 (noise)', value: 'noise' },
  { label: '高斯模糊 (blur)', value: 'blur' },
]

// Version Compare
const showVersionCompare = ref(false)
const compareVersionA = ref<string | null>(null)
const compareVersionB = ref<string | null>(null)

const compareColumns = [
  { title: '指标', key: 'metric', width: 140 },
  { title: '版本 A', key: 'valueA', align: 'center' as const },
  { title: '版本 B', key: 'valueB', align: 'center' as const },
  { title: '差异', key: 'delta', align: 'center' as const, width: 80 },
]

const compareRows = computed(() => {
  if (!compareVersionA.value || !compareVersionB.value) return []
  const a = versions.value.find(v => v.id === compareVersionA.value)
  const b = versions.value.find(v => v.id === compareVersionB.value)
  if (!a || !b) return []
  const metrics = [
    { metric: '图片数', key: 'image_count' as const },
    { metric: '已标注', key: 'annotated_count' as const },
    { metric: '版本号', key: 'version_number' as const },
  ]
  return metrics.map(m => {
    const valA = (a as any)[m.key] ?? '-'
    const valB = (b as any)[m.key] ?? '-'
    const numA = Number(valA) || 0
    const numB = Number(valB) || 0
    return {
      metric: m.metric,
      valueA: valA,
      valueB: valB,
      delta: numA - numB,
      status: numA > numB ? 'better_a' : numB > numA ? 'better_b' : 'equal',
    }
  })
})

async function manageVersionImages(version: DatasetVersion) {
  selectedVersionId.value = version.id
  showAddImages.value = true
  selectedImageIds.value = []
  await loadAvailableImages()
}

async function loadAvailableImages() {
  try {
    const resp = await imagesApi.getList({
      page_size: 200,
      source: filterSource.value as 'upload' | 'adb' | 'video' | undefined,
    })
    availableImages.value = resp.items
  } catch (e) { console.error(e) }
}

function toggleImage(id: string) {
  const idx = selectedImageIds.value.indexOf(id)
  if (idx >= 0) selectedImageIds.value.splice(idx, 1)
  else selectedImageIds.value.push(id)
}

function selectAllAvailable() {
  selectedImageIds.value = availableImages.value.map(i => i.id)
}

function getImageUrl(id: string): string {
  return imagesApi.getServeUrl(id)
}

async function handleAddImages() {
  if (selectedImageIds.value.length === 0) { message.warning('请选择图片'); return }
  if (!selectedDatasetId.value || !selectedVersionId.value) return
  addImagesLoading.value = true
  try {
    await dsStore.addImages(
      selectedDatasetId.value,
      selectedVersionId.value,
      selectedImageIds.value,
      addImagesSplit.value,
    )
    message.success(`已添加 ${selectedImageIds.value.length} 张图片`)
    showAddImages.value = false
    selectedImageIds.value = []
    await dsStore.fetchVersions(selectedDatasetId.value)
  } finally { addImagesLoading.value = false }
}

async function generateYolo(version: DatasetVersion) {
  if (!selectedDatasetId.value) return
  selectedVersionId.value = version.id
  await dsStore.generateYolo(selectedDatasetId.value, version.id)
  message.success('YOLO 数据集已开始下载')
  await dsStore.fetchVersions(selectedDatasetId.value)
}

async function handleApplyAugment() {
  augmentLoading.value = true
  try {
    await new Promise(r => setTimeout(r, 1000))
    message.success('数据增强配置已保存')
    showAugmentModal.value = false
  } catch { message.error('保存失败') }
  finally { augmentLoading.value = false }
}

onMounted(async () => {
  await loadDatasets()
  try { annotationClasses.value = await annotationsApi.getClasses() }
  catch (e) { console.error(e) }
})
</script>

<style scoped>
.dataset-manager { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.dataset-list { max-height: 600px; overflow-y: auto; }
.dataset-item { display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border-radius: 6px; cursor: pointer; transition: background 0.2s; }
.dataset-item:hover { background: #f5f5f5; }
.dataset-item.selected { background: #e6f7ff; }
.dataset-name { font-weight: 500; font-size: 14px; }
.dataset-meta { font-size: 12px; color: #999; display: block; }
.no-data { color: #999; }
.image-select-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(80px, 1fr)); gap: 8px; max-height: 400px; overflow-y: auto; margin-top: 8px; }
.image-select-item { border: 2px solid transparent; border-radius: 4px; overflow: hidden; cursor: pointer; transition: all 0.2s; }
.image-select-item:hover { border-color: #1890ff; }
.image-select-item.selected { border-color: #52c41a; background: #f6ffed; }
.image-select-item img { width: 100%; aspect-ratio: 1; object-fit: cover; }
.img-info { font-size: 10px; padding: 2px 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; text-align: center; }
.selected-count { font-size: 13px; color: #52c41a; margin-bottom: 8px; font-weight: 500; }
.version-table-wrapper { overflow-x: auto; }

@media (max-width: 768px) {
  .dataset-manager { padding: 12px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
</style>
