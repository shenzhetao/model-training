<template>
  <div class="template-manager">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">模板管理</a-typography-title>
        <a-tag color="cyan">{{ templates.length }} 个模板</a-tag>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="loadTemplates">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showUpload = true">
            <template #icon><UploadOutlined /></template>
            上传模板
          </a-button>
        </a-space>
      </div>
    </div>

    <a-row :gutter="16">
      <!-- Left: Template Tree -->
      <a-col :span="8">
        <a-card title="模板目录" size="small">
          <a-tree
            v-if="treeData.length > 0"
            :tree-data="treeData"
            :selectedKeys="selectedKeys"
            @select="handleTreeSelect"
            :show-icon="true"
          >
            <template #icon><FileImageOutlined /></template>
            <template #title="{ dataRef }">
              <div class="tree-node">
                <span>{{ dataRef.title }}</span>
                <span v-if="dataRef.count" class="node-count">{{ dataRef.count }}</span>
              </div>
            </template>
          </a-tree>
          <a-empty v-else description="暂无模板" />
        </a-card>
      </a-col>

      <!-- Right: Template Grid + Test -->
      <a-col :span="16">
        <a-row :gutter="16">
          <!-- Template Grid -->
          <a-col :span="14">
            <a-card title="模板列表" size="small">
              <template #extra>
                <a-space>
                  <a-input
                    v-model:value="searchText"
                    placeholder="搜索模板..."
                    style="width: 160px"
                    allowClear
                    @change="filterTemplates"
                  />
                  <a-select
                    v-model:value="filterClass"
                    placeholder="按类别筛选"
                    style="width: 140px"
                    allowClear
                    @change="loadTemplates"
                  >
                    <a-select-option v-for="cls in classes" :key="cls.class_name" :value="cls.class_name">
                      {{ cls.display_name }}
                    </a-select-option>
                  </a-select>
                </a-space>
              </template>

              <div v-if="filteredTemplates.length > 0" class="template-grid">
                <div
                  v-for="t in filteredTemplates"
                  :key="t.id"
                  class="template-card"
                  :class="{ selected: selectedTemplateId === t.id }"
                  @click="selectTemplate(t)"
                >
                  <div class="template-thumb">
                    <img :src="getThumbUrl(t.id)" :alt="t.name" @error="handleImgError" />
                    <div class="template-overlay">
                      <a-switch v-model:checked="t.is_active" size="small" @click.stop="toggleActive(t)" />
                    </div>
                  </div>
                  <div class="template-info">
                    <div class="template-name">{{ t.name }}</div>
                    <div class="template-meta">
                      <a-tag :color="getClassColor(t.class_name)" size="small">{{ t.class_name }}</a-tag>
                      <span class="template-size">{{ t.width }}x{{ t.height }}</span>
                    </div>
                  </div>
                  <div class="template-actions">
                    <a-button type="text" size="small" danger @click.stop="deleteTemplate(t)">
                      <template #icon><DeleteOutlined /></template>
                    </a-button>
                  </div>
                </div>
              </div>
              <a-empty v-else description="暂无模板" />
            </a-card>
          </a-col>

          <!-- Right Panel: Detail / Test -->
          <a-col :span="10">
            <a-card title="模板详情" size="small" style="margin-bottom: 16px">
              <div v-if="selectedTemplate" class="template-detail">
                <img :src="getThumbUrl(selectedTemplate.id)" class="detail-img" />
                <a-descriptions :column="1" size="small">
                  <a-descriptions-item label="名称">{{ selectedTemplate.name }}</a-descriptions-item>
                  <a-descriptions-item label="类别">{{ selectedTemplate.class_name }}</a-descriptions-item>
                  <a-descriptions-item label="尺寸">{{ selectedTemplate.width }}x{{ selectedTemplate.height }}</a-descriptions-item>
                  <a-descriptions-item label="匹配阈值">{{ selectedTemplate.match_threshold }}</a-descriptions-item>
                  <a-descriptions-item label="上传时间">
                    {{ new Date(selectedTemplate.created_at).toLocaleString('zh-CN') }}
                  </a-descriptions-item>
                </a-descriptions>
              </div>
              <a-empty v-else description="选择模板查看详情" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
            </a-card>

            <a-card title="匹配测试" size="small">
              <a-form layout="vertical">
                <a-form-item label="选择图片">
                  <a-select
                    v-model:value="testImageId"
                    placeholder="从已上传图片中选择"
                    show-search
                    option-filter-prop="children"
                    style="width: 100%"
                    allowClear
                  >
                    <a-select-option v-for="img in testImages" :key="img.id" :value="img.id">
                      {{ img.original_filename }} ({{ img.width }}x{{ img.height }})
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="测试模板">
                  <a-select
                    v-model:value="testTemplateIds"
                    mode="multiple"
                    placeholder="选择测试模板（空则全部）"
                    style="width: 100%"
                    allowClear
                  >
                    <a-select-option v-for="t in templates" :key="t.id" :value="t.id">
                      {{ t.name }} ({{ t.class_name }})
                    </a-select-option>
                  </a-select>
                </a-form-item>
                <a-form-item label="匹配阈值">
                  <a-slider v-model:value="testThreshold" :min="0.1" :max="1.0" :step="0.05" />
                  <span class="threshold-value">{{ (testThreshold * 100).toFixed(0) }}%</span>
                </a-form-item>
                <a-button type="primary" block :loading="testLoading" @click="runTest">
                  <template #icon><ThunderboltOutlined /></template>
                  测试匹配
                </a-button>

                <div v-if="testResults.length > 0" class="test-results">
                  <a-divider>匹配结果 ({{ testResults.length }})</a-divider>
                  <div v-for="r in testResults" :key="r.template_id" class="test-result-item">
                    <a-tag :color="r.matched ? 'green' : 'red'">
                      {{ r.matched ? '匹配' : '未匹配' }}
                    </a-tag>
                    <span class="result-name">{{ r.template_name }}</span>
                    <span class="result-conf">{{ (r.conf * 100).toFixed(1) }}%</span>
                    <span v-if="r.matched" class="result-pos">
                      ({{ r.x }}, {{ r.y }})
                    </span>
                  </div>
                </div>
              </a-form>
            </a-card>
          </a-col>
        </a-row>
      </a-col>
    </a-row>

    <!-- Upload Modal -->
    <a-modal v-model:open="showUpload" title="上传模板" @ok="handleUpload" :confirm-loading="uploading">
      <a-form :model="uploadForm" layout="vertical">
        <a-form-item label="模板文件" required>
          <a-upload
            :before-upload="handleFileChange"
            :show-upload-list="false"
            accept=".png,.jpg,.jpeg,.bmp,.webp"
          >
            <a-button><UploadOutlined />选择 PNG/JPG 图片</a-button>
          </a-upload>
          <div v-if="previewUrl" class="upload-preview">
            <img :src="previewUrl" alt="preview" />
          </div>
        </a-form-item>
        <a-form-item label="类别" required>
          <a-select v-model:value="uploadForm.class_name" placeholder="选择或输入类别" show-search>
            <a-select-option v-for="cls in classes" :key="cls.class_name" :value="cls.class_name">
              {{ cls.display_name }}
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="模板名称" required>
          <a-input v-model:value="uploadForm.name" placeholder="如: btn_attack_normal.png" />
        </a-form-item>
        <a-form-item label="匹配阈值">
          <a-slider v-model:value="uploadForm.match_threshold" :min="0.5" :max="1.0" :step="0.05" />
          <span>{{ (uploadForm.match_threshold * 100).toFixed(0) }}%</span>
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import {
  ReloadOutlined,
  UploadOutlined,
  DeleteOutlined,
  FileImageOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons-vue'
import { useTemplatesStore } from '@/stores/templates'
import templatesApi from '@/api/templates'
import imagesApi from '@/api/images'
import type { Template } from '@/api/templates'
import type { ImageResponse } from '@/api/images'

const store = useTemplatesStore()
const templates = computed(() => store.templates)
const classes = computed(() => store.classes)
const testResults = computed(() => store.testResults)
const testLoading = computed(() => store.testLoading)
const uploading = computed(() => store.uploading)

const searchText = ref('')
const filterClass = ref<string | null>(null)
const selectedTemplateId = ref<string | null>(null)
const selectedTemplate = computed(() =>
  templates.value.find(t => t.id === selectedTemplateId.value) || null
)
const filteredTemplates = ref<Template[]>([])

const testImages = ref<ImageResponse[]>([])
const testImageId = ref<string | null>(null)
const testTemplateIds = ref<string[]>([])
const testThreshold = ref(0.8)

const showUpload = ref(false)
const previewUrl = ref('')
const uploadForm = reactive({
  class_name: '',
  name: '',
  match_threshold: 0.85,
  file: null as File | null,
})

const selectedKeys = computed(() =>
  selectedTemplateId.value ? [selectedTemplateId.value] : []
)

const treeData = computed(() => {
  const groups: Record<string, Template[]> = {}
  for (const t of templates.value) {
    if (!groups[t.class_name]) groups[t.class_name] = []
    groups[t.class_name].push(t)
  }
  return Object.entries(groups).map(([cls, tmpls]) => ({
    key: cls,
    title: `${classes.value.find(c => c.class_name === cls)?.display_name || cls} (${tmpls.length})`,
    count: tmpls.length,
    children: tmpls.map(t => ({
      key: t.id,
      title: t.name,
      isTemplate: true,
    })),
  }))
})

function getThumbUrl(id: string) {
  return templatesApi.getServeUrl(id)
}

function getClassColor(className: string): string {
  const colors = ['blue', 'green', 'orange', 'purple', 'red', 'cyan', 'magenta']
  let h = 0
  for (const c of className) h = (h * 31 + c.charCodeAt(0)) % colors.length
  return colors[h]
}

function handleTreeSelect(keys: string[]) {
  if (keys.length > 0) {
    const k = keys[0]
    if (k.includes('-')) {
      selectedTemplateId.value = k
    } else {
      selectedTemplateId.value = null
      filterClass.value = k
    }
  }
}

function selectTemplate(t: Template) {
  selectedTemplateId.value = t.id
}

function filterTemplates() {
  let list = templates.value
  if (filterClass.value) list = list.filter(t => t.class_name === filterClass.value)
  if (searchText.value) {
    const q = searchText.value.toLowerCase()
    list = list.filter(t =>
      t.name.toLowerCase().includes(q) || t.class_name.toLowerCase().includes(q)
    )
  }
  filteredTemplates.value = list
}

async function loadTemplates() {
  await Promise.all([store.fetchClasses(), store.fetchTemplates()])
  filteredTemplates.value = templates.value
  await loadTestImages()
}

async function loadTestImages() {
  try {
    const resp = await imagesApi.getList({ page_size: 100 })
    testImages.value = resp.items
  } catch (e) { console.error(e) }
}

async function toggleActive(t: Template) {
  await store.updateTemplate(t.id, { is_active: !t.is_active })
  message.success(`模板已${t.is_active ? '启用' : '禁用'}`)
}

async function deleteTemplate(t: Template) {
  Modal.confirm({
    title: '确认删除',
    content: `删除模板「${t.name}」？`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      await store.deleteTemplate(t.id)
      message.success('已删除')
      if (selectedTemplateId.value === t.id) selectedTemplateId.value = null
    },
  })
}

