<template>
  <div class="annotation-manager">
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">标注管理</a-typography-title>
        <a-tag v-if="stats" :color="projectStatusColor">
          {{ stats.total_projects }} 个项目
        </a-tag>
      </div>
      <div class="header-actions">
        <a-space>
          <a-button @click="loadStats">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
          <a-button type="primary" @click="showCreateProject = true">
            <template #icon><PlusOutlined /></template>
            新建项目
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- Stats Overview -->
    <a-row :gutter="16" style="margin-bottom: 16px">
      <a-col :span="6">
        <a-statistic title="总标注数" :value="stats?.total_annotations || 0" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="手动标注" :value="stats?.manual_annotations || 0" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="自动标注" :value="stats?.auto_annotations || 0" />
      </a-col>
      <a-col :span="6">
        <a-statistic title="已完成项目" :value="stats?.completed || 0" />
      </a-col>
    </a-row>

    <!-- Main Tabs -->
    <a-tabs v-model:activeKey="activeTab">
      <!-- Projects Tab -->
      <a-tab-pane key="projects" tab="标注项目">
        <div class="tab-toolbar">
          <a-space>
            <a-select
              v-model:value="projectFilter"
              placeholder="筛选状态"
              style="width: 140px"
              allowClear
              @change="loadProjects"
            >
              <a-select-option value="draft">草稿</a-select-option>
              <a-select-option value="in_progress">进行中</a-select-option>
              <a-select-option value="completed">已完成</a-select-option>
            </a-select>
          </a-space>
        </div>

        <a-table
          :data-source="projects"
          :columns="projectColumns"
          :loading="loading"
          :pagination="{ pageSize: 10 }"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'status'">
              <a-tag :color="getStatusColor(record.status)">
                {{ getStatusLabel(record.status) }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'progress'">
              <a-progress
                :percent="record.total_images > 0
                  ? Math.round((record.annotated_images / record.total_images) * 100)
                  : 0"
                size="small"
              />
              <span class="progress-text">
                {{ record.annotated_images }} / {{ record.total_images }}
              </span>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="openProject(record)">标注</a-button>
                <a-button type="link" size="small" @click="editProject(record)">编辑</a-button>
                <a-button type="link" danger size="small" @click="deleteProject(record)">删除</a-button>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- Annotate Tab -->
      <a-tab-pane key="annotate" tab="图片标注">
        <a-row :gutter="16">
          <!-- Left: Image List -->
          <a-col :span="8">
            <a-card title="图片列表" size="small">
              <div class="image-filter">
                <a-select
                  v-model:value="annotateSourceFilter"
                  placeholder="来源筛选"
                  style="width: 100%"
                  allowClear
                  @change="loadAnnotateImages"
                >
                  <a-select-option value="upload">手动上传</a-select-option>
                  <a-select-option value="adb">ADB 截图</a-select-option>
                  <a-select-option value="video">视频抽帧</a-select-option>
                </a-select>
              </div>
              <div class="image-list" v-if="annotateImages.length > 0">
                <div
                  v-for="img in annotateImages"
                  :key="img.id"
                  class="image-item"
                  :class="{ selected: img.id === selectedAnnotateImageId }"
                  @click="selectAnnotateImage(img)"
                >
                  <img :src="getImageUrl(img.id)" :alt="img.original_filename" class="thumb" />
                  <div class="image-item-info">
                    <span class="img-name">{{ img.original_filename }}</span>
                    <span class="img-meta">{{ img.width }}x{{ img.height }}</span>
                  </div>
                </div>
              </div>
              <a-empty v-else description="暂无图片，请先上传图片" />
              <div class="pagination">
                <a-pagination
                  v-model:current="annotatePage"
                  :total="annotateTotal"
                  :page-size="20"
                  size="small"
                  @change="loadAnnotateImages"
                />
              </div>
            </a-card>
          </a-col>

          <!-- Right: Canvas -->
          <a-col :span="16">
            <a-card title="标注画布" size="small">
              <template #extra>
                <a-space>
                  <a-tag v-if="selectedAnnotateImageId">
                    {{ annotations.length }} 个标注
                  </a-tag>
                  <a-button
                    :type="drawMode === 'view' ? 'primary' : 'default'"
                    size="small"
                    @click="setDrawMode('view')"
                  >浏览</a-button>
                  <a-button
                    :type="drawMode === 'draw' ? 'primary' : 'default'"
                    size="small"
                    @click="setDrawMode('draw')"
                  >画框</a-button>
                  <a-button
                    :type="drawMode === 'edit' ? 'primary' : 'default'"
                    size="small"
                    @click="setDrawMode('edit')"
                  >编辑</a-button>
                  <a-button size="small" @click="saveAnnotations" :loading="saving">
                    保存
                  </a-button>
                  <a-button size="small" @click="exportYOLO">
                    导出 YOLO
                  </a-button>
                </a-space>
              </template>

              <!-- Canvas Container -->
              <div
                class="canvas-container"
                ref="canvasContainer"
                @mousedown="handleCanvasMouseDown"
                @mousemove="handleCanvasMouseMove"
                @mouseup="handleCanvasMouseUp"
              >
                <div v-if="!selectedAnnotateImageId" class="canvas-placeholder">
                  <FileImageOutlined class="placeholder-icon" />
                  <p>从左侧选择一张图片开始标注</p>
                </div>
                <canvas
                  v-else
                  ref="canvasRef"
                  class="annotation-canvas"
                  @click="handleCanvasClick"
                />
              </div>

              <!-- Class Palette -->
              <div class="class-palette" v-if="selectedAnnotateImageId">
                <span class="palette-label">选择类别：</span>
                <a-tag
                  v-for="cls in classes"
                  :key="cls.id"
                  :color="selectedClassId === cls.id ? cls.color : 'default'"
                  class="class-tag"
                  @click="selectedClassId = cls.id"
                  :style="selectedClassId === cls.id ? { backgroundColor: cls.color, borderColor: cls.color } : {}"
                >
                  {{ cls.display_name }}
                </a-tag>
              </div>

              <!-- Annotation List -->
              <a-divider>已标注 ({{ annotations.length }})</a-divider>
              <div class="annotation-list-container" ref="annotationListRef" @scroll="onAnnotationScroll">
                <div
                  v-if="annotations.length > 0"
                  class="annotation-list"
                  :style="{ height: `${annotations.length * rowHeight}px`, position: 'relative' }"
                >
                  <div
                    v-for="(ann, idx) in visibleAnnotations"
                    :key="ann.id"
                    class="annotation-row"
                    :style="{
                      position: 'absolute',
                      top: 0,
                      left: 0,
                      width: '100%',
                      height: `${rowHeight}px`,
                      transform: `translateY(${getRowOffset(idx)}px)`,
                    }"
                  >
                    <div class="ann-col ann-class">
                      <a-tag :color="getClassColor(ann.class_id)">
                        {{ classNameMap[ann.class_id] || ann.class_id?.slice(0, 8) }}
                      </a-tag>
                    </div>
                    <div class="ann-col ann-bbox">
                      {{ Math.round(ann.bbox_x) }},{{ Math.round(ann.bbox_y) }}
                      ({{ Math.round(ann.bbox_width) }}x{{ Math.round(ann.bbox_height) }})
                    </div>
                    <div class="ann-col ann-conf">
                      {{ ann.conf ? (ann.conf * 100).toFixed(1) + '%' : '-' }}
                    </div>
                    <div class="ann-col ann-action">
                      <a-button type="link" size="small" danger @click="removeAnnotation(ann.id)">删除</a-button>
                    </div>
                  </div>
                </div>
                <a-empty v-else description="暂无标注" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
              </div>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>

      <!-- Classes Tab -->
      <a-tab-pane key="classes" tab="类别管理">
        <div class="tab-toolbar">
          <a-button type="primary" @click="showCreateClass = true">
            <template #icon><PlusOutlined /></template>
            新建类别
          </a-button>
        </div>
        <a-table
          :data-source="classes"
          :columns="classColumns"
          :pagination="{ pageSize: 10 }"
          row-key="id"
        >
          <template #bodyCell="{ column, record }">
            <template v-if="column.key === 'color'">
              <a-tag :color="record.color" style="width: 60px; text-align: center">
                {{ record.color }}
              </a-tag>
            </template>
            <template v-else-if="column.key === 'action'">
              <a-space>
                <a-button type="link" size="small" @click="editClass(record)">编辑</a-button>
                <a-button type="link" danger size="small" @click="deleteClass(record)">删除</a-button>
              </a-space>
            </template>
          </template>
        </a-table>
      </a-tab-pane>

      <!-- Review Tab -->
      <a-tab-pane key="review" tab="审核管理">
        <a-row :gutter="16">
          <a-col :span="selectedReview ? 12 : 24">
            <a-card title="审核队列" size="small">
              <template #extra>
                <a-space>
                  <a-select v-model:value="reviewFilter" placeholder="筛选" style="width:120px" allowClear @change="loadReviewQueue">
                    <a-select-option value="in_review">待审核</a-select-option>
                    <a-select-option value="rejected">已退回</a-select-option>
                  </a-select>
                  <a-button size="small" @click="loadReviewQueue"><ReloadOutlined />刷新</ReloadOutlined></a-button>
                </a-space>
              </template>

              <!-- Review Stats -->
              <a-row :gutter="12" style="margin-bottom:16px">
                <a-col :span="6"><a-statistic title="待审核" :value="reviewStats.pending_review" /></a-col>
                <a-col :span="6"><a-statistic title="已退回" :value="reviewStats.needs_revision" /></a-col>
                <a-col :span="6"><a-statistic title="已完成" :value="reviewStats.completed" /></a-col>
                <a-col :span="6"><a-statistic title="进行中" :value="reviewStats.in_progress" /></a-col>
              </a-row>

              <a-table
                :data-source="reviewQueue"
                :columns="reviewColumns"
                :loading="reviewLoading"
                :pagination="{ pageSize: 10 }"
                row-key="id"
                size="small"
              >
                <template #bodyCell="{ column, record }">
                  <template v-if="column.key === 'status'">
                    <a-tag :color="getReviewStatusColor(record.status)">
                      {{ getReviewStatusLabel(record.status) }}
                    </a-tag>
                  </template>
                  <template v-else-if="column.key === 'action'">
                    <a-button type="link" size="small" @click="selectReviewProject(record)">审核</a-button>
                  </template>
                </template>
              </a-table>
            </a-card>
          </a-col>

          <!-- Review Detail -->
          <a-col :span="12" v-if="selectedReview">
            <a-card size="small">
              <template #title>
                <div style="display:flex;align-items:center;gap:8px">
                  <span>{{ selectedReview.name }}</span>
                  <a-tag :color="getReviewStatusColor(selectedReview.status)">{{ getReviewStatusLabel(selectedReview.status) }}</a-tag>
                </div>
              </template>
              <template #extra>
                <a-button type="link" size="small" @click="selectedReview = null">关闭</a-button>
              </template>

              <a-descriptions :column="2" size="small" bordered style="margin-bottom:16px">
                <a-descriptions-item label="进度">
                  {{ selectedReview.annotated_images }} / {{ selectedReview.total_images }} 张
                  <a-progress :percent="selectedReview.total_images > 0 ? Math.round(selectedReview.annotated_images / selectedReview.total_images * 100) : 0" size="small" style="margin-top:4px" />
                </a-descriptions-item>
                <a-descriptions-item label="已审核">{{ selectedReview.reviewed_images }} 张</a-descriptions-item>
                <a-descriptions-item label="创建时间">{{ new Date(selectedReview.created_at).toLocaleString('zh-CN') }}</a-descriptions-item>
                <a-descriptions-item label="描述">{{ selectedReview.description || '-' }}</a-descriptions-item>
              </a-descriptions>

              <a-divider>退回反馈</a-divider>
              <p v-if="selectedReview.review_feedback" style="color:#f5222d;font-size:13px">{{ selectedReview.review_feedback }}</p>
              <a-empty v-else description="暂无反馈" :image="Empty.PRESENTED_IMAGE_SIMPLE" />

              <a-divider>审核操作</a-divider>
              <a-space direction="vertical" style="width:100%">
                <a-button type="primary" block @click="handleApproveProject(selectedReview)" :loading="reviewActionLoading">
                  <template #icon><CheckOutlined /></template>通过审核
                </a-button>
                <a-textarea v-model:value="rejectFeedback" placeholder="填写退回原因（可选）" :rows="2" />
                <a-button type="default" block danger @click="handleRejectProject(selectedReview)" :loading="reviewActionLoading">
                  <template #icon><CloseOutlined /></template>退回修改
                </a-button>
              </a-space>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>

    <!-- Create/Edit Project Modal -->
    <a-modal
      v-model:open="showCreateProject"
      :title="editingProject ? '编辑项目' : '新建项目'"
      @ok="handleSaveProject"
      :confirm-loading="saving"
    >
      <a-form :model="projectForm" layout="vertical">
        <a-form-item label="项目名称" required>
          <a-input v-model:value="projectForm.name" placeholder="请输入项目名称" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="projectForm.description" :rows="3" />
        </a-form-item>
        <a-form-item label="包含类别">
          <a-select
            v-model:value="projectForm.class_ids"
            mode="multiple"
            placeholder="选择标注类别"
          >
            <a-select-option v-for="cls in classes" :key="cls.id" :value="cls.id">
              <a-space>
                <a-badge :color="cls.color" />
                {{ cls.display_name }}
              </a-space>
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="分配给" v-if="editingProject">
          <a-input v-model:value="projectForm.assigned_to" placeholder="用户 ID" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- Create/Edit Class Modal -->
    <a-modal
      v-model:open="showCreateClass"
      :title="editingClass ? '编辑类别' : '新建类别'"
      @ok="handleSaveClass"
      :confirm-loading="saving"
    >
      <a-form :model="classForm" layout="vertical">
        <a-form-item label="类别名称" required>
          <a-input v-model:value="classForm.name" placeholder="如: btn_attack" />
        </a-form-item>
        <a-form-item label="显示名称" required>
          <a-input v-model:value="classForm.display_name" placeholder="如: 攻击按钮" />
        </a-form-item>
        <a-form-item label="描述">
          <a-textarea v-model:value="classForm.description" :rows="2" />
        </a-form-item>
        <a-form-item label="颜色">
          <a-input type="color" v-model:value="classForm.color" style="width: 100px" />
        </a-form-item>
        <a-form-item label="YOLO 类别 ID" required>
          <a-input-number
            v-model:value="classForm.yolo_class_id"
            :min="0"
            placeholder="对应 YOLO 模型中的类别编号"
          />
        </a-form-item>
        <a-form-item label="快捷键">
          <a-input v-model:value="classForm.short_key" placeholder="如: a" maxlength="1" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { Empty } from 'ant-design-vue'
