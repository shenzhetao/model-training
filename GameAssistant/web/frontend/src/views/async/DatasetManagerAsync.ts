import { defineAsyncComponent } from 'vue'
import AsyncLoading from '@/components/AsyncLoading.vue'

const LoadingComponent = {
  component: AsyncLoading,
  props: { tip: '正在加载数据集管理...' }
}

const ErrorComponent = {
  template: '<div class="async-error">加载失败，请刷新重试</div>'
}

export const DatasetManagerAsync = defineAsyncComponent({
  loader: () => import('@/views/DatasetManager.vue'),
  loadingComponent: LoadingComponent.component,
  errorComponent: ErrorComponent,
  delay: 200,
  timeout: 10000
})
