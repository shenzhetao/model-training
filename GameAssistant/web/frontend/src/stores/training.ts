import { defineStore } from 'pinia'
import { ref } from 'vue'
import trainingApi, { type TrainingJob, type TrainingLog, type TrainingProgress } from '@/api/training'

export const useTrainingStore = defineStore('training', () => {
  const jobs = ref<TrainingJob[]>([])
  const currentJob = ref<TrainingJob | null>(null)
  const metrics = ref<TrainingLog[]>([])
  const progress = ref<TrainingProgress | null>(null)
  const loading = ref(false)
  const starting = ref(false)

  let eventSource: EventSource | null = null

  async function fetchJobs(params?: { status?: string; dataset_version_id?: string }) {
    loading.value = true
    try { jobs.value = await trainingApi.getList(params) }
    catch (e) { console.error(e) }
    finally { loading.value = false }
  }

  async function createJob(data: Partial<TrainingJob>) {
    starting.value = true
    try {
      const job = await trainingApi.create(data)
      jobs.value.unshift(job)
      return job
    } finally { starting.value = false }
  }

  async function fetchMetrics(jobId: string) {
    try { metrics.value = await trainingApi.getMetrics(jobId) }
    catch (e) { console.error(e) }
  }

  async function fetchProgress(jobId: string) {
    try { progress.value = await trainingApi.getProgress(jobId) }
    catch (e) { console.error(e) }
  }

  async function stopJob(jobId: string) {
    await trainingApi.stop(jobId)
    const idx = jobs.value.findIndex(j => j.id === jobId)
    if (idx >= 0) jobs.value[idx].status = 'cancelled'
  }

  function subscribeToLogs(jobId: string, onEpoch: (log: TrainingLog) => void) {
    closeEventSource()
    eventSource = new EventSource(trainingApi.getLogsSSE(jobId))
    eventSource.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.type === 'epoch') {
          metrics.value.push(data as TrainingLog)
          if (currentJob.value?.id === jobId) {
            currentJob.value.current_epoch = data.epoch
          }
          onEpoch(data as TrainingLog)
        } else if (data.type === 'done') {
          closeEventSource()
          fetchJobs()
        }
      } catch { /* ignore parse errors */ }
    }
    eventSource.onerror = () => { closeEventSource() }
  }

  function closeEventSource() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function reset() {
    closeEventSource()
    jobs.value = []
    currentJob.value = null
    metrics.value = []
    progress.value = null
    loading.value = false
    starting.value = false
  }

  return { jobs, currentJob, metrics, progress, loading, starting, fetchJobs, createJob, fetchMetrics, fetchProgress, stopJob, subscribeToLogs, closeEventSource, reset }
})
