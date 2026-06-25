import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import annotationsApi, {
  type AnnotationClass,
  type Annotation,
  type AnnotationProject,
  type ProjectStats,
} from '@/api/annotations'

export type AnnotationMode = 'view' | 'draw' | 'edit'

export const useAnnotationsStore = defineStore('annotations', () => {
  // State
  const classes = ref<AnnotationClass[]>([])
  const projects = ref<AnnotationProject[]>([])
  const currentProject = ref<AnnotationProject | null>(null)
  const annotations = ref<Annotation[]>([])
  const selectedAnnotationId = ref<string | null>(null)
  const stats = ref<ProjectStats | null>(null)
  const loading = ref(false)
  const saving = ref(false)
  const drawingMode = ref<AnnotationMode>('view')
  const selectedImageId = ref<string | null>(null)
  const imageWidth = ref(0)
  const imageHeight = ref(0)

  // Class map for quick lookup
  const classMap = computed(() => {
    const map: Record<string, AnnotationClass> = {}
    for (const c of classes.value) {
      map[c.id] = c
    }
    return map
  })

  const classNameMap = computed(() => {
    const map: Record<string, string> = {}
    for (const c of classes.value) {
      map[c.id] = c.display_name
    }
    return map
  })

  // Actions
  async function fetchClasses() {
    try {
      classes.value = await annotationsApi.getClasses()
    } catch (error) {
      console.error('Failed to fetch classes:', error)
    }
  }

  async function fetchProjects(params?: { page?: number; page_size?: number; status?: string }) {
    loading.value = true
    try {
      projects.value = await annotationsApi.getProjects(params)
    } catch (error) {
      console.error('Failed to fetch projects:', error)
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await annotationsApi.getStats()
    } catch (error) {
      console.error('Failed to fetch stats:', error)
    }
  }

  async function loadImageAnnotations(imageId: string, projectId?: string) {
    loading.value = true
    selectedImageId.value = imageId
    annotations.value = []
    try {
      const resp = await annotationsApi.getImageAnnotations(imageId, projectId)
      annotations.value = resp.annotations
      imageWidth.value = resp.image_width
      imageHeight.value = resp.image_height
    } catch (error) {
      console.error('Failed to load annotations:', error)
    } finally {
      loading.value = false
    }
  }

  async function addAnnotation(ann: Partial<Annotation>, projectId: string) {
    saving.value = true
    try {
      const created = await annotationsApi.createAnnotation({
        ...ann,
        image_id: selectedImageId.value!,
        project_id: projectId,
      } as any)
      annotations.value.push(created)
      return created
    } catch (error) {
      console.error('Failed to add annotation:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  async function createAnnotation(ann: Partial<Annotation>, projectId: string) {
    saving.value = true
    try {
      const created = await annotationsApi.createAnnotation({
        ...ann,
        project_id: projectId,
      } as any)
      annotations.value.push(created)
      return created
    } catch (error) {
      console.error('Failed to create annotation:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  async function updateAnnotation(id: string, data: Partial<Annotation>) {
    saving.value = true
    try {
      const updated = await annotationsApi.updateAnnotation(id, data)
      const idx = annotations.value.findIndex(a => a.id === id)
      if (idx >= 0) annotations.value[idx] = updated
      return updated
    } catch (error) {
      console.error('Failed to update annotation:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  async function removeAnnotation(id: string) {
    saving.value = true
    try {
      await annotationsApi.deleteAnnotation(id)
      annotations.value = annotations.value.filter(a => a.id !== id)
    } catch (error) {
      console.error('Failed to remove annotation:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  async function batchSave(anns: Partial<Annotation>[], projectId: string) {
    saving.value = true
    try {
      const resp = await annotationsApi.batchCreateAnnotations(selectedImageId.value!, anns)
      if (resp.created > 0 || resp.updated > 0) {
        await loadImageAnnotations(selectedImageId.value!, projectId)
      }
      return resp
    } catch (error) {
      console.error('Failed to batch save:', error)
      throw error
    } finally {
      saving.value = false
    }
  }

  function setDrawingMode(mode: AnnotationMode) {
    drawingMode.value = mode
  }

  function selectAnnotation(id: string | null) {
    selectedAnnotationId.value = id
  }

  function reset() {
    classes.value = []
    projects.value = []
    currentProject.value = null
    annotations.value = []
    selectedAnnotationId.value = null
    stats.value = null
    loading.value = false
    saving.value = false
    drawingMode.value = 'view'
    selectedImageId.value = null
  }

  return {
    classes,
    projects,
    currentProject,
    annotations,
    selectedAnnotationId,
    stats,
    loading,
    saving,
    drawingMode,
    selectedImageId,
    imageWidth,
    imageHeight,
    classMap,
    classNameMap,
    fetchClasses,
    fetchProjects,
    fetchStats,
    loadImageAnnotations,
    createAnnotation,
    addAnnotation,
    updateAnnotation,
    removeAnnotation,
    batchSave,
    setDrawingMode,
    selectAnnotation,
    reset,
  }
})