import {
  PlusOutlined,
  ReloadOutlined,
  FileImageOutlined,
  CheckOutlined,
  CloseOutlined,
} from '@ant-design/icons-vue'
import { useAnnotationsStore } from '@/stores/annotations'
import annotationsApi from '@/api/annotations'
import imagesApi from '@/api/images'
import type { AnnotationClass, AnnotationProject } from '@/api/annotations'
import type { ImageResponse } from '@/api/images'

const annStore = useAnnotationsStore()

const activeTab = ref('projects')
const loading = computed(() => annStore.loading)
const saving = computed(() => annStore.saving)
const classes = computed(() => annStore.classes)
const projects = computed(() => annStore.projects)
const stats = computed(() => annStore.stats)
const classNameMap = computed(() => annStore.classNameMap)
const annotations = computed(() => annStore.annotations)

// ── Stats ───────────────────────────────────────────────────
const projectStatusColor = computed(() => {
  const s = stats.value
  if (!s) return 'default'
  if (s.completed > 0) return 'green'
  if (s.in_progress > 0) return 'blue'
  return 'default'
})

async function loadStats() {
  await annStore.fetchStats()
}

// ── Projects ────────────────────────────────────────────────
const projectFilter = ref<string | null>(null)

const projectColumns = [
  { title: '名称', dataIndex: 'name', key: 'name' },
  { title: '状态', key: 'status', width: 100 },
  { title: '进度', key: 'progress', width: 180 },
  { title: '已审核', key: 'reviewed_images', width: 80,
    customRender: ({ record }: { record: AnnotationProject }) => `${record.reviewed_images} / ${record.total_images}` },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 180,
    customRender: ({ text }: { text: string }) => new Date(text).toLocaleString('zh-CN') },
  { title: '操作', key: 'action', width: 180 },
]

