<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <img src="@/assets/logo.svg" alt="GameAssistant" />
        <h1>GameAssistant</h1>
        <p>模型训练管理平台</p>
      </div>
      <a-form
        :model="formState"
        @finish="handleLogin"
        layout="vertical"
        class="login-form"
      >
        <a-form-item
          name="username"
          :rules="[{ required: true, message: '请输入用户名' }]"
        >
          <a-input
            v-model:value="formState.username"
            placeholder="用户名"
            size="large"
          >
            <template #prefix>
              <UserOutlined />
            </template>
          </a-input>
        </a-form-item>
        <a-form-item
          name="password"
          :rules="[{ required: true, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="formState.password"
            placeholder="密码"
            size="large"
          >
            <template #prefix>
              <LockOutlined />
            </template>
          </a-input-password>
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            size="large"
            block
            :loading="loading"
          >
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { message } from 'ant-design-vue'
import { UserOutlined, LockOutlined } from '@ant-design/icons-vue'
import { usersApi } from '@/api/users'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const loading = ref(false)

const formState = reactive({
  username: '',
  password: ''
})

async function handleLogin() {
  loading.value = true
  try {
    const response = await usersApi.login(formState)
    // Persist token FIRST so the next request's Authorization header is attached
    authStore.setToken(response.access_token)
    // Fetch current user info after login
    const userInfo = await usersApi.getCurrentUser()
    authStore.setUser(userInfo)
    const redirect = route.query.redirect as string || '/images'
    router.push(redirect)
    message.success('登录成功')
  } catch (error) {
    message.error('用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-card {
  width: 400px;
  padding: 40px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.login-header img {
  height: 64px;
  margin-bottom: 16px;
}

.login-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
  color: #333;
}

.login-header p {
  color: #666;
}

.login-form {
  margin-top: 24px;
}
</style>
