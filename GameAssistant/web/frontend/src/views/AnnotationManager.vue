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
        <a-statistic title="已完成项目数" :value="stats?.completed || 0" />
      </a-col>
    </a-row>

    <!-- Main Tabs -->
    <a-tabs v-model:activeKey="activeTab" @change="onTabChange">
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
              <a-select-option value="in_review">待审核</a-select-option>
              <a-select-option value="completed">已完成</a-select-option>
              <a-select-option value="rejected">已退回</a-select-option>
              <a-select-option value="reviewed">已审核</a-select-option>
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
                :percent="calcProgress(record.annotated_images, record.total_images)"
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
                <a-button type="link" size="small" @click="handleSubmitForReviewById(record.id)">提交审核</a-button>
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
              <template #extra>
                <a-space>
                  <a-select
                    v-model:value="annotateProjectId"
                    placeholder="选择项目"
                    style="width: 140px"
                    @change="onAnnotateProjectChange"
                  >
                    <a-select-option v-for="p in projects" :key="p.id" :value="p.id">
                      {{ p.name }}
                    </a-select-option>
                  </a-select>
                  <a-button
                    size="small"
                    type="primary"
                    :disabled="!canAddToProject"
                    @click="addSelectedImageToProject"
                  >
                    添加到项目
                  </a-button>
                </a-space>
              </template>
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
                    <span class="img-meta">
                      {{ img.width }}x{{ img.height }}
                      <a-tag
                        v-if="getImageStatusTag(img.id)"
                        :color="getImageStatusTag(img.id)!.color"
                        size="small"
                        style="margin-left:4px"
                      >{{ getImageStatusTag(img.id)!.text }}</a-tag>
                    </span>
                  </div>
                  <a-button
                    v-if="annotateProjectId && isImageInProject(img.id)"
                    type="text"
                    danger
                    size="small"
                    class="remove-from-project-btn"
                    @click.stop="removeImageFromProject(img.id)"
                    title="从项目中移除"
                  >
                    <template #icon><CloseOutlined /></template>
                  </a-button>
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
              <div class="annotation-list-label">已标注 ({{ annotations.length }})</div>
              <a-divider style="margin: 8px 0" />
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
          <a-col :span="selectedReview ? 14 : 24">
            <a-card title="审核队列" size="small">
              <template #extra>
                <a-space>
                  <a-select v-model:value="reviewFilter" placeholder="筛选" style="width:120px" allowClear @change="loadReviewQueue">
                    <a-select-option value="in_review">待审核</a-select-option>
                    <a-select-option value="rejected">已退回</a-select-option>
                  </a-select>
                  <a-button size="small" @click="loadReviewQueue"><ReloadOutlined />刷新</a-button>
                </a-space>
              </template>

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
          <a-col :span="10" v-if="selectedReview">
            <a-card size="small">
              <template #title>
                <div style="display:flex;align-items:center;gap:8px">
                  <span>{{ selectedReview.name }}</span>
                  <a-tag :color="getReviewStatusColor(selectedReview.status)">{{ getReviewStatusLabel(selectedReview.status) }}</a-tag>
                </div>
              </template>
              <template #extra>
                <a-button type="link" size="small" @click="closeReviewDetail">关闭</a-button>
              </template>

              <a-descriptions :column="2" size="small" bordered style="margin-bottom:16px">
                <a-descriptions-item label="进度">
                  {{ selectedReview.annotated_images }} / {{ selectedReview.total_images }} 张
                  <a-progress :percent="calcProgress(selectedReview.annotated_images, selectedReview.total_images)" size="small" style="margin-top:4px" />
                </a-descriptions-item>
                <a-descriptions-item label="已审核">{{ selectedReview.reviewed_images }} 张</a-descriptions-item>
                <a-descriptions-item label="创建时间">{{ new Date(selectedReview.created_at).toLocaleString('zh-CN') }}</a-descriptions-item>
                <a-descriptions-item label="描述">{{ selectedReview.description || '-' }}</a-descriptions-item>
              </a-descriptions>

              <div class="section-label">图片审核</div>
              <a-divider style="margin: 8px 0" />
              <div v-if="reviewImageLoading" style="text-align:center;padding:24px">
                <a-spin />
              </div>
              <a-empty v-else-if="!reviewImages.length" description="该项目暂无图片" :image="Empty.PRESENTED_IMAGE_SIMPLE" />
              <div v-else style="max-height: 420px; overflow-y: auto; padding-right: 4px">
                <a-list size="small" :data-source="reviewImages" item-layout="vertical">
                  <template #renderItem="{ item }">
                    <a-list-item :key="item.id">
                      <template #actions>
                        <a-tag v-if="getImageReviewStatus(item.id) === 'approve'" color="success">已通过</a-tag>
                        <a-tag v-else-if="getImageReviewStatus(item.id) === 'request_changes'" color="error">已退回</a-tag>
                        <a-tag v-else color="default">未审核</a-tag>
                        <a-button
                          size="small"
                          type="primary"
                          :loading="reviewImageSubmitting === item.id + ':approve'"
                          @click="confirmSingleApprove(item)"
                        >通过</a-button>
                        <a-button
                          size="small"
                          danger
                          :loading="reviewImageSubmitting === item.id + ':reject'"
                          @click="openSingleRejectModal(item)"
                        >退回</a-button>
                      </template>
                      <a-list-item-meta :description="getImageReviewReason(item.id)">
                        <template #title>
                          <div style="display:flex;align-items:center;gap:8px">
                            <a-image
                              :src="`/images/${item.id}/serve?size=128`"
                              :width="48"
                              :height="48"
                              style="object-fit: cover; border-radius: 4px"
                            />
                            <span>{{ item.original_filename || item.id }}</span>
                          </div>
                        </template>
                      </a-list-item-meta>
                    </a-list-item>
                  </template>
                </a-list>
              </div>

              <div class="section-label" style="margin-top: 16px">项目级操作</div>
              <a-divider style="margin: 8px 0" />
              <a-space direction="vertical" style="width:100%">
                <a-button type="primary" block @click="confirmBulkApprove" :loading="reviewActionLoading">
                  <template #icon><CheckOutlined /></template>一键通过全部图片并完成项目
                </a-button>
                <a-textarea v-model:value="rejectFeedback" placeholder="一键退回时使用的退回原因" :rows="2" />
                <a-button type="default" block danger @click="confirmBulkReject" :loading="reviewActionLoading">
                  <template #icon><CloseOutlined /></template>一键退回全部图片
                </a-button>
              </a-space>
            </a-card>
          </a-col>
        </a-row>
      </a-tab-pane>
    </a-tabs>

    <!-- Single-image reject modal -->
    <a-modal
      v-model:open="showSingleRejectModal"
      title="退回该图片"
      ok-text="确认退回"
      cancel-text="取消"
      :ok-button-props="{ danger: true }"
      @ok="handleSingleRejectConfirm"
    >
      <p style="margin-bottom: 8px">图片：{{ singleRejectTarget?.original_filename || singleRejectTarget?.id }}</p>
      <a-textarea v-model:value="singleRejectReason" placeholder="填写退回原因" :rows="3" />
    </a-modal>

    <!-- Bulk confirm modal -->
    <a-modal
      v-model:open="showBulkConfirm"
      :title="bulkConfirmTitle"
      :ok-text="bulkConfirmOkText"
      :ok-button-props="bulkConfirmDanger ? { danger: true } : { type: 'primary' }"
      @ok="handleBulkConfirm"
    >
      <p>{{ bulkConfirmContent }}</p>
    </a-modal>

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

