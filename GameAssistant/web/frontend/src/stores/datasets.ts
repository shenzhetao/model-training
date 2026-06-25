import { defineStore } from 'pinia'
import { ref } from 'vue'
import datasetsApi, { type Dataset, type DatasetVersion, type VersionStats } from '@/api/datasets'
import request from '@/api/request'

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
      // The interceptor unwraps blob responses to { data, headers, status }
      // and rejects with a real Error on HTTP/JSON-error responses.
      const resp = await request.post(
        `/datasets/${datasetId}/versions/${versionId}/generate-yolo`,
        null,
        { responseType: 'blob' as const }
      ) as unknown as { data: Blob; headers: Record<string, string>; status: number }

      const blob = resp.data
      const filename = parseFilename(resp.headers) ?? `yolo_dataset_${versionId.slice(0, 8)}.zip`

      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      return blob
    } catch (e) {
      console.error(e)
      throw e
    } finally {
      generating.value = false
    }
  }

  function parseFilename(headers: Record<string, string>): string | null {
    const cd = headers['content-disposition'] || headers['Content-Disposition']
    if (!cd) return null
    // RFC 5987: filename*=UTF-8''<percent-encoded>
    const utf8 = cd.match(/filename\*\s*=\s*[^']*''([^;]+)/i)
    if (utf8) {
      try {
        return decodeURIComponent(utf8[1].trim().replace(/^"|"$/g, ''))
      } catch {
        // fall through
      }
    }
    const ascii = cd.match(/filename\s*=\s*"?([^";]+)"?/i)
    if (ascii) return ascii[1].trim()
    return null
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