async function loadProjects() {
  await annStore.fetchProjects({ status: projectFilter.value || undefined })
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    draft: 'default', in_progress: 'processing', completed: 'success', reviewed: 'purple',
  }
  return map[status] || 'default'
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿', in_progress: '进行中', completed: '已完成', reviewed: '已审核',
  }
  return map[status] || status
}

// Project modal
const showCreateProject = ref(false)
const editingProject = ref<AnnotationProject | null>(null)
const projectForm = reactive({
  name: '',
  description: '',
  class_ids: [] as string[],
  assigned_to: '',
})

function editProject(project: AnnotationProject) {
  editingProject.value = project
  projectForm.name = project.name
  projectForm.description = project.description || ''
  projectForm.class_ids = project.class_ids || []
  projectForm.assigned_to = project.assigned_to || ''
  showCreateProject.value = true
}

async function handleSaveProject() {
  if (!projectForm.name.trim()) {
    message.error('请输入项目名称')
    return
  }
  try {
    if (editingProject.value) {
      await annotationsApi.updateProject(editingProject.value.id, {
        name: projectForm.name,
        description: projectForm.description,
        class_ids: projectForm.class_ids,
        assigned_to: projectForm.assigned_to || undefined,
      })
      message.success('项目已更新')
    } else {
      await annotationsApi.createProject({
        name: projectForm.name,
        description: projectForm.description,
        class_ids: projectForm.class_ids,
      })
      message.success('项目已创建')
    }
    showCreateProject.value = false
    editingProject.value = null
    await loadProjects()
    await loadStats()
  } catch (error) {
    message.error('保存失败')
  }
}

