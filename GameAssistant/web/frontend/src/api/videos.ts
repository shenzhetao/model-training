import request from './request'
import type { AxiosProgressEvent } from 'axios'

export interface SourceVideoResponse {
  id: string
  filename: string
  original_filename: string
  file_path: string
  file_size: number
  duration: number
  width: number
  height: number
  fps: number
  uploaded_by?: string
  uploaded_at: string
  is_deleted: boolean
}

export interface VideoUploadResponse {
  success: boolean
  message: string
  video?: SourceVideoResponse
}

export interface VideoListResponse {
  items: SourceVideoResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export type ExtractionStrategy = 'interval' | 'count' | 'scene_change'
export type ExtractionStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'

export interface ExtractionTaskResponse {
  id: string
  video_id: string
  strategy: ExtractionStrategy
  interval_seconds?: number
  frame_count?: number
  scene_threshold?: number
  status: ExtractionStatus
  total_frames?: number
  extracted_frames: number
  started_at?: string
  completed_at?: string
  created_by?: string
  created_at: string
  error_message?: string
}

export interface ExtractionTaskCreate {
  strategy: ExtractionStrategy
  interval_seconds?: number
  frame_count?: number
  scene_threshold?: number
}

export interface ExtractionTaskCreateResponse {
  success: boolean
  message: string
  task?: ExtractionTaskResponse
}

export interface ExtractionTaskListResponse {
  items: ExtractionTaskResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface VideoQueryParams {
  page?: number
  page_size?: number
}

export interface ExtractionTaskQueryParams {
  page?: number
  page_size?: number
  status?: ExtractionStatus
}

export const videosApi = {
  /**
   * Upload a video file
   */
  async upload(
    file: File,
    onProgress?: (percent: number) => void
  ): Promise<VideoUploadResponse> {
    const formData = new FormData()
    formData.append('file', file)

    return request.post('/videos/upload', formData, {
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
   * Get paginated video list
   */
  async getList(params: VideoQueryParams = {}): Promise<VideoListResponse> {
    const queryParams = new URLSearchParams()
    if (params.page) queryParams.set('page', String(params.page))
    if (params.page_size) queryParams.set('page_size', String(params.page_size))

    const query = queryParams.toString()
    return request.get(`/videos/${query ? `?${query}` : ''}`)
  },

  /**
   * Get single video details
   */
  async getById(id: string): Promise<SourceVideoResponse> {
    return request.get(`/videos/${id}`)
  },

  /**
   * Get video stream URL
   */
  getServeUrl(id: string): string {
    return `/videos/${id}/serve`
  },

  /**
   * Delete a video
   */
  async delete(id: string): Promise<{ success: boolean; message: string }> {
    return request.delete(`/videos/${id}`)
  },

  /**
   * Create frame extraction task
   */
  async createExtractionTask(
    videoId: string,
    taskData: ExtractionTaskCreate
  ): Promise<ExtractionTaskCreateResponse> {
    return request.post(`/videos/${videoId}/extract-frames`, taskData)
  },

  /**
   * Get extraction task details
   */
  async getExtractionTask(taskId: string): Promise<ExtractionTaskResponse> {
    return request.get(`/videos/tasks/${taskId}`)
  },

  /**
   * Get paginated extraction task list
   */
  async getExtractionTaskList(
    params: ExtractionTaskQueryParams = {}
  ): Promise<ExtractionTaskListResponse> {
    const queryParams = new URLSearchParams()
    if (params.page) queryParams.set('page', String(params.page))
    if (params.page_size) queryParams.set('page_size', String(params.page_size))
    if (params.status) queryParams.set('status', params.status)

    const query = queryParams.toString()
    return request.get(`/videos/tasks/list${query ? `?${query}` : ''}`)
  },

  /**
   * Cancel an extraction task
   */
  async cancelExtractionTask(taskId: string): Promise<{ success: boolean; message: string }> {
    return request.delete(`/videos/tasks/${taskId}`)
  },
}

export default videosApi
