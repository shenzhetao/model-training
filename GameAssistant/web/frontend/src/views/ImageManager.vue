<template>
  <div class="image-manager">
    <!-- Header -->
    <div class="page-header">
      <div class="header-left">
        <a-typography-title :level="2">图片管理</a-typography-title>
        <span class="total-count">共 {{ imagesStore.total }} 张图片</span>
      </div>
      <div class="header-actions">
        <a-space>
          <a-select
            v-model:value="sourceFilter"
            placeholder="筛选来源"
            style="width: 120px"
            allowClear
            @change="handleSourceFilterChange"
          >
            <a-select-option value="upload">手动上传</a-select-option>
            <a-select-option value="adb">ADB截图</a-select-option>
            <a-select-option value="video">视频抽帧</a-select-option>
          </a-select>
          <a-button @click="handleRefresh">
            <template #icon><ReloadOutlined /></template>
            刷新
          </a-button>
        </a-space>
      </div>
    </div>

    <!-- Video Extraction Panel -->
    <a-collapse v-model:activeKey="videoPanelActive" class="video-panel">
      <a-collapse-panel key="video" header="视频抽帧">
        <template #extra><VideoCameraOutlined /></template>
        <div class="video-extraction">
          <a-row :gutter="16">
            <a-col :span="12">
              <!-- Video Upload -->
              <div class="video-upload-section">
                <a-typography-title :level="5">1. 上传视频</a-typography-title>
                <a-upload
                  :before-upload="handleVideoSelect"
                  :show-upload-list="false"
                  accept=".mp4,.avi,.mkv,.mov,.wmv,.flv,.webm"
                  :disabled="uploadingVideo"
                >
                  <a-button type="primary" :loading="uploadingVideo">
                    <template #icon><UploadOutlined /></template>
                    选择视频文件
                  </a-button>
                </a-upload>
                <p class="upload-hint">支持 MP4, AVI, MKV, MOV 等格式，最大 10GB</p>
              </div>

              <!-- Video List -->
              <div v-if="videos.length > 0" class="video-list-section">
                <a-typography-title :level="5">已上传视频</a-typography-title>
                <a-list
                  size="small"
                  :data-source="videos"
                  :pagination="{ pageSize: 5 }"
                >
                  <template #renderItem="{ item }">
                    <a-list-item>
                      <a-list-item-meta>
                        <template #title>
                          <span class="video-name" :class="{ selected: selectedVideoId === item.id }" @click="selectVideo(item)">
                            {{ item.original_filename }}
                          </span>
                        </template>
                        <template #description>
                          {{ item.duration.toFixed(1) }}s | {{ item.width }}x{{ item.height }} | {{ formatFileSize(item.file_size) }}
                        </template>
                      </a-list-item-meta>
                      <template #actions>
                        <a-button type="link" danger size="small" @click="handleDeleteVideo(item.id)">
                          <DeleteOutlined />
                        </a-button>
                      </template>
                    </a-list-item>
                  </template>
                </a-list>
              </div>
            </a-col>

            <a-col :span="12">
              <!-- Extraction Settings -->
              <div class="extraction-settings">
                <a-typography-title :level="5">2. 抽帧配置</a-typography-title>
                
                <a-form :model="extractionConfig" layout="vertical">
                  <a-form-item label="抽帧策略">
                    <a-radio-group v-model:value="extractionConfig.strategy">
                      <a-radio value="interval">按时间间隔</a-radio>
                      <a-radio value="count">固定数量</a-radio>
                      <a-radio value="scene_change">场景变化</a-radio>
                    </a-radio-group>
                  </a-form-item>

                  <a-form-item 
                    v-if="extractionConfig.strategy === 'interval'" 
                    label="间隔（秒）"
                  >
                    <a-input-number
                      v-model:value="extractionConfig.intervalSeconds"
                      :min="0.1"
                      :max="3600"
                      :step="0.1"
                      style="width: 100%"
                    />
                    <p class="config-hint">每隔 N 秒抽取一帧</p>
                  </a-form-item>

                  <a-form-item 
                    v-if="extractionConfig.strategy === 'count'" 
                    label="抽帧数量"
                  >
                    <a-input-number
                      v-model:value="extractionConfig.frameCount"
                      :min="1"
                      :max="10000"
                      style="width: 100%"
                    />
                    <p class="config-hint">均匀抽取 N 帧</p>
                  </a-form-item>

                  <a-form-item 
                    v-if="extractionConfig.strategy === 'scene_change'" 
                    label="场景变化阈值"
                  >
                    <a-slider
                      v-model:value="extractionConfig.sceneThreshold"
                      :min="0.05"
                      :max="1"
                      :step="0.05"
                      :marks="{ 0.05: '低', 0.3: '中', 0.6: '高', 1: '最高' }"
                    />
                    <p class="config-hint">帧间差异超过此阈值时抽取（值越低越敏感）</p>
                  </a-form-item>
                </a-form>

                <!-- Start Extraction Button -->
                <a-button
                  type="primary"
                  :disabled="!selectedVideoId || startingExtraction"
                  :loading="startingExtraction"
                  @click="startExtraction"
                  block
                >
                  <template #icon><PlayCircleOutlined /></template>
                  开始抽帧
                </a-button>
              </div>
            </a-col>
          </a-row>

          <!-- Active Tasks -->
          <a-divider>抽帧任务</a-divider>
          <div class="extraction-tasks">
            <a-empty v-if="activeTasks.length === 0" description="暂无进行中的抽帧任务" />
            <a-list v-else size="small" :data-source="activeTasks">
              <template #renderItem="{ item }">
                <a-list-item>
                  <a-list-item-meta>
                    <template #title>
                      <span :class="getTaskStatusClass(item.status)">
                        {{ getTaskStatusText(item.status) }}
                      </span>
                      <span class="task-info"> | {{ item.strategy }}</span>
                    </template>
                    <template #description>
                      <a-progress
                        v-if="item.total_frames"
                        :percent="Math.round((item.extracted_frames / item.total_frames) * 100)"
                        :status="item.status === 'failed' ? 'exception' : undefined"
                        size="small"
                      />
                      <span v-else>等待开始...</span>
                    </template>
                  </a-list-item-meta>
                </a-list-item>
              </template>
            </a-list>
          </div>
        </div>
      </a-collapse-panel>
    </a-collapse>

    <!-- Upload Area -->
    <div
      class="upload-area"
      :class="{ 'drag-over': isDragOver }"
      @dragover.prevent="handleDragOver"
      @dragleave.prevent="handleDragLeave"
      @drop.prevent="handleDrop"
    >
      <div class="upload-content">
        <CloudUploadOutlined class="upload-icon" />
        <p class="upload-text">拖拽图片文件或 ZIP 包到此处上传</p>
        <p class="upload-hint">支持 JPG, PNG, GIF, BMP, WEBP 格式</p>
        <div class="upload-buttons">
          <a-upload
            :before-upload="handleFileSelect"
            :show-upload-list="false"
            accept=".jpg,.jpeg,.png,.gif,.bmp,.webp"
          >
            <a-button type="primary">
              <template #icon><UploadOutlined /></template>
              上传单张图片
            </a-button>
          </a-upload>
          <a-upload
            :before-upload="handleZipSelect"
            :show-upload-list="false"
            accept=".zip"
          >
            <a-button>
              <template #icon><FileZipOutlined /></template>
              上传 ZIP 包
            </a-button>
          </a-upload>
        </div>
        <div v-if="imagesStore.uploading" class="upload-progress">
          <a-progress :percent="imagesStore.uploadProgress" status="active" />
          <span>上传中...</span>
        </div>
      </div>
    </div>

    <!-- Selection Actions -->
    <div v-if="imagesStore.hasSelection" class="selection-bar">
      <a-space>
        <span>已选择 {{ imagesStore.selectionCount }} 项</span>
        <a-button type="link" @click="imagesStore.toggleSelectAll">
          {{ imagesStore.allSelected ? '取消全选' : '全选' }}
        </a-button>
        <a-button type="link" danger @click="handleBatchDelete">
          <template #icon><DeleteOutlined /></template>
          删除选中
        </a-button>
        <a-button type="link" @click="imagesStore.clearSelection">取消选择</a-button>
      </a-space>
    </div>

    <!-- Image Grid -->
    <div class="image-grid-container">
      <div v-if="imagesStore.loading && imagesStore.images.length === 0" class="loading-container">
        <a-spin size="large" />
        <p>加载中...</p>
      </div>

      <div v-else-if="imagesStore.images.length === 0" class="empty-container">
        <InboxOutlined class="empty-icon" />
        <p>暂无图片</p>
        <p class="empty-hint">点击上方按钮上传图片</p>
      </div>

      <div v-else class="image-grid">
        <div
          v-for="(image, index) in imagesStore.images"
          :key="image.id"
          class="image-card"
          :class="{ selected: imagesStore.selectedIds.has(image.id) }"
          @click="handleImageClick(image, index, $event)"
        >
          <div class="image-thumbnail" @click.stop="openLightbox(index)">
            <img
              :src="getImageUrl(image.id)"
              :alt="image.original_filename"
              loading="lazy"
            />
            <div class="image-overlay">
              <EyeOutlined />
            </div>
          </div>
          <div class="image-info">
            <div class="image-name" :title="image.original_filename">
              {{ image.original_filename }}
            </div>
            <div class="image-meta">
              <a-tag :color="getSourceColor(image.source)" size="small">
                {{ getSourceLabel(image.source) }}
              </a-tag>
              <span class="image-size">{{ formatFileSize(image.file_size) }}</span>
            </div>
          </div>
          <div class="image-checkbox">
            <a-checkbox
              :checked="imagesStore.selectedIds.has(image.id)"
              @click.stop="imagesStore.toggleSelection(image.id)"
            />
          </div>
          <div class="image-actions">
            <a-button
              type="text"
              size="small"
              danger
              @click.stop="handleDeleteImage(image.id)"
            >
              <template #icon><DeleteOutlined /></template>
            </a-button>
          </div>
        </div>
      </div>

      <!-- Pagination -->
      <div v-if="imagesStore.totalPages > 1" class="pagination">
        <a-pagination
          v-model:current="currentPage"
          :total="imagesStore.total"
          :page-size="imagesStore.pageSize"
          show-quick-jumper
          @change="handlePageChange"
        />
      </div>
    </div>

    <!-- Lightbox -->
    <a-modal
      v-model:open="lightboxVisible"
      :footer="null"
      :width="900"
      :bodyStyle="{ padding: 0, background: '#000' }"
      :centered="true"
      @cancel="closeLightbox"
    >
      <div class="lightbox" @keydown="handleLightboxKeydown" tabindex="0" ref="lightboxRef">
        <div class="lightbox-content">
          <img
            v-if="currentLightboxImage"
            :src="getImageUrl(currentLightboxImage.id)"
            :alt="currentLightboxImage.original_filename"
          />
        </div>
        <div class="lightbox-nav lightbox-prev" @click="prevImage">
          <LeftOutlined />
        </div>
        <div class="lightbox-nav lightbox-next" @click="nextImage">
          <RightOutlined />
        </div>
        <div class="lightbox-info">
          <span>{{ currentLightboxImage?.original_filename }}</span>
          <span>{{ currentLightboxImage?.width }} x {{ currentLightboxImage?.height }}</span>
          <span>{{ formatFileSize(currentLightboxImage?.file_size || 0) }}</span>
          <span>{{ imagesStore.lightboxIndex + 1 }} / {{ imagesStore.images.length }}</span>
        </div>
        <div class="lightbox-actions">
          <a-button type="text" danger @click="handleDeleteCurrentImage">
            <template #icon><DeleteOutlined /></template>
          </a-button>
        </div>
      </div>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import { message, Modal } from 'ant-design-vue'
