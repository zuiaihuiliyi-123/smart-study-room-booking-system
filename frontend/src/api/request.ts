import axios from 'axios'
import { ElMessage } from 'element-plus'

declare module 'axios' {
  interface AxiosRequestConfig {
    /**
     * 静默失败：拦截器不弹 `ElMessage`。
     * 用于**看板 10 秒轮询**这类后台刷新——失败由页面内联提示「更新失败，显示 mm:ss 的数据」，
     * 不能让每 10 秒一次的失败把屏幕刷满 toast（FR-053 / IR-004：失败保留上一次数据并提示）。
     */
    silent?: boolean
  }
}

/** 单次请求的可选行为：静默失败 / 取消信号（轮询组件卸载时用） */
export interface RequestOptions {
  silent?: boolean
  signal?: AbortSignal
}

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api/v1',
  timeout: 15_000,
})

request.interceptors.request.use((config) => {
  // 「记住我」时令牌在 localStorage，否则在 sessionStorage（关闭浏览器即失效）
  const token =
    localStorage.getItem('ssr_token') ?? sessionStorage.getItem('ssr_token') ?? ''
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 主动取消（切页 / 轮询停止）：静默上抛，不弹错误提示
    if (axios.isCancel?.(error) || error?.code === 'ERR_CANCELED' || error?.name === 'CanceledError') {
      return Promise.reject(error)
    }

    const status = error.response?.status
    const message =
      error.response?.data?.message ?? error.response?.data?.detail ?? '请求失败，请稍后重试'

    if (status === 401) {
      // 凭证已失效：两种存储都要清，避免残留令牌反复触发 401
      localStorage.removeItem('ssr_token')
      localStorage.removeItem('ssr_user')
      sessionStorage.removeItem('ssr_token')
      sessionStorage.removeItem('ssr_user')
      if (window.location.pathname !== '/login') {
        // 记住当前页面，登录后可回到原处（登录页已支持读取 redirect 参数）
        const back = encodeURIComponent(window.location.pathname + window.location.search)
        window.location.href = `/login?redirect=${back}`
      }
    }

    // 401 的跳转与清除凭据不受 silent 影响，只有提示需要静默
    if (!error.config?.silent) {
      ElMessage.error(message)
    }

    return Promise.reject(error)
  },
)

export const http = {
  get<T>(url: string, params?: object, options?: RequestOptions) {
    return request.get<unknown, T>(url, { params, ...options })
  },
  post<T>(url: string, data?: unknown) {
    return request.post<unknown, T>(url, data)
  },
  patch<T>(url: string, data?: unknown) {
    return request.patch<unknown, T>(url, data)
  },
  delete<T>(url: string, params?: object, options?: RequestOptions) {
    return request.delete<unknown, T>(url, { params, ...options })
  },
}
