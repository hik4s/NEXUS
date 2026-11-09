export interface User { id: string; company_id: string; full_name: string; email: string; role: string; roles: string[] }
export interface Company { id: string; name: string; slug: string }
export interface Login { access_token: string; user: User }
export interface Product { id: string; name: string; sku: string; price: string; cost: string }
export interface Warehouse { id: string; name: string; code: string; is_active: boolean }
export interface Stock { warehouse_id: string; product_id: string; quantity: number; product_name: string; product_sku: string }
export interface Movement { id: string; product_id: string; warehouse_id: string; movement_type: string; quantity: number; balance_after: number; created_at: string }
export interface Customer { id: string; name: string; email: string | null; status: string }
export interface Issue { row: number; field: string | null; code: string; message: string }
export interface ImportItem { sku: string; quantity: number; row: number; unit_price?: string; product_name?: string; product_id?: string }
export interface ImportEntry { id: string; external_order_id: string; source_lines: number[]; normalized_items: ImportItem[]; errors: Issue[]; warnings: Issue[]; status: 'valid' | 'invalid' | 'committed' | 'duplicate'; sales_order_id: string | null }
export interface BatchSummary { id: string; filename: string; sha256: string; status: 'reviewed' | 'committed' | 'partially_committed'; created_at: string }
export interface Batch extends BatchSummary { unassigned_errors: Issue[]; entries: ImportEntry[] }
export interface CommitResult { batch_id: string; orders: { entry_id: string; order_id: string; reused: boolean }[] }
export interface OrderItem { id: string; product_id: string; product_name: string; product_sku: string; quantity: number; unit_price: string; total: string }
export interface Order { id: string; company_id: string; order_number: string; status: 'draft' | 'confirmed' | 'cancelled'; total: string; subtotal: string; created_at: string; items: OrderItem[]; fulfillment: { warehouse_id: string; status: string } | null }
export interface Receivable { id: string; sales_order_id: string | null; description: string; amount: string; paid_amount: string; due_date: string; status: string }
export interface FinanceSummary { total_cash: string; accounts_receivable_open: string; overdue_receivable: string }
export interface Audit { id: string; action: string; status: string; resource_type: string | null; created_at: string; metadata_json?: Record<string, unknown> }
export interface Page<T> { items: T[]; total: number; page: number; pageSize: number }
export const canOperate = (user: User) => user.roles.some(role => role === 'admin' || role === 'manager');
