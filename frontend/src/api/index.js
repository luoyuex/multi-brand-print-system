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
}
