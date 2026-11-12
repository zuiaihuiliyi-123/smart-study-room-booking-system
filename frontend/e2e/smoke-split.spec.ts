import { expect, test } from '@playwright/test'

import { FIXED_TIME, login } from './helpers'

test.beforeEach(async ({ page }) => {
  await page.clock.setFixedTime(FIXED_TIME)
})

test('管理员用户管理与审计日志可渲染', async ({ page }) => {
  await login(page, 'admin')

  await page.goto('/admin/users')
  await expect(page.getByRole('heading', { name: '用户管理' })).toBeVisible()
  await expect(page.getByText('姓名 / 学号').first()).toBeVisible()
  await expect(page.getByRole('table').first()).toBeVisible({ timeout: 15_000 })

  await page.goto('/admin/audit')
  await expect(page.getByRole('heading', { name: '审计日志' })).toBeVisible()
  await expect(page.getByText('操作类型').first()).toBeVisible()
  await expect(page.getByRole('table').first()).toBeVisible({ timeout: 15_000 })
})
