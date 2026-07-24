import axios from 'axios'

const TOKEN_KEY = 'auth_token'

export function getToken() {
  return localStorage.getItem(TOKEN_KEY)
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  else localStorage.removeItem(TOKEN_KEY)
}

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 请求拦截：带上登录令牌
http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// 响应拦截：统一错误提示（组件里按需 import ElMessage）
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const status = err.response?.status
    const msg = err.response?.data?.detail || '请求失败'
    // 401：登录失效，清 token 并跳登录（登录接口自身的 401 不跳，由页面提示）
    if (status === 401 && !err.config?.url?.includes('/auth/login')) {
      setToken(null)
      if (location.pathname !== '/login') {
        location.href = '/login'
      }
    }
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

export const authApi = {
  login:          (data) => http.post('/auth/login', data),
  me:             ()     => http.get('/auth/me'),
  changePassword: (data) => http.post('/auth/change-password', data),
  // 账号管理（仅管理员）
  listUsers:      ()          => http.get('/auth/users'),
  createUser:     (data)      => http.post('/auth/users', data),
  updateUser:     (id, data)  => http.put(`/auth/users/${id}`, data),
  removeUser:     (id)        => http.delete(`/auth/users/${id}`),
}

export const brandApi = {
  list: () => http.get('/brands/'),
  create: (data) => http.post('/brands/', data),
}

export const storeApi = {
  list: (params) => http.get('/stores/', { params }),
  create: (data) => http.post('/stores/', data),
  update: (id, data) => http.put(`/stores/${id}`, data),
  remove: (id) => http.delete(`/stores/${id}`),
}

export const productApi = {
  list: (params) => http.get('/products/', { params }),
  create: (data) => http.post('/products/', data),
  update: (id, data) => http.put(`/products/${id}`, data),
  remove: (id) => http.delete(`/products/${id}`),
}

export const orderApi = {
  list:   (params)   => http.get('/orders/', { params }),
  get:    (id)       => http.get(`/orders/${id}`),
  create: (data)     => http.post('/orders/', data),
  update: (id, data) => http.put(`/orders/${id}`, data),
  // 触发后端静默打印：成功出纸后订单才标记为已打印
  print:  (id)       => http.post(`/orders/${id}/print`),
  remove: (id)       => http.delete(`/orders/${id}`),
}

export const printApi = {
  printers:     ()        => http.get('/print/printers'),
  getConfig:    ()        => http.get('/print/config'),
  updateConfig: (data)    => http.put('/print/config', data),
  test:         (printer) => http.post('/print/test', { printer }),
  // 打印机状态（就绪/离线/缺纸/卡纸 + 队列任务数）
  status:       (printer) => http.get('/print/status', { params: printer ? { printer_name: printer } : {} }),
  // 一键批量打印：按 order_ids 顺序后台串行打印，返回批次初始快照（含 batch_id）
  batch:        (orderIds, printer) => http.post('/print/batch', { order_ids: orderIds, printer }),
  // 轮询兜底：取批次当前快照（SSE 不可用时降级用）
  batchSnapshot: (batchId) => http.get(`/print/batch/${batchId}`),
  // SSE 进度流地址（用 EventSource 直连，绕过 axios）：拼上 baseURL 前缀
  batchStreamUrl: (batchId) => `/api/print/batch/${batchId}/stream`,
}

export const billApi = {
  list:          (params)    => http.get('/bills/', { params }),
  get:           (id)        => http.get(`/bills/${id}`),
  // 预览某客户某账期未出账汇总（不落库）
  preview:       (data)      => http.post('/bills/preview', data),
  // 回款对账汇总：某客户某账期内所有订单（无视是否已出账）按天汇总，只读不落库
  summary:       (data)      => http.post('/bills/summary', data),
  // 生成账单（认领未出账订单）
  create:        (data)      => http.post('/bills/', data),
  // 编辑账单：改账期（重算明细）/ 备注
  update:        (id, data)  => http.patch(`/bills/${id}`, data),
  // 一键生成今日账单：每个有未出账订单的客户各出一张
  generateToday: ()          => http.post('/bills/generate-today'),
  markSent:      (id, value) => http.patch(`/bills/${id}/sent`, { value }),
  markPaid:      (id, value) => http.patch(`/bills/${id}/paid`, { value }),
  remove:        (id)        => http.delete(`/bills/${id}`),
  // 小票图片改为前端用 html2canvas 生成（见 BillReceipt.vue），不再走后端渲染
}
