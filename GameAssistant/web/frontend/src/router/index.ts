import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

// Import async components for non-primary views
import { AnnotationManagerAsync } from '@/views/async/AnnotationManagerAsync'
import { TemplateManagerAsync } from '@/views/async/TemplateManagerAsync'
import { DatasetManagerAsync } from '@/views/async/DatasetManagerAsync'
import { ModelManagerAsync } from '@/views/async/ModelManagerAsync'
import { TrainingManagerAsync } from '@/views/async/TrainingManagerAsync'
import { InferencePlaygroundAsync } from '@/views/async/InferencePlaygroundAsync'
import { UserManagementAsync } from '@/views/async/UserManagementAsync'

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/Login.vue'),
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    component: () => import('@/layouts/BasicLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/images',
      },
      {
        path: 'images',
        name: 'ImageManager',
        component: () => import('@/views/ImageManager.vue'),
        meta: { title: '图片管理' },
      },
      {
        path: 'annotations',
        name: 'AnnotationManager',
        component: AnnotationManagerAsync,
        meta: { title: '标注管理' },
      },
      {
        path: 'templates',
        name: 'TemplateManager',
        component: TemplateManagerAsync,
        meta: { title: '模板管理' },
      },
      {
        path: 'datasets',
        name: 'DatasetManager',
        component: DatasetManagerAsync,
        meta: { title: '数据集管理' },
      },
      {
        path: 'models',
        name: 'ModelManager',
        component: ModelManagerAsync,
        meta: { title: '模型管理' },
      },
      {
        path: 'training',
        name: 'TrainingManager',
        component: TrainingManagerAsync,
        meta: { title: '训练管理' },
      },
      {
        path: 'inference',
        name: 'InferencePlayground',
        component: InferencePlaygroundAsync,
        meta: { title: '推理测试' },
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: UserManagementAsync,
        meta: { title: '用户管理', requiresAdmin: true },
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, _from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.meta.requiresAuth !== false

  if (requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.name === 'Login' && authStore.isAuthenticated) {
    next({ name: 'ImageManager' })
  }
  // Admin-only routes check
  else if (to.meta.requiresAdmin && !authStore.isAdmin) {
    message.error('需要管理员权限')
    next({ name: 'ImageManager' })
  }
  else {
    next()
  }
})

export default router
