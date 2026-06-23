import { defineAsyncComponent } from 'vue'
import AsyncLoading from '@/components/AsyncLoading.vue'

const LoadingComponent = {
  component: AsyncLoading,
  props: { tip: '正在加载推理测试...' }
}

const ErrorComponent = {
  template: '<div class="async-error">加载失败，请刷新重试</div>'
}

export const InferencePlaygroundAsync = defineAsyncComponent({
  loader: () => import('@/views/InferencePlayground.vue'),
  loadingComponent: LoadingComponent.component,
  errorComponent: ErrorComponent,
  delay: 200,
  timeout: 10000
})
