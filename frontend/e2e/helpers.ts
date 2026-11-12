import { expect, type Page } from '@playwright/test'

/** 固定浏览器时间：让种子数据、默认预约时段与签到窗口完全可复现。 */
export const FIXED_TIME = new Date('2026-11-12T10:00:00+08:00')

export type DemoRole = 'student' | 'admin'

const DEMO = {
  student: { studentNo: 'student', password: 'student123', home: '/student/home' },
  admin: { studentNo: 'admin', password: 'admin123', home: '/admin/dashboard' },
} as const

/** 统一登录入口（MSW 演示账号）。 */
export async function login(page: Page, role: DemoRole = 'student'): Promise<void> {
  const account = DEMO[role]
  await page.goto('/login')
  await page.getByPlaceholder('请输入学号或工号').fill(account.studentNo)
  await page.getByPlaceholder('请输入密码').fill(account.password)
  await page.getByRole('button', { name: '登录', exact: true }).click()
  await page.waitForURL(`**${account.home}`)
}

/** 切到无障碍列表视图（日期/筛选变化后地图组件会重建回地图视图，需要重新切换）。 */
export async function switchToList(page: Page): Promise<void> {
  await expect(page.getByRole('button', { name: '列表' })).toBeVisible({ timeout: 15_000 })
  await page.getByRole('button', { name: '列表' }).click()
  await expect(page.locator('.seat-map-list__chair').first()).toBeVisible({ timeout: 15_000 })
}

/** 打开预约页并切到列表视图，返回列表里第一个可约座位按钮。 */
export async function openBookingList(page: Page) {
  await page.goto('/student/booking')
  await switchToList(page)
  const freeSeat = page
    .locator('.seat-map-list__chair:not([disabled])')
    .filter({ hasText: '可约' })
    .first()
  await expect(freeSeat).toBeVisible({ timeout: 15_000 })
  return freeSeat
}

/** 选择“今天 / 明天”并等待新的可预约座位返回。 */
export async function pickDate(page: Page, label: '今天' | '明天'): Promise<void> {
  const response = page.waitForResponse(
    (res) => res.url().includes('/reservations/available-seats') && res.ok(),
  )
  await page.locator('.date-chip').filter({ hasText: label }).first().click()
  await response
  await switchToList(page)
}

export interface BookedSeat {
  seatLabel: string
  reserveDate: string
  /** 预约开始时间 HH:mm，用于推进浏览器时钟进入签到窗口 */
  startTime: string
}

/** 预约第一个可约座位并提交；返回座位标签，便于后续在列表中定位。 */
export async function bookFirstFreeSeat(
  page: Page,
  date: '今天' | '明天' = '今天',
): Promise<BookedSeat> {
  await openBookingList(page)
  if (date !== '今天') await pickDate(page, date)

  const target = page
    .locator('.seat-map-list__chair:not([disabled])')
    .filter({ hasText: '可约' })
    .first()
  await expect(target).toBeVisible({ timeout: 15_000 })
  const seatLabel = (await target.getAttribute('aria-label')) ?? ''
  await target.click()

  const submit = page.getByRole('button', { name: '提交预约', exact: true })
  await expect(submit).toBeVisible()
  await expect(submit).toBeEnabled()
  await submit.click()
  await expect(page.getByText('预约成功').first()).toBeVisible()

  // 成功提示里包含日期：`2026-11-12 10:05–12:05`
  const dateText = date === '明天' ? '2026-11-13' : '2026-11-12'
  await expect(page.getByText(dateText).first()).toBeVisible()

  const drawerText = await page
    .locator('.el-drawer')
    .filter({ hasText: dateText })
    .first()
    .textContent({ timeout: 5_000 })
  const startTime = drawerText?.match(/\d{4}-\d{2}-\d{2} (\d{2}:\d{2})–/)?.[1] ?? '10:05'

  return { seatLabel, reserveDate: dateText, startTime }
}

/** 通过左侧菜单进入“我的预约”，避免整页刷新把 MSW 内存数据重置掉。 */
export async function gotoMyReservations(page: Page): Promise<void> {
  await page.getByRole('menuitem', { name: '我的预约', exact: true }).click()
  await page.waitForURL('**/student/reservations')
  await expect(page.getByRole('heading', { name: '我的预约' })).toBeVisible()
}

/** 关闭预约详情抽屉（非模态）。 */
export async function closeBookingDrawer(page: Page): Promise<void> {
  const close = page.getByRole('button', { name: '关闭', exact: true })
  if (await close.isVisible().catch(() => false)) await close.click()
}
