import request from './request'

export interface DetectionItem {
  cls: string
  x: number
  y: number
  w: number
  h: number
  conf: number
  source: string
}

export interface InferenceResult {
  id: string
  name?: string
  source_type: string
  source_file?: string
  model_id?: string
  inference_mode: string
  confidence_threshold: number
  total_detections: number
  detections_json: DetectionItem[]
  inference_time_ms?: number
  image_path?: string
  annotated_image_path?: string
  video_frame_index?: number
  device_id?: string
  created_by?: string
  created_at: string
}

export interface InferenceStats {
  total: number
  device: number
  image: number
  video: number
}

export const inferenceApi = {
  async getList(params?: {
    page?: number
    page_size?: number
    source_type?: string
    model_id?: string
  }): Promise<InferenceResult[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.source_type) q.set('source_type', params.source_type)
    if (params?.model_id) q.set('model_id', params.model_id)
    return request.get(`/inference/${q.toString() ? `?${q}` : ''}`)
  },

  async create(data: Partial<InferenceResult>): Promise<InferenceResult> {
    return request.post('/inference/', data)
  },

  async delete(id: string): Promise<void> {
    return request.delete(`/inference/${id}`)
  },

  async getStats(): Promise<InferenceStats> {
    return request.get('/inference/stats/summary')
  },
}

export default inferenceApi
