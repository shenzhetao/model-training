<template>
  <a-layout class="basic-layout">
    <!-- Mobile Drawer -->
    <a-drawer
      v-model:open="drawerVisible"
      placement="left"
      :width="260"
      :headerStyle="{ display: 'none' }"
      :bodyStyle="{ padding: 0 }"
      class="mobile-drawer"
    >
      <div class="drawer-header">
        <img src="@/assets/logo.svg" alt="GameAssistant" class="drawer-logo" />
        <span class="drawer-title">GameAssistant</span>
      </div>
      <a-menu
        v-model:selectedKeys="currentMenu"
        theme="light"
        mode="inline"
        :items="menuItems"
        @click="handleMenuClick"
      />
    </a-drawer>

    <a-layout-header class="header">
      <div class="header-left">
        <a-button
          type="text"
          class="menu-toggle hide-desktop"
          @click="drawerVisible = true"
        >
          <template #icon><MenuOutlined /></template>
        </a-button>
        <div class="logo">
          <img src="@/assets/logo.svg" alt="GameAssistant" class="logo-img" />
          <span class="logo-text hide-mobile">GameAssistant</span>
        </div>
      </div>

      <a-menu
        v-model:selectedKeys="currentMenu"
        theme="dark"
        mode="horizontal"
        :items="menuItems"
        @click="handleMenuClick"
        class="main-menu hide-mobile"
      />
      <!-- Admin-only menu -->
      <a-menu
        v-if="isAdmin"
        v-model:selectedKeys="currentMenu"
        theme="dark"
        mode="horizontal"
        :items="adminMenuItems"
        @click="handleMenuClick"
        class="admin-menu hide-mobile"
      />

      <div class="header-right">
        <a-tooltip title="刷新">
          <a-button type="text" class="header-btn" @click="handleRefresh" :loading="refreshing">
            <template #icon><ReloadOutlined :spin="refreshing" /></template>
          </a-button>
        </a-tooltip>
        <a-dropdown>
          <div class="user-info">
            <a-avatar class="user-avatar" size="small">{{ username.charAt(0).toUpperCase() }}</a-avatar>
            <span class="user-name hide-mobile">{{ username }}</span>
            <DownOutlined class="user-arrow" />
          </div>
          <template #overlay>
            <a-menu>
              <a-menu-item key="profile">
                <UserOutlined /> 个人设置
              </a-menu-item>
              <a-menu-divider />
              <a-menu-item key="logout" @click="handleLogout">
                <LogoutOutlined /> 退出登录
              </a-menu-item>
            </a-menu>
          </template>
        </a-dropdown>
      </div>
    </a-layout-header>
    <a-layout-content class="content">
      <router-view v-slot="{ Component }">
        <transition name="page" mode="out-in">
          <component :is="Component" :key="route.path" />
        </transition>
      </router-view>
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import {
  UserOutlined, LogoutOutlined, ReloadOutlined,
  DownOutlined, MenuOutlined,
} from '@ant-design/icons-vue'
import { MenuProps } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const refreshing = ref(false)
const drawerVisible = ref(false)
const username = computed(() => authStore.username)

const menuItems: MenuProps['items'] = [
  { key: '/images', label: '图片管理' },
  { key: '/annotations', label: '标注管理' },
  { key: '/datasets', label: '数据集' },
  { key: '/models', label: '模型管理' },
  { key: '/training', label: '训练管理' },
  { key: '/inference', label: '推理测试' },
  { key: '/templates', label: '模板管理' },
]

// Admin-only menu items
const adminMenuItems: MenuProps['items'] = [
  { key: '/users', label: '用户管理' },
]

const isAdmin = computed(() => authStore.isAdmin)

const currentMenu = ref<string[]>([route.path])

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
  drawerVisible.value = false
}

function handleRefresh() {
  refreshing.value = true
  setTimeout(() => { refreshing.value = false }, 800)
  window.location.reload()
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

function onResize() {
  if (window.innerWidth > 768) {
    drawerVisible.value = false
  }
}

onMounted(() => {
  currentMenu.value = [route.path]
  window.addEventListener('resize', onResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', onResize)
})
</script>

<style scoped>
.basic-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 20px;
  height: 56px;
  line-height: 56px;
  position: sticky;
  top: 0;
  z-index: 10;
  box-shadow: 0 1px 8px rgba(0, 0, 0, 0.15);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.menu-toggle {
  color: rgba(255, 255, 255, 0.75);
  font-size: 18px;
}

.menu-toggle:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 24px;
  flex-shrink: 0;
}

.logo-img {
  height: 28px;
  margin-right: 8px;
}

.logo-text {
  color: #ffffff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: -0.3px;
  white-space: nowrap;
}

.main-menu {
  flex: 1;
  background: transparent;
  border-bottom: none;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: 16px;
  flex-shrink: 0;
}

.header-btn {
  color: rgba(255, 255, 255, 0.75);
  display: flex;
  align-items: center;
}

.header-btn:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.1);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 6px;
  transition: background 0.2s;
  color: rgba(255, 255, 255, 0.85);
}

.user-info:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.user-avatar {
  background: var(--ga-primary, #1890ff);
  font-weight: 600;
  flex-shrink: 0;
}

.user-name {
  font-size: 13px;
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.user-arrow {
  font-size: 10px;
  opacity: 0.6;
}

.content {
  padding: 24px;
  background: var(--ga-bg-base, #f0f2f5);
  min-height: calc(100vh - 56px);
  flex: 1;
}

/* Drawer */
.drawer-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  background: #001529;
}

.drawer-logo {
  height: 28px;
}

.drawer-title {
  color: #fff;
  font-size: 16px;
  font-weight: 700;
}

/* Page transition */
.page-enter-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.page-leave-active {
  transition: opacity 0.15s ease;
}
.page-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.page-leave-to {
  opacity: 0;
}

/* Responsive */
.hide-mobile {
  /* shown on desktop */
}

.hide-desktop {
  display: none;
}

@media (max-width: 768px) {
  .header {
    padding: 0 12px;
  }

  .hide-mobile {
    display: none !important;
  }

  .hide-desktop {
    display: flex;
  }

  .logo {
    margin-right: 0;
  }

  .content {
    padding: 12px;
  }

  .drawer-header {
    padding: 12px 16px;
  }
}
</style>
