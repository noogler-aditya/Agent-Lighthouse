import { expect, test } from '@playwright/test';

async function registerViaApi(request, username, password) {
  const response = await request.post('http://127.0.0.1:8000/api/auth/register', {
    data: { username, password },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function loginViaUi(page, username, password) {
  await page.goto('/');
  // Click 'Sign In' on the Landing Page navigation
  await page.getByRole('button', { name: 'Sign In' }).first().click();

  // Fill form inside AuthModal
  await page.getByPlaceholder('Enter your username').fill(username);
  await page.getByPlaceholder('••••••••').fill(password);

  // Click 'Sign In' inside the modal (submit button)
  await page.locator('.auth-form').getByRole('button', { name: 'Sign In' }).click();

  await expect(page.getByText('Select a trace to begin')).toBeVisible();
}

test('dashboard loads traces, supports ws updates, and refreshes session', async ({ page, request }) => {
  const username = `e2e_${Date.now()}_${crypto.randomUUID().slice(0, 8)}`;
  const password = 'e2e-password';
  const userSession = await registerViaApi(request, username, password);
  const createTrace = await request.post('http://127.0.0.1:8000/api/traces', {
    headers: { Authorization: `Bearer ${userSession.access_token}` },
    data: {
      name: `e2e-trace-${Date.now()}`,
      metadata: { source: 'playwright' },
    },
  });
  expect(createTrace.ok()).toBeTruthy();
  const trace = await createTrace.json();

  await loginViaUi(page, username, password);

  // Force an expired/invalid access token and verify refresh keeps session alive.
  await page.evaluate(() => {
    localStorage.setItem('lighthouse_access_token', 'invalid.token.value');
  });
  await page.reload();
  await expect(page.locator('.auth-card')).toHaveCount(0);

  // Refresh list after trace creation and select trace for WS subscription.
  await page.reload();
  await expect(page.getByText(trace.name)).toBeVisible();
  await page.getByText(trace.name).click();
  await expect(page.getByText(/Live/i)).toBeVisible();

  const toolCard = page.locator('.metric-card', { hasText: 'Tool Calls' }).locator('.metric-value');
  await expect(toolCard).toHaveText('0');

  const createSpan = await request.post(`http://127.0.0.1:8000/api/traces/${trace.trace_id}/spans`, {
    headers: { Authorization: `Bearer ${userSession.access_token}` },
    data: {
      name: 'e2e-tool-span',
      kind: 'tool',
      agent_name: 'Playwright Agent',
    },
  });
  expect(createSpan.ok()).toBeTruthy();

  await expect.poll(async () => {
    const traceResponse = await request.get(`http://127.0.0.1:8000/api/traces/${trace.trace_id}`, {
      headers: { Authorization: `Bearer ${userSession.access_token}` },
    });
    if (!traceResponse.ok()) return -1;
    const payload = await traceResponse.json();
    return payload.tool_calls || 0;
  }).toBe(1);

  await page.reload();
  await expect(page.getByText(trace.name)).toBeVisible();
  await page.getByText(trace.name).click();

  const refreshedToolCard = page.locator('.metric-card', { hasText: 'Tool Calls' }).locator('.metric-value');
  await expect(refreshedToolCard).toHaveText('1');

  await page.getByRole('button', { name: /state/i }).click();
  await expect(page.getByText('No state available')).toBeVisible();
  await expect(page.locator('.no-state .hint')).toContainText('State is captured when the agent is paused');
});
