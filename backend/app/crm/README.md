# CRM module

## B3 scope

The CRM foundation contains three core aggregates:

- `Customer`: a company-owned account/contact record.
- `Lead`: a sales opportunity that can optionally point to a customer and a responsible user.
- `Interaction`: a timestamped activity attached to exactly one customer or lead.

All records are tenant-scoped through `company_id`. API access is protected by RBAC permissions and mutations emit audit events.

## API

- `GET/POST /api/v1/crm/customers`
- `GET/PATCH /api/v1/crm/customers/{customer_id}`
- `GET/POST /api/v1/crm/leads`
- `GET/PATCH /api/v1/crm/leads/{lead_id}`
- `GET/POST /api/v1/crm/interactions`

Filtering and pagination are intentionally simple in B3. Search, segmentation, activities timeline, pipeline analytics and scoring belong to later CRM milestones.
