import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import imagesApi, { type ImageResponse, type ImageQueryParams } from '@/api/images'

export const useImagesStore = defineStore('images', () => {
  // State
  const images = ref<ImageResponse[]>([])
  const selectedIds = ref<Set<string>>(new Set())
  const currentImage = ref<ImageResponse | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const uploadProgress = ref(0)
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(20)
  const totalPages = ref(1)
  const sourceFilter = ref<string | null>(null)

  // Lightbox state
  const lightboxVisible = ref(false)
  const lightboxIndex = ref(0)

  // Computed
  const hasSelection = computed(() => selectedIds.value.size > 0)
  const selectionCount = computed(() => selectedIds.value.size)
  const allSelected = computed(() =>
    images.value.length > 0 && selectedIds.value.size === images.value.length
  )

  // Actions
  async function fetchImages(params: ImageQueryParams = {}) {
    loading.value = true
    try {
      const response = await imagesApi.getList({
        page: params.page || page.value,
        page_size: params.page_size || pageSize.value,
        source: params.source as 'upload' | 'adb' | 'video' | undefined || sourceFilter.value as any,
      })

      images.value = response.items
      total.value = response.total
      page.value = response.page
      pageSize.value = response.page_size
      totalPages.value = response.total_pages
    } catch (error) {
      console.error('Failed to fetch images:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  async function fetchNextPage() {
    if (page.value < totalPages.value) {
      page.value++
      await fetchImages({ page: page.value })
    }
  }

  async function fetchPrevPage() {
    if (page.value > 1) {
      page.value--
      await fetchImages({ page: page.value })
    }
  }

  async function goToPage(targetPage: number) {
    if (targetPage >= 1 && targetPage <= totalPages.value) {
      page.value = targetPage
      await fetchImages({ page: targetPage })
    }
  }

  function setSourceFilter(source: string | null) {
    sourceFilter.value = source
    page.value = 1
  }

  async function uploadSingle(file: File, source: 'upload' | 'adb' | 'video' = 'upload') {
    uploading.value = true
    uploadProgress.value = 0
    try {
      const response = await imagesApi.uploadSingle(file, source, (percent) => {
        uploadProgress.value = percent
      })

      if (response.success && response.image) {
        // Add to the beginning of the list
        images.value.unshift(response.image)
        total.value++
      }

      return response
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  async function uploadBatch(file: File, source: 'upload' | 'adb' | 'video' = 'upload') {
    uploading.value = true
    uploadProgress.value = 0
    try {
      const response = await imagesApi.uploadBatch(file, source, (percent) => {
        uploadProgress.value = percent
      })

      if (response.success) {
        // Refresh the list to show new images
        await fetchImages()
      }

      return response
    } finally {
      uploading.value = false
      uploadProgress.value = 0
    }
  }

  async function deleteImage(id: string) {
    try {
      const response = await imagesApi.deleteSingle(id)
      if (response.success) {
        // Remove from list
        const index = images.value.findIndex((img: ImageResponse) => img.id === id)
        if (index !== -1) {
          images.value.splice(index, 1)
        }
        total.value--
        // Remove from selection
        selectedIds.value.delete(id)
      }
      return response
    } catch (error) {
      console.error('Failed to delete image:', error)
      throw error
    }
  }

  async function deleteSelected() {
    const ids = Array.from(selectedIds.value)
    if (ids.length === 0) return { success: false, message: 'No images selected' }

    try {
      const response = await imagesApi.deleteBatch(ids)
      if (response.success) {
        // Remove deleted images from list
        images.value = images.value.filter((img: ImageResponse) => !selectedIds.value.has(img.id))
        total.value -= response.deleted_count
        // Clear selection
        selectedIds.value.clear()
      }
      return response
    } catch (error) {
      console.error('Failed to delete images:', error)
      throw error
    }
  }

  function toggleSelection(id: string) {
    if (selectedIds.value.has(id)) {
      selectedIds.value.delete(id)
    } else {
      selectedIds.value.add(id)
    }
    // Trigger reactivity
    selectedIds.value = new Set(selectedIds.value)
  }

  function selectAll() {
    selectedIds.value = new Set(images.value.map((img: ImageResponse) => img.id))
  }

  function clearSelection() {
    selectedIds.value.clear()
    selectedIds.value = new Set()
  }

  function toggleSelectAll() {
    if (allSelected.value) {
      clearSelection()
    } else {
      selectAll()
    }
  }

  // Lightbox controls
  function openLightbox(index: number) {
    lightboxIndex.value = index
    lightboxVisible.value = true
  }

  function closeLightbox() {
    lightboxVisible.value = false
  }

  function lightboxNext() {
    if (lightboxIndex.value < images.value.length - 1) {
      lightboxIndex.value++
    }
  }

  function lightboxPrev() {
    if (lightboxIndex.value > 0) {
      lightboxIndex.value--
    }
  }

  function setCurrentImage(image: ImageResponse | null) {
    currentImage.value = image
  }

  function reset() {
    images.value = []
    selectedIds.value.clear()
    currentImage.value = null
    loading.value = false
    uploading.value = false
    uploadProgress.value = 0
    total.value = 0
    page.value = 1
    pageSize.value = 20
    totalPages.value = 1
    sourceFilter.value = null
    lightboxVisible.value = false
    lightboxIndex.value = 0
  }

  return {
    // State
    images,
    selectedIds,
    currentImage,
    loading,
    uploading,
    uploadProgress,
    total,
    page,
    pageSize,
    totalPages,
    sourceFilter,
    lightboxVisible,
    lightboxIndex,

    // Computed
    hasSelection,
    selectionCount,
    allSelected,

    // Actions
    fetchImages,
    fetchNextPage,
    fetchPrevPage,
    goToPage,
    setSourceFilter,
    uploadSingle,
    uploadBatch,
    deleteImage,
    deleteSelected,
    toggleSelection,
    selectAll,
    clearSelection,
    toggleSelectAll,
    openLightbox,
    closeLightbox,
    lightboxNext,
    lightboxPrev,
    setCurrentImage,
    reset,
  }
})
