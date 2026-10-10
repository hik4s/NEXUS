# Procurement domain

B6 introduces supplier management, supplier-product sourcing data, purchase orders and purchase receipts.

Core flow:

```text
Supplier
   ↓
Purchase Order (draft)
   ↓ submit
submitted
   ↓ approve
approved
   ↓ receive
partially_received → received
   ↓
Inventory receipt movement
   ↓
Product reference cost update
```

Partial receiving is supported. A receipt can contain a subset of purchase-order items and quantities; stock is increased only by the quantity physically received.

The product `cost` field is treated as the current reference cost. This is intentionally **not** a formal accounting inventory valuation method yet; FIFO/weighted-average/accounting valuation belongs to the future Finance domain.
