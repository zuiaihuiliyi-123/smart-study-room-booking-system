import { expect, test } from '@playwright/test'

import {
  bookFirstFreeSeat,
  closeBookingDrawer,
  FIXED_TIME,
  gotoMyReservations,
  login,
  openBookingList,
} from './helpers'

test.beforeEach(async ({ page }) => {
  // 冻结“系统时间”，但不冻结定时器：seed、默认时段、签到窗口都基于 10:00
  await page.clock.setFixedTime(FIXED_TIME)
})

test('主流程 1：学生登录进入学习空间', async ({ page }) => {
  await login(page, 'student')

  await expect(page).toHaveURL(/\/student\/home$/)
  await expect(page.getByText(/你好，/).first()).toBeVisible()
  await expect(page.getByText('演示学生').first()).toBeVisible()
})

test('主流程 2：学生预约座位并提交成功', async ({ page }) => {
  await login(page, 'student')
  await openBookingList(page)

  const seat = page
    .locator('.seat-map-list__chair:not([disabled])')
    .filter({ hasText: '可约' })
    .first()
  await seat.click()

  await expect(page.getByRole('button', { name: '提交预约', exact: true })).toBeEnabled()
  await page.getByRole('button', { name: '提交预约', exact: true }).click()

  await expect(page.getByText('预约成功').first()).toBeVisible()
  await expect(page.getByText('签到时间：').first()).toBeVisible()
  await closeBookingDrawer(page)
})

test('主流程 3：学生取消明天的预约', async ({ page }) => {
  await login(page, 'student')
  const booked = await bookFirstFreeSeat(page, '明天')
  await closeBookingDrawer(page)

  await gotoMyReservations(page)
  const row = page
    .locator('tr')
    .filter({ hasText: booked.reserveDate })
    .filter({ hasText: '待使用' })
    .first()
  await expect(row).toBeVisible({ timeout: 15_000 })

  await row.getByRole('button', { name: '取消', exact: true }).click()
  await page.getByRole('button', { name: '确认取消', exact: true }).click()

  await expect(page.getByText('预约已取消').first()).toBeVisible()
  await expect(
    page
      .locator('tr')
      .filter({ hasText: booked.reserveDate })
      .filter({ hasText: '已取消' })
      .first(),
  ).toBeVisible()
})

test('主流程 4：学生签到后签退', async ({ page }) => {
  await login(page, 'student')
  const booked = await bookFirstFreeSeat(page, '今天')
  await closeBookingDrawer(page)

  // 把“当前时间”推进到预约时段内，使签到窗口 [开始−15, 开始+15) 处于打开状态
  const [hour, minute] = booked.startTime.split(':').map(Number)
  await page.clock.setFixedTime(new Date(2026, 10, 12, hour, minute, 0))
  await gotoMyReservations(page)

  const row = page
    .locator('tr')
    .filter({ hasText: booked.reserveDate })
    .filter({ hasText: '待使用' })
    .first()
  await expect(row).toBeVisible({ timeout: 15_000 })

  await row.getByRole('button', { name: '签到', exact: true }).click()
  await expect(page.getByText('签到成功').first()).toBeVisible()

  const inUseRow = page
    .locator('tr')
    .filter({ hasText: booked.reserveDate })
    .filter({ hasText: '使用中' })
    .first()
  await expect(inUseRow).toBeVisible({ timeout: 15_000 })
  await inUseRow.getByRole('button', { name: '签退', exact: true }).click()
  await expect(page.getByText('签退成功').first()).toBeVisible()
})

test('主流程 5：管理员临时关闭自习室', async ({ page }) => {
  await login(page, 'admin')
  await page.goto('/admin/rooms')

  const closeButtons = page.getByRole('button', { name: '临时关闭' })
  await expect(closeButtons.first()).toBeVisible({ timeout: 15_000 })
  await closeButtons.first().click()

  await expect(page.getByRole('heading', { name: /临时关闭 ·/ })).toBeVisible()
  await page
    .getByPlaceholder('如：线路检修，暂停开放（会写入审计日志）')
    .fill('E2E：线路检修，临时关闭')

  await page.getByRole('button', { name: '查询受影响预约' }).click()
  const execute = page.getByRole('button', { name: '确认执行关闭' })
  await expect(execute).toBeEnabled({ timeout: 15_000 })
  await execute.click()

  // ElMessageBox 二次确认
  await page.getByRole('button', { name: '确认执行', exact: true }).click()

  await expect(page.getByText(/已临时关闭/).first()).toBeVisible({ timeout: 15_000 })
})
