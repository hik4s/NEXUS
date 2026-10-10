from fastapi import APIRouter

from app.api.v1.routes import async_processing, platform, audit, auth, companies, crm, finance, health, inventory, logistics, procurement, products, sales, users, workflow, integrations, intelligence

api_router = APIRouter()
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
