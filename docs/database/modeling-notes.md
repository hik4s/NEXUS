# Database modeling notes

The first domains are Identity, CRM, Sales, Inventory, Procurement, Finance, Logistics and Workflow.

Modeling rules:

- Prefer normalized transactional data.
- Add constraints that encode invariants.
- Add indexes based on access patterns.
- Use explicit foreign keys and deletion behavior.
- Keep historical/audit data where business traceability matters.
- Use migrations for every schema change.
