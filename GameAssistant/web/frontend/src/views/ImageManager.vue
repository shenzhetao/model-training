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
} from '@ant-design/icons-vue'
import { useImagesStore } from '@/stores/images'
import type { ImageResponse } from '@/api/images'
import imagesApi from '@/api/images'

const imagesStore = useImagesStore()

// Local state
const isDragOver = ref(false)
const sourceFilter = ref<string | null>(null)
const currentPage = ref(1)
const lightboxRef = ref<HTMLElement | null>(null)

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
const handleFileSelect: UploadProps['beforeUpload'] = async (file: File) => {
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

const handleZipSelect: UploadProps['beforeUpload'] = async (file: File) => {
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
    handleZipSelect(file)
  } else {
    handleFileSelect(file)
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
        const response = await imagesStore.deleteSelected()
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
})

onUnmounted(() => {
  imagesStore.reset()
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
</style>
