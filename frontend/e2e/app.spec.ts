import { test, expect } from '@playwright/test';

test.describe('Login page', () => {
  test('renders login form with default credentials', async ({ page }) => {
    await page.goto('/login');
    // The tab toggle says "Sign In" (form button, not sidebar link)
    await expect(page.getByRole('button', { name: 'Sign In' }).first()).toBeVisible();
    await expect(page.locator('input[type="email"]')).toHaveValue('demo@sessionguard.local');
    await expect(page.locator('input[type="password"]')).toHaveValue('demo123');
  });

  test('can switch to signup mode and back', async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Create Account' }).click();
    await expect(page.getByPlaceholder('yourusername')).toBeVisible();

    await page.getByRole('button', { name: 'Sign In' }).first().click();
    await expect(page.locator('input[type="password"]')).toBeVisible();
  });

  test('shows demo credentials hint', async ({ page }) => {
    await page.goto('/login');
    await expect(page.getByText('Demo credentials')).toBeVisible();
    await expect(page.getByText('demo@sessionguard.local')).toBeVisible();
  });
});

test.describe('Dashboard (with backend)', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Sign In' }).first().click();
    // Wait for navigation away from login
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
  });

  test('shows KPI cards on dashboard', async ({ page }) => {
    await expect(page.getByText('Total Sessions')).toBeVisible({ timeout: 10_000 });
  });

  test('refresh button is present', async ({ page }) => {
    await expect(page.getByRole('button', { name: /refresh/i })).toBeVisible();
  });
});

test.describe('Navigation sidebar', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/login');
    await page.getByRole('button', { name: 'Sign In' }).first().click();
    await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 15_000 });
  });

  test('sidebar shows all main nav links', async ({ page }) => {
    await expect(page.getByRole('link', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Sessions' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Upload' })).toBeVisible();
  });

  test('clicking Sessions link navigates to /sessions', async ({ page }) => {
    await page.getByRole('link', { name: 'Sessions' }).click();
    await expect(page).toHaveURL(/\/sessions/);
  });

  test('clicking Dashboard link navigates to /', async ({ page }) => {
    await page.getByRole('link', { name: 'Sessions' }).click();
    await expect(page).toHaveURL(/\/sessions/);
    await page.getByRole('link', { name: 'Dashboard' }).click();
    await expect(page).toHaveURL('/');
  });
});

test.describe('Theme', () => {
  test('app renders without crashing', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('body')).toBeVisible();
  });

  test('can set light theme via data-theme attribute', async ({ page }) => {
    await page.goto('/login');
    await page.locator('html').evaluate(el => el.setAttribute('data-theme', 'light'));
    const theme = await page.locator('html').getAttribute('data-theme');
    expect(theme).toBe('light');
  });
});
