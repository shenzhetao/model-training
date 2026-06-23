import axios, { type AxiosError, type InternalAxiosRequestConfig, type AxiosResponse, type AxiosRequestConfig, type AxiosProgressEvent } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'

export interface RequestConfig extends AxiosRequestConfig {
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void
  skipCache?: boolean
}

interface CacheEntry {
  data: unknown
  timestamp: number
  ttl: number
}

const DEFAULT_CACHE_TTL = 5 * 60 * 1000 // 5 minutes
const requestCache = new Map<string, CacheEntry>()

function generateCacheKey(config: InternalAxiosRequestConfig): string {
  return `${config.method}:${config.url}:${JSON.stringify(config.params || {})}:${JSON.stringify(config.data || {})}`
}

function setCachedResponse<T>(key: string, data: T, ttl: number = DEFAULT_CACHE_TTL): void {
  // Limit cache size
  if (requestCache.size >= 50) {
    const firstKey = requestCache.keys().next().value
    if (firstKey) requestCache.delete(firstKey)
  }
  requestCache.set(key, { data, timestamp: Date.now(), ttl })
}

export function clearRequestCache(): void {
  requestCache.clear()
}

export function invalidateCache(predicate?: (key: string) => boolean): void {
  if (!predicate) {
    requestCache.clear()
    return
  }
  const keysToDelete: string[] = []
  requestCache.forEach((_, key) => {
    if (predicate(key)) keysToDelete.push(key)
  })
  keysToDelete.forEach((key) => requestCache.delete(key))
}

const api = axios.create({
  baseURL: '/api',
  timeout: 300000, // 5 minutes for large file uploads
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for caching
api.interceptors.request.use(
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

// Response interceptor for caching GET requests
api.interceptors.response.use(
  async (response: AxiosResponse) => {
    const config = response.config

    // For blob responses, return the raw response object so callers can access response.data
    if (config.responseType === 'blob') {
      return response
    }

    // Cache GET requests (not with skipCache flag)
    if (config.method === 'get' && !(config as RequestConfig).skipCache) {
      const cacheKey = generateCacheKey(config)
      setCachedResponse(cacheKey, response.data, DEFAULT_CACHE_TTL)
    }

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

interface RequestMethods {
  post<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T>
  get<T = any>(url: string, config?: RequestConfig): Promise<T>
  delete<T = any>(url: string, config?: RequestConfig): Promise<T>
  put<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T>
  patch<T = any>(url: string, data?: any, config?: RequestConfig): Promise<T>
}

const request: RequestMethods = {
  post: <T>(url: string, data?: any, config?: RequestConfig) =>
    api.post<T>(url, data, config as AxiosRequestConfig) as Promise<T>,
  get: <T>(url: string, config?: RequestConfig) =>
    api.get<T>(url, config as AxiosRequestConfig) as Promise<T>,
  delete: <T>(url: string, config?: RequestConfig) =>
    api.delete<T>(url, config as AxiosRequestConfig) as Promise<T>,
  put: <T>(url: string, data?: any, config?: RequestConfig) =>
    api.put<T>(url, data, config as AxiosRequestConfig) as Promise<T>,
  patch: <T>(url: string, data?: any, config?: RequestConfig) =>
    api.patch<T>(url, data, config as AxiosRequestConfig) as Promise<T>,
}

export default request
