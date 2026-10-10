# B7 — Finance

## Scope

B7 introduces the operational finance layer of NEXUS. It is intentionally not an accounting/fiscal compliance engine yet.

### Delivered
- Financial accounts with opening/current balances.
- Accounts receivable linked to confirmed sales orders.
- Accounts payable linked to received purchase receipts.
- Partial and full payments.
- Manual income/expense transactions.
- Finance summary endpoint.
- Finance RBAC (`finance:read`, `finance:write`, `finance:pay`).
- Audit events for financial operations.
- Tenant isolation.
- Sales → receivable integration.
- Procurement receipt → payable integration.

## Business rules

1. A confirmed sales order creates one receivable for its total.
2. A purchase receipt creates one payable for the received amount.
3. Partial payments are supported.
4. A fully paid receivable/payable cannot receive another payment.
5. Expenses cannot exceed the selected financial account balance.
6. A confirmed sale with received money cannot be cancelled.
7. Overdue status is derived from due date when the item is not settled or cancelled.

## Deliberate non-goals

- Formal double-entry accounting.
- Brazilian tax/fiscal compliance.
- Bank reconciliation.
- Inventory valuation / CMV calculation.
- Invoicing/NF-e integration.

These are later milestones and should not be mixed into the first operational finance layer.
