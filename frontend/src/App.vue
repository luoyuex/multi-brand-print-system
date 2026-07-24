<template>
  <!-- 登录页：不显示导航框架 -->
  <router-view v-if="isLoginPage" />

  <el-container v-else style="min-height: 100vh;">

    <!-- ── 顶部导航（平板 & 桌面）──────────────────── -->
    <el-header
      height="54px"
      class="app-header"
    >
      <div class="header-inner">
        <span class="header-logo">
          <img :src="logoUrl" class="logo-img" alt="" />
          多品牌录单系统
        </span>
        <!-- 桌面水平菜单 -->
        <el-menu
          v-if="!isMobile"
          :router="true"
          mode="horizontal"
          background-color="transparent"
          text-color="rgba(255,255,255,0.85)"
          active-text-color="#ffffff"
          class="desktop-menu"
          :default-active="$route.path"
        >
          <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
            <img :src="item.icon" class="menu-icon" alt="" />
            {{ item.label }}
          </el-menu-item>
        </el-menu>

        <!-- 右侧：当前用户 + 退出（桌面显示名字，移动端只显示图标）-->
        <el-dropdown class="user-dropdown" @command="onUserCommand">
          <span class="user-trigger">
            <el-icon><User /></el-icon>
            <template v-if="!isMobile">
              {{ auth.user?.name || auth.user?.username }}
              <el-tag size="small" effect="dark" class="role-tag">
                {{ auth.isAdmin ? '管理员' : '员工' }}
              </el-tag>
            </template>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </el-header>

    <!-- ── 页面内容 ───────────────────────────────── -->
    <el-main class="app-main page-content">
      <router-view />
    </el-main>

    <!-- ── 底部 Tab 栏（仅移动端）──────────────────── -->
    <div v-if="isMobile" class="bottom-tab-bar">
      <router-link
        v-for="item in mobileNavItems"
        :key="item.path"
        :to="item.path"
        class="tab-item"
        :class="{ active: $route.path === item.path }"
      >
        <img :src="item.icon" class="tab-icon" alt="" />
        <span class="tab-label">{{ item.tabLabel }}</span>
      </router-link>
    </div>

    <!-- 修改密码 -->
    <el-dialog v-model="pwdVisible" title="修改密码" :width="isMobile ? '92%' : '360px'">
      <el-form :model="pwdForm" label-width="80px">
        <el-form-item label="原密码">
          <el-input v-model="pwdForm.old_password" type="password" show-password />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.new_password" type="password" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="pwdVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdSaving" @click="submitPwd">保存</el-button>
      </template>
    </el-dialog>

  </el-container>
</template>

<script setup>
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User } from '@element-plus/icons-vue'
import { useBreakpoint } from './composables/useBreakpoint'
import { useAuthStore } from './stores/auth'
import { authApi } from './api'
import logoUrl from './status/logo.jpg'
// 导航图标（src/status，按导航顺序 1~6）
import icon1 from './status/1.png'
import icon2 from './status/2.png'
import icon3 from './status/3.png'
import icon4 from './status/4.png'
import icon5 from './status/5.png'
import icon6 from './status/6.png'
import icon7 from './status/7.png'

const { isMobile } = useBreakpoint()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const isLoginPage = computed(() => route.path === '/login')

// 桌面菜单与移动端 Tab 共用；label 桌面用，tabLabel 移动端用
// admin=true 的项仅管理员可见；mobile=false 的项移动端底部栏不显示（如账号管理）
const allNavItems = [
  { path: '/',         icon: icon1, label: '录单',     tabLabel: '录单', admin: false, mobile: true },
  { path: '/print',    icon: icon2, label: '打印列表', tabLabel: '打印', admin: false, mobile: true },
  { path: '/bills',    icon: icon3, label: '账单',     tabLabel: '账单', admin: true,  mobile: true },
  { path: '/stores',   icon: icon4, label: '店铺管理', tabLabel: '店铺', admin: true,  mobile: true },
  { path: '/products', icon: icon5, label: '商品管理', tabLabel: '商品', admin: true,  mobile: true },
  { path: '/brands',   icon: icon6, label: '品牌管理', tabLabel: '品牌', admin: true,  mobile: true },
  // 账号管理：仅管理员、仅 PC（移动端底部放不下）
  { path: '/users',    icon: icon7, label: '账号管理', tabLabel: '账号', admin: true,  mobile: false },
]