import type { UploadProps } from 'ant-design-vue'
import {
  ReloadOutlined,
  CloudUploadOutlined,
  UploadOutlined,
  FileZipOutlined,
  EyeOutlined,
  DeleteOutlined,
  InboxOutlined,
  LeftOutlined,
  RightOutlined,
  VideoCameraOutlined,
  PlayCircleOutlined,
} from '@ant-design/icons-vue'
import { useImagesStore } from '@/stores/images'
import type { ImageResponse } from '@/api/images'
import imagesApi from '@/api/images'
import videosApi, { 
  type SourceVideoResponse, 
  type ExtractionTaskResponse,
  type ExtractionStrategy 
} from '@/api/videos'

const imagesStore = useImagesStore()

// Local state
const isDragOver = ref(false)
const sourceFilter = ref<string | null>(null)
const currentPage = ref(1)
const lightboxRef = ref<HTMLElement | null>(null)

// Video extraction state
const videoPanelActive = ref<string[]>([])
const videos = ref<SourceVideoResponse[]>([])
const selectedVideoId = ref<string | null>(null)
const uploadingVideo = ref(false)
const startingExtraction = ref(false)
const activeTasks = ref<ExtractionTaskResponse[]>([])
const extractionConfig = ref({
  strategy: 'interval' as 'interval' | 'count' | 'scene_change',
  intervalSeconds: 1,
  frameCount: 100,
  sceneThreshold: 0.3,
})

