import request from './request'

// ── Types ──────────────────────────────────────────────────

export interface TemplateClass {
  id: string
  class_name: string
  display_name: string
  description?: string
  default_threshold: number
  icon?: string
  sort_order: number
  created_at: string
}

export interface Template {
  id: string
  class_id?: string
  class_name: string
  name: string
  file_path: string
  file_size: number
  width: number
  height: number
  match_threshold: number
  roi_x?: number
  roi_y?: number
  roi_width?: number
  roi_height?: number
  is_active: boolean
  uploaded_by?: string
  created_at: string
  updated_at: string
}

export interface TemplateTestResult {
  template_id: string
  template_name: string
  matched: boolean
  x: number
  y: number
  w: number
  h: number
  conf: number
}

// ── API ────────────────────────────────────────────────────

export const templatesApi = {
  async getClasses(): Promise<TemplateClass[]> {
    return request.get('/templates/classes')
  },

  async createClass(data: Partial<TemplateClass>): Promise<TemplateClass> {
    return request.post('/templates/classes', data)
  },

  async updateClass(id: string, data: Partial<TemplateClass>): Promise<TemplateClass> {
    return request.put(`/templates/classes/${id}`, data)
  },

  async deleteClass(id: string): Promise<void> {
    return request.delete(`/templates/classes/${id}`)
  },

  async getList(params?: {
    page?: number
    page_size?: number
    class_name?: string
    is_active?: boolean
  }): Promise<Template[]> {
    const q = new URLSearchParams()
    if (params?.page) q.set('page', String(params.page))
    if (params?.page_size) q.set('page_size', String(params.page_size))
    if (params?.class_name) q.set('class_name', params.class_name)
    if (params?.is_active !== undefined) q.set('is_active', String(params.is_active))
    return request.get(`/templates/${q.toString() ? `?${q}` : ''}`)
  },

  async upload(formData: FormData): Promise<Template> {
    return request.post('/templates/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  async getById(id: string): Promise<Template> {
    return request.get(`/templates/${id}`)
  },

  async update(id: string, data: Partial<Template>): Promise<Template> {
    return request.put(`/templates/${id}`, data)
  },

  async delete(id: string): Promise<void> {
    return request.delete(`/templates/${id}`)
  },

  getServeUrl(id: string): string {
    return `/api/templates/${id}/serve`
  },

  async testMatching(params: {
    image_id?: string
    image_url?: string
    template_ids?: string[]
    threshold?: number
    multi_match?: boolean
    method?: string
  }): Promise<{ success: boolean; results: TemplateTestResult[]; message: string }> {
    return request.post('/templates/test', params)
  },
}

export default templatesApi
