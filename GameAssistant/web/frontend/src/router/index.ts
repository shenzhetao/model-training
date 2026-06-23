import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '@/stores/auth'

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
        component: () => import('@/views/AnnotationManager.vue'),
        meta: { title: '标注管理' },
      },
      {
        path: 'templates',
        name: 'TemplateManager',
        component: () => import('@/views/TemplateManager.vue'),
        meta: { title: '模板管理' },
      },
      {
        path: 'datasets',
        name: 'DatasetManager',
        component: () => import('@/views/DatasetManager.vue'),
        meta: { title: '数据集管理' },
      },
      {
        path: 'models',
        name: 'ModelManager',
        component: () => import('@/views/ModelManager.vue'),
        meta: { title: '模型管理' },
      },
      {
        path: 'training',
        name: 'TrainingManager',
        component: () => import('@/views/TrainingManager.vue'),
        meta: { title: '训练管理' },
      },
      {
        path: 'inference',
        name: 'InferencePlayground',
        component: () => import('@/views/InferencePlayground.vue'),
        meta: { title: '推理测试' },
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('@/views/UserManagement.vue'),
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