// Load videos on mount
async function loadVideos() {
  try {
    const response = await videosApi.getList({ page_size: 100 })
    videos.value = response.items
  } catch (error) {
    console.error('Failed to load videos:', error)
  }
}

// Load active tasks
async function loadActiveTasks() {
  try {
    const response = await videosApi.getExtractionTaskList({ page_size: 50 })
    // Filter to show only pending/running tasks
    activeTasks.value = response.items.filter(
      (task: ExtractionTaskResponse) => ['pending', 'running'].includes(task.status)
    )
  } catch (error) {
    console.error('Failed to load tasks:', error)
  }
}

// Video upload handler
async function handleVideoSelect(file: File) {
  const validExtensions = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm']
  const ext = '.' + file.name.toLowerCase().split('.').pop()
  if (!validExtensions.includes(ext)) {
    message.error('不支持的视频格式')
    return false
  }
  if (file.size > 10 * 1024 * 1024 * 1024) {
    message.error('视频文件大小不能超过 10GB')
    return false
  }

  uploadingVideo.value = true
  try {
    const response = await videosApi.upload(file)
    if (response.success && response.video) {
      message.success('视频上传成功')
      videos.value.unshift(response.video)
      selectedVideoId.value = response.video.id
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '视频上传失败')
  } finally {
    uploadingVideo.value = false
  }
  return false
}

