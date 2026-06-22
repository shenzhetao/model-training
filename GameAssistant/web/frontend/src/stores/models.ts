import { defineStore } from 'pinia'
import { ref } from 'vue'
import modelsApi, { type TrainedModel, type ModelStats } from '@/api/models'

export const useModelsStore = defineStore('models', () => {
  const models = ref<TrainedModel[]>([])
  const selectedModel = ref<TrainedModel | null>(null)
  const stats = ref<ModelStats | null>(null)
  const loading = ref(false)
  const uploading = ref(false)

  async function fetchModels(params?: { architecture?: string; is_active?: boolean }) {
    loading.value = true
    try { models.value = await modelsApi.getList(params) }
    catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function fetchStats() {
    try { stats.value = await modelsApi.getStats() }
    catch (e) { console.error(e) }
  }

  async function uploadModel(formData: FormData) {
    uploading.value = true
    try {
      const m = await modelsApi.upload(formData)
      models.value.unshift(m)
      return m
    } finally { uploading.value = false }
  }

  async function activateModel(id: string) {
    await modelsApi.activate(id)
    for (const m of models.value) m.is_active = m.id === id
  }

  async function deleteModel(id: string) {
    await modelsApi.delete(id)
    models.value = models.value.filter(m => m.id !== id)
    if (selectedModel.value?.id === id) selectedModel.value = null
  }

  function reset() {
    models.value = []
    selectedModel.value = null
    stats.value = null
    loading.value = false
    uploading.value = false
  }

  return { models, selectedModel, stats, loading, uploading, fetchModels, fetchStats, uploadModel, activateModel, deleteModel, reset }
})
