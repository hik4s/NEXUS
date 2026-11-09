import { test, expect } from '@playwright/test';
import type { Page, APIRequestContext } from '@playwright/test';
import { fileURLToPath } from 'node:url';
import { join } from 'node:path';

const API = 'http://127.0.0.1:8811/api/v1';
const password = process.env.NEXUS_DEMO_PASSWORD!;
const screenshots = process.env.NEXUS_CAPTURE_DIR || fileURLToPath(new URL('../test-results/screenshots/', import.meta.url));
async function login(page: Page, email = 'gestor.aurora@example.com') {
  await page.getByLabel('E-mail', { exact: true }).fill(email);
  await page.getByLabel('Senha', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Entrar no workspace' }).click();
  await expect(page.getByRole('heading', { name: 'Visão geral', exact: true })).toBeVisible();
}
async function auth(request: APIRequestContext, email: string) {
  const response = await request.post(`${API}/auth/login`, { data: { email, password } });
  expect(response.ok()).toBeTruthy(); const data = await response.json();
  return { Authorization: `Bearer ${data.access_token}` };
}
async function navigate(page: Page, name: string) { await page.getByRole('navigation', { name: 'Navegação principal' }).getByRole('link', { name, exact: true }).click(); }

test('duas empresas: importar, revisar, confirmar, cancelar e recuperar a sessão com segurança', async ({ page, request }) => {
  const errors: string[] = []; page.on('pageerror', error => errors.push(error.message));
  const aurora = await auth(request, 'gestor.aurora@example.com');
  const horizonte = await auth(request, 'admin.horizonte@example.com');
  const initial = await (await request.get(`${API}/inventory/stock`, { headers: aurora })).json();
  const starting = initial.find((row: { product_sku: string }) => row.product_sku === 'PROD-A');
  await page.goto('/'); await login(page);
  await navigate(page, 'Importações');
  const ref = `E2E-${Date.now()}`;
  await page.locator('input[type=file]').setInputFiles({ name: 'pedidos-e2e.csv', mimeType: 'text/csv', buffer: Buffer.from(`external_order_id,sku,quantity\n${ref},PROD-A,2\n${ref}-ERRO,SKU-INEXISTENTE,1\n`) });
  await page.getByRole('button', { name: 'Revisar arquivo', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'pedidos-e2e.csv', exact: true })).toBeVisible();
  await expect(page.getByRole('checkbox', { name: `Selecionar ${ref}-ERRO`, exact: true })).toBeDisabled();
  await expect(page.getByText(/SKU não encontrado/)).toBeVisible();
  await page.screenshot({ path: join(screenshots, 'ui-import-review.png'), fullPage: true });
  const batchId = page.url().split('/imports/')[1];
  await page.getByRole('checkbox', { name: `Selecionar ${ref}`, exact: true }).check();
  await page.getByRole('button', { name: 'Gerar 1 rascunho', exact: true }).click();
  await expect(page.getByRole('status')).toContainText('1 rascunho disponível');
  const batch = await (await request.get(`${API}/order-imports/${batchId}`, { headers: aurora })).json();
  const orderId = batch.entries.find((entry: { external_order_id: string }) => entry.external_order_id === ref).sales_order_id;
  const draftStock = await (await request.get(`${API}/inventory/stock`, { headers: aurora })).json();
  expect(draftStock.find((row: { product_sku: string }) => row.product_sku === 'PROD-A').quantity).toBe(starting.quantity);
  const beforeAR = await (await request.get(`${API}/finance/receivables`, { headers: aurora })).json();
  expect(beforeAR.filter((row: { sales_order_id: string }) => row.sales_order_id === orderId)).toHaveLength(0);
  await page.getByRole('link', { name: `Abrir pedido ${ref}`, exact: true }).click();
  await expect(page.getByRole('heading', { name: /^ORD-/ })).toBeVisible();
  await page.getByLabel('Depósito de saída').selectOption(starting.warehouse_id);
  await page.getByLabel('Prazo para recebimento (dias)').fill('30');
  await page.getByRole('button', { name: 'Confirmar venda', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirmar operação' }).click();
  await expect(page.getByRole('status')).toContainText('Venda confirmada');
  await expect(page.locator('.order-status')).toContainText('Confirmado');
  const stock = await (await request.get(`${API}/inventory/stock`, { headers: aurora })).json();
  expect(stock.find((row: { product_sku: string }) => row.product_sku === 'PROD-A').quantity).toBe(starting.quantity - 2);
  const rows = await (await request.get(`${API}/finance/receivables`, { headers: aurora })).json();
  const ar = rows.filter((row: { sales_order_id: string }) => row.sales_order_id === orderId);
  expect(ar).toHaveLength(1); expect(Number(ar[0].amount)).toBe(65.8);
  await page.screenshot({ path: join(screenshots, 'ui-order-confirmed.png'), fullPage: true });
  await page.getByRole('button', { name: 'Cancelar pedido', exact: true }).click();
  await page.getByRole('dialog').getByRole('button', { name: 'Confirmar operação' }).click();
  await expect(page.getByRole('status')).toContainText('Pedido cancelado');
  const afterStock = await (await request.get(`${API}/inventory/stock`, { headers: aurora })).json();
  expect(afterStock.find((row: { product_sku: string }) => row.product_sku === 'PROD-A').quantity).toBe(starting.quantity);
  const afterAR = await (await request.get(`${API}/finance/receivables`, { headers: aurora })).json();
  expect(afterAR.find((row: { sales_order_id: string }) => row.sales_order_id === orderId).status).toBe('cancelled');
  expect((await request.get(`${API}/sales/orders/${orderId}`, { headers: horizonte })).status()).toBe(404);
  expect((await request.get(`${API}/order-imports/${batchId}`, { headers: horizonte })).status()).toBe(404);
  await navigate(page, 'Visão geral'); await expect(page.getByRole('heading', { name: 'Pedidos recentes' })).toBeVisible();
  await page.screenshot({ path: join(screenshots, 'ui-overview.png'), fullPage: true });
  expect(await page.evaluate(() => Object.keys(localStorage))).not.toContain('nexus_token');
  await page.getByLabel('Menu da sessão').click(); await page.getByRole('button', { name: 'Sair do workspace' }).click();
  await login(page, 'admin.horizonte@example.com');
  await page.goto(`/#/orders/${orderId}`); await expect(page.getByRole('alert')).toContainText('não está disponível nesta empresa');
  await page.reload(); await expect(page.getByRole('button', { name: 'Entrar no workspace' })).toBeVisible();
  expect(errors).toEqual([]);
});

test('mobile: navegação por teclado e páginas sem transbordamento horizontal', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 }); await page.goto('/');
  await page.screenshot({ path: join(screenshots, 'ui-login-mobile.png'), fullPage: true });
  await page.getByLabel('E-mail', { exact: true }).fill('gestor.aurora@example.com');
  await page.getByLabel('Senha', { exact: true }).fill(password); await page.getByLabel('Senha', { exact: true }).press('Enter');
  await expect(page.getByRole('heading', { name: 'Visão geral', exact: true })).toBeVisible();
  for (const [link, heading] of [['Visão geral', 'Visão geral'], ['Importações', 'Importações'], ['Pedidos', 'Pedidos de venda'], ['Catálogo', 'Catálogo e preparação'], ['Estoque', 'Estoque'], ['Recebíveis', 'Recebíveis'], ['Auditoria', 'Auditoria']]) {
    await navigate(page, link); await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
    await expect(page.getByRole('status').filter({ hasText: 'Carregando dados' })).toHaveCount(0);
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
  }
  await navigate(page, 'Visão geral'); await page.screenshot({ path: join(screenshots, 'ui-overview-mobile.png'), fullPage: true });
});
