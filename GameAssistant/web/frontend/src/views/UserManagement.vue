<template>
  <div class="user-management">
    <div class="page-header">
      <h2>用户管理</h2>
      <a-button type="primary" @click="openCreateModal">
        <template #icon><PlusOutlined /></template>
        创建用户
      </a-button>
    </div>

    <a-card>
      <a-table
        :columns="columns"
        :data-source="users"
        :loading="loading"
        :pagination="pagination"
        row-key="id"
        @change="handleTableChange"
      >
        <template #bodyCell="{ column, record }">
          <template v-if="column.key === 'username'">
            <a-space>
              <a-avatar :size="24" style="background: #1890ff">
                {{ record.username.charAt(0).toUpperCase() }}
              </a-avatar>
              <span>{{ record.username }}</span>
            </a-space>
          </template>
          <template v-else-if="column.key === 'role'">
            <a-tag :color="getRoleColor(record.role)">
              {{ getRoleLabel(record.role) }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'is_active'">
            <a-badge
              :status="record.is_active ? 'success' : 'error'"
              :text="record.is_active ? '启用' : '禁用'"
            />
          </template>
          <template v-else-if="column.key === 'is_password_changed'">
            <a-tag :color="record.is_password_changed ? 'green' : 'orange'">
              {{ record.is_password_changed ? '已修改' : '待修改' }}
            </a-tag>
          </template>
          <template v-else-if="column.key === 'created_at'">
            {{ formatDate(record.created_at) }}
          </template>
          <template v-else-if="column.key === 'action'">
            <a-space>
              <a-button type="link" size="small" @click="openEditModal(record)">
                编辑
              </a-button>
              <a-popconfirm
                title="确定要删除此用户吗？"
                ok-text="确定"
                cancel-text="取消"
                @confirm="handleDelete(record.id)"
                :disabled="record.id === currentUserId"
              >
                <a-button
                  type="link"
                  size="small"
                  danger
                  :disabled="record.id === currentUserId"
                >
                  删除
                </a-button>
              </a-popconfirm>
            </a-space>
          </template>
        </template>
      </a-table>
    </a-card>

    <!-- Create/Edit Modal -->
    <a-modal
      v-model:open="modalVisible"
      :title="isEditMode ? '编辑用户' : '创建用户'"
      @ok="handleSubmit"
      :confirmLoading="submitting"
      ok-text="确定"
      cancel-text="取消"
    >
      <a-form
        ref="formRef"
        :model="formState"
        :label-col="{ span: 6 }"
        :wrapper-col="{ span: 16 }"
      >
        <a-form-item
          label="用户名"
          name="username"
          :rules="[{ required: !isEditMode, message: '请输入用户名' }]"
        >
          <a-input
            v-model:value="formState.username"
            placeholder="请输入用户名"
            :disabled="isEditMode"
          />
        </a-form-item>

        <a-form-item
          label="邮箱"
          name="email"
          :rules="[{ type: 'email', message: '请输入有效的邮箱地址' }]"
        >
          <a-input v-model:value="formState.email" placeholder="请输入邮箱（可选）" />
        </a-form-item>

        <a-form-item
          label="角色"
          name="role"
          :rules="[{ required: !isEditMode, message: '请选择角色' }]"
        >
          <a-select v-model:value="formState.role" :disabled="isEditMode">
            <a-select-option value="admin">管理员</a-select-option>
            <a-select-option value="annotator">标注员</a-select-option>
            <a-select-option value="reviewer">审核员</a-select-option>
          </a-select>
        </a-form-item>

        <a-form-item
          :label="isEditMode ? '重置密码' : '密码'"
          name="password"
          :rules="isEditMode ? [] : [{ required: !isEditMode, message: '请输入密码' }]"
        >
          <a-input-password
            v-model:value="formState.password"
            :placeholder="isEditMode ? '留空则不修改密码' : '留空使用默认密码: Changeme123'"
          />
        </a-form-item>

        <a-form-item label="状态" name="is_active" v-if="isEditMode">
          <a-switch v-model:checked="formState.is_active" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { message } from 'ant-design-vue'
import { PlusOutlined } from '@ant-design/icons-vue'
import { usersApi, type User, type CreateUserRequest, type UpdateUserRequest } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

interface FormState {
  username: string
  email?: string
  role: 'admin' | 'annotator' | 'reviewer'
  password?: string
  is_active: boolean
}

const authStore = useAuthStore()
const currentUserId = computed(() => authStore.user?.id)

const columns = [
  {
    title: '用户名',
    key: 'username',
    dataIndex: 'username',
  },
  {
    title: '邮箱',
    dataIndex: 'email',
    key: 'email',
  },
  {
    title: '角色',
    key: 'role',
    dataIndex: 'role',
  },
  {
    title: '状态',
    key: 'is_active',
    dataIndex: 'is_active',
  },
  {
    title: '密码状态',
    key: 'is_password_changed',
    dataIndex: 'is_password_changed',
  },
  {
    title: '创建时间',
    key: 'created_at',
    dataIndex: 'created_at',
    width: 180,
  },
  {
    title: '操作',
    key: 'action',
    width: 150,
  },
]

const users = ref<User[]>([])
const loading = ref(false)
const modalVisible = ref(false)
const isEditMode = ref(false)
const submitting = ref(false)
const editingId = ref<string | null>(null)
const formRef = ref()

const pagination = reactive({
  current: 1,
  pageSize: 20,
  total: 0,
  showSizeChanger: true,
  showQuickJumper: true,
  showTotal: (total: number) => `共 ${total} 条`,
})

const formState = reactive<FormState>({
  username: '',
  email: '',
  role: 'annotator',
  password: '',
  is_active: true,
})

function getRoleColor(role: string) {
  const colors: Record<string, string> = {
    admin: 'red',
    annotator: 'blue',
    reviewer: 'green',
  }
  return colors[role] || 'default'
}

function getRoleLabel(role: string) {
  const labels: Record<string, string> = {
    admin: '管理员',
    annotator: '标注员',
    reviewer: '审核员',
  }
  return labels[role] || role
}

function formatDate(dateStr: string) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN')
}

