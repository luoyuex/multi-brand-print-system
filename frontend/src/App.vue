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
          <el-menu-item v-for="item in navItems" :key="item.path" :index="item.path">
            <img :src="item.icon" class="menu-icon" alt="" />
            {{ item.label }}
          </el-menu-item>
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
        v-for="item in navItems"
        :key="item.path"
        :to="item.path"
        class="tab-item"
        :class="{ active: $route.path === item.path }"
      >
        <img :src="item.icon" class="tab-icon" alt="" />
        <span class="tab-label">{{ item.tabLabel }}</span>
      </router-link>
    </div>

  </el-container>
</template>

<script setup>
import { useBreakpoint } from './composables/useBreakpoint'
// 导航图标（src/status，按导航顺序 1~6）
import icon1 from './status/1.png'
import icon2 from './status/2.png'
import icon3 from './status/3.png'
import icon4 from './status/4.png'
import icon5 from './status/5.png'
import icon6 from './status/6.png'

const { isMobile } = useBreakpoint()

// 桌面菜单与移动端 Tab 共用；label 桌面用，tabLabel 移动端用
const navItems = [
  { path: '/',         icon: icon1, label: '录单',     tabLabel: '录单' },
  { path: '/print',    icon: icon2, label: '打印列表', tabLabel: '打印' },
  { path: '/bills',    icon: icon3, label: '账单',     tabLabel: '账单' },
  { path: '/stores',   icon: icon4, label: '店铺管理', tabLabel: '店铺' },
  { path: '/products', icon: icon5, label: '商品管理', tabLabel: '商品' },
  { path: '/brands',   icon: icon6, label: '品牌管理', tabLabel: '品牌' },
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
.menu-icon {
  width: 20px;
  height: 20px;
  object-fit: contain;
  margin-right: 6px;
  vertical-align: -4px;
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
