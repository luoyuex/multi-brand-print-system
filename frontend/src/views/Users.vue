<template>
  <div>
    <el-card>
      <template #header>
        <span>账号管理</span>
        <el-button type="primary" style="float:right;" @click="openAdd">+ 新增账号</el-button>
      </template>

      <el-table :data="users" border stripe>
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="用户名" min-width="120" />
        <el-table-column prop="name" label="显示名" min-width="120">
          <template #default="{ row }">{{ row.name || '-' }}</template>
        </el-table-column>
        <el-table-column label="角色" width="100">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
              {{ row.role === 'admin' ? '管理员' : '员工' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'" size="small">
              {{ row.is_active ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" @click="openReset(row)">改密</el-button>
            <el-button
              size="small"
              type="danger"
              :disabled="row.id === auth.user?.id"
              @click="remove(row)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增/编辑 Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="editTarget ? '编辑账号' : '新增账号'"
      width="420px"
    >
      <el-form :model="form" label-width="70px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" :disabled="!!editTarget" placeholder="登录用户名" />
        </el-form-item>
        <el-form-item label="显示名">
          <el-input v-model="form.name" placeholder="选填，如 张三" />
        </el-form-item>
        <el-form-item v-if="!editTarget" label="密码">
          <el-input v-model="form.password" type="password" show-password placeholder="登录密码" />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio label="staff">员工</el-radio>
            <el-radio label="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="editTarget" label="状态">
          <el-switch v-model="form.is_active" active-text="启用" inactive-text="停用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 Dialog -->
    <el-dialog v-model="resetVisible" title="重置密码" width="380px">
      <el-form label-width="70px">
        <el-form-item label="账号">{{ resetTarget?.username }}</el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="newPassword" type="password" show-password placeholder="输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doReset">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { authApi } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const users = ref([])
const dialogVisible = ref(false)
const editTarget = ref(null)
const saving = ref(false)
const form = ref({ username: '', name: '', password: '', role: 'staff', is_active: true })

const resetVisible = ref(false)
const resetTarget = ref(null)
const newPassword = ref('')

onMounted(load)

async function load() {
  users.value = await authApi.listUsers()
}

function openAdd() {
  editTarget.value = null
  form.value = { username: '', name: '', password: '', role: 'staff', is_active: true }
  dialogVisible.value = true
}

function openEdit(row) {
  editTarget.value = row
  form.value = { username: row.username, name: row.name || '', role: row.role, is_active: row.is_active }
  dialogVisible.value = true
}

async function save() {
  if (!editTarget.value) {
    if (!form.value.username.trim()) return ElMessage.warning('用户名不能为空')
    if (!form.value.password.trim()) return ElMessage.warning('密码不能为空')
  }
  saving.value = true
  try {
    if (editTarget.value) {
      await authApi.updateUser(editTarget.value.id, {
        name: form.value.name,
        role: form.value.role,
        is_active: form.value.is_active,
      })
      ElMessage.success('已更新')
    } else {
      await authApi.createUser({
        username: form.value.username.trim(),
        name: form.value.name,
        password: form.value.password,
        role: form.value.role,
      })
      ElMessage.success('已新增')
    }
    dialogVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

function openReset(row) {
  resetTarget.value = row
  newPassword.value = ''
  resetVisible.value = true
}

async function doReset() {
  if (!newPassword.value.trim()) return ElMessage.warning('新密码不能为空')
  saving.value = true
  try {
    await authApi.updateUser(resetTarget.value.id, { password: newPassword.value })
    ElMessage.success('密码已重置')
    resetVisible.value = false
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确定删除账号「${row.username}」？`, '提示', { type: 'warning' })
  try {
    await authApi.removeUser(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    ElMessage.error(e.message)
  }
}
</script>