function calcProgress(annotated: number, total: number): number {
  if (total > 0) {
    return Math.round((annotated / total) * 100)
  }
  return 0
}

async function loadStats() {
  await annStore.fetchStats()
}

// ── Projects ────────────────────────────────────────────────
const projectFilter = ref<string | null>(null)

const projectColumns = [
  { title: '名称', dataIndex: 'name', key: 'name', width: 180, ellipsis: true },
  { title: '描述', dataIndex: 'description', key: 'description', width: 160, ellipsis: true },
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

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    in_progress: '进行中',
    in_review: '待审核',
    completed: '已完成',
    reviewed: '已审核',
    rejected: '已退回',
  }
  return map[status] || status
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    draft: 'default',
    in_progress: 'processing',
    in_review: 'blue',
    completed: 'success',
    reviewed: 'success',
    rejected: 'error',
  }
  return map[status] || 'default'
}

// ── Annotate Tab Project Selection ──────────────────────────
const annotateProjectId = ref<string | null>(null)
const projectImageIds = ref<Set<string>>(new Set())

const canAddToProject = computed(() => {
  if (!annotateProjectId.value || !selectedAnnotateImageId.value) return false
  return !projectImageIds.value.has(selectedAnnotateImageId.value)
})

function isImageInProject(imageId: string): boolean {
  return projectImageIds.value.has(imageId)
}