async function fetchUsers() {
  loading.value = true
  try {
    const skip = (pagination.current - 1) * pagination.pageSize
    const data = await usersApi.listUsers(skip, pagination.pageSize)
    users.value = data
    pagination.total = data.length
  } catch {
    message.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  isEditMode.value = false
  editingId.value = null
  Object.assign(formState, {
    username: '',
    email: '',
    role: 'annotator',
    password: '',
    is_active: true,
  })
  modalVisible.value = true
}

function openEditModal(user: User) {
  isEditMode.value = true
  editingId.value = user.id
  Object.assign(formState, {
    username: user.username,
    email: user.email || '',
    role: user.role,
    password: '',
    is_active: user.is_active,
  })
  modalVisible.value = true
}

async function handleSubmit() {
  try {
    await formRef.value.validate()
  } catch {
    return
  }

  submitting.value = true
  try {
    if (isEditMode.value && editingId.value) {
      const data: UpdateUserRequest = {
        email: formState.email || undefined,
        is_active: formState.is_active,
      }
      if (formState.role) {
        data.role = formState.role
      }
      if (formState.password) {
        data.password = formState.password
      }
      await usersApi.updateUser(editingId.value, data)
      message.success('用户更新成功')
    } else {
      const data: CreateUserRequest = {
        username: formState.username,
        email: formState.email || undefined,
        role: formState.role,
      }
      if (formState.password) {
        data.password = formState.password
      }
      await usersApi.createUser(data)
      message.success('用户创建成功')
    }
    modalVisible.value = false
    fetchUsers()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    message.error(detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  try {
    await usersApi.deleteUser(id)
    message.success('用户删除成功')
    fetchUsers()
  } catch (error: any) {
    const detail = error?.response?.data?.detail
    message.error(detail || '删除失败')
  }
}

function handleTableChange(pag: any) {
  pagination.current = pag.current
  pagination.pageSize = pag.pageSize
  fetchUsers()
}

onMounted(() => {
  fetchUsers()
})
</script>

<style scoped>
.user-management {
  width: 100%;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}
</style>