// Select video
function selectVideo(video: SourceVideoResponse) {
  selectedVideoId.value = video.id
}

// Delete video
async function handleDeleteVideo(videoId: string) {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这个视频吗？抽帧产生的图片不会被删除。',
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await videosApi.delete(videoId)
        message.success('视频已删除')
        videos.value = videos.value.filter(v => v.id !== videoId)
        if (selectedVideoId.value === videoId) {
          selectedVideoId.value = null
        }
      } catch (error) {
        message.error('删除失败')
      }
    },
  })
}

// Start extraction
async function startExtraction() {
  if (!selectedVideoId.value) {
    message.warning('请先选择一个视频')
    return
  }

  startingExtraction.value = true
  try {
    const taskData = {
      strategy: extractionConfig.value.strategy as ExtractionStrategy,
    } as {
      strategy: ExtractionStrategy
      interval_seconds?: number
      frame_count?: number
      scene_threshold?: number
    }
    if (extractionConfig.value.strategy === 'interval') {
      taskData.interval_seconds = extractionConfig.value.intervalSeconds
    } else if (extractionConfig.value.strategy === 'count') {
      taskData.frame_count = extractionConfig.value.frameCount
    } else if (extractionConfig.value.strategy === 'scene_change') {
      taskData.scene_threshold = extractionConfig.value.sceneThreshold
    }

    const response = await videosApi.createExtractionTask(selectedVideoId.value, taskData)
    if (response.success && response.task) {
      message.success('抽帧任务已启动')
      activeTasks.value.unshift(response.task)
      // Start polling for task status
      pollTaskStatus(response.task.id)
    }
  } catch (error: any) {
    message.error(error?.response?.data?.detail || '创建抽帧任务失败')
  } finally {
    startingExtraction.value = false
  }
}