function getImageStatusTag(imageId: string) {
  if (!isImageInProject(imageId)) return null
  if (!annotateProjectId.value) return null
  const savedSet = savedImageIds.value.get(annotateProjectId.value)
  if (savedSet?.has(imageId)) return { color: 'green', text: '已保存' }
  return { color: 'blue', text: '已添加' }
}

async function onAnnotateProjectChange(projectId: string) {
  annotateProjectId.value = projectId
  // 切换项目时清空当前画布
  selectedAnnotateImageId.value = null
  annStore.annotations = []
  await loadProjectImages(projectId)
}

async function loadProjectImages(projectId: string) {
  try {
    const res: any = await annotationsApi.getProjectImages(projectId)
    const imageIds = res.items?.map((item: any) => item.image_id) || []
    projectImageIds.value = new Set(imageIds)
    // 清除不属于新项目的已保存记录
    savedImageIds.value.set(projectId, new Set())
  } catch (error) {
    console.error('Failed to load project images:', error)
    projectImageIds.value = new Set()
  }
}

// Tab 切换时刷新数据
async function onTabChange(tabKey: string) {
  switch (tabKey) {
    case 'projects':
      await loadProjects()
      break
    case 'annotate':
      await loadAnnotateImages()
      break
    case 'classes':
      await annStore.fetchClasses()
      break
    case 'review':
      await loadReviewQueue()
      break
  }
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
  currentProjectId.value = project.id
  annStore.currentProject = project
  activeTab.value = 'annotate'
  // 设置当前项目并加载项目图片
  annotateProjectId.value = project.id
  loadProjectImages(project.id)
}

function selectProject(projectId: string) {
  currentProjectId.value = projectId
  const project = projects.value.find(p => p.id === projectId)
  if (project) {
    annStore.currentProject = project
  }
  activeTab.value = 'annotate'
  // 设置当前项目并加载项目图片
  annotateProjectId.value = projectId
  loadProjectImages(projectId)
}

// Current project for review submission
const currentProjectId = ref<string | null>(null)

// ── Annotate ────────────────────────────────────────────────
const annotateImages = ref<ImageResponse[]>([])
const selectedAnnotateImageId = ref<string | null>(null)
const annotateSourceFilter = ref<string | null>(null)
const annotatePage = ref(1)
const annotateTotal = ref(0)
const drawMode = ref<'view' | 'draw' | 'edit'>('view')
const selectedClassId = ref<string | null>(null)
const selectedAnnotationId = ref<string | null>(null)  // 当前选中的标注ID
// 已保存的图片ID集合，按项目隔离: Map<projectId, Set<imageId>>
const savedImageIds = ref<Map<string, Set<string>>>(new Map())

const canvasRef = ref<HTMLCanvasElement | null>(null)
const canvasContainer = ref<HTMLDivElement | null>(null)
const annotationListRef = ref<HTMLElement | null>(null)
const rowHeight = 40

let isDrawing = false
let drawStartX = 0
let drawStartY = 0
let isDragging = false
let dragAnnotationId: string | null = null
let dragOffsetX = 0
let dragOffsetY = 0
let scale = 1

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
  await annStore.loadImageAnnotations(img.id, annotateProjectId.value || undefined)
  await nextTick()
  renderCanvas()
}

async function addSelectedImageToProject() {
  if (!annotateProjectId.value || !selectedAnnotateImageId.value) {
    message.warning('请先选择一个项目和一张图片')
    return
  }
  try {
    await annotationsApi.addProjectImages(annotateProjectId.value, [selectedAnnotateImageId.value])
    message.success('图片已添加到项目')
    savedImageIds.value.get(annotateProjectId.value)?.delete(selectedAnnotateImageId.value)
    await loadProjectImages(annotateProjectId.value)
    await loadProjects()
    await loadStats()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '添加失败')
  }
}