function handleFileChange(file: File) {
  uploadForm.file = file
  const reader = new FileReader()
  reader.onload = e => { previewUrl.value = e.target?.result as string }
  reader.readAsDataURL(file)
  return false
}

async function handleUpload() {
  if (!uploadForm.file || !uploadForm.class_name || !uploadForm.name) {
    message.error('请填写完整信息')
    return
  }
  const fd = new FormData()
  fd.append('file', uploadForm.file)
  fd.append('class_name', uploadForm.class_name)
  fd.append('name', uploadForm.name)
  fd.append('match_threshold', String(uploadForm.match_threshold))
  try {
    await store.uploadTemplate(fd)
    message.success('上传成功')
    showUpload.value = false
    previewUrl.value = ''
    uploadForm.file = null
    uploadForm.name = ''
    await loadTemplates()
  } catch {
    message.error('上传失败')
  }
}

async function runTest() {
  if (!testImageId.value) {
    message.warning('请选择一张图片')
    return
  }
  await store.testMatching({
    image_id: testImageId.value,
    template_ids: testTemplateIds.value.length > 0 ? testTemplateIds.value : undefined,
    threshold: testThreshold.value,
  })
}

function handleImgError(e: Event) {
  const img = e.target as HTMLImageElement
  img.src = "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='100' height='100'%3E%3Crect width='100' height='100' fill='%23f0f0f0'/%3E%3Ctext x='50' y='50' text-anchor='middle' dy='.3em' fill='%23999' font-size='12'%3ENo Image%3C/text%3E%3C/svg%3E"
}

