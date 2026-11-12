/**
 * 主题（浅色 / 暗色）状态、记忆与切换动画。
 *
 * 分工（改的时候要一起看）：
 * - `frontend/index.html` 里的内联脚本负责**首屏防闪**：在样式加载前就把 data-theme / class 写好；
 * - 本文件负责**运行期切换**、记忆与过渡动画。
 * 两处共用存储键 `ssr_theme`，改一处必须同步另一处。
 *
 * 切换动画有两级降级：
 * 1. 支持 View Transitions 的浏览器（Chromium 系）→ 整页交叉淡入，图表画布也在快照里；
 * 2. 其余浏览器 → 临时给 <html> 挂 `.ssr-theme-transition`，走 index.scss 第 11 节的颜色过渡；
 * 3. 系统开启「减少动态效果」时不加任何过渡，直接切换。
 */
import { computed, ref } from 'vue'

export type ThemeMode = 'light' | 'dark'

const STORAGE_KEY = 'ssr_theme'
const DEFAULT_THEME: ThemeMode = 'light'
/** 过渡总时长，与 index.scss 第 11 节的 transition / view-transition 动画保持一致 */
const TRANSITION_MS = 280
const TRANSITION_CLASS = 'ssr-theme-transition'

/** View Transitions 在各浏览器实现进度不一，用一个结构类型做运行时探测（TS 自带声明与本项目 lib 版本有出入） */
interface ViewTransitionHost {
  startViewTransition?: (callback: () => void) => unknown
}

function viewTransitionHost(): ViewTransitionHost | null {
  if (typeof document === 'undefined') return null
  const host = document as unknown as ViewTransitionHost
  return typeof host.startViewTransition === 'function' ? host : null
}

function readStoredTheme(): ThemeMode {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    if (stored === 'light' || stored === 'dark') return stored
  } catch {
    // 隐私模式 / 存储被禁用：用默认值，不影响页面
  }
  return DEFAULT_THEME
}

function prefersReducedMotion(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

/** 浏览器是否会用整页交叉淡入来过渡主题（图表画布也会一起被淡入淡出） */
export function supportsViewTransition(): boolean {
  return viewTransitionHost() !== null && !prefersReducedMotion()
}

/** 是否允许播放切主题的动画（给图表容器判断要不要做透明度呼吸） */
export function themeMotionAllowed(): boolean {
  return !prefersReducedMotion()
}

/** 主题是模块级单例：顶栏开关、图表、任何页面读到的都是同一份状态 */
const mode = ref<ThemeMode>(readStoredTheme())
let transitionTimer = 0

function paint(root: HTMLElement, next: ThemeMode): void {
  root.classList.toggle('dark', next === 'dark')
  root.dataset.theme = next
  root.style.colorScheme = next
}

/** 直接把当前主题落到 <html>（启动时调用，不带动画，避免首屏闪一下过渡） */
export function initTheme(): void {
  paint(document.documentElement, mode.value)
}

function runSwitch(root: HTMLElement, next: ThemeMode): void {
  mode.value = next
  paint(root, next)
}

function switchWithAnimation(root: HTMLElement, next: ThemeMode): void {
  const host = viewTransitionHost()
  if (host?.startViewTransition && themeMotionAllowed()) {
    try {
      host.startViewTransition(() => runSwitch(root, next))
      return
    } catch {
      // 上一次过渡还没结束等异常场景：退回下面的颜色过渡
    }
  }
  if (!themeMotionAllowed()) {
    runSwitch(root, next)
    return
  }
  // 先挂过渡类、再改令牌，浏览器会按新的计算样式做补间；过渡结束就摘掉，避免常驻影响 hover
  window.clearTimeout(transitionTimer)
  root.classList.add(TRANSITION_CLASS)
  runSwitch(root, next)
  transitionTimer = window.setTimeout(() => {
    root.classList.remove(TRANSITION_CLASS)
  }, TRANSITION_MS + 60)
}

export function setTheme(next: ThemeMode): void {
  try {
    localStorage.setItem(STORAGE_KEY, next)
  } catch {
    // 存不下也不影响本次切换
  }
  if (next === mode.value) return
  switchWithAnimation(document.documentElement, next)
}

export function toggleTheme(): void {
  setTheme(mode.value === 'dark' ? 'light' : 'dark')
}

export function useTheme() {
  return {
    mode,
    isDark: computed(() => mode.value === 'dark'),
    setTheme,
    toggleTheme,
  }
}
