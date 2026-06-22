import request from './request'

export interface DeviceInfo {
  device_id: string
  state: string
  resolution: [number, number]
  model?: string
  product?: string
}

export interface ADBStatusResponse {
  adb_available: boolean
  server_running: boolean
  connected: boolean
  device?: DeviceInfo
  message: string
}

export interface DeviceListResponse {
  available: boolean
  server_running: boolean
  devices: DeviceInfo[]
  default_device?: DeviceInfo
}

export interface DetectionItem {
  cls: string
  x: number
  y: number
  w: number
  h: number
  conf: number
  source: string
}

export interface InferenceResponse {
  success: boolean
  device_id?: string
  resolution?: [number, number]
  detections: DetectionItem[]
  annotated_image_url?: string
  message: string
}

export interface InferenceParams {
  device_id?: string
  mode?: 'hybrid' | 'template' | 'yolo'
  yolo_conf?: number
}

export const adbApi = {
  async getStatus(device_id?: string): Promise<ADBStatusResponse> {
    const params = device_id ? `?device_id=${encodeURIComponent(device_id)}` : ''
    return request.get(`/adb/status${params}`)
  },

  async listDevices(): Promise<DeviceListResponse> {
    return request.get('/adb/devices')
  },

  getScreenshotUrl(device_id?: string): string {
    const params = device_id ? `?device_id=${encodeURIComponent(device_id)}` : ''
    return `/api/v1/adb/screenshot${params}`
  },

  async runInference(params: InferenceParams = {}): Promise<InferenceResponse> {
    const query = new URLSearchParams()
    if (params.device_id) query.set('device_id', params.device_id)
    if (params.mode) query.set('mode', params.mode)
    if (params.yolo_conf !== undefined) query.set('yolo_conf', String(params.yolo_conf))
    const q = query.toString()
    return request.get(`/adb/inference${q ? `?${q}` : ''}`)
  },
}

export default adbApi
