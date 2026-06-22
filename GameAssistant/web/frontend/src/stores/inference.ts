import { defineStore } from 'pinia'
import { ref } from 'vue'
import inferenceApi, { type InferenceResult } from '@/api/inference'

export const useInferenceStore = defineStore('inference', () => {
  const history = ref<InferenceResult[]>([])
  const currentResult = ref<InferenceResult | null>(null)
  const stats = ref<{ total: number; device: number; image: number; video: number } | null>(null)
  const loading = ref(false)

  async function fetchHistory(params?: { source_type?: string }) {
    loading.value = true
    try { history.value = await inferenceApi.getList(params) }
    catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function fetchStats() {
    try { stats.value = await inferenceApi.getStats() }
    catch (e) { console.error(e) }
  }

  async function recordResult(data: Partial<InferenceResult>) {
    const result = await inferenceApi.create(data)
    history.value.unshift(result)
    return result
  }

  async function deleteResult(id: string) {
    await inferenceApi.delete(id)
    history.value = history.value.filter(r => r.id !== id)
    if (currentResult.value?.id === id) currentResult.value = null
  }

  function reset() {
    history.value = []
    currentResult.value = null
    stats.value = null
    loading.value = false
  }

  return { history, currentResult, stats, loading, fetchHistory, fetchStats, recordResult, deleteResult, reset }
})
