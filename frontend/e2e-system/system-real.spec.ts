import { expect, test } from '@playwright/test'

import { closeBookingDrawer, login, switchToList } from '../e2e/helpers'

/**
 * 系统测试：真实后端 + 真实 MySQL，覆盖登录、选座预约、取消、管理端看板。
 * 不使用浏览器内 MSW，也不冻结系统时间。
 */
test.describe('真实系统主流程', () => {
  test('学生登录并进入真实首页', async ({ page }) => {
    await login(page, 'student')

    await expect(page).toHaveURL(/\/student\/home$/)
    await expect(page.getByText(/你好，/).first()).toBeVisible()
    await expect(page.getByRole('menuitem', { name: '预约座位' })).toBeVisible()
  })

  test('学生预约明天座位并取消', async ({ page }) => {
    await login(page, 'student')
    await page.goto('/student/booking')

    const tomorrow = page.locator('.date-chip').filter({ hasText: '明天' }).first()
    await expect(tomorrow).toBeVisible()
    const available = page.waitForResponse(
      (response) =>
        response.url().includes('/reservations/available-seats') && response.ok(),
    )
    await tomorrow.click()
    await available
    await switchToList(page)

    const freeSeat = page
      .locator('.seat-map-list__chair:not([disabled])')
      .filter({ hasText: '可约' })
      .first()
    await expect(freeSeat).toBeVisible()
    await freeSeat.click()

    const submit = page.getByRole('button', { name: '提交预约', exact: true })
    await expect(submit).toBeEnabled()
    await submit.click()
    await expect(page.getByText('预约成功').first()).toBeVisible()
    await closeBookingDrawer(page)

    await page.getByRole('menuitem', { name: '我的预约', exact: true }).click()
    await page.waitForURL('**/student/reservations')

    const pendingRow = page
      .locator('tr')
      .filter({ hasText: '待使用' })
      .first()
    await expect(pendingRow).toBeVisible()
    await pendingRow.getByRole('button', { name: '取消', exact: true }).click()
    await page.getByRole('button', { name: '确认取消', exact: true }).click()

    await expect(page.getByText('预约已取消').first()).toBeVisible()
    await expect(
      page.locator('tr').filter({ hasText: '已取消' }).first(),
    ).toBeVisible()
  })

  test('管理员登录看板并进入预约管理', async ({ page }) => {
    await login(page, 'admin')

    await expect(page).toHaveURL(/\/admin\/dashboard$/)
    await expect(page.getByRole('heading', { name: '数据看板' })).toBeVisible()
    await expect(page.getByText('座位总数').first()).toBeVisible()

    await page.getByRole('menuitem', { name: '预约管理', exact: true }).click()
    await page.waitForURL('**/admin/reservations')
    await expect(page.getByRole('heading', { name: '预约管理' })).toBeVisible()
  })
})
