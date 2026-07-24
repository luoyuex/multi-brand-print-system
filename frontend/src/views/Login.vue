<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <img :src="logoUrl" class="login-logo" alt="" />
        <div class="login-title">多品牌录单系统</div>
      </div>
      <el-form :model="form" @submit.prevent="submit">
        <el-form-item>
          <el-input
            v-model="form.username"
            size="large"
            placeholder="用户名"
            :prefix-icon="User"
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-form-item>
          <el-input
            v-model="form.password"
            type="password"
            size="large"
            placeholder="密码"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button
          type="primary"
          size="large"
          class="login-btn"
          :loading="loading"
          @click="submit"
        >登 录</el-button>
      </el-form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import logoUrl from '../status/logo.jpg'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)

async function submit() {
  if (!form.value.username.trim() || !form.value.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    await auth.login(form.value.username.trim(), form.value.password)
    ElMessage.success('登录成功')
    const redirect = route.query.redirect || '/'
    router.replace(redirect)
  } catch (e) {
    ElMessage.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #409eff 0%, #2176d9 100%);
  padding: 20px;
}
.login-card {
  width: 100%;
  max-width: 360px;
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  padding: 36px 28px 28px;
}
.login-brand {
  text-align: center;
  margin-bottom: 28px;
}
.login-logo {
  height: 56px;
  width: auto;
  border-radius: 10px;
  object-fit: contain;
}
.login-title {
  margin-top: 12px;
  font-size: 19px;
  font-weight: 700;
  color: #303133;
  letter-spacing: 0.5px;
}
.login-btn {
  width: 100%;
  margin-top: 4px;
}
</style>
