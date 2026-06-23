import request from './request'

// ── Types ──────────────────────────────────────────────────

export interface Dataset {
  id: string
  name: string
  description?: string
  created_by?: string
  created_at: string
  updated_at: string
  is_deleted: boolean
}

export interface DatasetVersion {
  id: string
  dataset_id: string
  version_name: string
  version_number: number
  train_ratio: number
  val_ratio: number
  test_ratio: number
  random_seed: number
  image_count: number
  annotated_count: number
  class_ids: string[]
  yolo_dataset_path?: string
  dataset_yaml_content?: string
  status: string
  created_by?: string
  created_at: string
  updated_at: string
}

export interface VersionStats {
  total: number
  train: number
  val: number
  test: number
  annotated: number
  unannotated: number
}

// ── API ────────────────────────────────────────────────────

export const datasetsApi = {
  async getList(params?: { page?: number; page_size?: number }): Promise<Dataset[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return request.get(`/datasets/${q.toString() ? `?${q}` : ''}`)
  },

  async create(data: Partial<Dataset>): Promise<Dataset> {
    return request.post('/datasets/', data)
  },

  async getById(id: string): Promise<Dataset> {
    return request.get(`/datasets/${id}`)
  },

  async update(id: string, data: Partial<Dataset>): Promise<Dataset> {
    return request.put(`/datasets/${id}`, data)
  },

  async delete(id: string): Promise<void> {
    return request.delete(`/datasets/${id}`)
  },

  async getVersions(datasetId: string): Promise<DatasetVersion[]> {
    return request.get(`/datasets/${datasetId}/versions`)
  },

  async createVersion(datasetId: string, data: Partial<DatasetVersion>): Promise<DatasetVersion> {
    return request.post(`/datasets/${datasetId}/versions`, data)
  },

  async getVersion(datasetId: string, versionId: string): Promise<DatasetVersion> {
    return request.get(`/datasets/${datasetId}/versions/${versionId}`)
  },

  async updateVersion(datasetId: string, versionId: string, data: Partial<DatasetVersion>): Promise<DatasetVersion> {
    return request.put(`/datasets/${datasetId}/versions/${versionId}`, data)
  },

  async addImages(datasetId: string, versionId: string, imageIds: string[], split = 'train'): Promise<{ added: number }> {
    return request.post(`/datasets/${datasetId}/versions/${versionId}/images`, {
      image_ids: imageIds,
      split,
    })
  },

  async getVersionStats(datasetId: string, versionId: string): Promise<VersionStats> {
    return request.get(`/datasets/${datasetId}/versions/${versionId}/stats`)
  },

  getGenerateYoloUrl(datasetId: string, versionId: string): string {
    return `/api/datasets/${datasetId}/versions/${versionId}/generate-yolo`
  },
}

export default datasetsApi
