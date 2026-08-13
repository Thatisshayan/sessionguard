import { test, expect } from '@playwright/test';

test.describe('Login page', () => {
  test('renders login form with default credentials', async ({ page }) => {
    await page.goto('/login');
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

test.describe('Dashboard Shell', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
  });

  test('shows application title and loading or dashboard state', async ({ page }) => {
    await expect(page.getByText('SessionGuard').first()).toBeVisible();
  });

  test('sidebar shows main navigation links', async ({ page }) => {
    await expect(page.getByRole('link', { name: /Dashboard/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Sessions/i }).first()).toBeVisible();
    await expect(page.getByRole('link', { name: /Upload/i }).first()).toBeVisible();
  });

  test('clicking Sessions link navigates to /sessions', async ({ page }) => {
    await page.getByRole('link', { name: /Sessions/i }).first().click();
    await expect(page).toHaveURL(/\/sessions/);
  });

  test('clicking Settings link navigates to /settings', async ({ page }) => {
    await page.getByRole('link', { name: /Settings/i }).first().click();
    await expect(page).toHaveURL(/\/settings/);
  });
});

test.describe('Theme & Shell', () => {
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
