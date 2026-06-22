import { defineStore } from 'pinia'
import { ref } from 'vue'
import datasetsApi, { type Dataset, type DatasetVersion, type VersionStats } from '@/api/datasets'

export const useDatasetsStore = defineStore('datasets', () => {
  const datasets = ref<Dataset[]>([])
  const currentDataset = ref<Dataset | null>(null)
  const versions = ref<DatasetVersion[]>([])
  const currentVersion = ref<DatasetVersion | null>(null)
  const versionStats = ref<VersionStats | null>(null)
  const loading = ref(false)
  const generating = ref(false)

  async function fetchDatasets() {
    loading.value = true
    try { datasets.value = await datasetsApi.getList() }
    catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function fetchVersions(datasetId: string) {
    try { versions.value = await datasetsApi.getVersions(datasetId) }
    catch (e) { console.error(e) }
  }

  async function createDataset(data: Partial<Dataset>) {
    const ds = await datasetsApi.create(data)
    datasets.value.unshift(ds)
    return ds
  }

  async function deleteDataset(id: string) {
    await datasetsApi.delete(id)
    datasets.value = datasets.value.filter(d => d.id !== id)
  }

  async function createVersion(datasetId: string, data: Partial<DatasetVersion>) {
    const v = await datasetsApi.createVersion(datasetId, data)
    versions.value.unshift(v)
    return v
  }

  async function fetchVersionStats(datasetId: string, versionId: string) {
    try { versionStats.value = await datasetsApi.getVersionStats(datasetId, versionId) }
    catch (e) { console.error(e) }
  }

  async function addImages(datasetId: string, versionId: string, imageIds: string[], split = 'train') {
    const resp = await datasetsApi.addImages(datasetId, versionId, imageIds, split)
    await fetchVersionStats(datasetId, versionId)
    return resp
  }

  async function generateYolo(datasetId: string, versionId: string) {
    generating.value = true
    try {
      window.open(datasetsApi.getGenerateYoloUrl(datasetId, versionId), '_blank')
    } finally {
      generating.value = false
    }
  }

  function reset() {
    datasets.value = []
    currentDataset.value = null
    versions.value = []
    currentVersion.value = null
    versionStats.value = null
    loading.value = false
    generating.value = false
  }

  return {
    datasets, currentDataset, versions, currentVersion, versionStats,
    loading, generating,
    fetchDatasets, fetchVersions, createDataset, deleteDataset,
    createVersion, fetchVersionStats, addImages, generateYolo, reset,
  }
})