// Poll task status
let pollIntervals: Record<string, number> = {}
function pollTaskStatus(taskId: string) {
  if (pollIntervals[taskId]) return
  
  pollIntervals[taskId] = window.setInterval(async () => {
    try {
      const task = await videosApi.getExtractionTask(taskId)
      const index = activeTasks.value.findIndex(t => t.id === taskId)
      if (index >= 0) {
        if (task.status === 'completed' || task.status === 'failed') {
          // Task finished
          activeTasks.value.splice(index, 1)
          clearInterval(pollIntervals[taskId])
          delete pollIntervals[taskId]
          
          if (task.status === 'completed') {
            message.success(`抽帧完成！共提取 ${task.extracted_frames} 张图片`)
            // Refresh images to show new frames
            imagesStore.fetchImages({ source: 'video' })
          } else {
            message.error(`抽帧失败: ${task.error_message}`)
          }
        } else {
          // Update task progress
          activeTasks.value[index] = task
        }
      } else {
        // Task no longer in active list, stop polling
        clearInterval(pollIntervals[taskId])
        delete pollIntervals[taskId]
      }
    } catch (error) {
      console.error('Failed to poll task status:', error)
    }
  }, 2000)
}

function getTaskStatusClass(status: string): string {
  const classes: Record<string, string> = {
    pending: 'status-pending',
    running: 'status-running',
    completed: 'status-completed',
    failed: 'status-failed',
  }
  return classes[status] || ''
}

function getTaskStatusText(status: string): string {
  const texts: Record<string, string> = {
    pending: '等待中',
    running: '抽帧中',
    completed: '已完成',
    failed: '失败',
  }
  return texts[status] || status
}

// Computed
const lightboxVisible = computed({
  get: () => imagesStore.lightboxVisible,
  set: (val: boolean) => {
    if (!val) imagesStore.closeLightbox()
  },
})

const currentLightboxImage = computed(() => {
  if (imagesStore.images.length > 0 && imagesStore.lightboxIndex < imagesStore.images.length) {
    return imagesStore.images[imagesStore.lightboxIndex]
  }
  return null
})

// Methods
function getImageUrl(id: string): string {
  return imagesApi.getServeUrl(id)
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

function getSourceColor(source: string): string {
  const colors: Record<string, string> = {
    upload: 'blue',
    adb: 'green',
    video: 'orange',
  }
  return colors[source] || 'default'
}

function getSourceLabel(source: string): string {
  const labels: Record<string, string> = {
    upload: '上传',
    adb: 'ADB',
    video: '视频',
  }
  return labels[source] || source
}

// Upload handlers
const handleFileSelect: UploadProps['beforeUpload'] = async (file: File, _fileList: unknown) => {
  if (!isValidImageFile(file.name)) {
    message.error('不支持的文件格式')
    return false
  }
  if (file.size > 50 * 1024 * 1024) {
    message.error('文件大小不能超过 50MB')
    return false
  }

  try {
    const response = await imagesStore.uploadSingle(file)
    if (response.success) {
      message.success('图片上传成功')
    } else if (response.is_duplicate) {
      message.warning('图片已存在')
    }
  } catch (error: any) {
    if (error?.response?.data?.detail?.detail === 'Duplicate image detected') {
      message.warning('图片已存在')
    } else {
      message.error('上传失败')
    }
  }
  return false
}

const handleZipSelect: UploadProps['beforeUpload'] = async (file: File, _fileList: unknown) => {
  if (!file.name.toLowerCase().endsWith('.zip')) {
    message.error('请选择 ZIP 文件')
    return false
  }
  if (file.size > 2 * 1024 * 1024 * 1024) {
    message.error('ZIP 文件大小不能超过 2GB')
    return false
  }

  try {
    const response = await imagesStore.uploadBatch(file)
    if (response.success) {
      message.success(
        `批量上传完成：成功 ${response.uploaded} 张，跳过 ${response.skipped + response.duplicates} 张`
      )
      if (response.errors.length > 0) {
        message.warning(`${response.failed} 张图片上传失败`)
      }
    }
  } catch (error) {
    message.error('批量上传失败')
  }
  return false
}

function isValidImageFile(filename: string): boolean {
  const ext = filename.toLowerCase().split('.').pop()
  return ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext || '')
}

