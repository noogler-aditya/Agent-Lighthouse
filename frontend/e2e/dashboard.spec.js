import { expect, test } from '@playwright/test';

async function loginViaApi(request, email, password) {
  const supabaseUrl = process.env.E2E_SUPABASE_URL || 'http://127.0.0.1:54321';
  const anonKey = process.env.E2E_SUPABASE_ANON_KEY || '';
  const response = await request.post(`${supabaseUrl}/auth/v1/token?grant_type=password`, {
    headers: {
      apikey: anonKey,
    },
    data: { email, password },
  });
  expect(response.ok()).toBeTruthy();
  return response.json();
}

async function loginViaUi(page, email, password) {
  await page.goto('/');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button', { name: /sign in/i }).click();
  await expect(page.getByText('Select a trace to begin')).toBeVisible();
}

test('dashboard loads traces, supports ws updates, and refreshes session', async ({ page, request }) => {
  const operatorEmail = process.env.E2E_OPERATOR_EMAIL || 'operator@example.com';
  const operatorPassword = process.env.E2E_OPERATOR_PASSWORD || 'operator-password';
  const viewerEmail = process.env.E2E_VIEWER_EMAIL || 'viewer@example.com';
  const viewerPassword = process.env.E2E_VIEWER_PASSWORD || 'viewer-password';

  const operator = await loginViaApi(request, operatorEmail, operatorPassword);
  const createTrace = await request.post('http://127.0.0.1:8000/api/traces', {
    headers: { Authorization: `Bearer ${operator.access_token}` },
    data: {
      name: `e2e-trace-${Date.now()}`,
      metadata: { source: 'playwright' },
    },
  });
  expect(createTrace.ok()).toBeTruthy();
  const trace = await createTrace.json();

  await loginViaUi(page, viewerEmail, viewerPassword);

  // Refresh list after trace creation and select trace for WS subscription.
  await page.reload();
  await expect(page.getByText(trace.name)).toBeVisible();
  await page.getByText(trace.name).click();
  await expect(page.getByText(/Live/i)).toBeVisible();

  const toolCard = page.locator('.metric-card', { hasText: 'Tool Calls' }).locator('.metric-value');
  await expect(toolCard).toHaveText('0');

  const createSpan = await request.post(`http://127.0.0.1:8000/api/traces/${trace.trace_id}/spans`, {
    headers: { Authorization: `Bearer ${operator.access_token}` },
    data: {
      name: 'e2e-tool-span',
      kind: 'tool',
      agent_name: 'Playwright Agent',
    },
  });
  expect(createSpan.ok()).toBeTruthy();

  await expect.poll(async () => {
    const traceResponse = await request.get(`http://127.0.0.1:8000/api/traces/${trace.trace_id}`, {
      headers: { Authorization: `Bearer ${operator.access_token}` },
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
