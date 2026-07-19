<template>
  <el-container style="min-height: 100vh;">

    <!-- ── 顶部导航（平板 & 桌面）──────────────────── -->
    <el-header
      height="54px"
      class="app-header"
    >
      <div class="header-inner">
        <span class="header-logo">🧾 多品牌录单系统</span>
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
          <el-menu-item index="/">📝 录单</el-menu-item>
          <el-menu-item index="/print">🖨️ 打印列表</el-menu-item>
          <el-menu-item index="/bills">💰 账单</el-menu-item>
          <el-menu-item index="/stores">🏪 店铺管理</el-menu-item>
          <el-menu-item index="/products">📦 商品管理</el-menu-item>
          <el-menu-item index="/brands">🏷️ 品牌管理</el-menu-item>
        </el-menu>
      </div>
    </el-header>

    <!-- ── 页面内容 ───────────────────────────────── -->
    <el-main class="app-main page-content">
      <router-view />
    </el-main>

    <!-- ── 底部 Tab 栏（仅移动端）──────────────────── -->
    <div v-if="isMobile" class="bottom-tab-bar">
      <router-link
        v-for="tab in tabs"
        :key="tab.path"
        :to="tab.path"
        class="tab-item"
        :class="{ active: $route.path === tab.path }"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
      </router-link>
    </div>

  </el-container>
</template>

<script setup>
import { useBreakpoint } from './composables/useBreakpoint'

const { isMobile } = useBreakpoint()

const tabs = [
  { path: '/',         icon: '📝', label: '录单'   },
  { path: '/print',    icon: '🖨️', label: '打印'   },
  { path: '/bills',    icon: '💰', label: '账单'   },
  { path: '/stores',   icon: '🏪', label: '店铺'   },
  { path: '/products', icon: '📦', label: '商品'   },
  { path: '/brands',   icon: '🏷️', label: '品牌'  },
]
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
  color: #fff;
  font-size: 17px;
  font-weight: 700;
  letter-spacing: 0.5px;
  white-space: nowrap;
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
  background: #fff;
  display: flex;
  align-items: stretch;
  box-shadow: 0 -1px 0 #e8eaec, 0 -4px 12px rgba(0,0,0,0.06);
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
  color: #909399;
  transition: color 0.2s;
}
.tab-item.active {
  color: var(--color-primary);
}
.tab-icon {
  font-size: 22px;
  line-height: 1;
}
.tab-label {
  font-size: 11px;
  font-weight: 500;
}
</style>
