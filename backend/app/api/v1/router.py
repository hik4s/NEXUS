from fastapi import APIRouter
from app.api.v1.routes import order_imports

from app.api.v1.routes import async_processing, platform, audit, auth, companies, crm, finance, health, inventory, logistics, procurement, products, sales, users, workflow, integrations, intelligence

api_router = APIRouter()
api_router.include_router(order_imports.router, tags=['order-imports'])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(health.router, tags=["health"])
api_router.include_router(companies.router, tags=["companies"])
api_router.include_router(products.router, tags=["products"])
api_router.include_router(users.router, tags=["users"])
api_router.include_router(audit.router, tags=["audit"])
api_router.include_router(crm.router, tags=["crm"])
api_router.include_router(sales.router, tags=["sales"])
api_router.include_router(inventory.router, tags=["inventory"])
api_router.include_router(procurement.router, tags=["procurement"])
api_router.include_router(finance.router, tags=["finance"])
api_router.include_router(logistics.router, tags=["logistics"])

api_router.include_router(workflow.router, tags=["workflow"])

api_router.include_router(platform.router, tags=["platform"])
api_router.include_router(async_processing.router, tags=["async-processing"])
api_router.include_router(integrations.router, tags=["integrations"])
api_router.include_router(intelligence.router, tags=["intelligence"])


# Exact paths and methods keep new legacy endpoints out of the public MVP.
PORTFOLIO_ROUTES = {
    '/auth/register': {'POST'}, '/auth/login': {'POST'}, '/auth/refresh': {'POST'}, '/auth/me': {'GET'},
    '/health': {'GET'}, '/health/ready': {'GET'},
    '/companies/me': {'GET'}, '/companies/{company_id}': {'GET'},
    '/companies/{company_id}/products': {'GET', 'POST'},
    '/users': {'GET', 'POST'}, '/users/roles': {'GET'}, '/users/{user_id}': {'PATCH'},
    '/audit-logs': {'GET'},
    '/crm/customers': {'GET', 'POST'}, '/crm/customers/{customer_id}': {'GET', 'PATCH'},
    '/sales/orders': {'GET', 'POST'}, '/sales/orders/{order_id}': {'GET'},
    '/sales/orders/{order_id}/status': {'PATCH'},
    '/inventory/warehouses': {'GET', 'POST'}, '/inventory/stock': {'GET'}, '/inventory/movements': {'GET', 'POST'},
    '/finance/accounts': {'GET'}, '/finance/receivables': {'GET'},
    '/finance/payables': {'GET'}, '/finance/transactions': {'GET'}, '/finance/summary': {'GET'},
    '/order-imports': {'GET', 'POST'}, '/order-imports/{batch_id}': {'GET'},
    '/order-imports/{batch_id}/revalidate': {'POST'}, '/order-imports/{batch_id}/commit': {'POST'},
    '/order-imports/{batch_id}/errors.csv': {'GET'},
}


def create_api_router(profile: str) -> APIRouter:
    if profile not in {'full', 'portfolio'}:
        raise ValueError('Unknown application profile')
    if profile == 'full':
        return api_router
    result = APIRouter()
    for module in (auth, health, companies, products, users, audit, crm, sales, inventory, finance, order_imports):
        subset = APIRouter()
        subset.routes.extend(route for route in module.router.routes
            if route.path in PORTFOLIO_ROUTES and route.methods <= PORTFOLIO_ROUTES[route.path])
        result.include_router(subset)
    return result