async function removeImageFromProject(imageId: string) {
  if (!annotateProjectId.value) {
    message.warning('请先选择一个项目')
    return
  }
  Modal.confirm({
    title: '确认移除',
    content: '确定要从项目中移除这张图片吗？',
    okText: '移除',
    okType: 'danger',
    async onOk() {
      try {
        await annotationsApi.removeProjectImages(annotateProjectId.value!, [imageId])
        message.success('图片已从项目移除')
        projectImageIds.value.delete(imageId)
        savedImageIds.value.get(annotateProjectId.value)?.delete(imageId)
        if (selectedAnnotateImageId.value === imageId) {
          selectedAnnotateImageId.value = null
          annStore.annotations = []
        }
        await loadProjects()
        await loadStats()
      } catch (error: any) {
        message.error(error?.response?.data?.detail || '移除失败')
      }
    },
  })
}

function getClassColor(classId: string): string {
  const cls = annStore.classMap[classId]
  return cls?.color || '#3B82F6'
}

function setDrawMode(mode: 'view' | 'draw' | 'edit') {
  if (mode === 'draw') {
    if (!classes.value || classes.value.length === 0) {
      message.warning('暂无可用标注类别，请先在「类别管理」中添加类别')
      return
    }
    if (!selectedClassId.value) {
      selectedClassId.value = classes.value[0].id
      message.info(`已自动选中第一个类别：${classes.value[0].display_name}`)
    }
  }
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
      const isSelected = ann.id === selectedAnnotationId.value
      drawBBox(ctx, ann.bbox_x * scale, ann.bbox_y * scale,
                ann.bbox_width * scale, ann.bbox_height * scale,
                ann.class_id, isSelected)
    }
  }
  img.src = getImageUrl(imgId)
}

function drawBBox(
  ctx: CanvasRenderingContext2D,
  x: number, y: number, w: number, h: number,
  classId: string,
  isSelected = false
) {
  const cls = annStore.classMap[classId]
  const color = cls?.color || '#3B82F6'

  // 填充色
  ctx.fillStyle = color
  ctx.globalAlpha = 0.25
  ctx.fillRect(x, y, w, h)
  ctx.globalAlpha = 1.0

  // 边框
  ctx.strokeStyle = color
  ctx.lineWidth = isSelected ? 3 : 2
  ctx.strokeRect(x, y, w, h)

  // 选中状态：画虚线边框和控制点
  if (isSelected) {
    ctx.strokeStyle = '#fff'
    ctx.lineWidth = 1
    ctx.setLineDash([3, 3])
    ctx.strokeRect(x - 2, y - 2, w + 4, h + 4)
    ctx.setLineDash([])

    // 控制点
    const handleSize = 6
    ctx.fillStyle = '#fff'
    ctx.strokeStyle = color
    ctx.lineWidth = 1
    const corners = [
      [x, y], [x + w, y], [x, y + h], [x + w, y + h]
    ]
    for (const [cx, cy] of corners) {
      ctx.fillRect(cx - handleSize / 2, cy - handleSize / 2, handleSize, handleSize)
      ctx.strokeRect(cx - handleSize / 2, cy - handleSize / 2, handleSize, handleSize)
    }
  }

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
  if (!annotateProjectId.value || !isImageInProject(selectedAnnotateImageId.value)) {
    message.warning('请先将图片添加到标注项目')
    return
  }
  // 在编辑模式下点击选中/取消选中标注
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const cx = (e.clientX - rect.left)
  const cy = (e.clientY - rect.top)

  // 查找点击的标注
  for (const ann of annStore.annotations) {
    const ax = ann.bbox_x * scale
    const ay = ann.bbox_y * scale
    const aw = ann.bbox_width * scale
    const ah = ann.bbox_height * scale
    if (cx >= ax && cx <= ax + aw && cy >= ay && cy <= ay + ah) {
      // 点击了标注框，切换选中状态
      if (selectedAnnotationId.value === ann.id) {
        selectedAnnotationId.value = null
      } else {
        selectedAnnotationId.value = ann.id
      }
      renderCanvas()
      return
    }
  }
  // 点击空白处取消选中
  selectedAnnotationId.value = null
  renderCanvas()
}