// Drag and drop
function handleDragOver(_e: DragEvent) {
  isDragOver.value = true
}

function handleDragLeave() {
  isDragOver.value = false
}

function handleDrop(e: DragEvent) {
  isDragOver.value = false
  const files = e.dataTransfer?.files
  if (!files || files.length === 0) return

  const file = files[0]
  if (file.name.toLowerCase().endsWith('.zip')) {
    ;(handleZipSelect as (file: File) => boolean | PromiseLike<boolean>)(file)
  } else {
    ;(handleFileSelect as (file: File) => boolean | PromiseLike<boolean>)(file)
  }
}

// Selection and actions
function handleImageClick(image: ImageResponse, index: number, event: MouseEvent) {
  if (event.ctrlKey || event.metaKey) {
    imagesStore.toggleSelection(image.id)
  } else {
    imagesStore.openLightbox(index)
  }
}

function openLightbox(index: number) {
  imagesStore.openLightbox(index)
  nextTick(() => {
    lightboxRef.value?.focus()
  })
}

function closeLightbox() {
  imagesStore.closeLightbox()
}

function prevImage() {
  imagesStore.lightboxPrev()
}

function nextImage() {
  imagesStore.lightboxNext()
}

function handleLightboxKeydown(e: KeyboardEvent) {
  if (e.key === 'ArrowLeft') {
    prevImage()
  } else if (e.key === 'ArrowRight') {
    nextImage()
  } else if (e.key === 'Escape') {
    closeLightbox()
  }
}

async function handleDeleteImage(id: string) {
  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这张图片吗？',
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        const response = await imagesStore.deleteImage(id)
        if (response.success) {
          message.success('删除成功')
        }
      } catch (error) {
        message.error('删除失败')
      }
    },
  })
}

async function handleDeleteCurrentImage() {
  const image = currentLightboxImage.value
  if (!image) return

  Modal.confirm({
    title: '确认删除',
    content: '确定要删除这张图片吗？',
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        const response = await imagesStore.deleteImage(image.id)
        if (response.success) {
          message.success('删除成功')
          closeLightbox()
        }
      } catch (error) {
        message.error('删除失败')
      }
    },
  })
}

async function handleBatchDelete() {
  const count = imagesStore.selectionCount
  Modal.confirm({
    title: '确认批量删除',
    content: `确定要删除选中的 ${count} 张图片吗？`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        const response = await imagesStore.deleteSelected() as { success: boolean; deleted_count: number }
        if (response.success) {
          message.success(`成功删除 ${response.deleted_count} 张图片`)
        }
      } catch (error) {
        message.error('批量删除失败')
      }
    },
  })
}

// Filter and pagination
function handleSourceFilterChange(value: string | null) {
  imagesStore.setSourceFilter(value)
  imagesStore.fetchImages({ source: value as any })
}

function handlePageChange(page: number) {
  currentPage.value = page
  imagesStore.goToPage(page)
}

function handleRefresh() {
  imagesStore.fetchImages()
}

// Lifecycle
onMounted(() => {
  imagesStore.fetchImages()
  loadVideos()
  loadActiveTasks()
})

onUnmounted(() => {
  imagesStore.reset()
  // Clear all polling intervals
  Object.values(pollIntervals).forEach(clearInterval)
  pollIntervals = {}
})
</script>

