import request from './request'

export interface TrainedModel {
  id: string
  name: string
  description?: string
  architecture: string
  task_type: string
  file_path: string
  file_size: number
  format: string
  dataset_version_id?: string
  class_ids: string[]
  yolo_class_names: string[]
  epochs?: number
  batch_size?: number
  img_size?: number
  map50?: number
  map50_95?: number
  train_loss?: number
  val_loss?: number
  trained_at?: string
  training_job_id?: string
  tags?: string[]
  is_active: boolean
  uploaded_by?: string
  created_at: string
  updated_at: string
}

export interface ModelStats {
  total_models: number
  active_models: number
  total_size_mb: number
  by_architecture: Record<string, number>
}

export const modelsApi = {
  async getList(params?: {
    page?: number
    page_size?: number
    architecture?: string
    is_active?: boolean
  }): Promise<TrainedModel[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.architecture) q.set('architecture', params.architecture)
    if (params?.is_active !== undefined) q.set('is_active', String(params.is_active))
    return request.get(`/models/${q.toString() ? `?${q}` : ''}`)
  },

  async upload(formData: FormData): Promise<TrainedModel> {
    return request.post('/models/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  async getById(id: string): Promise<TrainedModel> {
    return request.get(`/models/${id}`)
  },

  async update(id: string, data: Partial<TrainedModel>): Promise<TrainedModel> {
    return request.put(`/models/${id}`, data)
  },

  async delete(id: string): Promise<void> {
    return request.delete(`/models/${id}`)
  },

  async activate(id: string): Promise<{ success: boolean }> {
    return request.post(`/models/${id}/activate`)
  },

  async getStats(): Promise<ModelStats> {
    return request.get('/models/stats/overview')
  },
}

export default modelsApi
