import request from './request'

export interface TrainingJob {
  id: string
  name: string
  dataset_version_id: string
  base_model_architecture: string
  status: string
  epochs: number
  batch_size: number
  img_size: number
  lr0: number
  lrf: number
  weight_decay: number
  momentum: number
  patience: number
  mosaic: number
  mixup: number
  hsv_h: number
  hsv_s: number
  hsv_v: number
  flip_lr: number
  resume_from?: string
  best_model_id?: string
  process_id?: number
  log_output?: string
  log_summary?: Record<string, unknown>
  current_epoch?: number
  gpu_device?: string
  started_at?: string
  completed_at?: string
  created_by?: string
  created_at: string
  error_message?: string
}

export interface TrainingLog {
  id: string
  training_job_id: string
  epoch: number
  train_box_loss?: number
  train_cls_loss?: number
  train_dfl_loss?: number
  val_box_loss?: number
  val_cls_loss?: number
  val_dfl_loss?: number
  precision?: number
  recall?: number
  map50?: number
  map50_95?: number
  lr?: number
  gpu_memory_mb?: number
  epoch_duration_sec?: number
  logged_at: string
}

export interface TrainingProgress {
  job_id: string
  status: string
  current_epoch: number
  total_epochs: number
  best_model_id?: string
  current_map50?: number
  current_map?: number
  latest_metrics?: TrainingLog
}

export const trainingApi = {
  async getList(params?: {
    page?: number
    page_size?: number
    status?: string
    dataset_version_id?: string
  }): Promise<TrainingJob[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.status) q.set('status', params.status)
    if (params?.dataset_version_id) q.set('dataset_version_id', params.dataset_version_id)
    return request.get(`/training/${q.toString() ? `?${q}` : ''}`)
  },

  async create(data: Partial<TrainingJob>): Promise<TrainingJob> {
    return request.post('/training/', data)
  },

  async getById(id: string): Promise<TrainingJob> {
    return request.get(`/training/${id}`)
  },

  async update(id: string, data: Partial<TrainingJob>): Promise<TrainingJob> {
    return request.put(`/training/${id}`, data)
  },

  async stop(id: string): Promise<{ success: boolean }> {
    return request.post(`/training/${id}/stop`)
  },

  async getMetrics(jobId: string): Promise<TrainingLog[]> {
    return request.get(`/training/${jobId}/metrics`)
  },

  async getProgress(jobId: string): Promise<TrainingProgress> {
    return request.get(`/training/${jobId}/progress`)
  },

  getLogsSSE(jobId: string): string {
    return `/api/v1/training/${jobId}/logs`
  },
}

export default trainingApi