<style scoped>
.image-manager {
  padding: 24px;
  min-height: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.header-left {
  display: flex;
  align-items: baseline;
  gap: 16px;
}

.total-count {
  color: rgba(0, 0, 0, 0.45);
  font-size: 14px;
}

/* Upload Area */
.upload-area {
  border: 2px dashed #d9d9d9;
  border-radius: 8px;
  padding: 40px;
  margin-bottom: 24px;
  text-align: center;
  background: #fafafa;
  transition: all 0.3s;
}

.upload-area.drag-over {
  border-color: #1890ff;
  background: #e6f7ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.upload-icon {
  font-size: 48px;
  color: #999;
}

.upload-text {
  font-size: 16px;
  color: #333;
  margin: 0;
}

.upload-hint {
  font-size: 12px;
  color: #999;
  margin: 0;
}

.upload-buttons {
  display: flex;
  gap: 16px;
  margin-top: 8px;
}

.upload-progress {
  width: 300px;
  margin-top: 16px;
}

/* Selection Bar */
.selection-bar {
  padding: 12px 16px;
  background: #e6f7ff;
  border-radius: 4px;
  margin-bottom: 16px;
}

/* Image Grid */
.image-grid-container {
  min-height: 400px;
}

.loading-container,
.empty-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  color: #999;
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 16px;
}

.empty-hint {
  font-size: 12px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 16px;
}

.image-card {
  position: relative;
  background: #fff;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;
  cursor: pointer;
}

.image-card:hover {
  border-color: #1890ff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.image-card.selected {
  border-color: #1890ff;
  background: #e6f7ff;
}

.image-thumbnail {
  position: relative;
  width: 100%;
  padding-top: 75%;
  background: #f5f5f5;
  overflow: hidden;
}

.image-thumbnail img {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.image-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-overlay :deep(.anticon) {
  font-size: 32px;
  color: #fff;
}

.image-thumbnail:hover .image-overlay {
  opacity: 1;
}

.image-info {
  padding: 12px;
}

.image-name {
  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 8px;
}

.image-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}

.image-checkbox {
  position: absolute;
  top: 8px;
  left: 8px;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-card:hover .image-checkbox,
.image-card.selected .image-checkbox {
  opacity: 1;
}

.image-actions {
  position: absolute;
  top: 8px;
  right: 8px;
  opacity: 0;
  transition: opacity 0.3s;
}

.image-card:hover .image-actions {
  opacity: 1;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  margin-top: 24px;
}

/* Lightbox */
.lightbox {
  position: relative;
  width: 100%;
  height: 70vh;
  display: flex;
  align-items: center;
  justify-content: center;
  outline: none;
}

.lightbox-content {
  max-width: 100%;
  max-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
}

.lightbox-content img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.lightbox-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 48px;
  height: 48px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.3s;
  font-size: 20px;
  color: #fff;
}

.lightbox-nav:hover {
  background: rgba(255, 255, 255, 0.3);
}

.lightbox-prev {
  left: 16px;
}

.lightbox-next {
  right: 16px;
}

.lightbox-info {
  position: absolute;
  bottom: 16px;
  left: 50%;
  transform: translateX(-50%);
  background: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 4px;
  color: #fff;
  font-size: 12px;
  display: flex;
  gap: 16px;
}

.lightbox-actions {
  position: absolute;
  top: 16px;
  right: 16px;
}

.lightbox-actions :deep(.ant-btn) {
  color: #fff;
}

.lightbox-actions :deep(.ant-btn:hover) {
  color: #ff4d4f;
}

/* Video Extraction Panel */
.video-panel {
  margin-bottom: 24px;
}

.video-extraction {
  padding: 8px 0;
}

.video-upload-section,
.video-list-section,
.extraction-settings {
  margin-bottom: 24px;
}

.upload-hint {
  font-size: 12px;
  color: #999;
  margin-top: 8px;
}

.config-hint {
  font-size: 12px;
  color: #999;
  margin-top: 4px;
}

.video-list-section {
  max-height: 300px;
  overflow-y: auto;
}

.video-name {
  cursor: pointer;
  transition: color 0.3s;
}

.video-name:hover {
  color: #1890ff;
}

.video-name.selected {
  color: #1890ff;
  font-weight: bold;
}

.extraction-tasks {
  max-height: 200px;
  overflow-y: auto;
}

/* Task status styles */
.status-pending {
  color: #999;
}

.status-running {
  color: #1890ff;
}

.status-completed {
  color: #52c41a;
}

.status-failed {
  color: #ff4d4f;
}

.task-info {
  color: #999;
  font-size: 12px;
}
</style>
