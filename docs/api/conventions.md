# API conventions

Base path: `/api/v1`

Use nouns for resources and HTTP semantics for operations.

Example:

- `GET /api/v1/products`
- `GET /api/v1/products/{product_id}`
- `POST /api/v1/products`
- `PATCH /api/v1/products/{product_id}`
- `DELETE /api/v1/products/{product_id}`

Errors should eventually use a consistent envelope. Validation belongs at the API boundary; business rules belong in services/domain logic.
