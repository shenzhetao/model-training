<template>
  <a-layout class="basic-layout">
    <a-layout-header class="header">
      <div class="logo">
        <img src="@/assets/logo.svg" alt="GameAssistant" />
        <span>GameAssistant</span>
      </div>
      <a-menu
        v-model:selectedKeys="currentMenu"
        theme="dark"
        mode="horizontal"
        :items="menuItems"
        @click="handleMenuClick"
      />
      <div class="user-info">
        <a-dropdown>
          <a-avatar>{{ username.charAt(0).toUpperCase() }}</a-avatar>
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
        <span class="username">{{ username }}</span>
      </div>
    </a-layout-header>
    <a-layout-content class="content">
      <router-view />
    </a-layout-content>
  </a-layout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { UserOutlined, LogoutOutlined } from '@ant-design/icons-vue'
import { MenuProps } from 'ant-design-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const username = computed(() => authStore.username)

const menuItems: MenuProps['items'] = [
  { key: '/images', label: '图片管理' },
  { key: '/annotations', label: '标注管理' },
  { key: '/templates', label: '模板管理' },
  { key: '/datasets', label: '数据集' },
  { key: '/models', label: '模型管理' },
  { key: '/training', label: '训练管理' },
  { key: '/inference', label: '推理测试' }
]

const currentMenu = ref<string[]>([route.path])

function handleMenuClick({ key }: { key: string }) {
  router.push(key)
}

function handleLogout() {
  authStore.logout()
  router.push('/login')
}

onMounted(() => {
  currentMenu.value = [route.path]
})
</script>

<style scoped>
.basic-layout {
  min-height: 100vh;
}

.header {
  display: flex;
  align-items: center;
  padding: 0 20px;
}

.logo {
  display: flex;
  align-items: center;
  margin-right: 40px;
  color: white;
  font-size: 18px;
  font-weight: bold;
}

.logo img {
  height: 32px;
  margin-right: 8px;
}

.user-info {
  margin-left: auto;
  display: flex;
  align-items: center;
  gap: 8px;
}

.username {
  color: white;
}

.content {
  padding: 24px;
  background: #f0f2f5;
  min-height: calc(100vh - 64px);
}
</style>
