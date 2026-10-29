import axios from 'axios'
import { ElMessage } from 'element-plus'

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15_000,
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('ssr_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const message =
      error.response?.data?.message ?? error.response?.data?.detail ?? '请求失败，请稍后重试'

    if (status === 401) {
      localStorage.removeItem('ssr_token')
      localStorage.removeItem('ssr_user')
      if (window.location.pathname !== '/login') {
        window.location.href = '/login'
      }
    }

    ElMessage.error(message)
    return Promise.reject(error)
  },
)

export const http = {
  get<T>(url: string, params?: object) {
    return request.get<unknown, T>(url, { params })
  },
  post<T>(url: string, data?: unknown) {
    return request.post<unknown, T>(url, data)
  },
  patch<T>(url: string, data?: unknown) {
    return request.patch<unknown, T>(url, data)
  },
  delete<T>(url: string) {
    return request.delete<unknown, T>(url)
  },
}