// 桌面：按角色过滤
const navItems = computed(() =>
  allNavItems.filter((i) => auth.isAdmin || !i.admin)
)
// 移动端：按角色过滤 + 去掉 mobile=false 的项
const mobileNavItems = computed(() =>
  allNavItems.filter((i) => (auth.isAdmin || !i.admin) && i.mobile)
)

// ── 用户菜单 ─────────────────────────────
const pwdVisible = ref(false)
const pwdSaving = ref(false)
const pwdForm = ref({ old_password: '', new_password: '' })

async function onUserCommand(command) {
  if (command === 'logout') {
    await ElMessageBox.confirm('确定退出登录？', '提示', { type: 'warning' })
    auth.logout()
    router.push('/login')
  } else if (command === 'password') {
    pwdForm.value = { old_password: '', new_password: '' }
    pwdVisible.value = true
  }
}

async function submitPwd() {
  if (!pwdForm.value.old_password || !pwdForm.value.new_password) {
    ElMessage.warning('请填写原密码和新密码')
    return
  }
  pwdSaving.value = true
  try {
    await authApi.changePassword(pwdForm.value)
    ElMessage.success('密码已修改')
    pwdVisible.value = false
  } catch (e) {
    ElMessage.error(e.message)
  } finally {
    pwdSaving.value = false
  }
}
</script>

<style scoped>
/* ── 顶部 Header ───────────────────────────── */
.app-header {
  background: linear-gradient(135deg, #409eff 0%, #2176d9 100%);
  box-shadow: 0 2px 8px rgba(32, 118, 217, 0.3);
  padding: 0;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  height: 100%;
  display: flex;
  align-items: center;
  padding: 0 20px;
}
.header-logo {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
  white-space: nowrap;
}
.logo-img {
  height: 30px;
  width: auto;
  border-radius: 6px;
  object-fit: contain;
  display: block;
}
.desktop-menu {
  margin-left: 32px;
  flex: 1;
  border-bottom: none !important;
}
:deep(.desktop-menu .el-menu-item) {
  border-bottom: 2px solid transparent !important;
  transition: all 0.2s;
}
:deep(.desktop-menu .el-menu-item.is-active) {
  border-bottom: 2px solid #fff !important;
  background: rgba(255, 255, 255, 0.12) !important;
}
.menu-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  margin-right: 6px;
  vertical-align: -4px;
}

/* 用户下拉 */
.user-dropdown {
  margin-left: auto;
  cursor: pointer;
}
.user-trigger {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #fff;
  font-size: 14px;
  outline: none;
}
.role-tag {
  margin-left: 4px;
  background: rgba(255, 255, 255, 0.2);
  border: none;
  color: #fff;
}

/* ── 主内容 ────────────────────────────────── */
.app-main {
  padding: 16px;
  background: #f0f4f9;
}
@media (min-width: 768px) {
  .app-main {
    padding: 20px 24px;
  }
}

/* ── 底部 Tab 栏 ────────────────────────────── */
.bottom-tab-bar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--tab-height);
  background: #2B82E5;
  display: flex;
  align-items: stretch;
  box-shadow: 0 -2px 12px rgba(0,0,0,0.12);
  z-index: 200;
}
.tab-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 3px;
  text-decoration: none;
  color: rgba(255, 255, 255, 0.7);
  transition: color 0.2s, opacity 0.2s;
  cursor: pointer;
}
.tab-item.active {
  color: #fff;
}
.tab-icon {
  width: 24px;
  height: 24px;
  object-fit: contain;
  /* 彩色 png 转白色单色，配蓝底更清晰统一 */
  filter: brightness(0) invert(1);
  opacity: 0.7;
  transition: opacity 0.2s;
}
.tab-item.active .tab-icon {
  opacity: 1;
}
.tab-label {
  font-size: 11px;
  font-weight: 500;
}
</style>
