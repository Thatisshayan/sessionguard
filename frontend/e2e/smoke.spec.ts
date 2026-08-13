import { test, expect } from '@playwright/test'

test.describe('SessionGuard Desktop E2E Smoke Suite', () => {
  test('Application Shell loads and navigates to Dashboard', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/SessionGuard/i)
    await expect(page.getByText('SessionGuard').first()).toBeVisible()
    await expect(page.getByRole('link', { name: /Dashboard/i }).first()).toBeVisible()
  })

  test('Sidebar Navigation routes to Sessions and Settings', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('link', { name: /Sessions/i }).first().click()
    await expect(page).toHaveURL(/\/sessions/)

    await page.getByRole('link', { name: /Settings/i }).first().click()
    await expect(page).toHaveURL(/\/settings/)
  })
})
