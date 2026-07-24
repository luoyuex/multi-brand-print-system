import { createRouter, createWebHistory } from 'vue-router'
import Login       from '../views/Login.vue'
import OrderEntry  from '../views/OrderEntry.vue'
import PrintQueue  from '../views/PrintQueue.vue'
import Bills       from '../views/Bills.vue'
import Products    from '../views/Products.vue'
import Brands      from '../views/Brands.vue'
import Stores      from '../views/Stores.vue'
import Users       from '../views/Users.vue'
import { useAuthStore } from '../stores/auth'

// meta.admin=true 的路由仅管理员可进；录单/打印员工也能用
const routes = [
  { path: '/login',    component: Login, meta: { public: true } },
  { path: '/',         component: OrderEntry },
  { path: '/print',    component: PrintQueue },
  { path: '/bills',    component: Bills,    meta: { admin: true } },
  { path: '/products', component: Products, meta: { admin: true } },
  { path: '/brands',   component: Brands,   meta: { admin: true } },
  { path: '/stores',   component: Stores,   meta: { admin: true } },
  { path: '/users',    component: Users,    meta: { admin: true } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 全局守卫：未登录跳登录页；管理员专属页员工访问时打回录单页
router.beforeEach(async (to) => {
  const authStore = useAuthStore()

  if (to.meta.public) {
    // 已登录再访问登录页，直接回首页
    if (authStore.isLoggedIn) return '/'
    return true
  }

  if (!authStore.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  // 刷新后 user 尚未加载，先拉一次当前用户
  if (!authStore.user) {
    await authStore.fetchMe()
    if (!authStore.isLoggedIn) {
      return { path: '/login', query: { redirect: to.fullPath } }
    }
  }

  if (to.meta.admin && !authStore.isAdmin) {
    return '/'
  }

  return true
})

export default router