async function deleteProject(project: AnnotationProject) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除项目「${project.name}」吗？`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await annotationsApi.deleteProject(project.id)
        message.success('已删除')
        await loadProjects()
        await loadStats()
      } catch {
        message.error('删除失败')
      }
    },
  })
}

function openProject(project: AnnotationProject) {
  activeTab.value = 'annotate'
}

// ── Annotate ────────────────────────────────────────────────
const annotateImages = ref<ImageResponse[]>([])
const selectedAnnotateImageId = ref<string | null>(null)
const annotateSourceFilter = ref<string | null>(null)
const annotatePage = ref(1)
const annotateTotal = ref(0)
const drawMode = ref<'view' | 'draw' | 'edit'>('view')
const selectedClassId = ref<string | null>(null)

const canvasRef = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)
const annotationListRef = ref<HTMLElement | null>(null)
const rowHeight = 40

let isDrawing = false
let drawStartX = 0
let drawStartY = 0
let scale = 1
let offsetX = 0
let offsetY = 0

const scrollTop = ref(0)
const viewHeight = ref(300)

const visibleAnnotations = computed(() => {
  const start = Math.max(0, Math.floor(scrollTop.value / rowHeight) - 2)
  const end = Math.min(annotations.value.length, Math.ceil((scrollTop.value + viewHeight.value) / rowHeight) + 2)
  return annotations.value.slice(start, end)
})

function getRowOffset(index: number): number {
  return index * rowHeight
}

function onAnnotationScroll(e: Event) {
  const el = e.target as HTMLElement
  scrollTop.value = el.scrollTop
}

const annotationColumns = [
  { title: '类别', key: 'cls', width: 120 },
  { title: '坐标', key: 'bbox', width: 200 },
  { title: '置信度', key: 'conf', width: 80 },
  { title: '操作', key: 'action', width: 80 },
]

async function loadAnnotateImages() {
  try {
    const resp = await imagesApi.getList({
      page: annotatePage.value,
      page_size: 20,
      source: annotateSourceFilter.value as 'upload' | 'adb' | 'video' | undefined,
    })
    annotateImages.value = resp.items
    annotateTotal.value = resp.total
  } catch (error) {
    console.error('Failed to load images:', error)
  }
}

function getImageUrl(id: string): string {
  return imagesApi.getServeUrl(id)
}

async function selectAnnotateImage(img: ImageResponse) {
  selectedAnnotateImageId.value = img.id
  await annStore.loadImageAnnotations(img.id)
  await nextTick()
  renderCanvas()
}

function getClassColor(classId: string): string {
  const cls = annStore.classMap[classId]
  return cls?.color || '#3B82F6'
}

function setDrawMode(mode: 'view' | 'draw' | 'edit') {
  drawMode.value = mode
  annStore.setDrawingMode(mode)
}

function renderCanvas() {
  const canvas = canvasRef.value
  const imgId = selectedAnnotateImageId.value
  if (!canvas || !imgId) return

  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const img = new Image()
  img.crossOrigin = 'anonymous'
  img.onload = () => {
    const container = canvasContainer.value
    if (!container) return

    const cw = container.clientWidth
    const ch = Math.min(container.clientHeight - 40, img.height)

    scale = Math.min(cw / img.width, ch / img.height, 1)
    canvas.width = img.width * scale
    canvas.height = img.height * scale
    canvas.style.width = `${canvas.width}px`
    canvas.style.height = `${canvas.height}px`

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

    // Draw annotations
    for (const ann of annStore.annotations) {
      drawBBox(ctx, ann.bbox_x * scale, ann.bbox_y * scale,
                ann.bbox_width * scale, ann.bbox_height * scale,
                ann.class_id)
    }
  }
  img.src = getImageUrl(imgId)
}

function drawBBox(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  classId: string
) {
  const cls = annStore.classMap[classId]
  const color = cls?.color || '#3B82F6'

  ctx.strokeStyle = color
  ctx.lineWidth = 2
  ctx.strokeRect(x, y, w, h)

  ctx.fillStyle = color
  ctx.globalAlpha = 0.25
  ctx.fillRect(x, y, w, h)
  ctx.globalAlpha = 1.0

  const label = cls?.display_name || classId
  ctx.font = 'bold 12px sans-serif'
  const tw = ctx.measureText(label).width
  ctx.fillStyle = color
  ctx.fillRect(x, y - 18, tw + 8, 18)
  ctx.fillStyle = '#fff'
  ctx.fillText(label, x + 4, y - 5)
}

function handleCanvasClick(e: MouseEvent) {
  if (drawMode.value !== 'edit') return
  // Remove bbox on click (find nearest)
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const cx = (e.clientX - rect.left)
  const cy = (e.clientY - rect.top)

  for (const ann of annStore.annotations) {
    const ax = ann.bbox_x * scale
    const ay = ann.bbox_y * scale
    const aw = ann.bbox_width * scale
    const ah = ann.bbox_height * scale
    if (cx >= ax && cx <= ax + aw && cy >= ay && cy <= ay + ah) {
      removeAnnotation(ann.id)
      return
    }
  }
}

function handleCanvasMouseDown(e: MouseEvent) {
  if (drawMode.value !== 'draw' || !selectedClassId.value) return
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  isDrawing = true
  drawStartX = e.clientX - rect.left
  drawStartY = e.clientY - rect.top
  e.preventDefault()
}

function handleCanvasMouseMove(e: MouseEvent) {
  if (!isDrawing || drawMode.value !== 'draw') return
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  const rect = canvas.getBoundingClientRect()
  const curX = e.clientX - rect.left
  const curY = e.clientY - rect.top

  // Re-render
  renderCanvas()

  const x = Math.min(drawStartX, curX)
  const y = Math.min(drawStartY, curY)
  const w = Math.abs(curX - drawStartX)
  const h = Math.abs(curY - drawStartY)

  ctx.strokeStyle = '#ff0000'
  ctx.lineWidth = 2
  ctx.setLineDash([5, 5])
  ctx.strokeRect(x, y, w, h)
  ctx.setLineDash([])
}

async function handleCanvasMouseUp(e: MouseEvent) {
  if (!isDrawing || drawMode.value !== 'draw') return
  isDrawing = false

  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const endX = e.clientX - rect.left
  const endY = e.clientY - rect.top

  const x = Math.min(drawStartX, endX)
  const y = Math.min(drawStartY, endY)
  const w = Math.abs(endX - drawStartX)
  const h = Math.abs(endY - drawStartY)

  if (w < 5 || h < 5) return

  // Convert back to image coordinates
  const imgX = x / scale
  const imgY = y / scale
  const imgW = w / scale
  const imgH = h / scale

  await annStore.addAnnotation({
    class_id: selectedClassId.value!,
    bbox_x: imgX,
    bbox_y: imgY,
    bbox_width: imgW,
    bbox_height: imgH,
    conf: 1.0,
    is_auto_annotated: false,
  })

  await nextTick()
  renderCanvas()
}

async function removeAnnotation(id: string) {
  await annStore.removeAnnotation(id)
  await nextTick()
  renderCanvas()
}

async function saveAnnotations() {
  message.success('标注已保存')
}

function exportYOLO() {
  window.open('/api/v1/annotations/export/yolo', '_blank')
}

// ── Classes ────────────────────────────────────────────────
const classColumns = [
  { title: 'ID', dataIndex: 'name', key: 'name', width: 140 },
  { title: '显示名称', dataIndex: 'display_name', key: 'display_name', width: 120 },
  { title: '颜色', key: 'color', width: 100 },
  { title: 'YOLO ID', dataIndex: 'yolo_class_id', key: 'yolo_class_id', width: 80 },
  { title: '快捷键', dataIndex: 'short_key', key: 'short_key', width: 80 },
  { title: '描述', dataIndex: 'description', key: 'description' },
  { title: '操作', key: 'action', width: 120 },
]

const reviewColumns = [
  { title: '项目名称', dataIndex: 'name', key: 'name', ellipsis: true },
  { title: '状态', key: 'status', width: 100 },
  { title: '标注进度', key: 'progress', width: 150,
    customRender: ({ record }: { record: any }) => `${record.annotated_images}/${record.total_images}` },
  { title: '创建时间', dataIndex: 'created_at', key: 'created_at', width: 160,
    customRender: ({ text }: { text: string }) => new Date(text).toLocaleDateString('zh-CN') },
  { title: '操作', key: 'action', width: 80 },
]

const showCreateClass = ref(false)
const editingClass = ref<AnnotationClass | null>(null)
const reviewQueue = ref<any[]>([])
const reviewStats = ref({ pending_review: 0, needs_revision: 0, completed: 0, in_progress: 0 })
const reviewLoading = ref(false)
const reviewActionLoading = ref(false)
const selectedReview = ref<any | null>(null)
const reviewFilter = ref<string | null>(null)
const rejectFeedback = ref('')
const classForm = reactive({
  name: '',
  display_name: '',
  description: '',
  color: '#3B82F6',
  yolo_class_id: 0,
  short_key: '',
  sort_order: 0,
})

function editClass(cls: AnnotationClass) {
  editingClass.value = cls
  classForm.name = cls.name
  classForm.display_name = cls.display_name
  classForm.description = cls.description || ''
  classForm.color = cls.color
  classForm.yolo_class_id = cls.yolo_class_id
  classForm.short_key = cls.short_key || ''
  classForm.sort_order = cls.sort_order
  showCreateClass.value = true
}

async function handleSaveClass() {
  if (!classForm.name.trim() || !classForm.display_name.trim()) {
    message.error('请填写类别名称和显示名称')
    return
  }
  try {
    if (editingClass.value) {
      await annotationsApi.updateClass(editingClass.value.id, classForm)
      message.success('类别已更新')
    } else {
      await annotationsApi.createClass(classForm)
      message.success('类别已创建')
    }
    showCreateClass.value = false
    editingClass.value = null
    await annStore.fetchClasses()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '保存失败')
  }
}

async function deleteClass(cls: AnnotationClass) {
  Modal.confirm({
    title: '确认删除',
    content: `确定要删除类别「${cls.display_name}」吗？`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await annotationsApi.deleteClass(cls.id)
        message.success('已删除')
        await annStore.fetchClasses()
      } catch {
        message.error('删除失败')
      }
    },
  })
}

// ── Review ───────────────────────────────────────────────────
function getReviewStatusColor(status: string): string {
  return { draft: 'default', in_progress: 'processing', in_review: 'blue', rejected: 'error', completed: 'success' }[status] || 'default'
}
function getReviewStatusLabel(status: string): string {
  return { draft: '草稿', in_progress: '进行中', in_review: '待审核', rejected: '已退回', completed: '已完成' }[status] || status
}

async function loadReviewQueue() {
  reviewLoading.value = true
  try {
    const res: any = await annotationsApi.getReviewQueue({})
    reviewQueue.value = res.items || []
    reviewStats.value = {
      pending_review: reviewQueue.value.filter((p: any) => p.status === 'in_review').length,
      needs_revision: reviewQueue.value.filter((p: any) => p.status === 'rejected').length,
      completed: 0,
      in_progress: 0,
    }
    const statsRes: any = await annotationsApi.getReviewSummary()
    reviewStats.value.completed = statsRes.completed || 0
    reviewStats.value.in_progress = statsRes.in_progress || 0
  } catch (e) { console.error(e) }
  finally { reviewLoading.value = false }
}

function selectReviewProject(project: any) {
  selectedReview.value = project
  rejectFeedback.value = project.review_feedback || ''
}

async function handleApproveProject(project: any) {
  reviewActionLoading.value = true
  try {
    await annotationsApi.approveProject(project.id)
    message.success('项目已通过审核')
    selectedReview.value = null
    await loadReviewQueue()
  } catch { message.error('操作失败') }
  finally { reviewActionLoading.value = false }
}

async function handleRejectProject(project: any) {
  reviewActionLoading.value = true
  try {
    await annotationsApi.rejectProject(project.id, { feedback: rejectFeedback.value })
    message.success('项目已退回')
    selectedReview.value = null
    await loadReviewQueue()
  } catch { message.error('操作失败') }
  finally { reviewActionLoading.value = false }
}

// ── Lifecycle ───────────────────────────────────────────────
onMounted(async () => {
  await Promise.all([
    annStore.fetchClasses(),
    loadProjects(),
    loadStats(),
    loadAnnotateImages(),
    loadReviewQueue(),
  ])
})

onUnmounted(() => {
  annStore.reset()
})
</script>

<style scoped>
.annotation-manager {
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

.tab-toolbar {
  margin-bottom: 16px;
}

.progress-text {
  font-size: 12px;
  color: #999;
  margin-left: 8px;
}

/* Annotate tab */
.image-list {
  max-height: 500px;
  overflow-y: auto;
}

.image-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px;
  cursor: pointer;
  border-radius: 4px;
  transition: background 0.2s;
}

.image-item:hover {
  background: #f5f5f5;
}

.image-item.selected {
  background: #e6f7ff;
}

.thumb {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 4px;
  flex-shrink: 0;
}

.image-item-info {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.img-name {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.img-meta {
  font-size: 11px;
  color: #999;
}

.canvas-container {
  min-height: 400px;
  max-height: 600px;
  overflow: auto;
  background: #f5f5f5;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.canvas-placeholder {
  text-align: center;
  color: #999;
}

.placeholder-icon {
  font-size: 48px;
  margin-bottom: 8px;
}

.annotation-canvas {
  display: block;
  cursor: crosshair;
}

.class-palette {
  margin-top: 12px;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.palette-label {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.class-tag {
  cursor: pointer;
  user-select: none;
}

.pagination {
  margin-top: 8px;
  text-align: center;
}

/* Annotation list — virtual scroll */
.annotation-list-container {
  max-height: 200px;
  overflow-y: auto;
}

.annotation-list {
  /* height set inline via style */
}

.annotation-row {
  display: flex;
  align-items: center;
  border-bottom: 1px solid #f0f0f0;
  padding: 0 8px;
  box-sizing: border-box;
  transition: background 0.15s;
}

.annotation-row:hover {
  background: #f5f5f5;
}

.ann-col {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  padding: 0 4px;
}

.ann-class { flex: 0 0 120px; }
.ann-bbox { flex: 1; font-size: 12px; color: #666; }
.ann-conf { flex: 0 0 60px; font-size: 12px; color: #999; text-align: center; }
.ann-action { flex: 0 0 60px; text-align: right; }

@media (max-width: 768px) {
  .annotation-manager { padding: 12px; }
  .page-header { flex-direction: column; align-items: flex-start; gap: 12px; }
}