function handleCanvasMouseDown(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const mouseX = e.clientX - rect.left
  const mouseY = e.clientY - rect.top

  // 编辑模式下：尝试开始拖动选中的标注
  if (drawMode.value === 'edit') {
    // 查找是否点击在选中标注上
    if (selectedAnnotationId.value) {
      const selectedAnn = annStore.annotations.find(a => a.id === selectedAnnotationId.value)
      if (selectedAnn) {
        const ax = selectedAnn.bbox_x * scale
        const ay = selectedAnn.bbox_y * scale
        const aw = selectedAnn.bbox_width * scale
        const ah = selectedAnn.bbox_height * scale
        if (mouseX >= ax && mouseX <= ax + aw && mouseY >= ay && mouseY <= ay + ah) {
          // 开始拖动
          isDragging = true
          dragAnnotationId = selectedAnnotationId.value
          dragOffsetX = mouseX - ax
          dragOffsetY = mouseY - ay
          e.preventDefault()
          return
        }
      }
    }
    return
  }

  // 绘制模式
  if (drawMode.value !== 'draw' || !selectedClassId.value) return
  if (!annotateProjectId.value || !isImageInProject(selectedAnnotateImageId.value)) {
    message.warning('请先将图片添加到标注项目')
    return
  }
  isDrawing = true
  drawStartX = mouseX
  drawStartY = mouseY
  e.preventDefault()
}

function handleCanvasMouseMove(e: MouseEvent) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const curX = e.clientX - rect.left
  const curY = e.clientY - rect.top

  // 拖动模式：移动选中的标注
  if (isDragging && dragAnnotationId) {
    const ann = annStore.annotations.find(a => a.id === dragAnnotationId)
    if (ann) {
      // 计算新的位置（转换为图片坐标）
      const newX = (curX - dragOffsetX) / scale
      const newY = (curY - dragOffsetY) / scale

      // 限制在图片范围内
      ann.bbox_x = Math.max(0, Math.min(newX, canvas.width / scale - ann.bbox_width))
      ann.bbox_y = Math.max(0, Math.min(newY, canvas.height / scale - ann.bbox_height))

      renderCanvas()
    }
    return
  }

  // 绘制模式
  if (!isDrawing || drawMode.value !== 'draw') return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

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
  const canvas = canvasRef.value

  // 拖动模式：结束拖动并保存
  if (isDragging && dragAnnotationId) {
    isDragging = false
    // 保存拖动后的位置
    const ann = annStore.annotations.find(a => a.id === dragAnnotationId)
    if (ann) {
      await annStore.updateAnnotation(ann.id, {
        bbox_x: ann.bbox_x,
        bbox_y: ann.bbox_y,
      })
    }
    dragAnnotationId = null
    renderCanvas()
    return
  }

  // 绘制模式
  if (!isDrawing || drawMode.value !== 'draw') return
  isDrawing = false
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

  if (!annotateProjectId.value) return

  // Auto-select first class if none is selected; warn if there are no classes
  if (!selectedClassId.value) {
    if (!classes.value || classes.value.length === 0) {
      message.warning('暂无可用标注类别，请先在「类别管理」中添加类别')
      return
    }
    selectedClassId.value = classes.value[0].id
    message.info(`已自动选中第一个类别：${classes.value[0].display_name}`)
  }

  await annStore.addAnnotation({
    class_id: selectedClassId.value!,
    bbox_x: imgX,
    bbox_y: imgY,
    bbox_width: imgW,
    bbox_height: imgH,
    conf: 1.0,
    is_auto_annotated: false,
  }, annotateProjectId.value)

  await nextTick()
  renderCanvas()
}

async function removeAnnotation(id: string) {
  await annStore.removeAnnotation(id)
  await nextTick()
  renderCanvas()
}

async function saveAnnotations() {
  if (!annotateProjectId.value) {
    message.warning('请先选择标注项目')
    return
  }
  if (!selectedAnnotateImageId.value) {
    message.warning('请先选择图片')
    return
  }
  if (!isImageInProject(selectedAnnotateImageId.value)) {
    message.warning('请先将图片添加到标注项目')
    return
  }
  if (!savedImageIds.value.has(annotateProjectId.value)) {
    savedImageIds.value.set(annotateProjectId.value, new Set())
  }
  savedImageIds.value.get(annotateProjectId.value)!.add(selectedAnnotateImageId.value)
  message.success('标注已保存')
}

async function handleSubmitForReview() {
  if (!currentProjectId.value) {
    message.warning('请先选择一个标注项目')
    return
  }
  await doSubmitForReview(currentProjectId.value)
}

async function handleSubmitForReviewById(projectId: string) {
  await doSubmitForReview(projectId)
}

async function doSubmitForReview(projectId: string) {
  try {
    await annotationsApi.submitForReview(projectId)
    message.success('已提交审核')
    await loadProjects()
    await loadStats()
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '提交审核失败')
  }
}

