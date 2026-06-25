import request from './request'
import type { AxiosProgressEvent } from 'axios'

export interface ImageResponse {
  id: string
  filename: string
  original_filename: string
  file_path: string
  file_size: number
  width: number
  height: number
  md5_hash: string
  phash?: string
  source: 'upload' | 'adb' | 'video'
  source_video_id?: string
  source_video_timestamp?: number
  uploaded_by?: string
  uploaded_at: string
  updated_at: string
  is_deleted: boolean
}

export interface ImageListResponse {
  items: ImageResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface ImageUploadResponse {
  success: boolean
  message: string
  image?: ImageResponse
  is_duplicate: boolean
  existing_image_id?: string
}

export interface BatchUploadResponse {
  success: boolean
  message: string
  total: number
  uploaded: number
  skipped: number
  failed: number
  duplicates: number
  images: ImageResponse[]
  errors: string[]
}

export interface ImageDeleteResponse {
  success: boolean
  message: string
  deleted_count: number
}

export interface ImageQueryParams {
  page?: number
  page_size?: number
  source?: 'upload' | 'adb' | 'video'
  skipCache?: boolean
}

export const imagesApi = {
  /**
   * Get paginated image list
   */
  async getList(params: ImageQueryParams = {}): Promise<ImageListResponse> {
    const queryParams = new URLSearchParams()
    if (params.page) queryParams.set('page', String(params.page))
    if (params.page_size) queryParams.set('page_size', String(params.page_size))
    if (params.source) queryParams.set('source', params.source)

    const query = queryParams.toString()
    return request.get(query ? `/images?${query}` : '/images')
  },

  /**
   * Get single image details
   */
  async getById(id: string): Promise<ImageResponse> {
    return request.get(`/images/${id}`)
  },

  /**
   * Upload single image
   */
  async uploadSingle(
    file: File,
    source: 'upload' | 'adb' | 'video' = 'upload',
    onProgress?: (percent: number) => void
  ): Promise<ImageUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source)

    return request.post('/images/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress
        ? (progressEvent: AxiosProgressEvent) => {
            const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
            onProgress(percent)
          }
        : undefined,
    })
  },

  /**
   * Upload batch images in ZIP
   */
  async uploadBatch(
    file: File,
    source: 'upload' | 'adb' | 'video' = 'upload',
    onProgress?: (percent: number) => void
  ): Promise<BatchUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('source', source)

    return request.post('/images/upload/batch', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: onProgress
        ? (progressEvent: AxiosProgressEvent) => {
            const percent = Math.round((progressEvent.loaded * 100) / (progressEvent.total || 1))
            onProgress(percent)
          }
        : undefined,
    })
  },

  /**
   * Delete single image
   */
  async deleteSingle(id: string): Promise<ImageDeleteResponse> {
    return request.delete(`/images/${id}`)
  },

  /**
   * Delete multiple images
   */
  async deleteBatch(ids: string[]): Promise<ImageDeleteResponse> {
    const imageIds = ids.join(',')
    return request.delete(`/images?image_ids=${encodeURIComponent(imageIds)}`)
  },

  /**
   * Get image URL for serving
   */
  getServeUrl(id: string): string {
    return `/images/${id}/serve`
  },

  /**
   * Get thumbnail URL (uses serve endpoint)
   */
  getThumbnailUrl(id: string, size: number = 200): string {
    return `/images/${id}/serve?size=${size}`
  },
}

export default imagesApi
