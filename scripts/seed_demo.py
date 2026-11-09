"""Explicit, idempotent provisioning for dedicated demonstration databases."""
import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'backend'))

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.models.company import Company
from app.models.inventory import StockBalance
from app.models.product import Product
from app.models.user import User
from app.rbac.service import ensure_rbac_seed, user_has_permission
from app.schemas.auth import RegisterRequest
from app.schemas.inventory import StockMovementCreate, WarehouseCreate
from app.schemas.product import ProductCreate
from app.schemas.user import UserCreateRequest
from app.services.auth_service import register_owner
from app.services.inventory_service import create_movement, create_warehouse, list_warehouses
from app.services.product_service import create_product
from app.services.user_service import create_company_user

COMPANIES = [
    ('aurora-demo', 'Aurora Comércio · Demo', 'admin.aurora@example.com', 'gestor.aurora@example.com', 'manager'),
    ('horizonte-demo', 'Horizonte Atacado · Demo', 'admin.horizonte@example.com', 'operador.horizonte@example.com', 'employee'),
]
PRODUCTS = [('PROD-A', 'Café especial 250g', '32.90', '18.70', 120),
            ('PROD-B', 'Filtro de papel · 100 un.', '14.50', '7.00', 80),
            ('PROD-C', 'Caneca cerâmica', '39.00', '22.00', 45)]


def validate_environment(confirm: bool) -> str:
    if os.environ.get('APP_ENV') not in {'demo', 'test'}:
        raise ValueError('APP_ENV must explicitly be demo or test; never run this against production')
    if not confirm:
        raise ValueError('--confirm-demo is required for a dedicated demo database')
    password = os.environ.get('NEXUS_DEMO_PASSWORD', '')
    if len(password) < 12:
        raise ValueError('Set NEXUS_DEMO_PASSWORD to a dedicated password of at least 12 characters')
    if not os.environ.get('DATABASE_URL'):
        raise ValueError('Set DATABASE_URL explicitly to a dedicated demonstration database')
    return password


def seed_demo(db: Session, password: str) -> list[dict]:
    ensure_rbac_seed(db)
    result = []
    for slug, name, admin_email, member_email, member_role in COMPANIES:
        company = db.scalar(select(Company).where(Company.slug == slug))
        if company is None:
            owner, _, _ = register_owner(db, RegisterRequest(company_name=name, company_slug=slug,
                full_name='Admin Aurora' if slug == 'aurora-demo' else 'Admin Horizonte',
                email=admin_email, password=password))
            company = db.get(Company, owner.company_id)
        else:
            if company.name != name:
                raise ValueError('Demo slug is already in use by a different company; refusing to modify it')
            owner = db.scalar(select(User).where(User.email == admin_email, User.company_id == company.id))
            if owner is None or not owner.is_active or not user_has_permission(db, owner.id, 'roles:manage'):
                raise ValueError('Demo administrator is missing/inactive or no longer privileged; manual review required')
        member = db.scalar(select(User).where(User.email == member_email))
        if member is None:
            create_company_user(db, owner, UserCreateRequest(full_name='Gestor Aurora' if member_role == 'manager' else 'Operador Horizonte',
                email=member_email, password=password, role_keys=[member_role]))
        elif member.company_id != company.id:
            raise ValueError('Demo email already belongs to another company; refusing to modify it')
        warehouses = list_warehouses(db, company.id)
        warehouse = next((row for row in warehouses if row.code == 'PRINCIPAL'), None)
        if warehouse is None:
            warehouse = create_warehouse(db, owner, WarehouseCreate(name='Depósito principal', code='PRINCIPAL'))
        for sku, product_name, price, cost, quantity in PRODUCTS:
            product = db.scalar(select(Product).where(Product.company_id == company.id, Product.sku == sku))
            if product is None:
                product = create_product(db, company.id, ProductCreate(name=product_name, sku=sku, price=price, cost=cost))
            balance = db.scalar(select(StockBalance).where(StockBalance.company_id == company.id,
                StockBalance.product_id == product.id, StockBalance.warehouse_id == warehouse.id))
            if balance is None:
                create_movement(db, owner, StockMovementCreate(warehouse_id=warehouse.id, product_id=product.id,
                    movement_type='receipt', quantity=quantity, notes='Saldo inicial da demonstração NEXUS'))
        result.append({'company': slug, 'admin': admin_email, 'member': member_email, 'member_role': member_role})
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--confirm-demo', action='store_true')
    args = parser.parse_args()
    try:
        password = validate_environment(args.confirm_demo)
        with Session(engine) as db:
            result = seed_demo(db, password)
        print(json.dumps({'demo_companies': result}, ensure_ascii=False))
    except ValueError as error:
        parser.exit(2, f'{error}\n')


if __name__ == '__main__':
    main()
