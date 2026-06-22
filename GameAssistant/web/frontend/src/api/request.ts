import axios, { type AxiosInstance, type AxiosError, type InternalAxiosRequestConfig, type AxiosResponse, type AxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'

export interface RequestConfig extends AxiosRequestConfig {
  onUploadProgress?: (progressEvent: ProgressEvent) => void
}

const _request: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 300000, // 5 minutes for large file uploads
  headers: {
    'Content-Type': 'application/json',
  },
})

_request.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

_request.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  async (error: AxiosError) => {
    const authStore = useAuthStore()

    if (error.response) {
      const status = error.response.status

      switch (status) {
        case 401:
          authStore.logout()
          message.error('登录已过期，请重新登录')
          window.location.href = '/login'
          break
        case 403:
          message.error('没有权限访问该资源')
          break
        case 404:
          message.error('请求的资源不存在')
          break
        case 422:
          message.error('请求参数验证失败')
          break
        case 500:
          message.error('服务器内部错误')
          break
        case 409: // Conflict - duplicate
          break
        default:
          message.error(`请求失败: ${status}`)
      }
    } else if (error.request) {
      message.error('网络连接失败，请检查网络')
    } else {
      message.error('请求配置错误')
    }

    return Promise.reject(error)
  }
)

const request: AxiosInstance = _request as unknown as AxiosInstance

request.post = function<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T> {
  return _request.post(url, data, config as AxiosRequestConfig)
}

request.delete = function<T = any>(url: string, config?: RequestConfig): Promise<T> {
  return _request.delete(url, config as AxiosRequestConfig)
}

request.get = function<T = any>(url: string, config?: RequestConfig): Promise<T> {
  return _request.get(url, config as AxiosRequestConfig)
}

export default request