async function exportYOLO() {
  try {
    await annotationsApi.exportYOLO()
  } catch (e) {
    console.error('Export failed:', e)
  }
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

// Per-image review state
interface ReviewImage { id: string; original_filename?: string }
const reviewImages = ref<ReviewImage[]>([])
const reviewImageReviews = ref<Record<string, { review_status: string; rejection_reason: string }>>({})
const reviewImageLoading = ref(false)
const reviewImageSubmitting = ref<string | null>(null)
const showSingleRejectModal = ref(false)
const singleRejectTarget = ref<ReviewImage | null>(null)
const singleRejectReason = ref('')

// Bulk confirm modal state
const showBulkConfirm = ref(false)
const bulkConfirmTitle = ref('')
const bulkConfirmContent = ref('')
const bulkConfirmOkText = ref('确认')
const bulkConfirmDanger = ref(false)
const bulkConfirmAction = ref<(() => Promise<void>) | null>(null)
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
    const statsRes: any = await annotationsApi.getReviewSummary()
    reviewStats.value = {
      pending_review: statsRes.pending_review || 0,
      needs_revision: statsRes.needs_revision || 0,
      completed: statsRes.completed || 0,
      in_progress: statsRes.in_progress || 0,
    }
  } catch (e) { console.error(e) }
  finally { reviewLoading.value = false }
}

function getImageReviewStatus(imageId: string): string | null {
  return reviewImageReviews.value[imageId]?.review_status || null
}

function getImageReviewReason(imageId: string): string {
  const r = reviewImageReviews.value[imageId]
  if (!r) return '未审核'
  if (r.review_status === 'request_changes' && r.rejection_reason) {
    return `退回原因：${r.rejection_reason}`
  }
  if (r.review_status === 'approve') return '已通过'
  if (r.review_status === 'request_changes') return '已退回'
  return '未审核'
}

async function selectReviewProject(project: any) {
  selectedReview.value = project
  rejectFeedback.value = project.review_feedback || ''
  reviewImages.value = []
  reviewImageReviews.value = {}
  await loadReviewImages(project.id)
  await refreshSelectedReview(project.id)
}

async function loadReviewImages(projectId: string) {
  reviewImageLoading.value = true
  try {
    // Get images linked to the project via /projects/{id}/images (returns {image_id, added_at})
    // Use store.imagesData which is already loaded for the annotate tab
    const res: any = await annotationsApi.getProjectImages(projectId)
    const items = (res?.items || []) as { image_id: string; added_at?: string }[]
    // Try to enrich with original_filename from the global image list (ImageManager)
    const allImages: any[] = (window as any).__allImages || []
    reviewImages.value = items.map(it => {
      const meta = allImages.find((im: any) => im.id === it.image_id)
      return {
        id: it.image_id,
        original_filename: meta?.original_filename || meta?.filename || it.image_id,
      }
    })
  } catch (e) { console.error(e) }
  finally { reviewImageLoading.value = false }
}

async function refreshSelectedReview(projectId: string) {
  try {
    const res: any = await annotationsApi.getProjectImageReviews(projectId)
    reviewImageReviews.value = res.reviews || {}
  } catch (e) { console.error(e) }
  try {
    const fresh: any = await annotationsApi.getProject(projectId)
    selectedReview.value = fresh
  } catch (e) { console.error(e) }
}

function closeReviewDetail() {
  selectedReview.value = null
  reviewImages.value = []
  reviewImageReviews.value = {}
}

async function confirmSingleApprove(item: ReviewImage) {
  showBulkConfirm.value = true
  bulkConfirmTitle.value = '通过该图片'
  bulkConfirmContent.value = `确定要将图片「${item.original_filename || item.id}」审核通过吗？`
  bulkConfirmOkText.value = '通过'
  bulkConfirmDanger.value = false
  bulkConfirmAction.value = async () => {
    await doSingleApprove(item)
  }
}

async function doSingleApprove(item: ReviewImage) {
  if (!selectedReview.value) return
  reviewImageSubmitting.value = item.id + ':approve'
  try {
    await annotationsApi.reviewProjectImage(selectedReview.value.id, item.id, { action: 'approve' })
    message.success('已通过')
    await refreshSelectedReview(selectedReview.value.id)
    await loadReviewQueue()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    reviewImageSubmitting.value = null
  }
}

function openSingleRejectModal(item: ReviewImage) {
  singleRejectTarget.value = item
  singleRejectReason.value = ''
  showSingleRejectModal.value = true
}

