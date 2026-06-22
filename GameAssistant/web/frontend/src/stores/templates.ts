import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import templatesApi, { type TemplateClass, type Template, type TemplateTestResult } from '@/api/templates'

export const useTemplatesStore = defineStore('templates', () => {
  const classes = ref<TemplateClass[]>([])
  const templates = ref<Template[]>([])
  const selectedTemplate = ref<Template | null>(null)
  const loading = ref(false)
  const uploading = ref(false)
  const testResults = ref<TemplateTestResult[]>([])
  const testLoading = ref(false)

  const classMap = computed(() => {
    const m: Record<string, TemplateClass> = {}
    for (const c of classes.value) m[c.id] = c
    return m
  })

  const groupedTemplates = computed(() => {
    const g: Record<string, Template[]> = {}
    for (const t of templates.value) {
      if (!g[t.class_name]) g[t.class_name] = []
      g[t.class_name].push(t)
    }
    return g
  })

  async function fetchClasses() {
    try { classes.value = await templatesApi.getClasses() }
    catch (e) { console.error(e) }
  }

  async function fetchTemplates(params?: { class_name?: string; is_active?: boolean }) {
    loading.value = true
    try {
      templates.value = await templatesApi.getList(params)
    } catch (e) {
      console.error(e)
    } finally {
      loading.value = false
    }
  }

  async function uploadTemplate(formData: FormData) {
    uploading.value = true
    try {
      const t = await templatesApi.upload(formData)
      templates.value.unshift(t)
      return t
    } finally {
      uploading.value = false
    }
  }

  async function deleteTemplate(id: string) {
    await templatesApi.delete(id)
    templates.value = templates.value.filter(t => t.id !== id)
  }

  async function updateTemplate(id: string, data: Partial<Template>) {
    const updated = await templatesApi.update(id, data)
    const idx = templates.value.findIndex(t => t.id === id)
    if (idx >= 0) templates.value[idx] = updated
    return updated
  }

  async function testMatching(params: {
    image_id?: string
    image_url?: string
    template_ids?: string[]
    threshold?: number
  }) {
    testLoading.value = true
    try {
      const resp = await templatesApi.testMatching(params)
      testResults.value = resp.results
      return resp
    } finally {
      testLoading.value = false
    }
  }

  function reset() {
    classes.value = []
    templates.value = []
    selectedTemplate.value = null
    testResults.value = []
    loading.value = false
    uploading.value = false
  }

  return {
    classes, templates, selectedTemplate, loading, uploading,
    testResults, testLoading, classMap, groupedTemplates,
    fetchClasses, fetchTemplates, uploadTemplate, deleteTemplate,
    updateTemplate, testMatching, reset,
  }
})