onMounted(() => { loadTemplates() })
</script>

<style scoped>
.template-manager { padding: 24px; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 24px; }
.header-left { display: flex; align-items: center; gap: 16px; }
.tree-node { display: flex; justify-content: space-between; width: 100%; }
.node-count { color: #999; font-size: 12px; }
.template-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px; }
.template-card { background: #fafafa; border: 2px solid transparent; border-radius: 8px; overflow: hidden; cursor: pointer; transition: all 0.2s; }
.template-card:hover { border-color: #1890ff; }
.template-card.selected { border-color: #1890ff; background: #e6f7ff; }
.template-thumb { position: relative; width: 100%; padding-top: 100%; background: #f0f0f0; }
.template-thumb img { position: absolute; top: 0; left: 0; width: 100%; height: 100%; object-fit: contain; }
.template-overlay { position: absolute; top: 4px; right: 4px; }
.template-info { padding: 8px; }
.template-name { font-size: 12px; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.template-meta { display: flex; align-items: center; gap: 4px; margin-top: 4px; }
.template-size { font-size: 11px; color: #999; }
.template-actions { padding: 0 4px 4px; text-align: right; }
.detail-img { width: 100%; max-height: 200px; object-fit: contain; border-radius: 8px; margin-bottom: 12px; }
.threshold-value { margin-left: 8px; color: #1890ff; font-weight: 500; }
.test-results { margin-top: 16px; }
.test-result-item { display: flex; align-items: center; gap: 8px; padding: 6px 0; border-bottom: 1px solid #f0f0f0; }
.result-name { flex: 1; font-size: 13px; }
.result-conf { color: #52c41a; font-weight: 500; }
.result-pos { color: #999; font-size: 12px; }
.upload-preview img { max-width: 200px; max-height: 200px; margin-top: 8px; border-radius: 8px; border: 1px solid #d9d9d9; }
</style>
