import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 10000,
})

// 响应拦截：统一错误提示（组件里按需 import ElMessage）
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const msg = err.response?.data?.detail || '请求失败'
    console.error('[API Error]', msg)
    return Promise.reject(new Error(msg))
  }
)

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
  // 生成账单（认领未出账订单）
  create:        (data)      => http.post('/bills/', data),
  // 一键生成今日账单：每个有未出账订单的客户各出一张
  generateToday: ()          => http.post('/bills/generate-today'),
  markSent:      (id, value) => http.patch(`/bills/${id}/sent`, { value }),
  markPaid:      (id, value) => http.patch(`/bills/${id}/paid`, { value }),
  remove:        (id)        => http.delete(`/bills/${id}`),
  // 小票图片直链：<img :src> 用；带 t 参数在标记状态变化后强制刷新
  imageUrl:      (id, t)     => `/api/bills/${id}/image${t ? `?t=${t}` : ''}`,
  // 下载 PNG：走 axios 拿 blob，前端另存为带客户/账期的文件名
  downloadImage: (id)        => http.get(`/bills/${id}/image`, { responseType: 'blob' }),
}
