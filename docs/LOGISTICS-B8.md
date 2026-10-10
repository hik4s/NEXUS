# B8 — Logistics

## Scope
- Drivers and vehicles
- Delivery lifecycle
- Driver/vehicle assignment
- Delivery routes and ordered stops
- Tracking timeline
- Proof of delivery
- Tenant isolation
- RBAC and audit

## Delivery lifecycle
`pending -> assigned -> in_transit -> delivered`

Alternative paths:
- `pending -> cancelled`
- `assigned -> cancelled`
- `in_transit -> failed`
- `failed -> assigned`
- `failed -> cancelled`

## Integration
`SalesOrder (confirmed) -> Warehouse Fulfillment -> Delivery -> Tracking -> Customer proof`

The current model intentionally keeps one delivery per sales order. Future phases can evolve this into split deliveries without changing the core tracking model.