async function handleSingleRejectConfirm() {
  if (!selectedReview.value || !singleRejectTarget.value) {
    showSingleRejectModal.value = false
    return
  }
  if (!singleRejectReason.value.trim()) {
    message.warning('请填写退回原因')
    return
  }
  const item = singleRejectTarget.value
  showSingleRejectModal.value = false
  reviewImageSubmitting.value = item.id + ':reject'
  try {
    await annotationsApi.reviewProjectImage(selectedReview.value.id, item.id, {
      action: 'request_changes',
      reason: singleRejectReason.value,
    })
    message.success('已退回')
    await refreshSelectedReview(selectedReview.value.id)
    await loadReviewQueue()
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    reviewImageSubmitting.value = null
    singleRejectTarget.value = null
  }
}

function confirmBulkApprove() {
  if (!selectedReview.value) return
  showBulkConfirm.value = true
  bulkConfirmTitle.value = '一键通过'
  bulkConfirmContent.value = `确定要将「${selectedReview.value.name}」中所有 ${reviewImages.value.length} 张图片全部通过审核吗？通过后项目状态将变为「已完成」。`
  bulkConfirmOkText.value = '一键通过'
  bulkConfirmDanger.value = false
  bulkConfirmAction.value = doBulkApprove
}

async function doBulkApprove() {
  if (!selectedReview.value) return
  reviewActionLoading.value = true
  try {
    await annotationsApi.bulkApproveProject(selectedReview.value.id)
    message.success('已全部通过，项目已完成')
    await loadReviewQueue()
    await refreshSelectedReview(selectedReview.value.id)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    reviewActionLoading.value = false
  }
}

function confirmBulkReject() {
  if (!selectedReview.value) return
  if (!rejectFeedback.value.trim()) {
    message.warning('请填写退回原因')
    return
  }
  showBulkConfirm.value = true
  bulkConfirmTitle.value = '一键退回'
  bulkConfirmContent.value = `确定要将「${selectedReview.value.name}」中所有 ${reviewImages.value.length} 张图片全部退回吗？项目状态将变为「已退回」。`
  bulkConfirmOkText.value = '一键退回'
  bulkConfirmDanger.value = true
  bulkConfirmAction.value = doBulkReject
}

async function doBulkReject() {
  if (!selectedReview.value) return
  reviewActionLoading.value = true
  try {
    await annotationsApi.bulkRejectProject(selectedReview.value.id, { reason: rejectFeedback.value })
    message.success('已全部退回')
    await loadReviewQueue()
    await refreshSelectedReview(selectedReview.value.id)
  } catch (e: any) {
    message.error(e?.response?.data?.detail || '操作失败')
  } finally {
    reviewActionLoading.value = false
  }
}

async function handleBulkConfirm() {
  const action = bulkConfirmAction.value
  bulkConfirmAction.value = null
  if (action) await action()
  showBulkConfirm.value = false
}

// ── Lifecycle ───────────────────────────────────────────────

function handleKeyDown(e: KeyboardEvent) {
  // Delete 键删除选中的标注
  if (e.key === 'Delete' || e.key === 'Backspace') {
    if (drawMode.value === 'edit' && selectedAnnotationId.value) {
      e.preventDefault()
      removeAnnotation(selectedAnnotationId.value)
      selectedAnnotationId.value = null
    }
  }
  // Escape 取消选中
  if (e.key === 'Escape') {
    if (selectedAnnotationId.value) {
      selectedAnnotationId.value = null
      renderCanvas()
    }
  }
}

onMounted(async () => {
  await Promise.all([
    annStore.fetchClasses(),
    loadProjects(),
    loadStats(),
    loadAnnotateImages(),
    loadReviewQueue(),
  ])
  // 添加键盘事件监听
  window.addEventListener('keydown', handleKeyDown)
})

onUnmounted(() => {
  annStore.reset()
  // 移除键盘事件监听
  window.removeEventListener('keydown', handleKeyDown)
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
  position: relative;
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

.remove-from-project-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.image-item:hover .remove-from-project-btn {
  opacity: 1;
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

/* Section labels for dividers */
.section-label {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  margin-bottom: 4px;
}

.annotation-list-label {
  font-size: 14px;
  font-weight: 500;
  color: rgba(0, 0, 0, 0.85);
  margin-bottom: 4px;
}
</style>
