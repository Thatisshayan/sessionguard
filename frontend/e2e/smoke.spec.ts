import { test, expect } from '@playwright/test'

test.describe('SessionGuard Desktop E2E Smoke Suite', () => {
  test('Application Shell loads and navigates to Dashboard', async ({ page }) => {
    await page.goto('/')
    await expect(page).toHaveTitle(/SessionGuard/i)
    await expect(page.getByText('SessionGuard')).toBeVisible()
    await expect(page.getByText('Dashboard')).toBeVisible()
  })

  test('Sidebar Navigation routes to Sessions and Settings', async ({ page }) => {
    await page.goto('/')
    await page.click('text=Sessions')
    await expect(page).toHaveURL(/\/sessions/)

    await page.click('text=Settings')
    await expect(page).toHaveURL(/\/settings/)
  })
})
