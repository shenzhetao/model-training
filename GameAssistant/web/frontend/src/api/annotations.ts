import request from './request'

// ── Class types ────────────────────────────────────────────
export interface AnnotationClass {
  id: string
  name: string
  display_name: string
  description?: string
  color: string
  short_key?: string
  sort_order: number
  yolo_class_id: number
  created_at: string
  updated_at: string
}

export interface Annotation {
  id: string
  image_id: string
  class_id: string
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
  conf?: number
  is_auto_annotated: boolean
  annotated_by?: string
  annotated_at: string
  updated_at: string
}

export interface ImageAnnotationsResponse {
  image_id: string
  image_width: number
  image_height: number
  annotations: Annotation[]
  annotated_count: number
  class_names: string[]
}

export interface AnnotationProject {
  id: string
  name: string
  description?: string
  status: string
  class_ids: string[]
  total_images: number
  annotated_images: number
  reviewed_images: number
  assigned_to?: string
  reviewed_by?: string
  created_by?: string
  created_at: string
  updated_at: string
  completed_at?: string
}

export interface ProjectStats {
  total_projects: number
  draft: number
  in_progress: number
  completed: number
  reviewed: number
  total_annotations: number
  auto_annotations: number
  manual_annotations: number
}

// ── API methods ─────────────────────────────────────────────

export const annotationsApi = {
  // Classes
  async getClasses(): Promise<AnnotationClass[]> {
    return request.get('/annotations/classes')
  },

  async createClass(data: Partial<AnnotationClass>): Promise<AnnotationClass> {
    return request.post('/annotations/classes', data)
  },

  async updateClass(id: string, data: Partial<AnnotationClass>): Promise<AnnotationClass> {
    return request.put(`/annotations/classes/${id}`, data)
  },

  async deleteClass(id: string): Promise<void> {
    return request.delete(`/annotations/classes/${id}`)
  },

  // Annotations
  async getImageAnnotations(imageId: string, projectId?: string): Promise<ImageAnnotationsResponse> {
    const q = new URLSearchParams()
    if (projectId) q.set('project_id', projectId)
    return request.get(`/annotations/images/${imageId}${q.toString() ? `?${q}` : ''}`)
  },

  async createAnnotation(data: Partial<Annotation>): Promise<Annotation> {
    return request.post('/annotations/', data)
  },

  async batchCreateAnnotations(
    imageId: string,
    annotations: Partial<Annotation>[]
  ): Promise<{ success: boolean; created: number; updated: number }> {
    return request.post('/annotations/batch', { image_id: imageId, annotations })
  },

  async updateAnnotation(id: string, data: Partial<Annotation>): Promise<Annotation> {
    return request.put(`/annotations/${id}`, data)
  },

  async deleteAnnotation(id: string): Promise<void> {
    return request.delete(`/annotations/${id}`)
  },

  async deleteImageAnnotations(imageId: string): Promise<void> {
    return request.delete(`/annotations/by-image/${imageId}`)
  },

  // Projects
  async getProjects(params?: {
    page?: number
    page_size?: number
    status?: string
  }): Promise<AnnotationProject[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.status) q.set('status', params.status)
    return request.get(`/annotations/projects${q.toString() ? `?${q}` : ''}`)
  },

  async createProject(data: Partial<AnnotationProject>): Promise<AnnotationProject> {
    return request.post('/annotations/projects', data)
  },

  async getProject(id: string): Promise<AnnotationProject> {
    return request.get(`/annotations/projects/${id}`)
  },

  async updateProject(id: string, data: Partial<AnnotationProject>): Promise<AnnotationProject> {
    return request.put(`/annotations/projects/${id}`, data)
  },

  async deleteProject(id: string): Promise<void> {
    return request.delete(`/annotations/projects/${id}`)
  },

  async addProjectImages(projectId: string, imageIds: string[]): Promise<{ added: number }> {
    return request.post(`/annotations/projects/${projectId}/images`, { image_ids: imageIds })
  },

  async removeProjectImages(projectId: string, imageIds: string[]): Promise<{ removed: number }> {
    return request.delete(`/annotations/projects/${projectId}/images?image_ids=${imageIds.join(',')}`)
  },

  async getProjectImages(projectId: string): Promise<{ items: { image_id: string }[]; total: number }> {
    return request.get(`/annotations/projects/${projectId}/images`)
  },

  // Stats
  async getStats(): Promise<ProjectStats> {
    return request.get('/annotations/stats')
  },

  // Review
  async submitForReview(projectId: string): Promise<AnnotationProject> {
    return request.post(`/annotations/projects/${projectId}/submit-review`)
  },

  async approveProject(projectId: string): Promise<{ success: boolean }> {
    return request.post(`/annotations/projects/${projectId}/approve`)
  },

  async rejectProject(projectId: string, data: { feedback?: string }): Promise<{ success: boolean }> {
    return request.post(`/annotations/projects/${projectId}/reject`, data)
  },

  async reviewProjectImage(
    projectId: string,
    imageId: string,
    data: { action: 'approve' | 'request_changes'; reason?: string }
  ): Promise<{ success: boolean; action: string }> {
    return request.post(`/annotations/projects/${projectId}/images/${imageId}/review`, data)
  },

  async getProjectImageReviews(projectId: string): Promise<{ reviews: Record<string, { review_status: string; rejection_reason: string; reviewed_at: string; reviewer_id: string | null }> }> {
    return request.get(`/annotations/projects/${projectId}/image-reviews`)
  },

  async bulkApproveProject(projectId: string): Promise<{ success: boolean; approved_count: number; status: string }> {
    return request.post(`/annotations/projects/${projectId}/bulk-approve`)
  },

  async bulkRejectProject(projectId: string, data: { reason?: string }): Promise<{ success: boolean; rejected_count: number; status: string }> {
    return request.post(`/annotations/projects/${projectId}/bulk-reject`, data)
  },

  async getReviewQueue(params?: { page?: number; page_size?: number }): Promise<{ items: AnnotationProject[]; total: number }> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    return request.get(`/annotations/projects/review-queue${q.toString() ? `?${q}` : ''}`)
  },

  async reviewAnnotation(annotationId: string, data: { action: string; comment?: string }): Promise<Annotation> {
    return request.post(`/annotations/annotations/${annotationId}/review`, data)
  },

  async getReviewSummary(): Promise<{ total_projects: number; pending_review: number; needs_revision: number; completed: number; in_progress: number }> {
    return request.get('/annotations/stats/review-summary')
  },

  async exportYOLO(projectId?: string): Promise<void> {
    const resp = await request.get(`/annotations/export/yolo${projectId ? `?project_id=${projectId}` : ''}`, {
      responseType: 'blob' as const,
    }) as unknown as { data: Blob; headers: Record<string, string> }
    const blob: Blob = resp.data
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `annotations_${new Date().toISOString().slice(0, 10)}.zip`
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  },
}

export default annotationsApi
