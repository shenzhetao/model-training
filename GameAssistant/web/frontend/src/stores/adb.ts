import { defineStore } from 'pinia'
import { ref } from 'vue'
import adbApi, { type DeviceInfo, type DetectionItem, type InferenceParams } from '@/api/adb'

export type InferenceMode = 'hybrid' | 'template' | 'yolo'

export const useADBDeviceStore = defineStore('adb', () => {
  const status = ref<'idle' | 'checking' | 'connected' | 'disconnected' | 'error'>('idle')
  const device = ref<DeviceInfo | null>(null)
  const devices = ref<DeviceInfo[]>([])
  const screenshotUrl = ref<string>('')
  const screenshotLoading = ref(false)
  const screenshotError = ref<string>('')
  const inferenceLoading = ref(false)
  const inferenceError = ref<string>('')
  const detections = ref<DetectionItem[]>([])
  const inferenceMode = ref<InferenceMode>('hybrid')
  const yoloConf = ref(0.4)
  const autoRefresh = ref(false)
  let refreshInterval: ReturnType<typeof setInterval> | null = null

  async function checkStatus(deviceId?: string) {
    status.value = 'checking'
    try {
      const resp = await adbApi.getStatus(deviceId)
      if (resp.connected && resp.device) {
        status.value = 'connected'
        device.value = resp.device
        devices.value = []
        screenshotError.value = ''
      } else {
        status.value = resp.adb_available ? 'disconnected' : 'error'
        device.value = null
        screenshotError.value = resp.message
      }
    } catch (error: any) {
      status.value = 'error'
      screenshotError.value = error?.response?.data?.detail || '检测失败'
    }
  }

  async function loadDevices() {
    try {
      const resp = await adbApi.listDevices()
      devices.value = resp.devices.filter(d => d.state === 'device')
      if (devices.value.length === 0) {
        screenshotError.value = '未检测到已连接的设备'
      }
    } catch {
      screenshotError.value = '获取设备列表失败'
    }
  }

  async function captureScreenshot(deviceId?: string) {
    screenshotLoading.value = true
    screenshotError.value = ''
    try {
      const url = adbApi.getScreenshotUrl(deviceId || device.value?.device_id)
      const baseUrl = url.startsWith('/') ? '' : '/'
      screenshotUrl.value = baseUrl + url + `&t=${Date.now()}`
    } catch (error: any) {
      screenshotError.value = error?.response?.data?.detail || '截图失败'
    } finally {
      screenshotLoading.value = false
    }
  }

  async function runInference(params: InferenceParams = {}) {
    inferenceLoading.value = true
    inferenceError.value = ''
    detections.value = []
    try {
      const resp = await adbApi.runInference({
        device_id: params.device_id || device.value?.device_id,
        mode: params.mode || inferenceMode.value,
        yolo_conf: params.yolo_conf ?? yoloConf.value,
      })
      detections.value = resp.detections || []
    } catch (error: any) {
      inferenceError.value = error?.response?.data?.detail || '推理失败'
    } finally {
      inferenceLoading.value = false
    }
  }

  function setMode(mode: InferenceMode) {
    inferenceMode.value = mode
  }

  function setYoloConf(conf: number) {
    yoloConf.value = conf
  }

  function startAutoRefresh(intervalMs = 5000) {
    stopAutoRefresh()
    autoRefresh.value = true
    refreshInterval = setInterval(() => {
      captureScreenshot()
      runInference()
    }, intervalMs)
  }

  function stopAutoRefresh() {
    autoRefresh.value = false
    if (refreshInterval) {
      clearInterval(refreshInterval)
      refreshInterval = null
    }
  }

  function reset() {
    stopAutoRefresh()
    status.value = 'idle'
    device.value = null
    devices.value = []
    screenshotUrl.value = ''
    screenshotLoading.value = false
    screenshotError.value = ''
    inferenceLoading.value = false
    inferenceError.value = ''
    detections.value = []
  }

  return {
    status,
    device,
    devices,
    screenshotUrl,
    screenshotLoading,
    screenshotError,
    inferenceLoading,
    inferenceError,
    detections,
    inferenceMode,
    yoloConf,
    autoRefresh,
    checkStatus,
    loadDevices,
    captureScreenshot,
    runInference,
    setMode,
    setYoloConf,
    startAutoRefresh,
    stopAutoRefresh,
    reset,
  }
})
